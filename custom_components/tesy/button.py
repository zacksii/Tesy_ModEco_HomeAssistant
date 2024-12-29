from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.service import ServiceCall
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Tesy update time button platform."""
    
    # Fetch the data needed from the config entry (for instance, device_id, api_url, etc.)
    data = hass.data[DOMAIN].get(config_entry.entry_id)
    if not data:
        _LOGGER.error(f"Data not found for entry: {config_entry.entry_id}")
        return False
    
    # Add the button entity to Home Assistant
    async_add_entities([TesyUpdateTimeButton(data)])

    return True

class TesyUpdateTimeButton(ButtonEntity):
    """Representation of a button to update the date/time of the Tesy Water Heater."""

    def __init__(self, data):
        """Initialize the button."""
        self._data = data
        self._device_id = data.get("device_id")
        self._device_name = data.get("device_name") or "Tesy Water Heater"
        self._attr_name = f"Update Time for {self._device_name}"
        self._attr_unique_id = f"{self._device_id}_update_time_button"
        self._attr_icon = "mdi:clock"

    async def async_press(self):
        """Handle the button press."""
        _LOGGER.info(f"Pressing the button to update the date/time for {self._device_name}")
        await self.async_update_time()

    async def async_update_time(self):
        """Call the service to update the device's date/time."""
        # Call the existing service to update the device time
        try:
            # Trigger the update_device_time service
            await self._update_device_time_service()
        except Exception as e:
            _LOGGER.error(f"Error while updating device time: {e}")

    async def _update_device_time_service(self):
        """Trigger the service to update the device time."""
        # Call the service to update the device time
        await self._data["hass"].services.async_call(
            DOMAIN,
            "update_device_time",
            {
                "entry_id": self._data["entry_id"],  # Pass the entry_id to the service
            },
        )
        _LOGGER.info(f"Requested device time update for {self._device_name}.")
