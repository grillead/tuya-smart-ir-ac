"""The Tuya Smart IR AC Local integration."""
import asyncio
import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import tinytuya

_LOGGER = logging.getLogger(__name__)

DOMAIN = "tuya_smart_ir_ac_local"
PLATFORMS = ["climate", "sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Tuya Smart IR AC Local component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Tuya Smart IR AC Local from a config entry."""
    
    hub_ip = entry.data["hub_ip"]
    hub_id = entry.data["hub_id"]
    hub_key = entry.data["hub_local_key"]
    device_id = entry.data.get("device_id", "")
    device_key = entry.data.get("device_local_key", "")
    
    update_interval = entry.options.get("update_interval", 60)

    # Création du coordinateur pour la mise à jour des données
    coordinator = TuyaLocalCoordinator(
        hass, hub_ip, hub_id, hub_key, device_id, device_key, update_interval
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "hub_ip": hub_ip,
        "hub_id": hub_id,
        "hub_key": hub_key,
        "device_id": device_id,
        "device_key": device_key,
    }

    # Configuration des plateformes
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class TuyaLocalCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Tuya data from local devices."""

    def __init__(self, hass, hub_ip, hub_id, hub_key, device_id, device_key, update_interval):
        """Initialize."""
        self.hub_device = tinytuya.Device(hub_id, hub_ip, hub_key)
        self.hub_device.set_version(3.3)
        
        self.climate_device = None
        if device_id and device_key:
            # Si on a un device climatisation séparé (virtual device)
            self.climate_device = tinytuya.Device(device_id, hub_ip, device_key)
            self.climate_device.set_version(3.3)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from Tuya devices."""
        try:
            # Récupération du status du HUB
            hub_data = await self.hass.async_add_executor_job(self.hub_device.status)
            
            climate_data = None
            if self.climate_device:
                climate_data = await self.hass.async_add_executor_job(
                    self.climate_device.status
                )
            
            return {
                "hub": hub_data,
                "climate": climate_data,
            }
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Tuya devices: {err}")

    async def send_ir_command(self, remote_id, command_data):
        """Send IR command through the hub."""
        try:
            # Pour les commandes IR via le hub
            # Format typique: {"control": "send_ir", "head": "", "key1": remote_id, "type": 0, "delay": 300}
            result = await self.hass.async_add_executor_job(
                self.hub_device.set_value,
                "201",  # DP pour IR control
                command_data
            )
            return result
        except Exception as err:
            _LOGGER.error("Error sending IR command: %s", err)
            return None

    async def set_climate_value(self, dp_id, value):
        """Set a value on the climate device."""
        try:
            if self.climate_device:
                result = await self.hass.async_add_executor_job(
                    self.climate_device.set_value,
                    dp_id,
                    value
                )
            else:
                # Si pas de device séparé, envoyer via le hub
                result = await self.hass.async_add_executor_job(
                    self.hub_device.set_value,
                    dp_id,
                    value
                )
            return result
        except Exception as err:
            _LOGGER.error("Error setting climate value: %s", err)
            return None
