"""Diagnostics without the local network address."""

from dataclasses import asdict

from homeassistant.components.diagnostics import async_redact_data

from . import EvoquaConfigEntry


async def async_get_config_entry_diagnostics(hass, entry: EvoquaConfigEntry) -> dict:
    coordinator = entry.runtime_data
    return {
        "settings": async_redact_data(coordinator.settings, {"host"}),
        "last_update_success": coordinator.last_update_success,
        "snapshot": asdict(coordinator.data) if coordinator.data else None,
    }
