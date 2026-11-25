"""700 P Modbus TCP: documented reads and explicitly requested writes."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import time
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


# Manual WT.050.810.010.DD.IM.0620, section 4.6, pp. 30-37.
# A 4xxxxx number is one-based: wire = manual - 400001. All documented
# FLOAT/UINT32 values use low word first, bytes within words big endian (CDAB).
CHEMICALS = ("chlorine", "ph", "orp", "total_chlorine", "conductivity")
CONTROL_CHANNELS = ("chlorine", "ph", "total_chlorine", "conductivity")
FLOW_POINTS = {}
POINT_CHANNEL = {}
UNIT_POINTS = {}
for _key, _channel in CHANNELS.items():
    _base = _channel.register - 400001
    UNIT_POINTS[f"{_key}_unit"] = _base + 2
    for _suffix, _label, _offset in (
        ("", "", 0), ("_range_min", "Messbereich Anfang", 7),
        ("_range_max", "Messbereich Ende", 9),
        ("_current_setpoint", "aktueller Sollwert", 11),
        ("_dosing", "Dosierleistung", 13),
    ):
        if _key not in CHEMICALS and _offset > 9:
            continue  # These slots are reserved, not data points.
        _point_key = _key + _suffix
        FLOW_POINTS[_point_key] = ReadPoint(
            _base + _offset, f"{_channel.label} {_label}".strip(),
            "%" if _suffix == "_dosing" else None,
            precision=_channel.precision,
        )
        POINT_CHANNEL[_point_key] = _key
FLOW_POINTS["flocculation_dosing"] = ReadPoint(189, "Flockung Dosierleistung", "%", precision=1)


@dataclass(frozen=True)
class WritePoint:
    address: int
    channel: str
    kind: str


WRITE_POINTS = {}
for _i, _key in enumerate(CONTROL_CHANNELS):
    for _j, (_suffix, _label, _unit) in enumerate((
        ("setpoint", "Sollwert (W)", None), ("xp", "P-Anteil (Xp)", "%"),
        ("tn", "I-Anteil (Tn)", "min"),
    )):
        _point_key = f"{_key}_{_suffix}"
        _address = 999 + _i * 6 + _j * 2
        FLOW_POINTS[_point_key] = ReadPoint(_address, f"{CHANNELS[_key].label} {_label}", _unit)
        POINT_CHANNEL[_point_key] = _key
        WRITE_POINTS[_point_key] = WritePoint(_address, _key, _suffix)
for _i, _key in enumerate((*CHEMICALS, "temperature")):
    for _j, (_suffix, _label) in enumerate((
        ("min1", "Min1"), ("max1", "Max1"), ("hyst1", "Hysterese1"),
        ("min2", "Min2"), ("max2", "Max2"), ("hyst2", "Hysterese2"),
    )):
        if _key == "temperature" and _j >= 3:
            break
        _point_key = f"{_key}_{_suffix}"
        _address = 1049 + _i * 12 + _j * 2
        FLOW_POINTS[_point_key] = ReadPoint(_address, f"{CHANNELS[_key].label} {_label}")
        POINT_CHANNEL[_point_key] = _key
        WRITE_POINTS[_point_key] = WritePoint(_address, _key, _suffix)
FUNCTION_ADDRESS = 1999
SHOCK_MASK = 0x0200

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
MODE_KEYS = {"chlorine": "operating_mode", "ph": "ph_operating_mode",
             "total_chlorine": "total_chlorine_operating_mode",
             "conductivity": "conductivity_operating_mode"}
ERROR_KEYS = {key: ("error_text" if key == "chlorine" else f"{key}_error_text") for key in CHEMICALS}
RAW_STATUS = {"alarm_word": 299, "input_word": 300, "relay_word": 301, "aux_relay_word": 302,
              **{f"{key}_mode_code": 303 + i for i, key in enumerate(CONTROL_CHANNELS)}}
FLOW_TEXTS = {
    "system_name": "Systemname", "software_version": "Software-Version",
    "device_date": "Gerätedatum", "device_time": "Gerätezeit",
    **{key: f"{CHANNELS[ch].label} Betriebsart" for ch, key in MODE_KEYS.items()},
    **{key: f"{CHANNELS[ch].label} Fehler" for ch, key in ERROR_KEYS.items()},
    **{f"{ch}_error_code": f"{CHANNELS[ch].label} Fehlercode" for ch in CHEMICALS},
    **{key: f"{CHANNELS[key.removesuffix('_unit')].label} Einheit" for key in UNIT_POINTS},
    **{key: key.replace("_", " ") for key in RAW_STATUS},
    "function_word": "Funktionswort",
}
FLOW_BINARIES = {
    **{f"di{i}": f"Digitaleingang {i}" for i in range(1, 4)},
    **{f"alarm{i}": f"Alarm {i}" for i in range(1, 9)},
    **{f"relay{k}": f"Relais K{k}" for k in (*range(1, 9), *range(21, 25))},
    "sample_water": "Messwasser", "sample_water_stop": "Messwasser-Stopp",
    "shock_chlorination": "Stoßchlorung",
    **{f"{ch}_problem": f"{CHANNELS[ch].label} Störung" for ch in CHEMICALS},
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
    binaries: dict[str, bool | None] = field(default_factory=dict)
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
    """Serialized connections; FC03 reads, allowlisted FC16/FC06 writes.

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
        self._last_write = -math.inf

    async def _read(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
        register: int, count: int,
    ) -> list[int]:
        address = register - self.register_base
        if not 1 <= count <= 125 or not 0 <= address <= 65536 - count:
            raise ValueError("Invalid register range")
        pdu = await self._exchange(reader, writer, 3, struct.pack(">HH", address, count), address)
        if len(pdu) != 2 + count * 2 or pdu[1] != count * 2:
            raise EvoquaError("Invalid FC03 response or register count")
        return list(struct.unpack(f">{count}H", pdu[2:]))

    async def _exchange(self, reader, writer, function, payload, address):
        self._transaction = (self._transaction + 1) % 65536
        transaction = self._transaction
        request = struct.pack(">HHHBB", transaction, 0, len(payload) + 2, self.unit_id, function) + payload
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
        if pdu[0] == function | 0x80 and len(pdu) == 2:
            raise ModbusError(pdu[1], address)
        if pdu[0] != function:
            raise EvoquaError("Unexpected Modbus function")
        return pdu

    @asynccontextmanager
    async def _connection(self):
        writer = None
        async with self._lock:
            try:
                async with asyncio.timeout(self.timeout):
                    reader, writer = await asyncio.open_connection(self.host, self.port)
                yield reader, writer
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

    async def _identity(self, reader, writer):
        identity = await self._read(reader, writer, 400001, 15)
        name = flow_text(identity[:10])
        software = flow_text(identity[10:15], r"V\s*:?\s*\d+\.\d+")
        version = re.search(r"(\d+)\.(\d+)", software)
        if not name or not version or tuple(map(int, version.groups())) < (1, 31):
            raise InvalidDevice("Missing system name or unsupported firmware identification")
        return name, software

    async def _read_flow_snapshot(self, reader, writer) -> Snapshot:
        """All meaningful registers in the v2 manual; reserved slots excluded."""
        async def read(address, count):
            return await self._read(reader, writer, 400001 + address, count)

        async def optional(address, count):
            try:
                return await read(address, count)
            except ModbusError as err:
                if err.code not in (2, 3):
                    raise
                return None  # Optional channel/register not fitted or supported.

        name, software = await self._identity(reader, writer)
        values = {"system_name": name, "software_version": software,
                  "device_date": flow_text(await read(15, 5), r"\d{2}\.\d{2}\.\d{4}"),
                  "device_time": flow_text(await read(20, 3), r"\d{2}:\d{2}")}
        measurements = {}
        units = {}
        for key, channel in CHANNELS.items():
            words = await optional(channel.register - 400001, 15 if key in CHEMICALS else 11)
            unit = normalize_unit(flow_text(words[2:7])) if words else None
            units[key] = unit
            values[f"{key}_unit"] = flow_text(words[2:7]) if words else None
            for point_key, point in FLOW_POINTS.items():
                if point.address >= 999 or POINT_CHANNEL.get(point_key) != key:
                    continue
                offset = point.address - (channel.register - 400001)
                value = decode_float(words[offset:offset+2], "CDAB") if words else None
                measurements[point_key] = Measurement(value, point.unit or unit)
        floc = await optional(189, 2)
        measurements["flocculation_dosing"] = Measurement(decode_float(floc, "CDAB") if floc else None, "%")
        for key, point in WRITE_POINTS.items():
            words = await optional(point.address, 2)
            measurements[key] = Measurement(decode_float(words, "CDAB") if words else None,
                                            FLOW_POINTS[key].unit or units[point.channel])
        words = await read(299, 18)
        status = {400300 + i: word for i, word in enumerate(words[:8])}
        values.update({key: words[address - 299] for key, address in RAW_STATUS.items()})
        alarms, inputs, relay1, relay2 = words[:4]
        details = {}
        for i, channel in enumerate(CONTROL_CHANNELS):
            mode = words[4 + i]
            flags = [label for bit, label in enumerate(MODE_NAMES) if mode & (1 << bit)]
            key = MODE_KEYS[channel]
            values[key] = compact_flags(flags, "Keine Aktivität")
            details[key] = flags
        binaries = {
            **{f"di{i}": bool(inputs & (1 << (i - 1))) for i in range(1, 4)},
            **{f"alarm{i}": bool(alarms & (1 << (i - 1))) for i in range(1, 9)},
            **{f"relay{i+1}": bool(relay1 & (1 << i)) for i in range(8)},
            **{f"relay{i+21}": bool(relay2 & (1 << i)) for i in range(4)},
            "sample_water": not bool(inputs & 8), "sample_water_stop": bool(inputs & 8),
            "shock_chlorination": bool(words[4] & 0x8000),
        }
        for i, channel in enumerate(CHEMICALS):
            error = int.from_bytes(ordered_bytes(words[8+i*2:10+i*2], "CDAB"), "big")
            status[400308 + i*2] = error
            flags = [ERROR_NAMES.get(bit, f"Unbekanntes Bit {bit}") for bit in range(32) if error & (1 << bit)]
            key = ERROR_KEYS[channel]
            values[key] = compact_flags(flags, "Keine Fehler")
            values[f"{channel}_error_code"] = error
            details[key] = flags
            binaries[f"{channel}_problem"] = bool(error)
        function = await optional(FUNCTION_ADDRESS, 1)
        values["function_word"] = function[0] if function else None
        return Snapshot(name, software, measurements, status, values, binaries, details)

    async def async_write_number(self, key: str, value: float) -> bool:
        """Write one allowlisted FLOAT, fresh bounds, no retry, verified readback.

        False means identical encoded value: no EEPROM write was sent.
        Hysteresis is the engineering-unit FLOAT, not a guessed digit conversion.
        The device remains responsible for its 1..25 display-digit constraint.
        """
        if self.profile != FLOW_PROFILE or self.register_base != 400001 or key not in WRITE_POINTS:
            raise EvoquaError("This register is not writable")
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise EvoquaError("Enter a finite numeric value")
        point = WRITE_POINTS[key]
        async with self._connection() as (reader, writer):
            await self._identity(reader, writer)
            current = await self._read(reader, writer, 400001 + point.address, 2)
            low, high = await self._write_bounds(reader, writer, key)
            if not low <= value <= high:
                raise EvoquaError(f"Value must be between {low:g} and {high:g}")
            try:
                canonical = struct.pack(">f", value)
            except (OverflowError, struct.error) as err:
                raise EvoquaError("Value cannot be encoded as FLOAT32") from err
            encoded = canonical[2:] + canonical[:2]
            if encoded == struct.pack(">HH", *current):
                return False
            self._reserve_write()
            payload = struct.pack(">HHB", point.address, 2, 4) + encoded
            try:
                reply = await self._exchange(reader, writer, 16, payload, point.address)
                if reply != struct.pack(">BHH", 16, point.address, 2):
                    raise EvoquaError("Invalid FC16 acknowledgement")
                result = await self._read(reader, writer, 400001 + point.address, 2)
                if struct.pack(">HH", *result) != encoded:
                    raise EvoquaError("Device readback differs from requested value")
            except (EvoquaError, OSError, TimeoutError, asyncio.IncompleteReadError) as err:
                raise EvoquaError("Write outcome not confirmed; read device state before another command. " + str(err)) from err
            return True

    async def _write_bounds(self, reader, writer, key):
        point = WRITE_POINTS[key]
        if point.kind == "xp":
            return 0, 1000
        if point.kind == "tn":
            return 0, 100
        words = await self._read(reader, writer, CHANNELS[point.channel].register + 7, 4)
        low, high = decode_float(words[:2], "CDAB"), decode_float(words[2:], "CDAB")
        if low is None or high is None or low >= high:
            raise EvoquaError("Cannot validate the device measuring range")
        if point.kind.startswith("hyst"):
            return 0.000001, high - low
        if point.kind.startswith(("min", "max")):
            other_kind = ("max" if point.kind.startswith("min") else "min") + point.kind[-1]
            other = WRITE_POINTS[f"{point.channel}_{other_kind}"]
            peer = decode_float(await self._read(reader, writer, 400001 + other.address, 2), "CDAB")
            if peer is None or not low <= peer <= high:
                raise EvoquaError("Cannot validate the paired limit")
            if point.kind.startswith("min"):
                high = peer
            else:
                low = peer
        return low, high

    def _reserve_write(self):
        now = time.monotonic()
        if now - self._last_write < 1:
            raise EvoquaError("Wait at least one second between write commands")
        self._last_write = now  # Also throttle uncertain/failed write attempts.

    async def async_shock_toggle(self) -> None:
        """Send the documented Start/Stop command, never infer on/off semantics.

        Bit 9 is a command, actual running state is mode bit 15. No automatic
        clearing/retry, and no repeated write when a command is still pending.
        """
        if self.profile != FLOW_PROFILE or self.register_base != 400001:
            raise EvoquaError("Writes require the documented 700 P profile")
        async with self._connection() as (reader, writer):
            await self._identity(reader, writer)
            current = (await self._read(reader, writer, 402000, 1))[0]
            if current & SHOCK_MASK:
                raise EvoquaError("Start/Stop command is still set; inspect the device before repeating")
            self._reserve_write()
            value = current | SHOCK_MASK
            payload = struct.pack(">HH", FUNCTION_ADDRESS, value)
            try:
                reply = await self._exchange(reader, writer, 6, payload, FUNCTION_ADDRESS)
                if reply != bytes([6]) + payload:
                    raise EvoquaError("Invalid FC06 acknowledgement")
                # The command can self-clear; read actual operating flags instead
                # of requiring a latched command bit or optimistically toggling HA.
                await self._read(reader, writer, 400304, 1)
            except (EvoquaError, OSError, TimeoutError, asyncio.IncompleteReadError) as err:
                raise EvoquaError("Start/Stop outcome not confirmed; inspect device state. " + str(err)) from err


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
