import datetime
import logging
from aiohttp import ClientSession
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

# Utility function to get the weekday number (0=Sunday, 1=Monday, ..., 6=Saturday)
def get_weekday(date: datetime.date) -> int:
    return (date.weekday() + 1) % 7

# Service definition
async def set_vacation_mode_service(hass: HomeAssistant, call: ServiceCall, api_url: str):
    """Handle the service call to set vacation mode."""
    try:
        # Extract the parameters from the service call
        vacation_end = call.data.get("vacation_end")
        vacation_temp = call.data.get("vacation_temp")

        if not vacation_end or not vacation_temp:
            _LOGGER.error("Missing required parameters: vacation_end or vacation_temp")
            return

        # Parse vacation_end into a datetime object
        vacation_datetime = datetime.datetime.fromisoformat(vacation_end)
        vYear = vacation_datetime.year % 100  # Get last two digits of the year
        vMonth = vacation_datetime.month
        vMDay = vacation_datetime.day
        vHour = vacation_datetime.hour
        vWDay = get_weekday(vacation_datetime.date())  # Calculate the day of the week

        # Construct the API URL
        url = (
            f"{api_url}/setVacation?"
            f"vYear={vYear}&vMonth={vMonth:02d}&vMDay={vMDay:02d}"
            f"&vWDay={vWDay}&vHour={vHour:02d}&vTemp={vacation_temp}"
        )

        _LOGGER.debug("Constructed URL: %s", url)

        # Send the request to the API
        async with ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    _LOGGER.info(
                        "Vacation mode successfully set: %s (temp=%s)",
                        vacation_end,
                        vacation_temp,
                    )
                else:
                    _LOGGER.error("Failed to set vacation mode: HTTP %s", response.status)

    except Exception as e:
        _LOGGER.error("Error setting vacation mode: %s", e)

# Register the service
async def register_set_vacation_mode_service(hass: HomeAssistant, api_url: str):
    """Register the set_vacation_mode service."""
    hass.services.async_register(
        "tesy",
        "set_vacation_mode",
        lambda call: set_vacation_mode_service(hass, call, api_url),
        schema=vol.Schema(
            {
                vol.Required("vacation_end"): vol.All(
                    str, vol.Match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
                ),
                vol.Required("vacation_temp"): vol.All(vol.Coerce(float), vol.Range(min=8, max=75)),
            }
        ),
    )
