"""Config flow for Flexible Thermostat integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_COLD_TOLERANCE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_SENSOR,
    CONF_TARGET_TEMP,
    CONF_TARGET_TEMP_STEP,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_NAME,
    DEFAULT_TARGET_TEMP_STEP,
    DEFAULT_TOLERANCE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Flexible Thermostat."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_HEATER): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="switch")
                    ),
                    vol.Required(CONF_SENSOR): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
                    vol.Required(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
                    vol.Required(
                        CONF_TARGET_TEMP_STEP, default=DEFAULT_TARGET_TEMP_STEP
                    ): vol.Coerce(float),
                    vol.Required(CONF_TARGET_TEMP, default=20.0): vol.Coerce(float),
                    vol.Required(
                        CONF_COLD_TOLERANCE, default=DEFAULT_TOLERANCE
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_HOT_TOLERANCE, default=DEFAULT_TOLERANCE
                    ): vol.Coerce(float),
                }
            ),
            errors=errors,
        )
