"""Diagnostics support for Abacus Mental Math."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .coordinator import AbacusMentalMathConfigEntry

TO_REDACT = {CONF_PASSWORD, "username", "last_active_at", "first_name", "last_name"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AbacusMentalMathConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "entry_options": dict(entry.options),
        "students": [
            async_redact_data(asdict(stats), TO_REDACT) for stats in coordinator.data.values()
        ],
    }
