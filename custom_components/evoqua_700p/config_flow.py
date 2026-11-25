"""IP-only setup using the Node-RED register configuration."""

from __future__ import annotations

import ipaddress

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import config_validation as cv

from .const import DEFAULTS, DOMAIN
from .evoqua import EvoquaClient, EvoquaError, InvalidDevice


def host_fields(host: str = "") -> vol.Schema:
    return vol.Schema({vol.Required("host", default=host): cv.string})


def normalize_host(host: str) -> str:
    """Only accept an IP, without a scheme, path or embedded port."""
    return str(ipaddress.ip_address(host.strip()))


async def validate(host: str) -> str:
    client = EvoquaClient(host, **{
        key: DEFAULTS[key]
        for key in ("port", "unit_id", "timeout", "register_base", "byte_order", "profile")
    })
    snapshot = await client.async_snapshot(DEFAULTS["channels"], True)
    return f"Evoqua 700P – {snapshot.system_name}"


class EvoquaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def _already_configured(self, host, exclude_entry_id=None) -> bool:
        return any(
            entry.entry_id != exclude_entry_id and entry.data.get("host") == host
            for entry in self._async_current_entries()
        )

    async def _async_host_step(self, step_id, user_input=None, entry=None) -> ConfigFlowResult:
        errors = {}
        host = (user_input or {}).get("host", entry.data["host"] if entry else "")
        if user_input is not None:
            try:
                host = normalize_host(host)
                if self._already_configured(host, entry.entry_id if entry else None):
                    return self.async_abort(reason="already_configured")
                title = await validate(host)
            except InvalidDevice:
                errors["base"] = "invalid_device"
            except EvoquaError:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["host"] = "invalid_host"
            else:
                if entry:
                    return self.async_update_reload_and_abort(entry, data_updates={"host": host})
                return self.async_create_entry(title=title, data={"host": host})
        return self.async_show_form(step_id=step_id, data_schema=host_fields(host), errors=errors)

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        return await self._async_host_step("user", user_input)

    async def async_step_reconfigure(self, user_input=None) -> ConfigFlowResult:
        return await self._async_host_step("reconfigure", user_input, self._get_reconfigure_entry())
