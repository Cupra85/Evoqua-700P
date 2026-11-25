"""Measured values and optional raw diagnostic error codes."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
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
    entities = [EvoquaMeasurement(coordinator, key) for key in coordinator.settings["channels"]]
    if coordinator.settings["include_status"]:
        entities.extend(
            EvoquaErrorCode(coordinator, key)
            for key in coordinator.settings["channels"]
            if CHANNELS[key].error_register is not None
        )
    async_add_entities(entities)


class EvoquaMeasurement(EvoquaEntity, SensorEntity):
    """A value with the unit reported by the device itself."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self.key = key
        self._attr_suggested_display_precision = CHANNELS[key].precision
        self._attr_icon = {
            "chlorine": "mdi:water", "ph": "mdi:ph", "orp": "mdi:flash",
            "total_chlorine": "mdi:water", "conductivity": "mdi:current-ac",
            "temperature": "mdi:thermometer", "circulation": "mdi:waves-arrow-right",
            "analog_input_2": "mdi:gauge",
        }[key]

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.measurements[self.key].value

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.coordinator.data.measurements[self.key].unit

    @property
    def device_class(self) -> SensorDeviceClass | None:
        if self.key == "temperature" and self.native_unit_of_measurement in ("°C", "°F"):
            return SensorDeviceClass.TEMPERATURE
        return None

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None

    @property
    def extra_state_attributes(self) -> dict:
        return {"modbus_register": CHANNELS[self.key].register}


class EvoquaErrorCode(EvoquaEntity, SensorEntity):
    """Raw channel error bitmask, without firmware-dependent interpretation."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, f"{key}_error_code")
        self.register = CHANNELS[key].error_register

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.status.get(self.register)
