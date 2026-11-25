"""Optional read-only channel fault and sample-water stop indicators."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EvoquaConfigEntry
from .entity import EvoquaEntity
from .evoqua import CHANNELS

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: EvoquaConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    if not coordinator.settings["include_status"]:
        return
    async_add_entities([
        EvoquaProblem(coordinator, "sample_water_stop", 400301, 1 << 3),
        *[
            EvoquaProblem(coordinator, f"{key}_problem", CHANNELS[key].error_register)
            for key in coordinator.settings["channels"]
            if CHANNELS[key].error_register is not None
        ],
    ])


class EvoquaProblem(EvoquaEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, key: str, register: int, mask: int = 0xFFFFFFFF) -> None:
        super().__init__(coordinator, key)
        self.register = register
        self.mask = mask

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data.status.get(self.register)
        return bool(value & self.mask) if value is not None else None
