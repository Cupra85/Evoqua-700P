"""Configure and test the controller before saving settings."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import DEFAULTS, DOMAIN
from .evoqua import BYTE_ORDERS, CHANNELS, EvoquaClient, EvoquaError, InvalidDevice

NETWORK_KEYS = ("host", "port", "unit_id", "timeout", "register_base", "byte_order")


def network_fields(values: dict[str, Any]) -> dict:
    return {
        vol.Required("host", default=values.get("host", "")): cv.string,
        vol.Required("port", default=values["port"]): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required("unit_id", default=values["unit_id"]): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        vol.Required("timeout", default=values["timeout"]): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        vol.Required("register_base", default=values["register_base"]): vol.In([400001, 400000]),
        vol.Required("byte_order", default=values["byte_order"]): vol.In(BYTE_ORDERS),
    }


def behavior_fields(values: dict[str, Any]) -> dict:
    return {
        vol.Required("channels", default=values["channels"]): vol.All(
            cv.multi_select({key: channel.label for key, channel in CHANNELS.items()}),
            vol.Length(min=1),
        ),
        vol.Required("scan_interval", default=values["scan_interval"]): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
        vol.Required("include_status", default=values["include_status"]): cv.boolean,
    }


def normalize_settings(settings: dict[str, Any]) -> dict[str, Any]:
    result = {**settings}
    result["host"] = settings["host"].strip().lower().rstrip(".")
    if not result["host"] or any(char.isspace() for char in result["host"]) or "/" in result["host"]:
        raise ValueError("Enter an IP address or hostname without a URL scheme")
    return result


async def validate(settings: dict[str, Any]) -> str:
    client = EvoquaClient(**{key: settings[key] for key in NETWORK_KEYS})
    snapshot = await client.async_snapshot(settings["channels"], settings["include_status"])
    return snapshot.system_name


def endpoint(settings: dict[str, Any]) -> tuple:
    return settings["host"], settings["port"], settings["unit_id"]


class EvoquaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def _already_configured(self, settings, exclude_entry_id=None) -> bool:
        return any(
            entry.entry_id != exclude_entry_id
            and endpoint({**DEFAULTS, **entry.data, **entry.options}) == endpoint(settings)
            for entry in self._async_current_entries()
        )

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        values = {**DEFAULTS, **(user_input or {})}
        if user_input is not None:
            try:
                settings = normalize_settings(values)
                if self._already_configured(settings):
                    return self.async_abort(reason="already_configured")
                name = await validate(settings)
            except InvalidDevice:
                errors["base"] = "invalid_device"
            except EvoquaError:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["host"] = "invalid_host"
            else:
                return self.async_create_entry(title=name, data=settings)
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({**network_fields(values), **behavior_fields(values)}), errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        values = {**DEFAULTS, **entry.data, **entry.options, **(user_input or {})}
        errors = {}
        if user_input is not None:
            try:
                settings = normalize_settings(values)
                if self._already_configured(settings, entry.entry_id):
                    return self.async_abort(reason="already_configured")
                await validate(settings)
            except InvalidDevice:
                errors["base"] = "invalid_device"
            except EvoquaError:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["host"] = "invalid_host"
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={key: settings[key] for key in NETWORK_KEYS},
                )
        return self.async_show_form(
            step_id="reconfigure", data_schema=vol.Schema(network_fields(values)), errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> EvoquaOptionsFlow:
        return EvoquaOptionsFlow()


class EvoquaOptionsFlow(config_entries.OptionsFlowWithReload):
    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        values = {**DEFAULTS, **self.config_entry.data, **self.config_entry.options, **(user_input or {})}
        errors = {}
        if user_input is not None:
            try:
                await validate(values)
            except InvalidDevice:
                errors["base"] = "invalid_device"
            except EvoquaError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(behavior_fields(values)), errors=errors,
        )
