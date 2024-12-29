import logging
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

async def toggle_away_mode(hass: HomeAssistant, enable: bool):
    """Toggle away mode for all Tesy water heaters."""
    devices = hass.data.get("tesy_devices", [])
    if not devices:
        _LOGGER.warning("No Tesy devices found to toggle away mode.")
        return

    for device in devices:
        try:
            if enable:
                await device.async_turn_away_mode_on()
                _LOGGER.info(f"Away mode enabled for {device.name}.")
            else:
                await device.async_turn_away_mode_off()
                _LOGGER.info(f"Away mode disabled for {device.name}.")
        except Exception as e:
            _LOGGER.error(f"Failed to toggle away mode for {device.name}: {e}")
