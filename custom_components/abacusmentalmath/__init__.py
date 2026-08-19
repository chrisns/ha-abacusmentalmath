"""The Abacus Mental Math integration (unofficial)."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import AbacusMentalMathClient
from .const import CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL
from .coordinator import AbacusMentalMathConfigEntry, AbacusMentalMathCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: AbacusMentalMathConfigEntry) -> bool:
    """Set up Abacus Mental Math from a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    client = AbacusMentalMathClient(
        session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD]
    )

    minutes = entry.options.get(CONF_SCAN_INTERVAL_MINUTES)
    update_interval = timedelta(minutes=minutes) if minutes else DEFAULT_SCAN_INTERVAL

    coordinator = AbacusMentalMathCoordinator(hass, entry, client, update_interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AbacusMentalMathConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
