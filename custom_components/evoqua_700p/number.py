"""Explicit controls for the 45 documented RW FLOAT registers."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory

from .entity import EvoquaEntity
from .evoqua import WRITE_POINTS

PARALLEL_UPDATES = 1


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(EvoquaNumber(entry.runtime_data, key) for key in WRITE_POINTS)


class EvoquaNumber(EvoquaEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_step = 0.001

    def __init__(self, coordinator, key):
        # Separate identity from existing read-only sensor with the same key.
        super().__init__(coordinator, key + "_control")
        self.key = key
        self._attr_translation_key = key

    @property
    def native_value(self):
        return self.coordinator.data.measurements[self.key].value

    @property
    def native_unit_of_measurement(self):
        return self.coordinator.data.measurements[self.key].unit

    @property
    def native_min_value(self):
        return self._bounds()[0]

    @property
    def native_max_value(self):
        return self._bounds()[1]

    def _bounds(self):
        point = WRITE_POINTS[self.key]
        if point.kind == "xp":
            return 0, 1000
        if point.kind == "tn":
            return 0, 100
        values = self.coordinator.data.measurements
        low = values[point.channel + "_range_min"].value
        high = values[point.channel + "_range_max"].value
        if low is None or high is None or low >= high:
            return 0, 0
        if point.kind.startswith("hyst"):
            return 0.000001, high - low
        if point.kind.startswith(("min", "max")):
            suffix = ("max" if point.kind.startswith("min") else "min") + point.kind[-1]
            peer = values[point.channel + "_" + suffix].value
            if peer is None or not low <= peer <= high:
                return 0, 0
            if point.kind.startswith("min"):
                high = peer
            else:
                low = peer
        return low, high

    @property
    def available(self):
        low, high = self._bounds()
        return super().available and self.native_value is not None and low <= high and (low, high) != (0, 0)

    @property
    def extra_state_attributes(self):
        point = WRITE_POINTS[self.key]
        attrs = {"modbus_register": 400001 + point.address, "modbus_wire_address": point.address,
                 "byte_order": "CDAB", "write_function": "FC16"}
        if point.kind.startswith("hyst"):
            attrs["device_constraint"] = "1..25 display digits; value uses device engineering units"
        return attrs

    async def async_set_native_value(self, value):
        await self.coordinator.async_write_number(self.key, value)
