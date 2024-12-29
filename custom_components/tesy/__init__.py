import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.restore_state import RestoreStateData
from .const import DOMAIN, SCHEDULE_ENDPOINTS
from .utils import get_tesy_device_type
from .services import register_set_vacation_mode_service

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Tesy integration from a config entry."""

    try:
        _LOGGER.info("Setting up Tesy integration for entry: %s", entry.entry_id)

        # Initialize API details and device-specific data
        api_url = f"http://{entry.data['ip']}"
        await register_set_vacation_mode_service(hass, api_url)
        devid = entry.data.get("device_id")
        macaddr = entry.data.get("macaddr")

        if not devid:
            _LOGGER.error("Device ID is missing in the config entry.")
            return False

        # Fetch device type details
        device_type = get_tesy_device_type(devid)
        device_name = f"Tesy {device_type.get('name', 'Device')}"
        min_setpoint = device_type.get('min_setpoint', 8)
        max_setpoint = device_type.get('max_setpoint', 75)

        # Store these attributes in `hass.data`
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {
            "api_url": api_url,
            "device_id": devid,
            "macaddr": macaddr,
            "device_name": device_name,
            "min_setpoint": min_setpoint,
            "max_setpoint": max_setpoint,
        }

        # Create dynamic entities using entity registry
        entity_registry = async_get_entity_registry(hass)
        entity_prefix = f"tesy_{entry.entry_id}"
        vacation_datetime_entity = f"input_datetime.{entity_prefix}_vacation_end"
        vacation_temp_entity = f"input_number.{entity_prefix}_temp_after_vacation"

        # Check and create input_datetime entity
        if not entity_registry.async_get(vacation_datetime_entity):
            hass.states.async_set(
                vacation_datetime_entity,
                None,
                {
                    "name": f"Tesy Vacation End {entry.entry_id}",
                    "has_date": True,
                    "has_time": True,
                },
            )

        # Check and create input_number entity
        if not entity_registry.async_get(vacation_temp_entity):
            hass.states.async_set(
                vacation_temp_entity,
                None,
                {
                    "name": f"Tesy Temp After Vacation {entry.entry_id}",
                    "min": min_setpoint,
                    "max": max_setpoint,
                    "step": 1,
                },
            )

        # Store dynamic entities in `hass.data`
        hass.data[DOMAIN][entry.entry_id].update({
            "vacation_datetime_entity": vacation_datetime_entity,
            "vacation_temp_entity": vacation_temp_entity,
        })

        # Create a DataUpdateCoordinator
        async def async_fetch_data():
            """Fetch data from the Tesy API."""
            data = {}
            try:
                _LOGGER.debug("Fetching data from Tesy API for device %s", devid)
                async with ClientSession() as session:
                    for endpoint in ["status", "calcRes", "devstat"]:
                        async with session.get(f"{api_url}/{endpoint}") as response:
                            if response.status == 200:
                                endpoint_data = await response.json(content_type=None)
                                if endpoint_data:
                                    data[endpoint] = endpoint_data
                                else:
                                    _LOGGER.warning("Empty %s data received.", endpoint)
                            else:
                                _LOGGER.error("Failed to fetch %s: HTTP %d", endpoint, response.status)

                    # Fetch schedules (P1, P2, P3, Vacation)
                    for schedule, endpoint in SCHEDULE_ENDPOINTS.items():
                        async with session.get(f"{api_url}/{endpoint}") as response:
                            if response.status == 200:
                                schedule_data = await response.json(content_type=None)
                                if schedule_data:
                                    data[schedule] = schedule_data
                                else:
                                    _LOGGER.warning("Empty schedule data for %s received.", schedule)
                            else:
                                _LOGGER.error("Failed to fetch schedule %s: HTTP %d", schedule, response.status)
            except Exception as e:
                _LOGGER.error("Error fetching data from Tesy API: %s", e)
            return data

        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="tesy",
            update_method=async_fetch_data,
            update_interval=timedelta(seconds=60),
        )

        # Perform the first refresh
        await coordinator.async_config_entry_first_refresh()

        # Update `hass.data` with coordinator
        hass.data[DOMAIN][entry.entry_id].update({
            "coordinator": coordinator,
        })
        _LOGGER.debug("Coordinator data update completed for entry: %s", entry.entry_id)

        # Forward entry setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, ["water_heater", "sensor", "switch"])

        # Register the refresh service
        async def handle_refresh_service(call: ServiceCall):
            """Handle refresh service call."""
            _LOGGER.info("Received request to refresh Tesy data for device %s", devid)
            await coordinator.async_request_refresh()

        hass.services.async_register(DOMAIN, "refresh", handle_refresh_service)

        # Register the update device time service
        async def async_update_device_time(call: ServiceCall):
            """Handle the service call to update device time."""
            device = hass.data[DOMAIN].get(entry.entry_id)
            if not device:
                _LOGGER.error("Device not found for time update.")
                return

            # Fetch current time from Home Assistant's time zone
            timezone = hass.config.time_zone
            local_time = datetime.now(ZoneInfo(timezone))
            t_offset = timezone.replace("/", "").replace(":", "")
            url = (
                f"{device['api_url']}/setdate?"
                f"tOffset={t_offset}&tDay={local_time.day}"
                f"&tMonth={local_time.month}&tYear={local_time.year}"
                f"&tHour={local_time.hour}&tMin={local_time.minute}&tSec={local_time.second}"
            )

            try:
                async with ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            _LOGGER.info("Successfully updated device time to %s", local_time)
                        else:
                            _LOGGER.error("Failed to update time: HTTP %s", response.status)
            except Exception as e:
                _LOGGER.error("Error updating device time: %s", e)

        hass.services.async_register(DOMAIN, "update_device_time", async_update_device_time)

        # Add an update listener for options changes
        async def update_listener(hass, entry):
            """Handle options updates."""
            _LOGGER.info("Options for Tesy integration have been updated.")
            await hass.config_entries.async_reload(entry.entry_id)

        entry.async_on_unload(entry.add_update_listener(update_listener))
        return True

    except Exception as e:
        _LOGGER.error("Failed to set up Tesy integration: %s", e)
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["water_heater", "sensor", "switch"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
