"""Support for Tuya Smart IR AC using local control."""
import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MIDDLE,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Mapping des modes HVAC vers les commandes IR Tuya
HVAC_MODE_TO_TUYA = {
    HVACMode.OFF: "0",
    HVACMode.AUTO: "1",
    HVACMode.COOL: "2",
    HVACMode.DRY: "3",
    HVACMode.FAN_ONLY: "4",
    HVACMode.HEAT: "5",
}

TUYA_TO_HVAC_MODE = {v: k for k, v in HVAC_MODE_TO_TUYA.items()}

# Mapping des vitesses de ventilation
FAN_MODE_TO_TUYA = {
    FAN_AUTO: "0",
    FAN_LOW: "1",
    FAN_MIDDLE: "2",
    FAN_HIGH: "3",
}

TUYA_TO_FAN_MODE = {v: k for k, v in FAN_MODE_TO_TUYA.items()}

# Mapping du swing
SWING_MODE_TO_TUYA = {
    SWING_OFF: "0",
    SWING_VERTICAL: "1",
    SWING_HORIZONTAL: "2",
    SWING_BOTH: "3",
}

TUYA_TO_SWING_MODE = {v: k for k, v in SWING_MODE_TO_TUYA.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tuya IR AC climate entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_id = hass.data[DOMAIN][entry.entry_id]["device_id"]
    
    async_add_entities([TuyaIRClimate(coordinator, entry, device_id)])


class TuyaIRClimate(CoordinatorEntity, ClimateEntity):
    """Representation of a Tuya IR AC."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_min_temp = 16
    _attr_max_temp = 30
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.HEAT,
    ]
    _attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MIDDLE, FAN_HIGH]
    _attr_swing_modes = [SWING_OFF, SWING_VERTICAL, SWING_HORIZONTAL, SWING_BOTH]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator, entry, device_id):
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._device_id = device_id
        self._attr_name = entry.data.get("name", "IR AC")
        self._attr_unique_id = f"{device_id}_climate"
        
        # État local
        self._hvac_mode = HVACMode.OFF
        self._target_temperature = 24
        self._fan_mode = FAN_AUTO
        self._swing_mode = SWING_OFF

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._attr_name,
            "manufacturer": "Tuya",
            "model": "IR AC Controller",
        }

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if self.coordinator.data and self.coordinator.data.get("climate"):
            # Essayer de lire depuis les données du coordinateur
            climate_data = self.coordinator.data["climate"]
            if isinstance(climate_data, dict) and "dps" in climate_data:
                mode_value = climate_data["dps"].get("1", "0")
                return TUYA_TO_HVAC_MODE.get(str(mode_value), HVACMode.OFF)
        return self._hvac_mode

    @property
    def target_temperature(self) -> float:
        """Return target temperature."""
        if self.coordinator.data and self.coordinator.data.get("climate"):
            climate_data = self.coordinator.data["climate"]
            if isinstance(climate_data, dict) and "dps" in climate_data:
                temp = climate_data["dps"].get("2", 24)
                return float(temp)
        return self._target_temperature

    @property
    def fan_mode(self) -> str:
        """Return current fan mode."""
        if self.coordinator.data and self.coordinator.data.get("climate"):
            climate_data = self.coordinator.data["climate"]
            if isinstance(climate_data, dict) and "dps" in climate_data:
                fan_value = climate_data["dps"].get("3", "0")
                return TUYA_TO_FAN_MODE.get(str(fan_value), FAN_AUTO)
        return self._fan_mode

    @property
    def swing_mode(self) -> str:
        """Return current swing mode."""
        if self.coordinator.data and self.coordinator.data.get("climate"):
            climate_data = self.coordinator.data["climate"]
            if isinstance(climate_data, dict) and "dps" in climate_data:
                swing_value = climate_data["dps"].get("4", "0")
                return TUYA_TO_SWING_MODE.get(str(swing_value), SWING_OFF)
        return self._swing_mode

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            temperature = int(kwargs[ATTR_TEMPERATURE])
            self._target_temperature = temperature
            
            # Envoi de la commande au device
            await self.coordinator.set_climate_value("2", temperature)
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if hvac_mode in HVAC_MODE_TO_TUYA:
            self._hvac_mode = hvac_mode
            mode_value = HVAC_MODE_TO_TUYA[hvac_mode]
            
            await self.coordinator.set_climate_value("1", mode_value)
            await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        if fan_mode in FAN_MODE_TO_TUYA:
            self._fan_mode = fan_mode
            fan_value = FAN_MODE_TO_TUYA[fan_mode]
            
            await self.coordinator.set_climate_value("3", fan_value)
            await self.coordinator.async_request_refresh()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new swing mode."""
        if swing_mode in SWING_MODE_TO_TUYA:
            self._swing_mode = swing_mode
            swing_value = SWING_MODE_TO_TUYA[swing_mode]
            
            await self.coordinator.set_climate_value("4", swing_value)
            await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)
