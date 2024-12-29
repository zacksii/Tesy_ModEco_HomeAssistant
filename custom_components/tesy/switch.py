import logging
from homeassistant.const import UnitOfTemperature
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from aiohttp import ClientSession



_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Tesy boost switch platform."""
    data = hass.data[DOMAIN].get(config_entry.entry_id)
    if data is None or "coordinator" not in data:
        _LOGGER.error("Coordinator not found for entry: %s", config_entry.entry_id)
        return
        
    coordinator = data["coordinator"]
    api_url = data["api_url"]
    device_id = data["device_id"]
    device_name = data.get("device_name")    
    
    switches = [
    TesyChildLockSwitch(coordinator, api_url, device_id, device_name),  
    TesyBoostSwitch(coordinator, api_url, device_id, device_name),
]
    async_add_entities(switches)

class TesyBoostSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of the Tesy Boost switch."""

    def __init__(self, coordinator, api_url, device_id, device_name):
        """Initialize the Tesy Boost switch."""
        super().__init__(coordinator)
        self._api_url = api_url
        self._device_id = device_id
        self._device_name = device_name
        self._attr_name = f"{device_name} Boost Switch"
        self._attr_unique_id = f"{device_id}_boost_switch"
        self._icon="mdi:rocket-launch-outline"

    @property
    def is_on(self):
        """Return true if the boost mode is active."""
        boost_state = self.coordinator.data.get("status", {}).get("boost")
        return boost_state == "1"

    async def async_turn_on(self, **kwargs):
        """Turn on the boost mode."""
        await self._set_boost_mode(True)

    async def async_turn_off(self, **kwargs):
        """Turn off the boost mode."""
        await self._set_boost_mode(False)

    async def _set_boost_mode(self, mode: bool):
        """Set the boost mode via the Tesy API."""
        try:
            async with ClientSession() as session:
                mode_value = "1" if mode else "0"
                url = f"{self._api_url}/boostSW?mode={mode_value}"

                async with session.get(url) as response:
                    if response.status == 200:
                        _LOGGER.info("Successfully set boost mode to %s", mode)
                        # Trigger a data refresh to reflect the change
                        await self.coordinator.async_request_refresh()
                    else:
                        _LOGGER.error("Failed to set boost mode. HTTP status: %s", response.status)
        except Exception as e:
            _LOGGER.error("Error setting boost mode: %s", e)

    async def async_update(self):
        """Refresh the data from the coordinator."""
        await self.coordinator.async_request_refresh()

class TesyChildLockSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of the Tesy Child Lock Switch."""

    def __init__(self, coordinator, api_url, device_id, device_name):
        """Initialize the Tesy Child Lock Switch."""
        super().__init__(coordinator)
        self._api_url = api_url
        self._device_id = device_id
        self._device_name = device_name
        self._attr_name = f"{device_name} Child Lock"
        self._attr_unique_id = f"{device_id}_child_lock"

    @property
    def is_on(self):
        """Return True if the child lock is active."""
        status_data = self.coordinator.data.get("status", {})
        return status_data.get("lockB") == "on"

    async def async_turn_on(self, **kwargs):
        """Turn on the child lock."""
        await self._set_lock_state("on")

    async def async_turn_off(self, **kwargs):
        """Turn off the child lock."""
        await self._set_lock_state("off")

    async def _set_lock_state(self, state: str):
        """Set the lock state via the API."""
        val = state
        url = f"{self._api_url}/lockKey?val={val}"
        try:
            session = async_get_clientsession(self.coordinator.hass)
            async with session.get(url) as response:
                if response.status == 200:
                    await self.coordinator.async_request_refresh()  # Refresh the data after state change
                else:
                    _LOGGER.error("Failed to set child lock: HTTP %s", response.status)
        except Exception as e:
            _LOGGER.error("Error setting child lock state: %s", e)
