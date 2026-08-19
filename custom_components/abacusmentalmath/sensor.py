"""Sensor platform for Abacus Mental Math — one set of metrics per child."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import StudentStats
from .const import DOMAIN, MANUFACTURER
from .coordinator import AbacusMentalMathConfigEntry, AbacusMentalMathCoordinator


@dataclass(frozen=True, kw_only=True)
class AbacusSensorDescription(SensorEntityDescription):
    """A sensor description with the function that reads its value off StudentStats."""

    value_fn: Callable[[StudentStats], StateType]


SENSORS: tuple[AbacusSensorDescription, ...] = (
    AbacusSensorDescription(
        key="units_today",
        translation_key="units_today",
        icon="mdi:abacus",
        native_unit_of_measurement="units",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.units_today,
    ),
    AbacusSensorDescription(
        key="units_yesterday",
        translation_key="units_yesterday",
        icon="mdi:abacus",
        native_unit_of_measurement="units",
        value_fn=lambda s: s.units_yesterday,
    ),
    AbacusSensorDescription(
        key="units_this_week",
        translation_key="units_this_week",
        icon="mdi:abacus",
        native_unit_of_measurement="units",
        value_fn=lambda s: s.units_this_week,
    ),
    AbacusSensorDescription(
        key="units_this_month",
        translation_key="units_this_month",
        icon="mdi:abacus",
        native_unit_of_measurement="units",
        value_fn=lambda s: s.units_this_month,
    ),
    AbacusSensorDescription(
        key="coins",
        translation_key="coins",
        icon="mdi:circle-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.coin_amount,
    ),
    AbacusSensorDescription(
        key="diamonds",
        translation_key="diamonds",
        icon="mdi:diamond-stone",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.diamond_amount,
    ),
    AbacusSensorDescription(
        key="last_active",
        translation_key="last_active",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda s: s.last_active_at,
    ),
    AbacusSensorDescription(
        key="wins_daily",
        translation_key="wins_daily",
        icon="mdi:trophy-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.wins_daily,
    ),
    AbacusSensorDescription(
        key="wins_weekly",
        translation_key="wins_weekly",
        icon="mdi:trophy-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.wins_weekly,
    ),
    AbacusSensorDescription(
        key="wins_monthly",
        translation_key="wins_monthly",
        icon="mdi:trophy-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.wins_monthly,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AbacusMentalMathConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a sensor per metric for every child, and pick up newly-added children later."""
    coordinator = entry.runtime_data
    known_student_ids: set[int] = set()

    @callback
    def _add_new_students() -> None:
        new_ids = set(coordinator.data) - known_student_ids
        if not new_ids:
            return
        known_student_ids.update(new_ids)
        async_add_entities(
            AbacusStudentSensor(coordinator, student_id, description)
            for student_id in new_ids
            for description in SENSORS
        )

    _add_new_students()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_students))


class AbacusStudentSensor(CoordinatorEntity[AbacusMentalMathCoordinator], SensorEntity):
    """One metric for one child."""

    _attr_has_entity_name = True
    entity_description: AbacusSensorDescription

    def __init__(
        self,
        coordinator: AbacusMentalMathCoordinator,
        student_id: int,
        description: AbacusSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._student_id = student_id
        self._attr_unique_id = f"{student_id}_{description.key}"
        stats = coordinator.data[student_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(student_id))},
            name=f"{stats.student.first_name} {stats.student.last_name}".strip(),
            manufacturer=MANUFACTURER,
            model="Student",
        )

    @property
    def available(self) -> bool:
        return super().available and self._student_id in self.coordinator.data

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data[self._student_id])
