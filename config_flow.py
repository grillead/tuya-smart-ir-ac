"""Config flow for Tuya Smart IR AC Local."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
import tinytuya

_LOGGER = logging.getLogger(__name__)

DOMAIN = "tuya_smart_ir_ac_local"

class TuyaSmartIRAcLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuya Smart IR AC Local."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validation de la connexion
            try:
                hub_ip = user_input["hub_ip"]
                hub_id = user_input["hub_id"]
                hub_key = user_input["hub_local_key"]
                
                # Test de connexion au HUB IR
                device = tinytuya.Device(hub_id, hub_ip, hub_key)
                device.set_version(3.3)
                
                # Tentative de récupération du status
                data = await self.hass.async_add_executor_job(device.status)
                
                if data is None or "Error" in str(data):
                    errors["base"] = "cannot_connect"
                else:
                    # Création de l'entrée
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data={
                            "name": user_input[CONF_NAME],
                            "hub_ip": hub_ip,
                            "hub_id": hub_id,
                            "hub_local_key": hub_key,
                            "device_id": user_input.get("device_id", ""),
                            "device_local_key": user_input.get("device_local_key", ""),
                        },
                    )
            except Exception as e:
                _LOGGER.exception("Unexpected error during setup: %s", e)
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="IR AC"): str,
                vol.Required("hub_ip"): str,
                vol.Required("hub_id"): str,
                vol.Required("hub_local_key"): str,
                vol.Optional("device_id", default=""): str,
                vol.Optional("device_local_key", default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return TuyaSmartIRAcLocalOptionsFlow(config_entry)


class TuyaSmartIRAcLocalOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Tuya Smart IR AC Local."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "update_interval",
                        default=self.config_entry.options.get("update_interval", 60),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=600)),
                }
            ),
        )
