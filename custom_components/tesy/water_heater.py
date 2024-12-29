import asyncio
import logging
from datetime import datetime
import pytz

from homeassistant.helpers import template
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_PERFORMANCE,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_WHOLE,
    STATE_OFF,
    STATE_ON,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    TESY_SUPPORTED_FEATURES,
    API_OPERATION_MODES,
    API_STATE_MAPPING,
    ATTR_POWER,
    ATTR_CURRENT_TEMP,
    ATTR_TARGET_TEMP,
    ATTR_LAST_OPERATION_MODE,
    DOMAIN,
)
from .utils import async_set_power, async_set_temperature, async_set_operation_mode
from .services import register_set_vacation_mode_service

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Tesy water heater platform."""
    data = hass.data[DOMAIN].get(config_entry.entry_id)
    if not data:
        _LOGGER.error(f"Data not found for entry: {config_entry.entry_id}")
        return False

    coordinator = data.get("coordinator")
    if not coordinator:
        _LOGGER.error(f"Coordinator not found for entry: {config_entry.entry_id}")
        return False

    api_url = data.get("api_url")
    device_id = data.get("device_id")
    device_name = data.get("device_name")
    min_temp = data.get("min_setpoint")
    max_temp = data.get("max_setpoint")

    async_add_entities([TesyWaterHeater(coordinator, api_url, device_id, device_name, min_temp, max_temp)])

    # Check and warn about missing UI helpers
    await check_ui_helpers(hass, config_entry.entry_id)

    return True

async def check_ui_helpers(hass, entry_id):
    """Check if required UI helpers exist, and warn if missing."""
    entity_registry = async_get_entity_registry(hass)

    # Validate input_datetime for vacation end
    vacation_end_entity_id = f"input_datetime.tesy_vacation_end_{entry_id}"
    if not entity_registry.async_get(vacation_end_entity_id):
        _LOGGER.warning(
            "The input_datetime entity '%s' is missing. Please define it in configuration.yaml.",
            vacation_end_entity_id
        )

    # Validate input_number for temperature after vacation
    temp_after_vacation_entity_id = f"input_number.tesy_temp_after_vacation_{entry_id}"
    if not entity_registry.async_get(temp_after_vacation_entity_id):
        _LOGGER.warning(
            "The input_number entity '%s' is missing. Please define it in configuration.yaml.",
            temp_after_vacation_entity_id
        )

class TesyWaterHeater(CoordinatorEntity, WaterHeaterEntity):
    """Representation of the Tesy Water Heater."""

    _attr_supported_features = TESY_SUPPORTED_FEATURES
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, api_url, device_id, device_name, min_temp, max_temp):
        """Initialize the Tesy Water Heater."""
        super().__init__(coordinator)
        self._api_url = api_url
        self._device_id = device_id
        self._device_name = device_name or "Tesy Generic Water Heater"
        self._attr_name = self._device_name
        self._attr_unique_id = f"{device_id}_water_heater"
        self._attr_min_temp = min_temp
        self._attr_max_temp = max_temp
        self._is_away_mode_on = False
        self._data = None

    @property
    def device_info(self):
        """Return device information for the water heater."""
        try:
            sw_version = self._device_id.split()[-1]
        except IndexError:
            sw_version = "Unknown"

        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "Tesy",
            "model": "Smart Water Heater",
            "sw_version": sw_version,
        }

    @property
    def state(self):
        """Return the hassio state of the water heater."""
        if self.coordinator.data.get("status", {}).get("boost") == "1":
            return STATE_PERFORMANCE
        return STATE_OFF if not self.is_on else self.current_operation

    @property
    def is_on(self):
        """This is the real state of the device. Return true if the water heater is on."""
        return self.coordinator.data.get("status", {}).get(ATTR_POWER, "off") == "on"

    @property
    def current_temperature(self):
        """Return the current temperature."""
        try:
            return float(self.coordinator.data.get("status", {}).get(ATTR_CURRENT_TEMP))
        except (ValueError, TypeError):
            _LOGGER.error("Invalid current temperature value.")
            return None

    @property
    def target_temperature(self):
        """Return the temperature we are trying to reach."""
        try:
            return float(self.coordinator.data.get("status", {}).get(ATTR_TARGET_TEMP))
        except (ValueError, TypeError):
            _LOGGER.error("Invalid target temperature value.")
            return None

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return list(API_OPERATION_MODES.keys()) if self.is_on else ["On"]

    @property
    def current_operation(self):
        """Return the current operation mode."""
        mode = self.coordinator.data.get("status", {}).get(ATTR_LAST_OPERATION_MODE)
        return next((key for key, value in API_OPERATION_MODES.items() if value == mode), "Unknown")

    @property
    def is_away_mode_on(self):
        """Return whether away mode is on."""
        return self._is_away_mode_on

    async def async_turn_away_mode_on(self):
        """Turn away mode on for the water heater."""
        self._is_away_mode_on = True

        vacation_end_entity_id = f"input_datetime.tesy_vacation_end_{self._device_id}"
        vacation_temp_entity_id = f"input_number.tesy_temp_after_vacation_{self._device_id}"

        vacation_end = self.coordinator.hass.states.get(vacation_end_entity_id).state
        vacation_temp = self.coordinator.hass.states.get(vacation_temp_entity_id).state

        if vacation_end and vacation_temp:
            try:
                await self.coordinator.hass.services.async_call(
                    'tesy',
                    'set_vacation_mode',
                    {
                        'vacation_end': vacation_end,
                        'vacation_temp': float(vacation_temp),
                    }
                )
            except Exception as e:
                _LOGGER.error(f"Failed to call set_vacation_mode_service: {e}")
        else:
            _LOGGER.error("Invalid vacation_end or vacation_temp values.")

        await self.async_update()

    async def async_set_temperature(self, **kwargs):
        """Set the target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            _LOGGER.error("No temperature specified.")
            return

        for attempt in range(3):
            if await async_set_temperature(self.coordinator.hass, self._api_url, temperature):
                break
            _LOGGER.warning(f"Failed to set temperature, retrying... (Attempt {attempt + 1}/3)")
            await asyncio.sleep(1)
        else:
            _LOGGER.error("Failed to set temperature after retries.")

        # Switch to manual mode if needed
        manual_mode = API_OPERATION_MODES.get("Manual")
        if self.coordinator.data.get("status", {}).get("mode") != manual_mode:
            success = await async_set_operation_mode(self.coordinator.hass, self._api_url, manual_mode)
            if not success:
                _LOGGER.error("Failed to switch to manual mode.")
                return

        success = await async_set_temperature(self.coordinator.hass, self._api_url, temperature)
        if not success:
            _LOGGER.error("Failed to set temperature to %s", temperature)

        await self.async_update()

    async def async_set_operation_mode(self, operation_mode: str):
        """Set the operation mode."""
        if operation_mode == "On":
            await self.async_turn_on()
            return
        elif operation_mode == "Off":
            await self.async_turn_off()
            return

        valid_modes = self.operation_list
        if operation_mode not in valid_modes:
            _LOGGER.error("Invalid operation mode: %s. Valid modes are: %s", operation_mode, ", ".join(valid_modes))
            return

        mode = API_OPERATION_MODES.get(operation_mode)
        if not mode:
            _LOGGER.error("Invalid operation mode mapping: %s", operation_mode)
            return

        if not await async_set_operation_mode(self.coordinator.hass, self._api_url, mode):
            _LOGGER.error("Failed to set operation mode: %s", operation_mode)
            return

        await self.async_update()

    async def async_turn_on(self):
        """Turn the water heater on."""
        if await async_set_power(self.coordinator.hass, self._api_url, "on"):
            last_mode = self.coordinator.data.get("status", {}).get(ATTR_LAST_OPERATION_MODE)
            if last_mode:
                await self.async_set_operation_mode(
                    next((k for k, v in API_OPERATION_MODES.items() if v == last_mode), "Manual")
                )
        else:
            _LOGGER.error("Failed to turn on the water heater.")

        await self.async_update()

    async def async_turn_off(self):
        """Turn the water heater off."""
        if not await async_set_power(self.coordinator.hass, self._api_url, "off"):
            _LOGGER.error("Failed to turn off the water heater.")
        await self.async_update()

    async def async_update(self):
        """Update the state of the water heater."""
        _LOGGER.debug("TesyWaterHeater.async_update() called.")
        await self.coordinator.async_request_refresh()
