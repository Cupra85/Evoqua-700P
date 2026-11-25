"""Evoqua 700P read-only Home Assistant integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import EvoquaCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
type EvoquaConfigEntry = ConfigEntry[EvoquaCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EvoquaConfigEntry) -> bool:
    coordinator = EvoquaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EvoquaConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: EvoquaConfigEntry) -> bool:
    """Keep the saved IP and entity identities when adopting the fixed profile."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        hass.config_entries.async_update_entry(
            entry, data={"host": entry.data["host"]}, options={}, version=2,
        )
    return True
