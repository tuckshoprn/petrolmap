# const.py
from datetime import timedelta

DOMAIN = "petrolmap"
CONF_POSTCODE = "postcode"
CONF_DISTANCE = "distance"
CONF_API_KEY = "api_key"
DEFAULT_DISTANCE = 5

FUEL_TYPE_NAMES = {
    1: "Unleaded Petrol",
    2: "Diesel",
    4: "Super Unleaded Petrol",
    5: "Premium Diesel"
}

# ✅ Updated API URL to match working endpoint
API_BASE_URL = "https://www.petrolprices.com/app/geojson/{fuel_type}/0/0/0/distance/{radius}?lat={lat}&lng={lng}"

PETROLMAP_API_URL = "https://petrolmap.co.uk/data/stations-guest"
GEOCODE_API_URL = "https://nominatim.openstreetmap.org/search"

API_TIMEOUT = 10
PRICE_AGE_LIMIT_DAYS = 7
PLATFORMS = ["sensor"]
UPDATE_INTERVAL = timedelta(hours=6)
