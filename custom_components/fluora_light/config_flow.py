"""Config flow for Fluora Light."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import CONF_HOSTNAME, CONF_NAME, CONF_PORT, DEFAULT_PORT, DOMAIN


class FluoraFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fluora Light."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOSTNAME], raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_HOSTNAME): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

