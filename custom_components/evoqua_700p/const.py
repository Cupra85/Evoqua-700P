"""Integration configuration."""

DOMAIN = "evoqua_700p"
DEFAULTS = {
    "port": 502,
    "unit_id": 1,
    "timeout": 1,
    "scan_interval": 10,
    "register_base": 400001,
    "byte_order": "ABCD",
    "channels": ["chlorine", "ph", "orp", "temperature"],
    "include_status": True,
    "profile": "node_red_206",
}
