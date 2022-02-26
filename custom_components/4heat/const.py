"""Constants for the 4Heat integration."""
from datetime import timedelta

from homeassistant.const import (
    TEMP_CELSIUS,
    PRESSURE_PA,
    PRESSURE_MBAR,
)

DOMAIN = "4heat"

ATTR_STOVE_ID = "stove_id"
ATTR_READING_ID = "reading_id"
ATTR_MARKER = "marker"
ATTR_NUM_VAL = "num_val"

DATA_QUERY = b'["SEL","0"]'
ERROR_QUERY = b'["SEC","3","I30001000000000000","I30002000000000000","I30017000000000000"]'
UNBLOCK_CMD = b'["SEC","1","J30255000000000001"]' # Unblock
OFF_CMD = b'["SEC","1","J30254000000000001"]' # OFF
ON_CMD = b'["SEC","1","J30253000000000001"]' # ON

OFF_CMD_OLD = b'["SEC","1","1"]' # OFF
ON_CMD_OLD = b'["SEC","1","0"]' # ON

MODES = [[ON_CMD, OFF_CMD, UNBLOCK_CMD], [ON_CMD_OLD, OFF_CMD_OLD, None]]
CONF_MODE = 'mode'
CMD_MODE_OPTIONS = ['Full set (default)', 'Limited set']

RESULT_VALS = 'SEC'
RESULT_ERROR = 'ERR'

TCP_PORT = 80

SOCKET_BUFFER = 1024
SOCKET_TIMEOUT = 10

DATA_COORDINATOR = "corrdinator"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=20)

MODE_TYPE = "30001"
ERROR_TYPE = "30002"
POWER_TYPE = "20364"

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
    "30012": ["Puffer temperature", TEMP_CELSIUS, ""],
    "30015": ["UN 30015", None, ""],
    "30017": ["Boiler water", TEMP_CELSIUS, ""],
    "30020": ["Water pressure", PRESSURE_MBAR, ""],
    "30025": ["Comb.FanRealSpeed", None, ""],
    "30026": ["UN 30026", TEMP_CELSIUS, ""],
    "30033": ["Exhaust depression", PRESSURE_PA, ""],
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
    "20364": ["Power Setting", None, ""],
    "20381": ["UN 20381", None, ""],
    "20365": ["UN 20365", None, ""],
    "20366": ["UN 20366", None, ""],
    "20369": ["UN 20369", None, ""],
    "20374": ["UN 20374", None, ""],
    "20375": ["UN 20375", None, ""],
    "20575": ["UN 20575", None, ""],
    "20493": ["Room temperature set point", TEMP_CELSIUS, ""],
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
    8: "Safety",
    9: "Block",
    10: "RecoverIgnition",
    11: "Standby",
    30: "Ignition",
    31: "Ignition",
    32: "Ignition",
    33: "Ignition",
    34: "Ignition",
}

ERROR_NAMES = {
    0: "No",
    1: "Safety Thermostat HV1: signalled also in case of Stove OFF",
    2: "Safety PressureSwitch HV2: signalled with Combustion Fan ON",
    3: "Extinguishing for Exhausting Temperature lowering",
    4: "Extinguishing for water over Temperature",
    5: "Extinguishing for Exhausting over Temperature",
    6: "unknown",
    7: "Encoder Error: No Encoder Signal (in case of P25=1 or 2)",
    8: "Encoder Error: Combustion Fan regulation failed (in case of P25=1 or 2)",
    9: "Low pressure in to the Boiler",
    10: "High pressure in to the Boiler Error",
    11: "DAY and TIME not correct due to prolonged absence of Power Supply",
    12: "Failed Ignition",
    13: "Ignition",
    14: "Ignition",
    15: "Lack of Voltage Supply",
    16: "Ignition",
    17: "Ignition",
    18: "Lack of Voltage Supply",
}

POWER_NAMES = {
    1: "P1",
    2: "P2",
    3: "P3",
    4: "P4",
    5: "P5",
    6: "P6",
    7: "Auto",
}