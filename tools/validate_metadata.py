"""Validate the package's JSON and translation coverage without dependencies."""

import json
from pathlib import Path

from probe import load_client

root = Path(__file__).resolve().parents[1]
component = root / "custom_components/evoqua_700p"
for path in root.rglob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))
manifest = json.loads((component / "manifest.json").read_text(encoding="utf-8"))
assert manifest["domain"] == "evoqua_700p"
assert manifest["config_flow"] is True
assert manifest["requirements"] == []
for path in [component / "strings.json", *sorted((component / "translations").glob("*.json"))]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(load_client().CHANNELS) <= set(data["entity"]["sensor"]), path
    assert "cannot_connect" in data["config"]["error"], path
    assert "reconfigure" in data["config"]["step"], path
print("JSON, manifest and translation coverage: OK")
