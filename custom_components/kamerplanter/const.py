"""Constants for the Kamerplanter integration."""

from typing import Final

DOMAIN: Final = "kamerplanter"

# Config keys
CONF_API_KEY: Final = "api_key"
CONF_TENANT_SLUG: Final = "tenant_slug"
CONF_LIGHT_MODE: Final = "light_mode"
CONF_INSTANCE_ID: Final = "instance_id"
CONF_API_PATH: Final = "api_path"

# Zeroconf / Discovery
MDNS_SERVICE_TYPE: Final = "_kamerplanter._tcp.local."
DEFAULT_API_PATH: Final = "/api"

# Sentinel flag for the synthetic location entry that carries HA-published tanks
# whose parent location is not published (issue #59). Consumers that iterate the
# location coordinator data by location key skip this entry via ``if not
# loc_key``; the standalone-tank and device-cleanup paths still find its
# ``_tanks`` list, so a published tank surfaces as a device even without a
# published location.
TANK_HOLDER_MARKER: Final = "_tank_holder"

# Default polling intervals (seconds)
DEFAULT_POLL_PLANTS: Final = 300
DEFAULT_POLL_LOCATIONS: Final = 300
DEFAULT_POLL_ALERTS: Final = 60
DEFAULT_POLL_TASKS: Final = 300
DEFAULT_POLL_IPM: Final = 120

# Minimum polling intervals (seconds)
MIN_POLL_ALERTS: Final = 30
MIN_POLL_PLANTS: Final = 120
MIN_POLL_LOCATIONS: Final = 120
MIN_POLL_TASKS: Final = 120
MIN_POLL_IPM: Final = 60

# Options keys
CONF_POLL_PLANTS: Final = "poll_interval_plants"
CONF_POLL_LOCATIONS: Final = "poll_interval_locations"
CONF_POLL_ALERTS: Final = "poll_interval_alerts"
CONF_POLL_TASKS: Final = "poll_interval_tasks"
CONF_POLL_IPM: Final = "poll_interval_ipm"

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
EVENT_IPM_ALERT: Final = f"{DOMAIN}_ipm_alert"

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
