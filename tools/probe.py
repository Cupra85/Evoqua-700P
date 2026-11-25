"""Read a 700 P without Home Assistant: python tools/probe.py 192.168.1.50."""

import argparse
import asyncio
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys


def load_client():
    path = Path(__file__).resolve().parents[1] / "custom_components/evoqua_700p/evoqua.py"
    spec = importlib.util.spec_from_file_location("evoqua_standalone", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


async def main() -> int:
    api = load_client()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--unit-id", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--register-base", type=int, choices=(400001, 400000), default=400001)
    parser.add_argument("--byte-order", choices=api.BYTE_ORDERS, default="ABCD")
    parser.add_argument("--channels", nargs="+", choices=api.CHANNELS, default=api.DEFAULT_CHANNELS)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    client = api.EvoquaClient(
        args.host, args.port, args.unit_id, args.timeout, args.register_base, args.byte_order,
    )
    try:
        snapshot = await client.async_snapshot(args.channels, args.status)
    except api.EvoquaError as err:
        print(str(err), file=sys.stderr)
        return 1
    print(json.dumps(asdict(snapshot), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
