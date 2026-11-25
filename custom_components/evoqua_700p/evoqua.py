"""Read-only Evoqua 700P Modbus TCP client (Python standard library only)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import math
import re
import struct


@dataclass(frozen=True)
class Channel:
    register: int
    label: str
    precision: int
    error_register: int | None = None


CHANNELS = {
    "chlorine": Channel(400100, "Chlor", 2, 400308),
    "ph": Channel(400115, "pH", 2, 400310),
    "orp": Channel(400130, "Redox", 0, 400312),
    "total_chlorine": Channel(400145, "Gesamtchlor", 2, 400314),
    "conductivity": Channel(400160, "Leitfähigkeit", 1, 400316),
    "temperature": Channel(400175, "Temperatur", 1),
    "circulation": Channel(400205, "Umwälzung", 1),
    "analog_input_2": Channel(400220, "Analogeingang 2", 2),
}
DEFAULT_CHANNELS = ["chlorine", "ph", "orp", "temperature"]
BYTE_ORDERS = ("ABCD", "CDAB", "BADC", "DCBA")


class EvoquaError(Exception):
    """Base communication or decoding error."""


class ModbusError(EvoquaError):
    """Modbus exception returned by the device."""

    def __init__(self, code: int, address: int) -> None:
        self.code = code
        self.address = address
        super().__init__(f"Modbus exception {code} at wire address {address}")


class InvalidDevice(EvoquaError):
    """The responding server could not be identified as a 700 P."""


@dataclass(frozen=True)
class Measurement:
    value: float | None
    unit: str | None


@dataclass(frozen=True)
class Snapshot:
    system_name: str
    software: str
    measurements: dict[str, Measurement]
    status: dict[int, int] = field(default_factory=dict)


def ordered_bytes(words: list[int], byte_order: str) -> bytes:
    """Convert a two-register value to canonical big endian bytes."""
    if byte_order not in BYTE_ORDERS or len(words) != 2:
        raise ValueError("Expected two registers and a valid byte order")
    raw = struct.pack(">HH", *words)
    return bytes(raw[byte_order.index(letter)] for letter in "ABCD")


def decode_float(words: list[int], byte_order: str = "ABCD") -> float | None:
    """Treat non-finite values as unavailable, never publish NaN or infinity."""
    value = struct.unpack(">f", ordered_bytes(words, byte_order))[0]
    return value if math.isfinite(value) else None


def decode_text(words: list[int]) -> str:
    """Text uses CP437 per the 700 P manual, independently of FLOAT order."""
    raw = struct.pack(f">{len(words)}H", *words)
    return raw.decode("cp437").split("\x00", 1)[0].strip()


def normalize_unit(unit: str) -> str | None:
    unit = unit.strip().replace("μ", "µ")
    if unit in ("", "-", "--", "pH"):
        return None
    aliases = {"mg/l": "mg/L", "mg/L": "mg/L", "m3/h": "m³/h"}
    return aliases.get(unit, unit)


class EvoquaClient:
    """One TCP connection per snapshot; only function code 03 is implemented.

    Connections close on success, timeout, cancellation and malformed replies.
    A new connection on the next poll recovers from controller restarts.
    """

    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 1,
        timeout: float = 5,
        register_base: int = 400001,
        byte_order: str = "ABCD",
    ) -> None:
        if not host or not 1 <= port <= 65535 or not 0 <= unit_id <= 255:
            raise ValueError("Invalid host, port or unit ID")
        if timeout <= 0 or register_base not in (400000, 400001):
            raise ValueError("Invalid timeout or register base")
        if byte_order not in BYTE_ORDERS:
            raise ValueError("Invalid byte order")
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.register_base = register_base
        self.byte_order = byte_order
        self._transaction = 0
        self._lock = asyncio.Lock()

    async def _read(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
        register: int, count: int,
    ) -> list[int]:
        address = register - self.register_base
        if not 1 <= count <= 125 or not 0 <= address <= 65536 - count:
            raise ValueError("Invalid register range")
        self._transaction = (self._transaction + 1) % 65536
        transaction = self._transaction
        request = struct.pack(">HHHBBHH", transaction, 0, 6, self.unit_id, 3, address, count)
        async with asyncio.timeout(self.timeout):
            writer.write(request)
            await writer.drain()
            header = await reader.readexactly(7)
            received_id, protocol, length, unit = struct.unpack(">HHHB", header)
            if received_id != transaction or protocol != 0 or unit != self.unit_id:
                raise EvoquaError("Mismatched Modbus TCP response header")
            if not 3 <= length <= 254:
                raise EvoquaError("Invalid Modbus TCP response length")
            pdu = await reader.readexactly(length - 1)
        if pdu[0] == 0x83 and len(pdu) == 2:
            raise ModbusError(pdu[1], address)
        if pdu[0] != 3 or len(pdu) != 2 + count * 2 or pdu[1] != count * 2:
            raise EvoquaError("Invalid FC03 response or register count")
        return list(struct.unpack(f">{count}H", pdu[2:]))

    async def async_snapshot(
        self, channels: list[str] | tuple[str, ...], include_status: bool = False,
    ) -> Snapshot:
        """Read identity and selected channels; propagate errors atomically."""
        if not channels or any(key not in CHANNELS for key in channels):
            raise ValueError("Select at least one known channel")
        writer = None
        async with self._lock:
            try:
                async with asyncio.timeout(self.timeout):
                    reader, writer = await asyncio.open_connection(self.host, self.port)
                info = await self._read(reader, writer, 400001, 15)
                name = decode_text(info[:10])
                software = decode_text(info[10:15])
                # Refuse unrelated Modbus servers and wrong address settings.
                compact = re.sub(r"[^A-Z0-9]", "", name.upper())
                if "700P" not in compact:
                    raise InvalidDevice(f"Expected a 700 P system name, received {name!r}")
                version = re.search(r"(\d+)\.(\d+)", software)
                if version and tuple(map(int, version.groups())) < (1, 31):
                    raise InvalidDevice(f"Firmware {software} is older than 1.31")
                measurements = {}
                for key in channels:
                    words = await self._read(reader, writer, CHANNELS[key].register, 7)
                    measurements[key] = Measurement(
                        decode_float(words[:2], self.byte_order),
                        normalize_unit(decode_text(words[2:7])),
                    )
                status = {}
                if include_status:
                    words = await self._read(reader, writer, 400300, 18)
                    status.update({400300 + i: word for i, word in enumerate(words[:8])})
                    for i in range(8, 18, 2):
                        status[400300 + i] = int.from_bytes(
                            ordered_bytes(words[i:i + 2], self.byte_order), "big"
                        )
                return Snapshot(name, software, measurements, status)
            except (OSError, TimeoutError, asyncio.IncompleteReadError) as err:
                raise EvoquaError(f"Modbus TCP communication failed: {err}") from err
            finally:
                if writer is not None:
                    writer.close()
                    try:
                        async with asyncio.timeout(1):
                            await writer.wait_closed()
                    except (OSError, TimeoutError):
                        pass
