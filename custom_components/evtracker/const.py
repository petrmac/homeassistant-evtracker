"""Constants for the EV Tracker integration."""

from typing import Final

DOMAIN: Final = "evtracker"
VERSION: Final = "1.0.0"

# Configuration keys
CONF_API_KEY: Final = "api_key"
CONF_CAR_ID: Final = "car_id"
CONF_CAR_NAME: Final = "car_name"
CONF_UPDATE_INTERVAL: Final = "update_interval"

# Tariff configuration keys
CONF_TARIFF_SOURCE: Final = "tariff_source"
CONF_TARIFF_ENTITY: Final = "tariff_entity"
CONF_TARIFF_LOW_START_1: Final = "tariff_low_start_1"
CONF_TARIFF_LOW_END_1: Final = "tariff_low_end_1"
CONF_TARIFF_LOW_START_2: Final = "tariff_low_start_2"
CONF_TARIFF_LOW_END_2: Final = "tariff_low_end_2"
CONF_TARIFF_LOW_START_3: Final = "tariff_low_start_3"
CONF_TARIFF_LOW_END_3: Final = "tariff_low_end_3"
CONF_TARIFF_LOW_START_4: Final = "tariff_low_start_4"
CONF_TARIFF_LOW_END_4: Final = "tariff_low_end_4"
CONF_TARIFF_WEEKEND_LOW: Final = "tariff_weekend_low"
CONF_TARIFF_WINDOW_TYPE: Final = "tariff_window_type"

# Price configuration keys
CONF_PRICE_HIGH: Final = "price_high"
CONF_PRICE_LOW: Final = "price_low"
CONF_VAT_PERCENTAGE: Final = "vat_percentage"
CONF_USE_PRICES: Final = "use_prices"

# Tariff window type options (what the configured windows represent)
WINDOW_TYPE_LOW: Final = "low"  # Windows define LOW tariff periods (default)
WINDOW_TYPE_HIGH: Final = "high"  # Windows define HIGH tariff periods

# Tariff source options
TARIFF_SOURCE_NONE: Final = "none"
TARIFF_SOURCE_SCHEDULE: Final = "schedule"
TARIFF_SOURCE_ENTITY: Final = "entity"

# Default values
DEFAULT_UPDATE_INTERVAL: Final = 300  # 5 minutes
DEFAULT_API_BASE_URL: Final = "https://api.evtracker.cz/api/v1"
DEFAULT_TARIFF_LOW_START_1: Final = "22:00"
DEFAULT_TARIFF_LOW_END_1: Final = "06:00"
DEFAULT_TARIFF_LOW_START_2: Final = ""  # Empty = disabled
DEFAULT_TARIFF_LOW_END_2: Final = ""
DEFAULT_TARIFF_LOW_START_3: Final = ""
DEFAULT_TARIFF_LOW_END_3: Final = ""
DEFAULT_TARIFF_LOW_START_4: Final = ""
DEFAULT_TARIFF_LOW_END_4: Final = ""
DEFAULT_TARIFF_WINDOW_TYPE: Final = WINDOW_TYPE_LOW

# Default price values
DEFAULT_PRICE_HIGH: Final = 0.0  # Price per kWh without VAT for HIGH tariff
DEFAULT_PRICE_LOW: Final = 0.0  # Price per kWh without VAT for LOW tariff
DEFAULT_VAT_PERCENTAGE: Final = 21.0  # Czech VAT rate
DEFAULT_USE_PRICES: Final = False  # Whether to use configured prices

# API endpoints
ENDPOINT_CARS: Final = "/cars"
ENDPOINT_CARS_DEFAULT: Final = "/cars/default"
ENDPOINT_SESSIONS: Final = "/sessions"
ENDPOINT_SESSIONS_SIMPLE: Final = "/sessions/simple"
ENDPOINT_HA_STATE: Final = "/homeassistant/state"

# Service names
SERVICE_LOG_SESSION: Final = "log_session"
SERVICE_LOG_SESSION_SIMPLE: Final = "log_session_simple"

# Service field names
ATTR_ENERGY_KWH: Final = "energy_kwh"
ATTR_START_TIME: Final = "start_time"
ATTR_END_TIME: Final = "end_time"
ATTR_CAR_ID: Final = "car_id"
ATTR_LOCATION: Final = "location"
ATTR_EXTERNAL_ID: Final = "external_id"
ATTR_PROVIDER: Final = "provider"
ATTR_ENERGY_SOURCE: Final = "energy_source"
ATTR_RATE_TYPE: Final = "rate_type"
ATTR_PRICE_PER_KWH: Final = "price_per_kwh"
ATTR_VAT_PERCENTAGE: Final = "vat_percentage"
ATTR_NOTES: Final = "notes"

# Sensor keys
SENSOR_MONTHLY_ENERGY: Final = "monthly_energy"
SENSOR_MONTHLY_COST: Final = "monthly_cost"
SENSOR_MONTHLY_SESSIONS: Final = "monthly_sessions"
SENSOR_YEARLY_ENERGY: Final = "yearly_energy"
SENSOR_YEARLY_COST: Final = "yearly_cost"
SENSOR_LAST_SESSION_ENERGY: Final = "last_session_energy"
SENSOR_LAST_SESSION_COST: Final = "last_session_cost"
SENSOR_AVG_COST_PER_KWH: Final = "avg_cost_per_kwh"

# Binary sensor keys
BINARY_SENSOR_CONNECTED: Final = "connected"
BINARY_SENSOR_LOW_TARIFF: Final = "low_tariff"

# Units
CURRENCY_CZK: Final = "CZK"
UNIT_KWH: Final = "kWh"
UNIT_CZK_PER_KWH: Final = "CZK/kWh"

# Energy sources
ENERGY_SOURCE_GRID: Final = "GRID"
ENERGY_SOURCE_SOLAR: Final = "SOLAR"

# Tariff rate types (for dual-rate electricity plans)
RATE_TYPE_HIGH: Final = "HIGH"  # Peak/daytime tariff
RATE_TYPE_LOW: Final = "LOW"  # Off-peak/night tariff

# Providers
PROVIDER_HOME: Final = "HOME"

# Error messages
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_INVALID_API_KEY: Final = "invalid_api_key"
ERROR_UNKNOWN: Final = "unknown"
