# config_flow.py
import voluptuous as vol
import logging
import re
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_POSTCODE, CONF_DISTANCE, CONF_API_KEY, DEFAULT_DISTANCE

_LOGGER = logging.getLogger(__name__)

# UK postcode format regex (simplified for common formats)
POSTCODE_REGEX = r'^[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}$'

class PetrolMapConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PetrolMap."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            postcode = user_input[CONF_POSTCODE].replace(" ", "").replace("+", "").upper()
            if not re.match(POSTCODE_REGEX, postcode):
                errors["base"] = "invalid_postcode"
            else:
                return self.async_create_entry(
                    title=f"PetrolMap {postcode}",
                    data={
                        CONF_POSTCODE: postcode,
                        CONF_DISTANCE: user_input[CONF_DISTANCE],
                        CONF_API_KEY: user_input.get(CONF_API_KEY, ""),
                    }
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_POSTCODE): str,
                vol.Required(CONF_DISTANCE, default=DEFAULT_DISTANCE): int,
                vol.Optional(CONF_API_KEY): str,
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PetrolMapOptionsFlow(config_entry)

class PetrolMapOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for PetrolMap."""
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            postcode = user_input[CONF_POSTCODE].replace(" ", "").replace("+", "").upper()
            if not re.match(POSTCODE_REGEX, postcode):
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_schema(),
                    errors={"base": "invalid_postcode"}
                )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_schema()
        )

    def _get_schema(self):
        """Return the schema for the options flow."""
        return vol.Schema({
            vol.Required(CONF_POSTCODE, default=self.config_entry.data.get(CONF_POSTCODE, "")): str,
            vol.Required(CONF_DISTANCE, default=self.config_entry.data.get(CONF_DISTANCE, DEFAULT_DISTANCE)): int,
            vol.Optional(CONF_API_KEY, default=self.config_entry.data.get(CONF_API_KEY, "")): str,
        })