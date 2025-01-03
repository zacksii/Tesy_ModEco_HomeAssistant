import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfVolume
from datetime import datetime
from .const import DOMAIN, SCHEDULE_ENDPOINTS, TESY_DEVICE_TYPES, ATTR_CURRENT_TEMP, ATTR_TARGET_TEMP, ATTR_TIME_ZONE, ATTR_DATE_TIME, ATTR_MODE

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
            TesySensor(coordinator, api_url, device_id, device_name, "heater_state", endpoint="status", unit=None, icon="mdi:radiator"),
            TesySensor(coordinator, api_url, device_id, device_name, ATTR_MODE, endpoint="status", unit=None, icon="mdi:settings"),
            TesySensor(coordinator, api_url, device_id, device_name, "err_flag", endpoint="status", unit=None, icon="mdi:alert"),
            TesySensor(coordinator, api_url, device_id, device_name, "lockB", endpoint="status", unit=None, icon="mdi:lock"),
            TesySensor(coordinator, api_url, device_id, device_name, "boost", endpoint="status", unit=None, icon="mdi:rocket"),
            TesySensor(coordinator, api_url, device_id, device_name, "watts", endpoint="status", unit=UnitOfPower.WATT, icon="mdi:power-plug"),
            TesySensor(coordinator, api_url, device_id, device_name, ATTR_CURRENT_TEMP, endpoint="status", unit="°C", icon="mdi:thermometer"),
            TesySensor(coordinator, api_url, device_id, device_name, ATTR_TARGET_TEMP, endpoint="status", unit="°C", icon="mdi:thermometer-plus"),
            TesySensor(coordinator, api_url, device_id, device_name, "mix40", endpoint="status", unit=UnitOfVolume.LITERS, icon="mdi:water"),
            TesySensor(coordinator, api_url, device_id, device_name, ATTR_DATE_TIME, endpoint="status", unit=None, icon="mdi:calendar"),
            TesySensor(coordinator, api_url, device_id, device_name, ATTR_TIME_ZONE, endpoint="status", unit=None, icon="mdi:clock"),
            TesySensor(coordinator, api_url, device_id, device_name, "resetDate", endpoint="calcRes", unit=None, icon="mdi:calendar-refresh"),
            TesySensor(coordinator, api_url, device_id, device_name, "volume", endpoint="calcRes", unit=UnitOfVolume.LITERS, icon="mdi:water"),
            TesySensor(coordinator, api_url, device_id, device_name, "watt", endpoint="calcRes", unit=UnitOfPower.WATT, icon="mdi:flash"),
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
            ATTR_MODE: "Operating Mode",
            "err_flag": "Error Flag",
            "lockB": "Child Lock Status",
            "boost": "Boost Mode",
            "watts": "Power Consumption (Watts)",
            ATTR_CURRENT_TEMP: "Current Temperature",
            ATTR_TARGET_TEMP: "Target Temperature",
            "mix40": "Water Mix at 40°C",
            "resetDate": "Reset Date of Energy Usage",
            "volume": "Water Volume",
            "watt": "Current Power",
            ATTR_TIME_ZONE: "Time Zone",
            ATTR_DATE_TIME: "Date/Time",            
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
        """Return the current energy consumption in Wh."""
        calc_res = self.coordinator.data.get("calcRes", {})
    
        # Retrieve 'sum' (total energy in Joules) and 'watt' (power in Watts) from calcRes
        total_energy_usage = calc_res.get("sum")
        watt = calc_res.get("watt")
    
        try:
            # Convert both values to numeric types if they are not already
            total_energy_usage = float(total_energy_usage) if total_energy_usage is not None else None
            watt = float(watt) if watt is not None else None
        except ValueError as e:
            _LOGGER.error("Failed to convert energy data to numeric values. Error: %s", e)
            return None
    
        if total_energy_usage is not None and watt is not None:
            try:
                # Convert Joules to Wh, then multiply by power
                energy = (total_energy_usage / 3600) * watt
                return int(energy)
            except (ValueError, TypeError) as e:
                _LOGGER.error("Invalid energy calculation. Error: %s", e)
                return None
        else:
            _LOGGER.warning(
                "Energy consumption data is incomplete. 'sum': %s, 'watt': %s",
                total_energy_usage,
                watt,
            )
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
        schedule_data = self.coordinator.data.get(self._schedule_type, None)

        if not schedule_data:
            _LOGGER.warning("No schedule data available for type: %s", self._schedule_type)
            return None
            
        if self._schedule_type == "vacation":
            # Handle vacation schedule format
            try:
                vacation_temp = schedule_data.get("vTemp")
                return vacation_temp
            except (AttributeError, KeyError) as e:
                _LOGGER.error(
                    "Error retrieving vacation temperature from schedule data: %s. Error: %s",
                    schedule_data,
                    e,
                )
                return None
            
        if not isinstance(schedule_data, list) or len(schedule_data) < 1:
            _LOGGER.error("Invalid schedule data format for type: %s. Data: %s", self._schedule_type, schedule_data)
            return None

        try:
            current_temp = schedule_data[0].get(f"h{current_hour:02d}")
            return current_temp
        except (IndexError, AttributeError) as e:
            _LOGGER.error(
                "Error retrieving temperature for current hour from schedule data: %s. Error: %s",
                schedule_data,
                e,
            )
            return None

    @property
    def extra_state_attributes(self):
        """Return detailed schedule data."""
        return {
            "schedule_details": self.coordinator.data.get(self._schedule_type, {}),
            "device_name": self._device_name,
            "source": "Tesy API",
        }
