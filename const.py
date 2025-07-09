# const.py
from datetime import timedelta

# General constants for the PetrolMap custom component
DOMAIN = "petrolmap"
CONF_POSTCODE = "postcode"
CONF_DISTANCE = "distance"
CONF_API_KEY = "api_key"
DEFAULT_DISTANCE = 5

# Fuel type mappings for PetrolPrices.com API
FUEL_TYPE_NAMES = {
    1: "Super Unleaded Petrol",  # Type1
    2: "Unleaded Petrol",        # Type2
    4: "Premium Diesel",         # Type4
    5: "Diesel"                  # Type5
}

# Brand type mappings for PetrolPrices.com API
BRAND_TYPES = {
    "all_brands": 0,      # All brands
    "bp": 1,              # BP stations
    "applegreen": 6,      # Applegreen stations
    "texaco": 7           # Texaco stations
}

# Sort type options for PetrolPrices.com API
SORT_TYPES = ["price", "distance"]  # Valid sort options: price (cheapest first), distance (nearest first)

# PetrolPrices.com API configuration
PETROL_PRICES_API_BASE_URL = "https://www.petrolprices.com/app/geojson/{fuel_type}/{brand_type}/{result_limit}/{offset}/{sort_type}/{radius}?lat={lat}&lng={lng}"
DEFAULT_FUEL_TYPE = 5  # Diesel (Type5)
DEFAULT_BRAND_TYPE = 0  # All brands
DEFAULT_RESULT_LIMIT = 0  # Default for guest users (no limit or API default)
DEFAULT_OFFSET = 0  # Default for guest users (no offset)
DEFAULT_SORT_TYPE = "price"  # Sort by price (cheapest first, alternate is distance - nearest first)

# API URLs
PETROLMAP_API_URL = "https://petrolmap.co.uk/data/stations-guest"
GEOCODE_API_URL = "https://nominatim.openstreetmap.org/search"

# API settings
API_TIMEOUT = 10
PRICE_AGE_LIMIT_DAYS = 7
PLATFORMS = ["sensor"]
UPDATE_INTERVAL = timedelta(hours=6)

# API notes
API_GUEST_LIMIT_NOTE = (
    "Guest users have a very small hourly view limit for the PetrolPrices.com API. "
    "Result limit and offset cannot be modified by guest users. "
    "Use these constants to construct API URLs and manage requests within the limit."
)