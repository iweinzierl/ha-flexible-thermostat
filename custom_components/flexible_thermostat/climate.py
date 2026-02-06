"""Platform for Flexible Thermostat integration."""
from __future__ import annotations

import logging
from typing import Any


from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    PRECISION_TENTHS,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import (
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_COLD_TOLERANCE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_SENSOR,
    CONF_TARGET_TEMP,
    DEFAULT_TOLERANCE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Flexible Thermostat platform."""
    
    name = config_entry.data.get(CONF_NAME)
    heater_entity_id = config_entry.data.get(CONF_HEATER)
    sensor_entity_id = config_entry.data.get(CONF_SENSOR)
    target_temp = config_entry.data.get(CONF_TARGET_TEMP)
    cold_tolerance = config_entry.data.get(CONF_COLD_TOLERANCE, DEFAULT_TOLERANCE)
    hot_tolerance = config_entry.data.get(CONF_HOT_TOLERANCE, DEFAULT_TOLERANCE)

    async_add_entities(
        [
            FlexibleThermostat(
                name,
                heater_entity_id,
                sensor_entity_id,
                target_temp,
                cold_tolerance,
                hot_tolerance,
            )
        ]
    )


class FlexibleThermostat(ClimateEntity, RestoreEntity):
    """Representation of a Flexible Thermostat."""

    def __init__(
        self,
        name: str,
        heater_entity_id: str,
        sensor_entity_id: str,
        target_temp: float,
        cold_tolerance: float,
        hot_tolerance: float,
    ) -> None:
        """Initialize the thermostat."""
        self._attr_name = name
        self.heater_entity_id = heater_entity_id
        self.sensor_entity_id = sensor_entity_id
        self._target_temp = target_temp
        self._cold_tolerance = cold_tolerance
        self._hot_tolerance = hot_tolerance
        
        self._hvac_mode = HVACMode.OFF
        self._cur_temp = None
        self._unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
        )
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._is_device_active = False

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Add listener for sensor changes
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self.sensor_entity_id], self._async_sensor_changed
            )
        )
        
        # Add listener for switch changes
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self.heater_entity_id], self._async_switch_changed
            )
        )

        # Restore state
        old_state = await self.async_get_last_state()
        if old_state is not None:
            if old_state.attributes.get(ATTR_TEMPERATURE) is not None:
                self._target_temp = float(old_state.attributes[ATTR_TEMPERATURE])
            
            if old_state.state:
                self._hvac_mode = old_state.state
            
            if self._hvac_mode == STATE_UNAVAILABLE or self._hvac_mode == STATE_UNKNOWN:
                 self._hvac_mode = HVACMode.OFF

        # Check current sensor state
        sensor_state = self.hass.states.get(self.sensor_entity_id)
        if sensor_state and sensor_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self._async_update_temp(sensor_state)

        # Check current switch state
        switch_state = self.hass.states.get(self.heater_entity_id)
        if switch_state and switch_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self._is_device_active = switch_state.state == STATE_ON

        self.async_write_ha_state()

    @callback
    def _async_sensor_changed(self, event) -> None:
        """Handle temperature changes."""
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        self._async_update_temp(new_state)
        self.async_write_ha_state()
        self._async_control_heating()

    @callback
    def _async_switch_changed(self, event) -> None:
        """Handle heater switch changes."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        self._is_device_active = new_state.state == STATE_ON
        self.async_write_ha_state()

    @callback
    def _async_update_temp(self, state: State) -> None:
        """Update thermostat with latest state from sensor."""
        try:
            self._cur_temp = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from sensor: %s", ex)

    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        return self._cur_temp

    @property
    def hvac_mode(self):
        """Return current operation."""
        return self._hvac_mode

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        if self._hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self._is_device_active:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temp

    @property
    def precision(self) -> float:
        """Return the precision of the system."""
        return PRECISION_TENTHS
    
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            self._hvac_mode = HVACMode.HEAT
            await self._async_control_heating()
        elif hvac_mode == HVACMode.OFF:
            self._hvac_mode = HVACMode.OFF
            if self._is_device_active:
                await self._async_turn_off_heater()
        else:
            _LOGGER.error("Unrecognized HVAC mode: %s", hvac_mode)
            return
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._target_temp = temperature
        await self._async_control_heating()
        self.async_write_ha_state()

    async def _async_control_heating(self):
        """Check if we need to turn heating on or off."""
        if not self._hvac_mode == HVACMode.HEAT:
            return

        if not self._cur_temp or not self._target_temp:
            return

        too_cold = self._target_temp - self._cold_tolerance
        too_hot = self._target_temp + self._hot_tolerance

        if self._is_device_active:
            if self._cur_temp >= too_hot:
                await self._async_turn_off_heater()
        else:
            if self._cur_temp <= too_cold:
                await self._async_turn_on_heater()

    async def _async_turn_on_heater(self):
        """Turn heater toggleable device on."""
        data = {"entity_id": self.heater_entity_id}
        await self.hass.services.async_call(
            "switch", "turn_on", data, context=self._context
        )

    async def _async_turn_off_heater(self):
        """Turn heater toggleable device off."""
        data = {"entity_id": self.heater_entity_id}
        await self.hass.services.async_call(
            "switch", "turn_off", data, context=self._context
        )
