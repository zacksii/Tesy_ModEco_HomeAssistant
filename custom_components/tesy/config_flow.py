import logging
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN
from .utils import get_tesy_device_type

_LOGGER = logging.getLogger(__name__)


class TesyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tesy integration."""

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step where the user inputs the device IP."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required("ip"): str}),
            )

        ip = user_input["ip"]

        # Fetch device info dynamically
        device_info = await self._fetch_device_info(ip)

        if not device_info or "devid" not in device_info:
            return self.async_show_form(
                step_id="user",
                errors={"base": "cannot_connect"},
            )
        devid = device_info.get("devid", "Unknown")
        macaddr = device_info.get("macaddr", "Unknown")
        device_type = get_tesy_device_type(devid)
        device_name = f"Tesy {device_type.get('name', 'Device')}"
        min_setpoint = device_type.get('min_setpoint', 8)
        max_setpoint = device_type.get('max_setpoint', 75)    
        
        # Include additional attributes from devstat API in the config entry
        return self.async_create_entry(
            title=f"Tesy ({ip})",
            data={
                "ip": ip,
                "device_id": devid,
                "macaddr": macaddr,
                "device_name": device_name,
                "min_setpoint": min_setpoint,
                "max_setpoint": max_setpoint,
            },
        )

    async def _fetch_device_info(self, ip: str) -> dict:
        """Fetch device information dynamically from the API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{ip}/devstat") as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        return data
                    else:
                        _LOGGER.error("Failed to fetch device info: HTTP %s", response.status)
                        return {}
        except Exception as e:
            _LOGGER.error("Error fetching device info: %s", e)
            return {}


class TesyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Tesy options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the Tesy options."""
        if user_input is not None:
            # Handle refresh or other options here
            if user_input.get("refresh"):
                await self.hass.services.async_call(DOMAIN, "refresh")
            return self.async_create_entry(title="", data=self.config_entry.options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Optional("refresh", default=False): bool}),
        )
