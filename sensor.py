# sensor.py
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, FUEL_TYPE_NAMES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    _LOGGER.debug(f"Setting up sensor for config entry: {config_entry.data}")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    data = coordinator.data
    _LOGGER.debug(f"Coordinator data: {data}")
    if not data or "stations" not in data or not data["stations"]:
        _LOGGER.warning("No valid station data available, skipping sensor creation")
        return

    for station_id, station in data["stations"].items():
        _LOGGER.debug(f"Processing station: {station}")
        for fuel_type in station.get("prices", {}):
            fuel_name = FUEL_TYPE_NAMES.get(int(fuel_type), "Unknown")
            if station["prices"].get(fuel_type):
                entities.append(PetrolMapSensor(coordinator, config_entry, station, fuel_type, fuel_name))
            else:
                _LOGGER.debug(f"No price data for fuel type {fuel_name} in station {station.get('name', 'Unknown')}")

    if not entities:
        _LOGGER.warning("No valid entities created from station data")
        return

    _LOGGER.debug(f"Adding entities: {[e.name for e in entities]}")
    async_add_entities(entities)

class PetrolMapSensor(CoordinatorEntity, SensorEntity):
    """Representation of a PetrolMap sensor."""

    def __init__(self, coordinator, config_entry, station, fuel_type, fuel_name):
        super().__init__(coordinator)
        self._station = station
        self._fuel_type = fuel_type
        self._fuel_name = fuel_name
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_{station['id']}_{fuel_type}"
        self._attr_name = f"PetrolMap {station['name']} {fuel_name}".replace(" ", "_").lower()
        self._attr_unit_of_measurement = "£/L"
        _LOGGER.debug(f"Created sensor: {self._attr_name}, unique_id: {self._attr_unique_id}")

    @property
    def state(self):
        """Return the state of the sensor."""
        price = self._station.get("prices", {}).get(str(self._fuel_type))
        _LOGGER.debug(f"State for {self._attr_name}: {price}")
        return f"{price:.2f}" if price else "unknown"

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = {
            "station_name": self._station.get("name"),
            "fuel_type": self._fuel_name,
            "address": self._station.get("address"),
            "postcode": self._station.get("postcode"),
            "last_updated": self._station.get("last_updated"),
            "brand": self._station.get("brand"),
            "features": self._station.get("features", []),
            "latitude": self._station.get("latitude"),
            "longitude": self._station.get("longitude")
        }
        _LOGGER.debug(f"Attributes for {self._attr_name}: {attrs}")
        return attrs