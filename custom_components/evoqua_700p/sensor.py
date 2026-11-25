"""Measured values and optional raw diagnostic error codes."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EvoquaConfigEntry
from .entity import EvoquaEntity
from .evoqua import FLOW_POINTS, FLOW_TEXTS, RAW_STATUS

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: EvoquaConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities = [EvoquaMeasurement(coordinator, key) for key in FLOW_POINTS]
    entities.extend(EvoquaValue(coordinator, key) for key in FLOW_TEXTS)
    async_add_entities(entities)


class EvoquaMeasurement(EvoquaEntity, SensorEntity):
    """A FLOAT read using the documented address and device-provided unit."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self.key = key
        self._attr_suggested_display_precision = FLOW_POINTS[key].precision
        self._attr_icon = {
            "chlorine": "mdi:water", "ph": "mdi:ph", "orp": "mdi:flash",
            "total_chlorine": "mdi:water", "conductivity": "mdi:current-ac",
            "temperature": "mdi:thermometer", "circulation": "mdi:waves-arrow-right",
            "analog_input_2": "mdi:gauge",
        }.get(key, "mdi:gauge")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.measurements[self.key].value

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.coordinator.data.measurements[self.key].unit

    @property
    def device_class(self) -> SensorDeviceClass | None:
        if self.key.startswith("temperature") and self.native_unit_of_measurement in ("°C", "°F"):
            return SensorDeviceClass.TEMPERATURE
        return None

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None

    @property
    def extra_state_attributes(self) -> dict:
        point = FLOW_POINTS[self.key]
        return {"modbus_wire_address": point.address, "byte_order": point.order}


class EvoquaValue(EvoquaEntity, SensorEntity):
    """Identity, device clock, operating flags and diagnostic information."""

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self.key = key
        if key in ("system_name", "software_version", "function_word") or key.endswith(("_unit", "_error_code", "_mode_code")) or key in RAW_STATUS:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if key.endswith(("_error_code", "_mode_code", "_unit")) or key in RAW_STATUS or key == "function_word":
            self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> str | int | None:
        return self.coordinator.data.values.get(self.key)

    @property
    def available(self):
        return super().available and self.native_value is not None

    @property
    def extra_state_attributes(self) -> dict:
        flags = self.coordinator.data.details.get(self.key)
        return {"active_flags": flags} if flags is not None else {}
