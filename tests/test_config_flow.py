"""Config + options + reauth flow tests, using HA's own test harness with mocked API calls.

No real network calls: AbacusMentalMathClient.async_login is patched throughout.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abacusmentalmath.api import AbacusMentalMathAuthError, AbacusMentalMathError
from custom_components.abacusmentalmath.const import CONF_SCAN_INTERVAL_MINUTES, DOMAIN

LOGIN_PATH = "custom_components.abacusmentalmath.config_flow.AbacusMentalMathClient.async_login"


async def test_user_flow_success(hass):
    with patch(LOGIN_PATH, new_callable=AsyncMock):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["type"] is FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: "parent@example.com", CONF_PASSWORD: "hunter2"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Abacus Mental Math (parent@example.com)"
    assert result["data"] == {CONF_EMAIL: "parent@example.com", CONF_PASSWORD: "hunter2"}


async def test_user_flow_invalid_auth(hass):
    with patch(LOGIN_PATH, new_callable=AsyncMock, side_effect=AbacusMentalMathAuthError("nope")):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: "parent@example.com", CONF_PASSWORD: "wrong"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass):
    with patch(LOGIN_PATH, new_callable=AsyncMock, side_effect=AbacusMentalMathError("boom")):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: "parent@example.com", CONF_PASSWORD: "hunter2"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_aborts_on_duplicate_email(hass):
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="parent@example.com",
        data={CONF_EMAIL: "parent@example.com", CONF_PASSWORD: "old"},
    ).add_to_hass(hass)

    with patch(LOGIN_PATH, new_callable=AsyncMock):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: "Parent@Example.com", CONF_PASSWORD: "hunter2"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow_success(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="parent@example.com",
        data={CONF_EMAIL: "parent@example.com", CONF_PASSWORD: "old"},
    )
    entry.add_to_hass(hass)

    with patch(LOGIN_PATH, new_callable=AsyncMock):
        result = await entry.start_reauth_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new-password"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new-password"


async def test_options_flow_sets_scan_interval(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="parent@example.com",
        data={CONF_EMAIL: "parent@example.com", CONF_PASSWORD: "hunter2"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL_MINUTES: 30}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL_MINUTES] == 30
