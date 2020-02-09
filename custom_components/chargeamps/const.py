"""Constants for Chargeamps."""
# Base component constants
DOMAIN = "chargeamps"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.2"
PLATFORMS = ["sensor", "switch"]
ISSUE_URL = "https://github.com/kirei/hass-chargeamps/issues"

# Icons
ICON = "mdi:car-connected"

# Configuration
CONF_CHARGEPOINTS = "chargepoints"
CONF_READONLY = "readonly"

# Defaults
DEFAULT_NAME = DOMAIN

# Possible dimmer values
DIMMER_VALUES = ["off", "low", "medium", "high"]
