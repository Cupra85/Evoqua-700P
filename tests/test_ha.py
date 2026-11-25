"""Real Home Assistant config flow, platform setup and migration tests."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER, SOURCE_RECONFIGURE
from pytest_homeassistant.common import MockConfigEntry

from custom_components.evoqua_700p.const import DOMAIN
from custom_components.evoqua_700p.evoqua import (
    FLOW_BINARIES, FLOW_POINTS, FLOW_TEXTS, EvoquaError, Measurement, Snapshot,
)


def snapshot():
    return Snapshot(
        "Pool", "V:2.06",
        {key: Measurement(1.25, point.unit) for key, point in FLOW_POINTS.items()},
        values={key: (0 if key == "chlorine_error_code" else "Test") for key in FLOW_TEXTS},
        binaries={key: False for key in FLOW_BINARIES},
    )


async def test_only_ip_is_shown_and_saved(hass):
    with patch("custom_components.evoqua_700p.config_flow.validate", return_value="Evoqua 700P – Pool") as validate, \
         patch("custom_components.evoqua_700p.async_setup_entry", return_value=True):
        form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        assert form["type"] == "form"
        assert {str(key) for key in form["data_schema"].schema} == {"host"}
        result = await hass.config_entries.flow.async_configure(form["flow_id"], {"host": " 192.0.2.10 "})
        assert result["type"] == "create_entry"
        assert result["data"] == {"host": "192.0.2.10"}
        validate.assert_awaited_once_with("192.0.2.10")
        await hass.async_block_till_done()


@pytest.mark.parametrize("host", ["", "http://192.0.2.10", "192.0.2.10:502", "999.1.1.1"])
async def test_invalid_ip_does_not_connect(hass, host):
    with patch("custom_components.evoqua_700p.config_flow.validate") as validate:
        form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(form["flow_id"], {"host": host})
        assert result["errors"] == {"host": "invalid_host"}
        validate.assert_not_called()


async def test_connection_failure_keeps_single_field(hass):
    with patch("custom_components.evoqua_700p.config_flow.validate", side_effect=EvoquaError("offline")):
        form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(form["flow_id"], {"host": "192.0.2.10"})
        assert result["errors"] == {"base": "cannot_connect"}
        assert {str(key) for key in result["data_schema"].schema} == {"host"}


async def test_duplicate_ip_is_rejected(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"host": "192.0.2.10"})
    entry.add_to_hass(hass)
    with patch("custom_components.evoqua_700p.config_flow.validate") as validate:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={"host": "192.0.2.10"},
        )
        assert result["type"] == "abort"
        assert result["reason"] == "already_configured"
        validate.assert_not_called()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_read_only_entities_load_and_unload(hass):
    entry = MockConfigEntry(domain=DOMAIN, title="Evoqua 700P – Pool", version=2, data={"host": "192.0.2.10"})
    entry.add_to_hass(hass)
    with patch("custom_components.evoqua_700p.evoqua.EvoquaClient.async_snapshot", return_value=snapshot()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        states = hass.states.async_all()
        assert len(states) == len(FLOW_POINTS) + len(FLOW_TEXTS) + len(FLOW_BINARIES)
        assert {state.domain for state in states} == {"sensor", "binary_sensor"}
        assert any(state.state == "1.25" for state in states)
        assert all(state.state not in ("unavailable", "unknown") for state in states)
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_old_entries_migrate_without_losing_ip(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, version=1,
        data={"host": "192.0.2.10", "unit_id": 2, "port": 1234},
        options={"scan_interval": 30},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.evoqua_700p.evoqua.EvoquaClient.async_snapshot", return_value=snapshot()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.version == 2
        assert dict(entry.data) == {"host": "192.0.2.10"}
        assert dict(entry.options) == {}
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_reconfigure_only_changes_ip(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"host": "192.0.2.10"})
    entry.add_to_hass(hass)
    with patch("custom_components.evoqua_700p.config_flow.validate", return_value="Evoqua 700P – Pool"), \
         patch("custom_components.evoqua_700p.evoqua.EvoquaClient.async_snapshot", return_value=snapshot()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        form = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )
        assert {str(key) for key in form["data_schema"].schema} == {"host"}
        result = await hass.config_entries.flow.async_configure(form["flow_id"], {"host": "192.0.2.11"})
        assert result["reason"] == "reconfigure_successful"
        assert dict(entry.data) == {"host": "192.0.2.11"}
        await hass.async_block_till_done()
        assert await hass.config_entries.async_unload(entry.entry_id)
