import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfVolume
from datetime import datetime
from .const import DOMAIN, SCHEDULE_ENDPOINTS, TESY_DEVICE_TYPES, ATTR_CURRENT_TEMP, ATTR_TARGET_TEMP, ATTR_TIME_ZONE, ATTR_DATE_TIME

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Tesy sensor platform."""
    entry_data = hass.data.get(DOMAIN, {}).get(config_entry.entry_id)
    if not entry_data:
        _LOGGER.error("Entry data not found for config entry: %s", config_entry.entry_id)
        return

    try:
        coordinator = entry_data.get("coordinator")
        if not coordinator:
            _LOGGER.error("Coordinator not found for entry: %s", config_entry.entry_id)
            return

        api_url = entry_data.get("api_url")
        device_id = entry_data.get("device_id")
        device_name = entry_data.get("device_name")

        if not all([api_url, device_id, device_name]):
            _LOGGER.error("Missing required entry data for sensors setup")
            return

        # Define all sensors
        sensors = [
            TesySensor(coordinator, api_url, device_id, device_name, "heater_state", endpoint="status", unit=None, icon=None),
            TesySensor(coordinator, api_url, device_id, device_name, "mode", endpoint="status", unit=None, icon=None),
            TesySensor(coordinator, api_url, device_id, device_name, "err_flag", endpoint="status", unit=None, icon="mdi:alert"),
            TesySensor(coordinator, api_url, device_id, device_name, "lockB", endpoint="status", unit=None, icon="mdi:lock"),
            TesySensor(coordinator, api_url, device_id, device_name, "boost", endpoint="status", unit=None, icon="mdi:rocket"),
            TesySensor(coordinator, api_url, device_id, device_name, "watts", endpoint="status", unit=UnitOfPower.WATT, icon="mdi:flash"),
            TesySensor(coordinator, api_url, device_id, device_name, ATTR_CURRENT_TEMP, endpoint="status", unit="°C", icon="mdi:thermometer"),
            TesySensor(coordinator, api_url, device_id, device_name, ATTR_TARGET_TEMP, endpoint="status", unit="°C", icon="mdi:thermometer"),
            TesySensor(coordinator, api_url, device_id, device_name, "mix40", endpoint="status", unit=UnitOfVolume.LITERS, icon="mdi:water"),
            TesySensor(coordinator, api_url, device_id, device_name, ATTR_DATE_TIME, endpoint="status", unit=None, icon="mdi:calendar"),
            TesySensor(coordinator, api_url, device_id, device_name, ATTR_TIME_ZONE, endpoint="status", unit=None, icon=None),
            TesySensor(coordinator, api_url, device_id, device_name, "sum", endpoint="calcRes", unit=UnitOfEnergy.WATT_HOUR, icon="mdi:chart-bar"),
            TesySensor(coordinator, api_url, device_id, device_name, "resetDate", endpoint="calcRes", unit=None, icon="mdi:calendar-refresh"),
            TesySensor(coordinator, api_url, device_id, device_name, "volume", endpoint="calcRes", unit=UnitOfVolume.LITERS, icon="mdi:water"),
            TesySensor(coordinator, api_url, device_id, device_name, "watt", endpoint="calcRes", unit=UnitOfPower.WATT, icon="mdi:power"),
            TesyEnergySensor(coordinator, api_url, device_id, device_name),
        ]

        # Add schedule sensors
        for schedule_type, endpoint in SCHEDULE_ENDPOINTS.items():
            sensors.append(
                TesyScheduleSensor(coordinator, api_url, device_id, device_name, schedule_type, endpoint)
            )

        async_add_entities(sensors)
    except Exception as e:
        _LOGGER.error("Error setting up Tesy sensors: %s", e, exc_info=True)


class TesySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tesy sensor."""

    def __init__(self, coordinator, api_url, device_id, device_name, key, endpoint="status", unit=None, icon=None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._api_url = api_url
        self._device_id = device_id
        self._device_name = device_name
        self._key = key
        self._endpoint = endpoint
        self._unit = unit
        self._icon = icon
        self._attr_unique_id = f"{device_id}_{endpoint}_{key}"

        # Define custom mappings for user-friendly names
        self._key_name_mapping = {
            "heater_state": "Heater State",
            "mode": "Mode",
            "err_flag": "Error Flag",
            "lockB": "Child Lock Status",
            "boost": "Boost Mode",
            "watts": "Power Consumption",
            "gradus": "Current Temperature",
            "ref_gradus": "Target Temperature",
            "mix40": "Mix 40L",
            "sum": "Total Energy",
            "resetDate": "Reset Date",
            "volume": "Water Volume",
            "watt": "Current Power",
            "tz" : "Time Zone",
            "date" : "Date/Time",            
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        key_name = self._key_name_mapping.get(self._key, self._key.replace('_', ' ').title())
        return f"{self._device_name} {key_name}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        data = self.coordinator.data.get(self._endpoint, {})
        return data.get(self._key)

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        devstat_data = self.coordinator.data.get("devstat", {})
        return {
            "macaddr": devstat_data.get("macaddr", "Unknown"),
            "device_name": self._device_name,
            "source": "Tesy API",
        }

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return self._icon

class TesyEnergySensor(CoordinatorEntity, SensorEntity):
    """Representation of the Tesy Energy Sensor."""

    def __init__(self, coordinator, api_url, device_id, device_name):
        """Initialize the Tesy Energy Sensor."""
        super().__init__(coordinator)
        self._api_url = api_url
        self._device_id = device_id
        self._device_name = device_name
        self._attr_name = f"{device_name} Energy Consumption"
        self._attr_unique_id = f"{device_id}_energy_consumption"
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_device_class = "energy"
        self._attr_state_class = "total_increasing"

    @property
    def native_value(self):
        """Return the current energy consumption."""
        calc_res = self.coordinator.data.get("calcRes", {})
        energy = calc_res.get("sum")
        if energy is not None:
            try:
                return int(energy)
            except ValueError:
                _LOGGER.error("Invalid energy value: %s", energy)
                return None
        _LOGGER.warning("Energy consumption data not available.")
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes for the energy sensor."""
        calc_res = self.coordinator.data.get("calcRes", {})
        devstat_data = self.coordinator.data.get("devstat", {})

        return {
            "reset_date": calc_res.get("resetDate"),
            "current_power": calc_res.get("watt"),
            "macaddr": devstat_data.get("macaddr", "Unknown"),
            "device_name": self._device_name,
        }

class TesyScheduleSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tesy schedule sensor."""

    def __init__(self, coordinator, api_url, device_id, device_name, schedule_type, endpoint):
        """Initialize the schedule sensor."""
        super().__init__(coordinator)
        self._api_url = api_url
        self._device_id = device_id
        self._device_name = device_name
        self._schedule_type = schedule_type
        self._endpoint = endpoint

        # Human-readable mapping of schedule types
        schedule_type_mapping = {
            "p1": "Program 1",
            "p2": "Program 2",
            "p3": "Program 3",
            "vacation": "Vacation",
        }
        self._attr_name = f"{device_name} Schedule {schedule_type_mapping.get(schedule_type, schedule_type).upper()}"
        self._attr_unique_id = f"{device_id}_schedule_{schedule_type}"

    @property
    def native_value(self):
        """Return the temperature for the current hour from the schedule."""
        current_hour = datetime.now().hour
        schedule_data = self.coordinator.data.get(self._schedule_type, [])

        if not schedule_data:
            return "No schedule available"

        current_day = datetime.now().strftime('%a')  # Get the current day in short form (e.g., Mon, Tue, etc.)

        for day_schedule in schedule_data:
            if current_day in day_schedule:
                current_day_schedule = day_schedule[current_day]
                current_temp = current_day_schedule.get(f"h{current_hour:02}", "Unknown")
                return current_temp

        return "No schedule available"

    @property
    def extra_state_attributes(self):
        """Return detailed schedule data."""
        return {
            "schedule_details": self.coordinator.data.get(self._schedule_type, {}),
            "device_name": self._device_name,
            "source": "Tesy API",
        }
