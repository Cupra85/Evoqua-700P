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
    api = load_client()
    assert set(api.FLOW_POINTS) | set(api.FLOW_TEXTS) == set(data["entity"]["sensor"]), path
    assert set(api.FLOW_BINARIES) == set(data["entity"]["binary_sensor"]), path
    assert set(api.WRITE_POINTS) == set(data["entity"]["number"]), path
    assert set(data["entity"]["button"]) == {"shock_start_stop"}, path
    assert "cannot_connect" in data["config"]["error"], path
    assert "reconfigure" in data["config"]["step"], path
    for step in ("user", "reconfigure"):
        assert set(data["config"]["step"][step]["data"]) == {"host"}, path
    assert "options" not in data, path
print("JSON, manifest and translation coverage: OK")
