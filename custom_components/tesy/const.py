"""Constants for the Tesy integration."""
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.water_heater import WaterHeaterEntityFeature

DOMAIN = "tesy"
HTTP_TIMEOUT = 15
UPDATE_INTERVAL = 30

TESY_SUPPORTED_FEATURES = (
    WaterHeaterEntityFeature.TARGET_TEMPERATURE
    | WaterHeaterEntityFeature.OPERATION_MODE
    | WaterHeaterEntityFeature.AWAY_MODE
    | WaterHeaterEntityFeature.ON_OFF
)

# API-specific mappings
API_OPERATION_MODES = {
    "Off": "Off",
    "On": "On",
    "Manual": "1",
    "Program 1": "2",
    "Program 2": "3",
    "Program 3": "4",
    "Eco Smart": "5",
    "Eco Comfort": "6",
    "Eco Night": "7",
    "Performance": "10",
}

API_STATE_MAPPING = {
    "on": STATE_ON,
    "off": STATE_OFF,
}

# Device attributes
ATTR_POWER = "power_sw"
ATTR_CURRENT_TEMP = "gradus"
ATTR_TARGET_TEMP = "ref_gradus"
ATTR_MODE = "mode"
ATTR_IS_HEATING = "heater_state"
ATTR_LAST_OPERATION_MODE = "mode"
ATTR_TIME_ZONE = "tz"
ATTR_DATE_TIME = "date"

# Device mapping
TESY_DEVICE_TYPES = {
    "2000": {
        "name": "ModEco",
        "min_setpoint": 8,
        "max_setpoint": 75,
    },
    "2002": {
        "name": "BeliSlimo",
        "min_setpoint": 15,
        "max_setpoint": 75,
        "use_showers": True,
    },
    "2003": {
        "name": "BiLight Smart",
        "min_setpoint": 15,
        "max_setpoint": 75,
    },
    "2004": {
        "name": "ModEco 2",
        "min_setpoint": 15,
        "max_setpoint": 75,
    },
    "2005": {
        "name": "BelliSlimo Lite",
        "min_setpoint": 15,
        "max_setpoint": 75,
        "use_showers": True,
    },
}

SCHEDULE_ENDPOINTS = {
    "p1": "getP1",
    "p2": "getP2",
    "p3": "getP3",
    "vacation": "getVacation",
}