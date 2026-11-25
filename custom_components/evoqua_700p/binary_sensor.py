"""Read-only inputs, alarms, relays and controller status."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EvoquaConfigEntry
from .entity import EvoquaEntity
from .evoqua import FLOW_BINARIES

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: EvoquaConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([EvoquaStatus(entry.runtime_data, key) for key in FLOW_BINARIES])


class EvoquaStatus(EvoquaEntity, BinarySensorEntity):
    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self.key = key
        if key.startswith("alarm") or key in ("sample_water_stop", "chlorine_problem"):
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:electric-switch" if key.startswith("relay") else "mdi:information-outline"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.binaries.get(self.key)
