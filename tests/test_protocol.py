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
        transaction, protocol, length, unit, function, address, count = struct.unpack(">HHHBBHH", raw)
        if protocol != 0 or length != 6 or function != 3:
            raise AssertionError("The client must only send correctly framed FC03 requests")
        self.requests.append((function, address, count, unit))
        if self.mode == "timeout":
            return b""
        if self.mode == "disconnect":
            return None
        words = [self.registers.get(self.base + address + i, 0) for i in range(count)]
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

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        self.connections += 1
        try:
            while True:
                raw = await reader.readexactly(12)
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


if __name__ == "__main__":
    unittest.main()

