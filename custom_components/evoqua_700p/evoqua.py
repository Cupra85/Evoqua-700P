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
FLOW_PROFILE = "node_red_206"


@dataclass(frozen=True)
class ReadPoint:
    """An absolute wire address, not an inferred manual-register offset."""

    address: int
    label: str
    unit: str | None = None
    order: str = "CDAB"
    precision: int = 2


# The Node-RED sequencers use different addressing and FLOAT orders in these
# two groups. Do not apply a global offset or byte order to this profile.
FLOW_POINTS = {
    "chlorine": ReadPoint(100, "Chlor", "mg/L", "ABCD"),
    "ph": ReadPoint(115, "pH", None, "ABCD"),
    "orp": ReadPoint(130, "Redox", "mV", "ABCD", 0),
    "temperature": ReadPoint(175, "Temperatur", "°C", "ABCD", 1),
    "chlorine_current_setpoint": ReadPoint(111, "Chlor aktueller Sollwert", "mg/L", "ABCD"),
    "ph_current_setpoint": ReadPoint(126, "pH aktueller Sollwert", None, "ABCD"),
    "chlorine_dosing": ReadPoint(113, "Chlor Dosierleistung", "%", "ABCD", 1),
    "ph_dosing": ReadPoint(128, "pH Dosierleistung", "%", "ABCD", 1),
    "chlorine_setpoint": ReadPoint(999, "Chlor Sollwert (W)", "mg/L"),
    "chlorine_xp": ReadPoint(1001, "Chlor P-Anteil (Xp)", "%", precision=1),
    "chlorine_tn": ReadPoint(1003, "Chlor I-Anteil (Tn)", "min", precision=1),
    "ph_setpoint": ReadPoint(1005, "pH Sollwert (W)"),
    "ph_xp": ReadPoint(1007, "pH P-Anteil (Xp)", "%", precision=1),
    "ph_tn": ReadPoint(1009, "pH I-Anteil (Tn)", "min", precision=1),
}
for _key, _label, _address, _unit in (
    ("chlorine", "Chlor", 1049, "mg/L"),
    ("ph", "pH", 1061, None),
    ("orp", "Redox", 1073, "mV"),
    ("temperature", "Temperatur", 1109, "°C"),
):
    for _i, (_suffix, _description) in enumerate((
        ("min1", "Min1"), ("max1", "Max1"), ("hyst1", "Hysterese1"),
        ("min2", "Min2"), ("max2", "Max2"), ("hyst2", "Hysterese2"),
    )):
        if _key == "temperature" and _i >= 3:
            break
        FLOW_POINTS[f"{_key}_{_suffix}"] = ReadPoint(
            _address + 2 * _i, f"{_label} {_description}", _unit,
        )

MODE_NAMES = (
    "Hand", "Automatik", "Regler aus", "Adaption läuft",
    "Stellmotorkalibrierung läuft", "Regler Stopp (Yout=0%)",
    "Regler einfrieren", "Regler Yout=100%", "Regler Yout=2xYout",
    "Stellrad entriegelt", "Stellmotor Poti Fehler", "Eco Mode Umschaltung",
    "Hochchlorung aktiv", "Regler Standby", "Cedox Regler aktiv", "Stoßchlorung aktiv",
)
ERROR_NAMES = {
    0: "Nullpunkt Kalibrierung", 1: "DPD Kalibrierung", 2: "pH7 Kalibrierung",
    3: "pHX Kalibrierung", 4: "Kalibrierfehler", 5: "Offset Kalibrierung",
    7: "Zellenfehler", 8: "Werkskalibrierung Fehler", 9: "Messwert unter Bereich",
    10: "Messwert über Bereich", 11: "Sollwertfehler", 12: "Grenzwertfehler",
    13: "HOCL Fehler", 14: "Gesamtchlor Kommunikationsfehler", 15: "Overfeed",
    16: "Adaption Fehler", 17: "CAN Kommunikation", 18: "Temperatur Fehler",
    20: "Kein Messwasser", 21: "Stellmotor Fehler", 22: "Stellmotor Kalibrier Fehler",
    23: "Bürdefehler mA-Ausgang 1", 24: "Bürdefehler mA-Ausgang 2",
    25: "Bürdefehler mA-Ausgang 3", 26: "Bürdefehler mA-Ausgang 4",
    27: "Stellglied stetig Fehler", 28: "Flockung Fehler", 29: "Hochchlorung Fehler",
    30: "Analog Hardware Fehler", 31: "Speicherfehler",
}
FLOW_TEXTS = {
    "system_name": "Systemname", "software_version": "Software-Version",
    "device_date": "Gerätedatum", "device_time": "Gerätezeit",
    "operating_mode": "Betriebsart", "error_text": "Fehler",
    "chlorine_error_code": "Fehlercode",
}
FLOW_BINARIES = {
    **{f"di{i}": f"Digitaleingang {i}" for i in range(1, 4)},
    **{f"alarm{i}": f"Alarm {i}" for i in range(1, 5)},
    **{f"relay{k}": f"Relais K{k}" for k in (*range(1, 9), *range(21, 25))},
    "sample_water": "Messwasser", "sample_water_stop": "Messwasser-Stopp",
    "shock_chlorination": "Stoßchlorung", "chlorine_problem": "Störung",
}


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
    values: dict[str, str | int | None] = field(default_factory=dict)
    binaries: dict[str, bool] = field(default_factory=dict)
    details: dict[str, list[str]] = field(default_factory=dict)


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
        profile: str = "manual",
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
        if profile not in ("manual", FLOW_PROFILE):
            raise ValueError("Unknown register profile")
        self.profile = profile
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
                if self.profile == FLOW_PROFILE:
                    return await self._read_flow_snapshot(reader, writer)
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

    async def _read_flow_snapshot(self, reader, writer) -> Snapshot:
        """Read the Node-RED profile with field-specific wire decoding."""
        async def read(address, count):
            return await self._read(reader, writer, address + self.register_base, count)

        # The system name is user-editable: the real installation calls it Pool.
        identity = await read(0, 15)
        name = flow_text(identity[:10])
        software = flow_text(identity[10:15], r"V\s*:?\s*\d+\.\d+")
        version = re.search(r"(\d+)\.(\d+)", software)
        if not name or not version or tuple(map(int, version.groups())) < (1, 31):
            raise InvalidDevice("Missing system name or unsupported firmware identification")
        measurements = {}
        for key, point in FLOW_POINTS.items():
            measurements[key] = Measurement(
                decode_float(await read(point.address, 2), point.order), point.unit,
            )
        alarms = (await read(299, 2))[0]
        inputs = (await read(300, 2))[0]
        relay1 = (await read(301, 1))[0]
        relay2 = (await read(302, 1))[0]
        mode = (await read(303, 2))[0]
        error = int.from_bytes(ordered_bytes(await read(307, 2), "CDAB"), "big")
        modes = [label for bit, label in enumerate(MODE_NAMES) if mode & (1 << bit)]
        errors = [ERROR_NAMES.get(bit, f"Unbekanntes Bit {bit}") for bit in range(32) if error & (1 << bit)]
        values = {
            "system_name": name, "software_version": software,
            "device_date": flow_text(await read(15, 5), r"\d{2}\.\d{2}\.\d{4}"),
            "device_time": flow_text(await read(20, 3), r"\d{2}:\d{2}"),
            "operating_mode": compact_flags(modes, "Keine Aktivität"),
            "error_text": compact_flags(errors, "Keine Fehler"),
            "chlorine_error_code": error,
        }
        binaries = {
            **{f"di{i}": bool(inputs & (1 << (i - 1))) for i in range(1, 4)},
            **{f"alarm{i}": bool(alarms & (1 << (i - 1))) for i in range(1, 5)},
            **{f"relay{i+1}": bool(relay1 & (1 << i)) for i in range(8)},
            **{f"relay{i+21}": bool(relay2 & (1 << i)) for i in range(4)},
            "sample_water": not bool(inputs & 8), "sample_water_stop": bool(inputs & 8),
            "shock_chlorination": bool(mode & 0x8000), "chlorine_problem": bool(error),
        }
        return Snapshot(name, software, measurements, {400308: error, 400301: inputs},
                        values, binaries, {"operating_mode": modes, "error_text": errors})


def flow_text(words: list[int], pattern: str | None = None) -> str:
    """Node-RED swaps bytes within text registers, not FLOAT words."""
    raw = struct.pack(f">{len(words)}H", *words)
    swapped = b"".join(raw[i:i+2][::-1] for i in range(0, len(raw), 2))
    candidates = [data.decode("cp437").replace("\x00", "").strip() for data in (swapped, raw)]
    if pattern:
        for candidate in candidates:
            match = re.fullmatch(pattern, candidate, re.IGNORECASE)
            if match:
                return match.group()
        return ""
    return candidates[0] or candidates[1]


def compact_flags(flags: list[str], empty: str) -> str:
    """HA states are limited to 255 characters; keep full flags in attributes."""
    joined = ", ".join(flags) or empty
    return joined if len(joined) <= 255 else f"{len(flags)} aktive Meldungen"
