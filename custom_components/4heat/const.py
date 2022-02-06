"""Constants for the 4Heat integration."""
from datetime import timedelta

from homeassistant.const import (
    TEMP_CELSIUS,
)

DOMAIN = "4heat"

DATA_QUERY = b'["SEL","0"]'
UNBLOCK_CMD = b'["SEC","1","J30255000000000001"]' # Unblock
OFF_CMD = b'["SEC","1","J30254000000000001"]' # OFF
ON_CMD = b'["SEC","1","J30253000000000001"]' # ON

TCP_PORT = 80

SOCKET_BUFFER = 1024
SOCKET_TIMEOUT = 10

DATA_COORDINATOR = "corrdinator"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=20)

MODE_TYPE = "30001"
ERROR_TYPE = "30002"

SENSOR_TYPES = {
    "30001": ["State", None, ""],
    "30002": ["Error", None, ""],
    "30003": ["Timer", None, ""],
    "30004": ["Ignition", None, ""],
    "30005": ["Exhaust temperature", TEMP_CELSIUS, ""],
    "30006": ["Room temperature", TEMP_CELSIUS, ""],
    "30007": ["Inputs", None, ""],
    "30008": ["Combustion fan", None, ""], #RPM
    "30009": ["Heating fan", None, ""],
    "30011": ["Combustion power", None, ""],
    "30012": ["UN 30012", None, ""],
    "30015": ["UN 30015", None, ""],
    "30017": ["Boiler water", TEMP_CELSIUS, ""],
    "30020": ["UN 30020", None, ""],
    "30025": ["Comb.FanRealSpeed", None, ""],
    "30026": ["UN 30026", None, ""],
    "30033": ["UN 30033", None, ""],
    "30040": ["UN 30040", None, ""],
    "30044": ["UN 30044", None, ""],
    "30084": ["UN 30084", None, ""],
    "40007": ["UN 40007", None, ""],
    "20180": ["Boiler target", TEMP_CELSIUS, ""],
    "20199": ["Boiler target", TEMP_CELSIUS, ""],
    "20205": ["UN 20205", None, ""],
    "20206": ["UN 20206", None, ""],
    "20211": ["UN 20211", None, ""],
    "20225": ["UN 20225", None, ""],
    "20364": ["UN 20364", None, ""],
    "20381": ["UN 20381", None, ""],
    "20365": ["UN 20365", None, ""],
    "20366": ["UN 20366", None, ""],
    "20369": ["UN 20369", None, ""],
    "20374": ["UN 20374", None, ""],
    "20375": ["UN 20375", None, ""],
    "20575": ["UN 20575", None, ""],
    "20493": ["UN 20493", None, ""],
    "20570": ["UN 20570", None, ""],
    "20801": ["Heating power", None, ""],
    "20803": ["UN 20803", None, ""],
    "20813": ["UN 20813", None, ""],
    "21700": ["Room termostat", TEMP_CELSIUS, ""],
    "40016": ["Outputs", None, ""],
    "50001": ["Auger on", None, ""],
}

MODE_NAMES = {
    0: "OFF",
    1: "Check Up",
    2: "Ignition",
    3: "Stabilization",
    4: "Ignition",
    5: "Run",
    6: "Modulation",
    7: "Extinguishing",
    7: "Safety",
    9: "Block",
    10: "RecoverIgnition",
    10: "Standby",
    30: "Ignition",
    31: "Ignition",
    32: "Ignition",
    33: "Ignition",
    34: "Ignition",
}
