"""Fetch one consistent snapshot for all Home Assistant entities."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULTS, DOMAIN
from .evoqua import EvoquaClient, EvoquaError, Snapshot

_LOGGER = logging.getLogger(__name__)


class EvoquaCoordinator(DataUpdateCoordinator[Snapshot]):
    """Poll the controller and make entities unavailable after any failed poll."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.settings = {**DEFAULTS, **entry.data, **entry.options}
        self.client = EvoquaClient(**{
            key: self.settings[key]
            for key in ("host", "port", "unit_id", "timeout", "register_base", "byte_order")
        })
        super().__init__(
            hass, _LOGGER, name=DOMAIN, config_entry=entry,
            update_interval=timedelta(seconds=self.settings["scan_interval"]),
        )

    async def _async_update_data(self) -> Snapshot:
        try:
            return await self.client.async_snapshot(
                self.settings["channels"], self.settings["include_status"]
            )
        except EvoquaError as err:
            raise UpdateFailed(str(err)) from err
