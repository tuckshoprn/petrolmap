# __init__.py
import logging
import asyncio
import aiohttp
import async_timeout
import re
from datetime import timedelta, datetime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryError
from .const import (
    DOMAIN, CONF_POSTCODE, CONF_DISTANCE, CONF_API_KEY, FUEL_TYPE_NAMES,
    UPDATE_INTERVAL, PETROL_PRICES_API_BASE_URL, PETROLMAP_API_URL, GEOCODE_API_URL,
    API_TIMEOUT, PRICE_AGE_LIMIT_DAYS, DEFAULT_BRAND_TYPE, DEFAULT_RESULT_LIMIT,
    DEFAULT_OFFSET, DEFAULT_SORT_TYPE
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry):
    """Set up PetrolMap from a config entry."""
    _LOGGER.debug(f"Setting up config entry: {config_entry.data}")
    
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"last_data": {}, "known_stations": set(), "cf_cookies": {}}
        _LOGGER.debug(f"Initialized hass.data[{DOMAIN}] with last_data, known_stations, and cf_cookies")
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=lambda: async_update_data(hass, config_entry),
        update_interval=UPDATE_INTERVAL,
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryError as e:
        _LOGGER.error(f"Initial refresh failed: {str(e)}")
        raise
    except Exception as e:
        _LOGGER.error(f"Unexpected error during initial refresh: {str(e)}")
        raise ConfigEntryError(f"Unexpected error during setup: {str(e)}")

    hass.data[DOMAIN][config_entry.entry_id] = coordinator
    _LOGGER.debug(f"Set hass.data[{DOMAIN}][{config_entry.entry_id}] with coordinator")
    
    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])
    return True

async def async_update_data(hass: HomeAssistant, config_entry):
    """Fetch data from PetrolPrices and PetrolMap APIs."""
    _LOGGER.debug(f"Starting async_update_data for config entry: {config_entry.data}")
    postcode = config_entry.data[CONF_POSTCODE]
    distance = config_entry.data[CONF_DISTANCE]
    api_key = config_entry.data.get(CONF_API_KEY, "")
    fuel_types = [1, 2, 4, 5]  # All fuel types

    async with aiohttp.ClientSession() as session:
        # Geocode postcode using Nominatim with fallback to FreeMapTools
        lat, lng = None, None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with async_timeout.timeout(API_TIMEOUT):
                    geocode_url = f"{GEOCODE_API_URL}?q={postcode}&format=json&limit=1"
                    headers = {"User-Agent": "HomeAssistant/1.0"}
                    _LOGGER.debug(f"Attempting Nominatim geocoding for postcode {postcode}")
                    async with session.get(geocode_url, headers=headers) as response:
                        if response.status != 200:
                            text = await response.text()
                            _LOGGER.warning(f"Nominatim geocoding failed with status {response.status}: {text}")
                            break
                        geocode_data = await response.json()
                        if not geocode_data:
                            _LOGGER.warning(f"No coordinates found for postcode {postcode} in Nominatim")
                            break
                        lat = float(geocode_data[0]["lat"])
                        lng = float(geocode_data[0]["lon"])
                        _LOGGER.debug(f"Geocoded {postcode} to lat: {lat}, lng: {lng}")
                        break
            except Exception as e:
                _LOGGER.warning(f"Nominatim geocoding error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                break

        # Fallback to FreeMapTools if Nominatim fails
        if lat is None or lng is None:
            _LOGGER.debug(f"Falling back to FreeMapTools for postcode {postcode}")
            try:
                async with async_timeout.timeout(API_TIMEOUT):
                    fallback_url = f"https://www.freemaptools.com/ajax/uk/uk-postcode-to-lat-lng.php?postcode={postcode}&alsosearchterminated=true"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
                        "accept": "*/*",
                        "accept-encoding": "gzip, deflate, br",
                        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                        "referer": "https://www.freemaptools.com/convert-uk-postcode-to-lat-lng.htm"
                    }
                    async with session.get(fallback_url, headers=headers) as response:
                        if response.status != 200:
                            text = await response.text()
                            _LOGGER.error(f"FreeMapTools geocoding failed with status {response.status}: {text}")
                            raise ConfigEntryError(f"FreeMapTools geocoding failed with status {response.status}")
                        geocode_data = await response.json()
                        if geocode_data.get("status") != 1 or not geocode_data.get("output"):
                            _LOGGER.error(f"Invalid FreeMapTools geocoding data: {geocode_data}")
                            raise ConfigEntryError("Invalid FreeMapTools geocoding response")
                        lat = float(geocode_data["output"][0]["latitude"])
                        lng = float(geocode_data["output"][0]["longitude"])
                        _LOGGER.debug(f"FreeMapTools geocoded {postcode} to lat: {lat}, lng: {lng}")
            except Exception as e:
                _LOGGER.error(f"FreeMapTools geocoding error: {str(e)}")
                raise ConfigEntryError(f"Geocoding failed after retries: {str(e)}")

        if lat is None or lng is None:
            raise ConfigEntryError(f"No coordinates found for postcode {postcode} after all attempts")

        # Scrape Cloudflare cookies
        if not hass.data[DOMAIN]["cf_cookies"]:
            try:
                async with async_timeout.timeout(API_TIMEOUT):
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                        "accept-encoding": "gzip, deflate, br",
                        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                    }
                    async with session.get("https://www.petrolprices.com", headers=headers) as response:
                        if response.status != 200:
                            _LOGGER.warning(f"Failed to scrape Cloudflare cookies: status {response.status}")
                        else:
                            cookies = response.cookies
                            hass.data[DOMAIN]["cf_cookies"] = {key: value.value for key, value in cookies.items()}
                            _LOGGER.debug(f"Scraped Cloudflare cookies: {hass.data[DOMAIN]['cf_cookies']}")
                            # Attempt to extract token from response headers or body
                            text = await response.text()
                            token_match = re.search(r'"cf-token":"([^"]+)"', text)
                            hass.data[DOMAIN]["cf_token"] = token_match.group(1) if token_match else "default_token"
            except Exception as e:
                _LOGGER.warning(f"Failed to scrape Cloudflare cookies: {str(e)}")
                hass.data[DOMAIN]["cf_token"] = "default_token"

        # Fetch fuel prices from PetrolPrices
        stations = {}
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        }
        if api_key:
            headers["authorization"] = f"Bearer {api_key}"
        if hass.data[DOMAIN].get("cf_token"):
            headers["cf-token"] = hass.data[DOMAIN]["cf_token"]

        max_retries = 3
        for fuel_type in fuel_types:
            url = PETROL_PRICES_API_BASE_URL.format(
                fuel_type=fuel_type,
                brand_type=DEFAULT_BRAND_TYPE,
                result_limit=DEFAULT_RESULT_LIMIT,
                offset=DEFAULT_OFFSET,
                sort_type=DEFAULT_SORT_TYPE,
                radius=distance,
                lat=lat,
                lng=lng
            )
            _LOGGER.debug(f"PetrolPrices API URL for fuel type {fuel_type}: {url}")
            for attempt in range(max_retries):
                try:
                    async with async_timeout.timeout(API_TIMEOUT):
                        async with session.get(url, headers=headers, cookies=hass.data[DOMAIN]["cf_cookies"]) as response:
                            if response.status == 429:
                                if attempt < max_retries - 1:
                                    wait_time = 2 ** attempt
                                    _LOGGER.warning(f"Rate limit hit for fuel type {fuel_type}, retrying after {wait_time}s")
                                    await asyncio.sleep(wait_time)
                                    continue
                                _LOGGER.warning(f"Rate limit exceeded for fuel type {fuel_type}, skipping")
                                break
                            if response.status == 401 or response.status == 403:
                                _LOGGER.error(f"PetrolPrices API unauthorized for fuel type {fuel_type}")
                                raise ConfigEntryError(f"PetrolPrices API requires valid API key")
                            if response.status != 200:
                                text = await response.text()
                                _LOGGER.error(f"API request failed for fuel type {fuel_type} with status {response.status}: {text}")
                                raise ConfigEntryError(f"API request failed with status {response.status}")
                            data = await response.json()
                            _LOGGER.debug(f"PetrolPrices API response for fuel type {fuel_type}: {data}")
                            if data.get("limitExceed"):
                                _LOGGER.warning(f"Rate limit exceeded in response for fuel type {fuel_type}")
                                break
                            for feature in data.get("stations", []):
                                station_id = str(feature["idstation"])
                                price = feature.get("price", 0) / 10  # Convert pence to GBP
                                if price <= 0:
                                    continue
                                if station_id not in stations:
                                    stations[station_id] = {
                                        "id": station_id,
                                        "name": feature.get("name", "Unknown"),
                                        "address": feature.get("address", "Unknown"),
                                        "postcode": feature.get("postcode", "Unknown"),
                                        "latitude": feature.get("latitude", lat),
                                        "longitude": feature.get("longitude", lng),
                                        "prices": {},
                                        "last_updated": feature.get("recordedtime"),
                                        "brand": feature.get("fuelbrand", "Unknown"),
                                        "features": [],
                                    }
                                if (datetime.now().astimezone() - datetime.fromisoformat(feature.get("recordedtime", "").replace("Z", "+00:00"))).days <= PRICE_AGE_LIMIT_DAYS:
                                    stations[station_id]["prices"][str(fuel_type)] = price
                except aiohttp.ClientError as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        _LOGGER.warning(f"Client error for fuel type {fuel_type}, retrying after {wait_time}s: {str(e)}")
                        await asyncio.sleep(wait_time)
                        continue
                    _LOGGER.warning(f"API client error for fuel type {fuel_type}, skipping: {str(e)}")
                    break
                except Exception as e:
                    _LOGGER.error(f"Unexpected API error for fuel type {fuel_type}: {str(e)}")
                    raise ConfigEntryError(f"Unexpected API error: {str(e)}")

        # Fetch station features from PetrolMap for new stations
        new_stations = set(stations.keys()) - hass.data[DOMAIN]["known_stations"]
        if new_stations or not hass.data[DOMAIN]["known_stations"]:
            _LOGGER.debug(f"Fetching PetrolMap for {len(new_stations)} new stations")
            petrolmap_url = f"{PETROLMAP_API_URL}?address={postcode}&fuel_type=petrol&search_type=postcode&brand=any&distance={distance}&p=map"
            try:
                async with async_timeout.timeout(API_TIMEOUT):
                    async with session.get(petrolmap_url, headers=headers) as response:
                        if response.status != 200:
                            _LOGGER.warning(f"PetrolMap API failed with status {response.status}")
                            petrolmap_data = {"success": False, "data": []}
                        else:
                            petrolmap_data = await response.json()
                            for pm_station in petrolmap_data.get("data", []):
                                pm_postcode = pm_station.get("Postcode", "").replace(" ", "").upper()
                                for station_id, station in stations.items():
                                    pp_postcode = station["postcode"].replace(" ", "").upper()
                                    if pm_postcode == pp_postcode:
                                        station["features"] = pm_station.get("Features", [])
                                        break
            except Exception as e:
                _LOGGER.warning(f"PetrolMap API error, proceeding without features: {str(e)}")
                petrolmap_data = {"success": False, "data": []}
            hass.data[DOMAIN]["known_stations"].update(new_stations)

        if not stations:
            _LOGGER.warning("No valid stations with prices found, returning cached data")
            return hass.data[DOMAIN].get("last_data", {}).get(config_entry.entry_id, {})

        result = {"stations": stations}
        hass.data[DOMAIN]["last_data"][config_entry.entry_id] = result
        _LOGGER.debug(f"Cached result for entry_id {config_entry.entry_id}")
        return result