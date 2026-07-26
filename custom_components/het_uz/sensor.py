"""Sensor platform for HET.uz."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_UZS, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LOGIN, DOMAIN
from .coordinator import HetUzDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class HetUzSensorEntityDescription(SensorEntityDescription):
    """Describe a HET.uz sensor entity."""

    value_key: str
    transform: Callable[[Any], Any] | None = None


def _divide(value: Any, divisor: float) -> float | None:
    """Divide API integer value, returning None for null inputs."""
    if value is None:
        return None
    return float(value) / divisor


SENSOR_TYPES: tuple[HetUzSensorEntityDescription, ...] = (
    HetUzSensorEntityDescription(
        key="balance",
        translation_key="balance",
        value_key="balance",
        transform=lambda v: _divide(v, 100),
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_UZS,
    ),
    HetUzSensorEntityDescription(
        key="last_crawl_reading",
        translation_key="last_crawl_reading",
        value_key="lastCrawlReading",
        transform=lambda v: _divide(v, 1000),
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HetUzSensorEntityDescription(
        key="last_crawl_date",
        translation_key="last_crawl_date",
        value_key="lastCrawlDate",
    ),
    HetUzSensorEntityDescription(
        key="last_payment",
        translation_key="last_payment",
        value_key="lastPayment",
        transform=lambda v: _divide(v, 100),
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_UZS,
    ),
    HetUzSensorEntityDescription(
        key="last_payment_date",
        translation_key="last_payment_date",
        value_key="lastPaymentDate",
    ),
    HetUzSensorEntityDescription(
        key="current_month_calc_kwh",
        translation_key="current_month_calc_kwh",
        value_key="currentMonthCalcKwh",
        transform=lambda v: _divide(v, 1000),
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HetUzSensorEntityDescription(
        key="current_month_calc_sum",
        translation_key="current_month_calc_sum",
        value_key="currentMonthCalcSum",
        transform=lambda v: _divide(v, 100),
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_UZS,
    ),
    HetUzSensorEntityDescription(
        key="eco_current_month_calc_kwh",
        translation_key="eco_current_month_calc_kwh",
        value_key="ecoCurrentMonthCalcKwh",
        transform=lambda v: _divide(v, 1000),
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HET.uz sensors from a config entry."""
    coordinator: HetUzDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        HetUzSensor(coordinator, description, entry)
        for description in SENSOR_TYPES
    )


class HetUzSensor(CoordinatorEntity[HetUzDataUpdateCoordinator], SensorEntity):
    """Representation of a HET.uz sensor."""

    entity_description: HetUzSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HetUzDataUpdateCoordinator,
        description: HetUzSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"HET.uz {entry.data[CONF_LOGIN]}",
            "manufacturer": "HET.uz",
            "model": "Household Consumer",
        }

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        raw_value = self.coordinator.data.get(self.entity_description.value_key)
        if raw_value is None:
            return None

        if self.entity_description.transform:
            return self.entity_description.transform(raw_value)

        return raw_value
