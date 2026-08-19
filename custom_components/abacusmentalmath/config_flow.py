"""Config flow for the Abacus Mental Math integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from .api import AbacusMentalMathAuthError, AbacusMentalMathClient, AbacusMentalMathError
from .const import (
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class AbacusMentalMathFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Abacus Mental Math."""

    VERSION = 1

    async def _async_validate(self, email: str, password: str) -> dict[str, str]:
        """Try logging in; return a dict of form errors (empty on success)."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        client = AbacusMentalMathClient(session, email, password)
        try:
            await client.async_login()
        except AbacusMentalMathAuthError:
            return {"base": "invalid_auth"}
        except AbacusMentalMathError:
            return {"base": "cannot_connect"}
        return {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL]
            errors = await self._async_validate(email, user_input[CONF_PASSWORD])
            if not errors:
                await self.async_set_unique_id(email.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Abacus Mental Math ({email})",
                    data={CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
        return self.async_show_form(step_id="user", data_schema=AUTH_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            errors = await self._async_validate(reauth_entry.data[CONF_EMAIL], user_input[CONF_PASSWORD])
            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={**reauth_entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"email": reauth_entry.data[CONF_EMAIL]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> AbacusMentalMathOptionsFlow:
        return AbacusMentalMathOptionsFlow()


class AbacusMentalMathOptionsFlow(OptionsFlowWithReload):
    """Let the user tune the poll interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        default_minutes = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, int(DEFAULT_SCAN_INTERVAL.total_seconds() / 60)
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL_MINUTES, default=default_minutes): vol.All(
                    vol.Coerce(int),
                    vol.Range(
                        min=int(MIN_SCAN_INTERVAL.total_seconds() / 60),
                        max=int(MAX_SCAN_INTERVAL.total_seconds() / 60),
                    ),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
