"""Data update coordinator for the Abacus Mental Math integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AbacusMentalMathAuthError, AbacusMentalMathClient, AbacusMentalMathError, StudentStats
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type AbacusMentalMathConfigEntry = ConfigEntry[AbacusMentalMathCoordinator]


class AbacusMentalMathCoordinator(DataUpdateCoordinator[dict[int, StudentStats]]):
    """Polls the parent account and re-discovers children on every refresh."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: AbacusMentalMathConfigEntry,
        client: AbacusMentalMathClient,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, StudentStats]:
        try:
            students = await self.client.async_list_students()
            stats = await asyncio.gather(
                *(self.client.async_get_student_stats(student) for student in students)
            )
        except AbacusMentalMathAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except AbacusMentalMathError as err:
            raise UpdateFailed(str(err)) from err

        return {item.student.id: item for item in stats}
