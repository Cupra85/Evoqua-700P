"""The documented shock chlorination Start/Stop command."""

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory

from .entity import EvoquaEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([EvoquaShockButton(entry.runtime_data, "shock_start_stop")])


class EvoquaShockButton(EvoquaEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:water-sync"

    @property
    def available(self):
        return super().available and self.coordinator.data.values.get("function_word") is not None

    @property
    def extra_state_attributes(self):
        return {"modbus_register": 402000, "modbus_wire_address": 1999,
                "command_mask": "0x0200", "write_function": "FC06",
                "running": self.coordinator.data.binaries.get("shock_chlorination")}

    async def async_press(self):
        await self.coordinator.async_shock_toggle()
