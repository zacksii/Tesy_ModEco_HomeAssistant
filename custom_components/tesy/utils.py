import logging
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import TESY_DEVICE_TYPES  

_LOGGER = logging.getLogger(__name__)

async def async_set_power(hass, api_url, value):
    """Send a power control request."""
    url = f"{api_url}/power?val={value}"
    try:
        async with async_get_clientsession(hass).get(url) as response:
            if response.status != 200:
                _LOGGER.error("Failed to set power to %s, Response: %s", value, await response.text())
            return response.status == 200
    except Exception as err:
        _LOGGER.error("Error in async_set_power: %s", err)
        return False


async def async_set_temperature(hass, api_url, temperature):
    """Set the target temperature of the water heater."""
    url = f"{api_url}/setTemp?val={temperature}"
    try:
        async with async_get_clientsession(hass).get(url) as response:
            if response.status != 200:
                _LOGGER.error("Failed to set temperature to %s. HTTP status: %s", temperature, response.status)
                return False
            return True
    except Exception as e:
        _LOGGER.error("Error in async_set_temperature: %s", e)
        return False

async def async_set_operation_mode(hass, api_url, mode):
    """Set the operation mode of the water heater."""
    url = f"{api_url}/modeSW?mode={mode}"
    try:
        async with async_get_clientsession(hass).get(url) as response:
            if response.status != 200:
                _LOGGER.error("Failed to set operation mode to %s. HTTP status: %s", mode, response.status)
                return False
            return True
    except Exception as e:
        _LOGGER.error("Error in async_set_operation_mode: %s", e)
        return False

def get_tesy_device_type(devid: str) -> str:
    """Get the device name based on the device ID."""
    return TESY_DEVICE_TYPES.get(devid[:4], {})
    