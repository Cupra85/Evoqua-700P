"""Common entity identity, independent of the controller's IP address."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EvoquaCoordinator


class EvoquaEntity(CoordinatorEntity[EvoquaCoordinator]):
    """An entity belonging to one configured 700 P."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EvoquaCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.title,
            manufacturer="Evoqua / Wallace & Tiernan",
            model=self.coordinator.data.system_name,
            sw_version=self.coordinator.data.software,
        )
