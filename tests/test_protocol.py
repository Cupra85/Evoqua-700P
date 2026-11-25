"""Socket-level tests with independently specified 700 P register fixtures."""

import asyncio
import importlib.util
import math
import os
from pathlib import Path
import selectors
import struct
import sys
import time
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "evoqua_protocol_under_test",
    Path(__file__).resolve().parents[1] / "custom_components/evoqua_700p/evoqua.py",
)
api = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = api
SPEC.loader.exec_module(api)

MEMORY = os.environ.get("EVOQUA_TEST_TRANSPORT") == "memory"


class MemorySelector(selectors.SelectSelector):
    def select(self, timeout=None):
        if timeout is None:
            raise RuntimeError("Memory test has no pending events or timeout")
        if timeout > 0:
            time.sleep(timeout)
        return []


class MemoryOnlyEventLoop(asyncio.SelectorEventLoop):
    """Single-threaded test loop without any OS sockets (restricted Windows)."""

    def __init__(self):
        super().__init__(selector=MemorySelector())

    def _make_self_pipe(self):
        pass

    def _close_self_pipe(self):
        pass

    def _write_to_self(self):
        pass


class MemoryWriter:
    """Feed the same protocol responses into a StreamReader without networking."""

    def __init__(self, controller, reader):
        self.controller = controller
        self.reader = reader
        self.is_closed = False

    def write(self, request):
        response = self.controller.reply(request)
        if response is None:
            self.reader.feed_eof()
        elif response:
            self.reader.feed_data(response[:5])
            asyncio.get_running_loop().call_soon(self.reader.feed_data, response[5:])

    async def drain(self):
        await asyncio.sleep(0)

    def close(self):
        if not self.is_closed:
            self.is_closed = True
            self.controller.closed += 1
            self.reader.feed_eof()

    async def wait_closed(self):
        pass


class Controller:
    """Fake server that records the actual function code and wire addresses."""

    def __init__(self, base=400001, order="ABCD"):
        self.base = base
        self.order = order
        self.registers = {}
        self.requests = []
        self.connections = 0
        self.closed = 0
        self.mode = None
        self.tasks = set()
        self.text(400001, "DEPOLOX Pool E 700 P", 20)
        self.text(400011, "V:1.31", 10)
        for address, value, unit in [
            (400100, 0.65, "mg/l"), (400115, 7.2, "pH"),
            (400130, 740, "mV"), (400145, 0.8, "mg/l"),
            (400160, 1.5, "mS/cm"), (400175, 26.5, "°C"),
            (400205, 15.2, "m3/h"), (400220, 42, "%"),
        ]:
            self.number(address, value)
            self.text(address + 2, unit, 10)
        for register in range(400300, 400318):
            self.registers[register] = 0
        self.registers[400301] = 8
        self.uint32(400308, 0x80000001)

    def text(self, address, value, size):
        raw = value.encode("cp437").ljust(size, b"\x00")[:size]
        for i, word in enumerate(struct.unpack(f">{size // 2}H", raw)):
            self.registers[address + i] = word

    def encoded(self, address, raw):
        encoded = bytes(raw["ABCD".index(letter)] for letter in self.order)
        self.registers[address], self.registers[address + 1] = struct.unpack(">HH", encoded)

    def number(self, address, value):
        self.encoded(address, struct.pack(">f", value))

    def uint32(self, address, value):
        self.encoded(address, value.to_bytes(4, "big"))

    async def start(self):
        if MEMORY:
            self.port = 15020
            return self
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def stop(self):
        if MEMORY:
            return
        self.server.close()
        await self.server.wait_closed()
        for task in list(self.tasks):
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

    async def connect_memory(self, host, port):
        self.connections += 1
        reader = asyncio.StreamReader()
        return reader, MemoryWriter(self, reader)

    def reply(self, raw):
        transaction, protocol, length, unit, function, address, count = struct.unpack(">HHHBBHH", raw[:12])
        if function in (6, 16):
            return self.write_reply(raw)
        if protocol != 0 or length != 6 or function != 3:
            raise AssertionError("The client must only send correctly framed FC03 requests")
        self.requests.append((function, address, count, unit))
        if self.mode == "timeout":
            return b""
        if self.mode == "disconnect":
            return None
        words = [self.registers.get(self.base + address + i, 0) for i in range(count)]
        if address in getattr(self, "unsupported", set()):
            return struct.pack(">HHHB", transaction, 0, 3, unit) + b"\x83\x02"
        pdu = bytes([3, count * 2]) + struct.pack(f">{count}H", *words)
        if self.mode == "exception":
            pdu = b"\x83\x02"
        elif self.mode == "bad_function":
            pdu = bytes([4]) + pdu[1:]
        elif self.mode == "bad_count":
            pdu = bytes([3, 0]) + pdu[2:]
        elif self.mode == "short_data":
            pdu = pdu[:-2]
        header = struct.pack(
            ">HHHB", transaction + (self.mode == "bad_transaction"),
            int(self.mode == "bad_protocol"),
            65535 if self.mode == "bad_length" else len(pdu) + 1,
            (unit + 1) % 256 if self.mode == "bad_unit" else unit,
        )
        return header + pdu

    def write_reply(self, raw):
        transaction, protocol, length, unit, function = struct.unpack(">HHHBB", raw[:8])
        address, count = struct.unpack(">HH", raw[8:12])
        assert protocol == 0 and length == len(raw) - 6
        self.requests.append((function, address, count, unit))
        if function == 16:
            assert count == 2 and raw[12] == 4 and len(raw) == 17
            words = struct.unpack(">HH", raw[13:])
        else:
            assert len(raw) == 12
            words = [count]
        if self.mode == "write_exception":
            pdu = bytes([function | 0x80, 3])
        else:
            if self.mode != "readback_mismatch":
                for i, word in enumerate(words):
                    self.registers[self.base + address + i] = word
            if self.mode == "write_disconnect":
                return None  # Device applied command; acknowledgement lost.
            if self.mode == "write_timeout":
                return b""
            pdu = raw[7:12]
            if self.mode == "write_bad_echo":
                pdu = pdu[:-1] + bytes([pdu[-1] ^ 1])
        return struct.pack(">HHHB", transaction, 0, len(pdu) + 1, unit) + pdu

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        self.connections += 1
        try:
            while True:
                header = await reader.readexactly(7)
                length = struct.unpack(">H", header[4:6])[0]
                raw = header + await reader.readexactly(length - 1)
                response = self.reply(raw)
                if self.mode == "timeout":
                    await reader.read()
                    return
                if response is None:
                    return
                # Deliberately fragment TCP to check readexactly, not packet assumptions.
                writer.write(response[:5])
                await writer.drain()
                await asyncio.sleep(0)
                writer.write(response[5:])
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            try:
                async with asyncio.timeout(1):
                    await writer.wait_closed()
            except (ConnectionError, TimeoutError):
                pass
            self.closed += 1
            self.tasks.discard(task)


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    if MEMORY:
        loop_factory = MemoryOnlyEventLoop

    async def asyncSetUp(self):
        self.controller = await Controller().start()
        if MEMORY:
            self.connection_patch = patch.object(api.asyncio, "open_connection", self.controller.connect_memory)
            self.connection_patch.start()
        self.client = api.EvoquaClient("127.0.0.1", self.controller.port, timeout=0.3)

    async def asyncTearDown(self):
        if MEMORY:
            self.connection_patch.stop()
        await self.controller.stop()

    async def test_all_measurements_and_status(self):
        result = await self.client.async_snapshot(list(api.CHANNELS), True)
        expected = {
            "chlorine": (0.65, "mg/L"), "ph": (7.2, None), "orp": (740, "mV"),
            "total_chlorine": (0.8, "mg/L"), "conductivity": (1.5, "mS/cm"),
            "temperature": (26.5, "°C"), "circulation": (15.2, "m³/h"),
            "analog_input_2": (42, "%"),
        }
        for key, (value, unit) in expected.items():
            self.assertAlmostEqual(result.measurements[key].value, value, places=5)
            self.assertEqual(result.measurements[key].unit, unit)
        self.assertEqual(result.status[400308], 0x80000001)
        self.assertEqual(result.status[400301], 8)
        self.assertEqual(self.controller.requests, [
            (3, 0, 15, 1), (3, 99, 7, 1), (3, 114, 7, 1), (3, 129, 7, 1),
            (3, 144, 7, 1), (3, 159, 7, 1), (3, 174, 7, 1), (3, 204, 7, 1),
            (3, 219, 7, 1), (3, 299, 18, 1),
        ])

    async def test_only_selected_channels_no_status(self):
        result = await self.client.async_snapshot(["ph"])
        self.assertEqual(set(result.measurements), {"ph"})
        self.assertEqual(result.status, {})
        self.assertEqual(len(self.controller.requests), 2)

    async def test_reconnect_after_success(self):
        for _ in range(2):
            await self.client.async_snapshot(["temperature"])
        self.assertEqual(self.controller.connections, 2)

    async def test_error_recovery(self):
        self.controller.mode = "disconnect"
        with self.assertRaises(api.EvoquaError):
            await self.client.async_snapshot(["ph"])
        self.controller.mode = None
        result = await self.client.async_snapshot(["ph"])
        self.assertAlmostEqual(result.measurements["ph"].value, 7.2, places=5)

    async def test_timeout_closes_connection(self):
        self.controller.mode = "timeout"
        with self.assertRaises(api.EvoquaError):
            await self.client.async_snapshot(["ph"])
        for _ in range(5):
            await asyncio.sleep(0.01)
            if self.controller.closed:
                break
        self.assertEqual(self.controller.closed, 1)

    async def test_cancellation_closes_connection(self):
        self.controller.mode = "timeout"
        task = asyncio.create_task(self.client.async_snapshot(["ph"]))
        while not self.controller.requests:
            await asyncio.sleep(0.001)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        for _ in range(5):
            await asyncio.sleep(0.01)
            if self.controller.closed:
                break
        self.assertEqual(self.controller.closed, 1)

    async def test_reject_malformed_responses(self):
        for mode in ["bad_function", "bad_count", "short_data", "bad_transaction", "bad_protocol", "bad_length", "bad_unit"]:
            with self.subTest(mode=mode):
                self.controller.mode = mode
                with self.assertRaises(api.EvoquaError):
                    await self.client.async_snapshot(["ph"])

    async def test_modbus_exception_has_code(self):
        self.controller.mode = "exception"
        with self.assertRaises(api.ModbusError) as caught:
            await self.client.async_snapshot(["ph"])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(caught.exception.address, 0)

    async def test_wrong_model_rejected(self):
        self.controller.text(400001, "OTHER CONTROLLER", 20)
        with self.assertRaises(api.InvalidDevice):
            await self.client.async_snapshot(["ph"])

    async def test_old_firmware_rejected(self):
        self.controller.text(400011, "V:1.30", 10)
        with self.assertRaises(api.InvalidDevice):
            await self.client.async_snapshot(["ph"])

    async def test_firmware_206_is_accepted(self):
        for software in ("V2.06", "V:2.06"):
            with self.subTest(software=software):
                self.controller.text(400011, software, 10)
                result = await self.client.async_snapshot(["ph", "temperature"])
                self.assertEqual(result.software, software)
                self.assertAlmostEqual(result.measurements["ph"].value, 7.2, places=5)
                self.assertEqual(result.measurements["temperature"].value, 26.5)

    async def test_nonfinite_values_are_unavailable(self):
        for value in [math.nan, math.inf, -math.inf]:
            with self.subTest(value=value):
                self.controller.number(400115, value)
                result = await self.client.async_snapshot(["ph"])
                self.assertIsNone(result.measurements["ph"].value)

    async def test_all_byte_orders(self):
        for order in ("ABCD", "CDAB", "BADC", "DCBA"):
            with self.subTest(order=order):
                self.controller.order = order
                self.controller.number(400115, 7.25)
                self.controller.uint32(400308, 0x80000001)
                self.client.byte_order = order
                result = await self.client.async_snapshot(["ph"], True)
                self.assertEqual(result.measurements["ph"].value, 7.25)
                self.assertEqual(result.status[400308], 0x80000001)

    async def test_alternate_register_base_and_unit(self):
        self.controller.base = 400000
        self.client.register_base = 400000
        self.client.unit_id = 255
        result = await self.client.async_snapshot(["temperature"])
        self.assertEqual(result.measurements["temperature"].value, 26.5)
        self.assertEqual(self.controller.requests, [(3, 1, 15, 255), (3, 175, 7, 255)])

    async def test_concurrent_snapshots_are_serialized(self):
        results = await asyncio.gather(*[self.client.async_snapshot(["ph"]) for _ in range(3)])
        self.assertEqual(len(results), 3)
        self.assertEqual(len(self.controller.requests), 6)

    async def test_invalid_channels_do_not_connect(self):
        for channels in ([], ["unknown"]):
            with self.assertRaises(ValueError):
                await self.client.async_snapshot(channels)
        self.assertEqual(self.controller.connections, 0)

    def test_known_ieee754_and_cp437_examples(self):
        self.assertEqual(api.decode_float([0x3FA0, 0x0000]), 1.25)
        self.assertEqual(api.decode_text([0xF843, 0x0000]), "°C")
        self.assertEqual(api.normalize_unit("μS/cm"), "µS/cm")


class FlowProfileTests(unittest.IsolatedAsyncioTestCase):
    """Fixtures independently transcribed from the manual v2 register table."""

    if MEMORY:
        loop_factory = MemoryOnlyEventLoop

    async def asyncSetUp(self):
        self.controller = await Controller().start()
        self.controller.registers.clear()
        self.client = api.EvoquaClient("127.0.0.1", self.controller.port, timeout=0.3,
                                       profile="node_red_206")
        if MEMORY:
            self.connection_patch = patch.object(api.asyncio, "open_connection", self.controller.connect_memory)
            self.connection_patch.start()
        self.text(0, "Pool", 20)
        self.text(10, "V:2.06", 10)
        self.text(15, "25.11.2026", 10)
        self.text(20, "08:51", 6)
        self.basic_addresses = [99, 114, 129, 174, 110, 125, 112, 127]
        self.parameter_addresses = [*range(999, 1023, 2), *range(1049, 1115, 2)]
        for base, unit in [(99,"mg/l"),(114,"pH"),(129,"mV"),(144,"mg/l"),
                           (159,"mS/cm"),(174,"°C"),(204,"%"),(219,"%")]:
            self.number(base, 1.25, "CDAB")
            self.text(base+2, unit, 10)
            self.number(base+7, 0, "CDAB")
            self.number(base+9, 100, "CDAB")
        self.number(189, 12.5, "CDAB")
        for address, value in zip(self.basic_addresses, [0.65, 7.2, 740, 26.5, 0.9, 7.8, 25, 30]):
            self.number(address, value, "CDAB")
        for address in self.parameter_addresses:
            self.number(address, 1.25, "CDAB")
        for address, value in {299: 5, 300: 12, 301: 0x81, 302: 9, 303: 0x8022,
                               307: 1, 308: 0x8010}.items():
            self.controller.registers[400001 + address] = value

    def text(self, address, value, size):
        raw = value.encode("cp437").ljust(size, b"\x00")[:size]
        raw = b"".join(raw[i:i+2][::-1] for i in range(0, len(raw), 2))
        for i, word in enumerate(struct.unpack(f">{size // 2}H", raw)):
            self.controller.registers[400001 + address + i] = word

    def number(self, address, value, order):
        self.controller.order = order
        self.controller.number(400001 + address, value)

    async def asyncTearDown(self):
        if MEMORY:
            self.connection_patch.stop()
        await self.controller.stop()

    async def snapshot(self):
        return await self.client.async_snapshot(["chlorine", "ph", "orp", "temperature"], True)

    async def test_exact_flow_wire_addresses_and_no_writes(self):
        result = await self.snapshot()
        self.assertEqual(len(result.measurements), 80)
        self.assertEqual(self.controller.requests, [
            (3, 0, 15, 1), (3, 15, 5, 1), (3, 20, 3, 1),
            *[(3, address, 15, 1) for address in [99, 114, 129, 144, 159]],
            (3, 174, 11, 1), (3, 204, 11, 1), (3, 219, 11, 1), (3, 189, 2, 1),
            *[(3, address, 2, 1) for address in self.parameter_addresses],
            (3, 299, 18, 1), (3, 1999, 1, 1),
        ])

    async def test_mixed_float_orders_and_fixed_units(self):
        result = await self.snapshot()
        self.assertAlmostEqual(result.measurements["chlorine"].value, 0.65, places=5)
        self.assertAlmostEqual(result.measurements["ph"].value, 7.2, places=5)
        self.assertEqual(result.measurements["chlorine_dosing"].value, 25)
        self.assertEqual(result.measurements["chlorine_setpoint"].value, 1.25)
        self.assertEqual(result.measurements["temperature_hyst1"].value, 1.25)
        self.assertIsNone(result.measurements["ph_setpoint"].unit)
        self.assertEqual(result.measurements["chlorine_setpoint"].unit, "mg/L")

    async def test_custom_system_name_and_swapped_firmware(self):
        result = await self.snapshot()
        self.assertEqual(result.system_name, "Pool")
        self.assertEqual(result.software, "V:2.06")
        self.assertEqual(result.values["device_date"], "25.11.2026")
        # Do not copy the installation-specific +10 hour workaround.
        self.assertEqual(result.values["device_time"], "08:51")

    async def test_digital_inputs_alarms_and_sample_water_polarity(self):
        bits = (await self.snapshot()).binaries
        self.assertFalse(bits["di1"])
        self.assertFalse(bits["di2"])
        self.assertTrue(bits["di3"])
        self.assertTrue(bits["sample_water_stop"])
        self.assertFalse(bits["sample_water"])
        self.assertTrue(bits["alarm1"])
        self.assertFalse(bits["alarm2"])
        self.assertTrue(bits["alarm3"])
        self.assertFalse(bits["alarm4"])

    async def test_relay_bits_and_operating_mode(self):
        result = await self.snapshot()
        bits = result.binaries
        for key in ("relay1", "relay8", "relay21", "relay24", "shock_chlorination"):
            self.assertTrue(bits[key], key)
        for key in ("relay2", "relay22", "relay23"):
            self.assertFalse(bits[key], key)
        self.assertEqual(result.details["operating_mode"],
                         ["Automatik", "Regler Stopp (Yout=0%)", "Stoßchlorung aktiv"])

    async def test_unsigned_low_word_first_error_flags(self):
        result = await self.snapshot()
        self.assertEqual(result.values["chlorine_error_code"], 0x80100001)
        self.assertEqual(result.details["error_text"],
                         ["Nullpunkt Kalibrierung", "Kein Messwasser", "Speicherfehler"])
        self.assertTrue(result.binaries["chlorine_problem"])

    async def test_empty_and_long_fault_states(self):
        for raw in (0, 0xFFFFFFFF):
            self.controller.registers[400308] = raw & 0xFFFF
            self.controller.registers[400309] = raw >> 16
            result = await self.snapshot()
            self.assertLessEqual(len(result.values["error_text"]), 255)
            if raw == 0:
                self.assertEqual(result.values["error_text"], "Keine Fehler")
                self.assertFalse(result.binaries["chlorine_problem"])
            else:
                self.assertEqual(len(result.details["error_text"]), 32)

    async def test_nan_parameter_is_unavailable_and_zero_preserved(self):
        self.number(999, math.nan, "CDAB")
        self.number(112, 0, "CDAB")
        result = await self.snapshot()
        self.assertIsNone(result.measurements["chlorine_setpoint"].value)
        self.assertEqual(result.measurements["chlorine_dosing"].value, 0)

    async def test_invalid_firmware_rejected_before_measurements(self):
        self.text(10, "garbage", 10)
        with self.assertRaises(api.InvalidDevice):
            await self.snapshot()
        self.assertEqual(len(self.controller.requests), 1)

    async def test_timeout_recovers_with_profile(self):
        self.controller.mode = "timeout"
        with self.assertRaises(api.EvoquaError):
            await self.snapshot()
        self.controller.mode = None
        self.assertEqual((await self.snapshot()).system_name, "Pool")



class WriteTests(unittest.IsolatedAsyncioTestCase):
    if MEMORY:
        loop_factory = MemoryOnlyEventLoop
    text = FlowProfileTests.text
    number = FlowProfileTests.number
    snapshot = FlowProfileTests.snapshot
    asyncTearDown = FlowProfileTests.asyncTearDown
    """Use the same fragmented TCP simulator for reads and physical write frames."""

    async def asyncSetUp(self):
        await FlowProfileTests.asyncSetUp(self)
        for base, count in [(1049, 6), (1061, 6), (1073, 6), (1085, 6), (1097, 6), (1109, 3)]:
            for offset in range(count):
                self.number(base + offset * 2, [0, 100, 1.25][offset % 3], "CDAB")

    def writes(self):
        return [request for request in self.controller.requests if request[0] != 3]

    async def test_all_45_documented_float_writes(self):
        expected_addresses = {*range(999, 1023, 2), *range(1049, 1115, 2)}
        self.assertEqual({point.address for point in api.WRITE_POINTS.values()}, expected_addresses)
        for key, point in api.WRITE_POINTS.items():
            value = 0.5 if point.kind.startswith("hyst") else 2
            self.client._last_write = -math.inf
            self.assertTrue(await self.client.async_write_number(key, value), key)
            actual = [self.controller.registers[400001 + point.address + i] for i in range(2)]
            self.assertEqual(actual, [0, 0x3F00 if value == 0.5 else 0x4000], key)
        self.assertEqual(len(self.writes()), 45)
        self.assertTrue(all(request[0] == 16 and request[2:] == (2, 1) for request in self.writes()))

    async def test_unchanged_float_is_not_written(self):
        self.assertFalse(await self.client.async_write_number("chlorine_setpoint", 1.25))
        self.assertEqual(self.writes(), [])

    async def test_read_only_unknown_and_invalid_values_never_write(self):
        for key, value in [("chlorine", 2), ("relay1", 1), ("raw_400001", 1),
                           ("chlorine_setpoint", math.nan), ("ph_xp", math.inf),
                           ("ph_tn", True), ("ph_tn", "2")]:
            with self.subTest(key=key, value=value), self.assertRaises(api.EvoquaError):
                await self.client.async_write_number(key, value)
        self.assertEqual(self.controller.connections, 0)

    async def test_fresh_ranges_and_paired_limits_are_enforced(self):
        for key, value in [("chlorine_setpoint", -1), ("ph_xp", 1001), ("ph_tn", 101),
                           ("chlorine_min1", 101), ("chlorine_max1", -1),
                           ("temperature_hyst1", 0), ("temperature_hyst1", 101)]:
            with self.subTest(key=key), self.assertRaises(api.EvoquaError):
                await self.client.async_write_number(key, value)
        # Simulate a limit changed locally since the previous HA poll.
        self.number(1051, 0.25, "CDAB")
        with self.assertRaises(api.EvoquaError):
            await self.client.async_write_number("chlorine_min1", 0.5)
        self.assertEqual(self.writes(), [])

    async def test_missing_range_blocks_write(self):
        self.number(106, math.nan, "CDAB")
        with self.assertRaises(api.EvoquaError):
            await self.client.async_write_number("chlorine_setpoint", 2)
        self.assertEqual(self.writes(), [])

    async def test_no_automatic_retry_on_uncertain_write(self):
        for mode in ("write_disconnect", "write_timeout", "write_bad_echo", "readback_mismatch", "write_exception"):
            with self.subTest(mode=mode):
                self.number(999, 1.25, "CDAB")
                self.client._last_write = -math.inf
                self.controller.requests.clear()
                self.controller.mode = mode
                with self.assertRaises(api.EvoquaError):
                    await self.client.async_write_number("chlorine_setpoint", 2)
                self.assertEqual(len(self.writes()), 1)
                self.controller.mode = None
                # A later poll is read-only, even after an acknowledgement was lost.
                await self.snapshot()
                self.assertEqual(len(self.writes()), 1)

    async def test_rate_limit_and_connection_cleanup(self):
        await self.client.async_write_number("chlorine_setpoint", 2)
        with self.assertRaises(api.EvoquaError):
            await self.client.async_write_number("ph_setpoint", 3)
        self.assertEqual(len(self.writes()), 1)
        await asyncio.sleep(0.01)
        self.assertEqual(self.controller.closed, 2)

    async def test_zero_tn_is_a_valid_value(self):
        self.assertTrue(await self.client.async_write_number("ph_tn", 0))
        self.assertEqual(self.controller.registers[401010], 0)
        self.assertEqual(self.controller.registers[401011], 0)

    async def test_shock_start_stop_exact_fc06_preserves_other_bits(self):
        self.controller.registers[402000] = 0x0041
        await self.client.async_shock_toggle()
        self.assertEqual(self.writes(), [(6, 1999, 0x0241, 1)])
        self.assertEqual(self.controller.registers[402000], 0x0241)
        self.assertEqual(self.controller.requests[-1], (3, 303, 1, 1))

    async def test_pending_shock_command_not_repeated(self):
        self.controller.registers[402000] = 0x0200
        with self.assertRaises(api.EvoquaError):
            await self.client.async_shock_toggle()
        self.assertEqual(self.writes(), [])

    async def test_shock_lost_ack_is_not_retried(self):
        self.controller.mode = "write_disconnect"
        with self.assertRaises(api.EvoquaError):
            await self.client.async_shock_toggle()
        self.assertEqual(len(self.writes()), 1)

    async def test_writes_require_valid_identity(self):
        self.text(10, "invalid", 10)
        with self.assertRaises(api.InvalidDevice):
            await self.client.async_write_number("chlorine_setpoint", 2)
        self.assertEqual(self.writes(), [])

    async def test_optional_register_failure_does_not_hide_core_values(self):
        self.controller.unsupported = {144, 1011, 1999}
        result = await self.snapshot()
        self.assertIsNone(result.measurements["total_chlorine"].value)
        self.assertIsNone(result.measurements["total_chlorine_setpoint"].value)
        self.assertIsNone(result.values["function_word"])
        self.assertAlmostEqual(result.measurements["ph"].value, 7.2, places=5)

    async def test_additional_modes_errors_alarms_and_dynamic_units(self):
        self.controller.registers[400300] = 0xF0
        self.controller.registers[400305] = 2
        self.controller.registers[400310] = 0x8000
        self.controller.registers[400311] = 0x8000
        self.text(161, "mS/cm", 10)
        result = await self.snapshot()
        self.assertEqual(result.values["ph_operating_mode"], "Automatik")
        self.assertEqual(result.values["ph_error_code"], 0x80008000)
        self.assertTrue(result.binaries["ph_problem"])
        self.assertEqual(result.measurements["conductivity_setpoint"].unit, "mS/cm")
        self.assertTrue(all(result.binaries[f"alarm{i}"] for i in range(5, 9)))


if __name__ == "__main__":
    unittest.main()

