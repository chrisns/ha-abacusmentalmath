"""End-to-end setup test: config entry -> coordinator -> sensor entities.

Mocks only the network boundary (AbacusMentalMathClient methods) so the
real coordinator, __init__.async_setup_entry, and sensor.py entity wiring
all run for real against HA's test harness.
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, STATE_UNAVAILABLE
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abacusmentalmath.api import Student, StudentStats
from custom_components.abacusmentalmath.const import DOMAIN

CLIENT = "custom_components.abacusmentalmath.api.AbacusMentalMathClient"


def _stats(student_id: int, name: str, units_today: int) -> StudentStats:
    return StudentStats(
        student=Student(id=student_id, first_name=name, last_name="Kid"),
        username=f"{name}Kid",
        coin_amount=5,
        diamond_amount=1,
        last_active_at=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
        wins_daily=0,
        wins_weekly=0,
        wins_monthly=0,
        units_today=units_today,
        units_yesterday=0,
        units_this_week=units_today,
        units_this_month=units_today,
    )


async def test_setup_creates_one_sensor_per_child_per_metric(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="parent@example.com",
        data={CONF_EMAIL: "parent@example.com", CONF_PASSWORD: "hunter2"},
    )
    entry.add_to_hass(hass)

    with (
        patch(f"{CLIENT}.async_list_students", new_callable=AsyncMock, return_value=[Student(1, "Freya", "Kid")]),
        patch(f"{CLIENT}.async_get_student_stats", new_callable=AsyncMock, return_value=_stats(1, "Freya", 5)),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.freya_kid_units_today")
    assert state is not None
    assert state.state == "5"

    coins = hass.states.get("sensor.freya_kid_coins")
    assert coins is not None and coins.state == "5"


async def test_new_child_added_after_second_refresh(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="parent@example.com",
        data={CONF_EMAIL: "parent@example.com", CONF_PASSWORD: "hunter2"},
    )
    entry.add_to_hass(hass)

    with (
        patch(f"{CLIENT}.async_list_students", new_callable=AsyncMock, return_value=[Student(1, "Freya", "Kid")]),
        patch(f"{CLIENT}.async_get_student_stats", new_callable=AsyncMock, return_value=_stats(1, "Freya", 5)),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("sensor.noah_kid_units_today") is None

    with (
        patch(
            f"{CLIENT}.async_list_students",
            new_callable=AsyncMock,
            return_value=[Student(1, "Freya", "Kid"), Student(2, "Noah", "Kid")],
        ),
        patch(
            f"{CLIENT}.async_get_student_stats",
            new_callable=AsyncMock,
            side_effect=lambda student: _stats(student.id, student.first_name, {1: 5, 2: 3}[student.id]),
        ),
    ):
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()

    state = hass.states.get("sensor.noah_kid_units_today")
    assert state is not None
    assert state.state == "3"
    # Freya's existing entity keeps updating normally alongside the new one.
    assert hass.states.get("sensor.freya_kid_units_today").state == "5"


async def test_child_dropped_from_account_goes_unavailable(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="parent@example.com",
        data={CONF_EMAIL: "parent@example.com", CONF_PASSWORD: "hunter2"},
    )
    entry.add_to_hass(hass)

    with (
        patch(f"{CLIENT}.async_list_students", new_callable=AsyncMock, return_value=[Student(1, "Freya", "Kid")]),
        patch(f"{CLIENT}.async_get_student_stats", new_callable=AsyncMock, return_value=_stats(1, "Freya", 5)),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    with patch(f"{CLIENT}.async_list_students", new_callable=AsyncMock, return_value=[]):
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()

    assert hass.states.get("sensor.freya_kid_units_today").state == STATE_UNAVAILABLE
