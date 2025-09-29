"""Support for Tuya temperature and humidity sensors."""
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    hub_id = hass.data[DOMAIN][entry.entry_id]["hub_id"]
    device_id = hass.data[DOMAIN][entry.entry_id]["device_id"]
    
    entities = []
    
    # Capteurs du hub (si disponibles)
    if coordinator.data and coordinator.data.get("hub"):
        hub_data = coordinator.data["hub"]
        if isinstance(hub_data, dict) and "dps" in hub_data:
            # Vérifier si température disponible (DP courant: 18 pour temp, 19 pour humidité)
            if "18" in hub_data["dps"]:
                entities.append(TuyaTemperatureSensor(coordinator, entry, hub_id, "hub"))
            if "19" in hub_data["dps"]:
                entities.append(TuyaHumiditySensor(coordinator, entry, hub_id, "hub"))
    
    # Capteurs du device climatisation (si disponibles)
    if device_id and coordinator.data and coordinator.data.get("climate"):
        climate_data = coordinator.data["climate"]
        if isinstance(climate_data, dict) and "dps" in climate_data:
            if "18" in climate_data["dps"]:
                entities.append(TuyaTemperatureSensor(coordinator, entry, device_id, "climate"))
            if "19" in climate_data["dps"]:
                entities.append(TuyaHumiditySensor(coordinator, entry, device_id, "climate"))
    
    if entities:
        async_add_entities(entities)


class TuyaTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tuya temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, entry, device_id, source):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._source = source
        self._attr_name = f"{entry.data.get('name', 'IR AC')} Temperature"
        self._attr_unique_id = f"{device_id}_temperature_{source}"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"Tuya {self._source.capitalize()}",
            "manufacturer": "Tuya",
            "model": "IR Hub" if self._source == "hub" else "IR AC Controller",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            data = self.coordinator.data.get(self._source)
            if data and isinstance(data, dict) and "dps" in data:
                # La température est souvent en dixièmes de degrés
                temp_raw = data["dps"].get("18")
                if temp_raw is not None:
                    try:
                        return float(temp_raw) / 10.0
                    except (ValueError, TypeError):
                        return None
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.native_value is not None
        )


class TuyaHumiditySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tuya humidity sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, entry, device_id, source):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._source = source
        self._attr_name = f"{entry.data.get('name', 'IR AC')} Humidity"
        self._attr_unique_id = f"{device_id}_humidity_{source}"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"Tuya {self._source.capitalize()}",
            "manufacturer": "Tuya",
            "model": "IR Hub" if self._source == "hub" else "IR AC Controller",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            data = self.coordinator.data.get(self._source)
            if data and isinstance(data, dict) and "dps" in data:
                humidity = data["dps"].get("19")
                if humidity is not None:
                    try:
                        return float(humidity)
                    except (ValueError, TypeError):
                        return None
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.native_value is not None
        )
