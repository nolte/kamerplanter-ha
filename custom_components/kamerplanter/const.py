"""Constants for the Kamerplanter integration."""

from typing import Final

DOMAIN: Final = "kamerplanter"

# Config keys
CONF_API_KEY: Final = "api_key"
CONF_TENANT_SLUG: Final = "tenant_slug"
CONF_LIGHT_MODE: Final = "light_mode"

# Default polling intervals (seconds)
DEFAULT_POLL_PLANTS: Final = 300
DEFAULT_POLL_LOCATIONS: Final = 300
DEFAULT_POLL_ALERTS: Final = 60
DEFAULT_POLL_TASKS: Final = 300

# Minimum polling intervals (seconds)
MIN_POLL_ALERTS: Final = 30
MIN_POLL_PLANTS: Final = 120
MIN_POLL_LOCATIONS: Final = 120
MIN_POLL_TASKS: Final = 120

# Options keys
CONF_POLL_PLANTS: Final = "poll_interval_plants"
CONF_POLL_LOCATIONS: Final = "poll_interval_locations"
CONF_POLL_ALERTS: Final = "poll_interval_alerts"
CONF_POLL_TASKS: Final = "poll_interval_tasks"

# Platforms
PLATFORMS: Final = [
    "sensor",
    "binary_sensor",
    "calendar",
    "todo",
    "button",
]

# Event types (HA-NFR-005)
EVENT_TASK_COMPLETED: Final = f"{DOMAIN}_task_completed"
EVENT_DATA_REFRESHED: Final = f"{DOMAIN}_data_refreshed"

# Notification event types (REQ-030)
EVENT_CARE_DUE: Final = f"{DOMAIN}_care_due"
EVENT_SEASONAL: Final = f"{DOMAIN}_seasonal"
EVENT_SENSOR_ALERT: Final = f"{DOMAIN}_sensor_alert"
EVENT_IPM_ALERT: Final = f"{DOMAIN}_ipm_alert"
EVENT_TANK_ALERT: Final = f"{DOMAIN}_tank_alert"
EVENT_HARVEST: Final = f"{DOMAIN}_harvest"
EVENT_TASK_DUE: Final = f"{DOMAIN}_task_due"
EVENT_WEATHER_ALERT: Final = f"{DOMAIN}_weather_alert"
EVENT_PHASE: Final = f"{DOMAIN}_phase"

# Services
SERVICE_REFRESH: Final = "refresh_data"
SERVICE_CLEAR_CACHE: Final = "clear_cache"
SERVICE_FILL_TANK: Final = "fill_tank"
SERVICE_WATER_CHANNEL: Final = "water_channel"
SERVICE_CONFIRM_CARE: Final = "confirm_care"

# Storage (HA-NFR-004)
STORAGE_VERSION: Final = 1

# API-Key prefix
API_KEY_PREFIX: Final = "kp_"
