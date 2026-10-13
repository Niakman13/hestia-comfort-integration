"""Stable keys for the first observation-only alpha."""
DOMAIN = "niak_comfort"
VERSION = "0.4.0-beta.4"
VIEW_VERSION = 1
SOURCES = {
    "indoor_temperature": "temperature", "outdoor_temperature": "temperature",
    "indoor_humidity": "humidity", "outdoor_humidity": "humidity", "co2": "co2",
    "rain": "rain", "pollution": "pollution", "heating": "heating",
    "wind_gust": "wind", "solar": "irradiance",
}
# Home Assistant areas that describe the outside: offered for exterior sources, never as rooms.
OUTDOOR_AREAS = ("exterieur", "extérieur", "dehors", "jardin", "terrasse", "balcon", "cour", "patio",
                 "outdoor", "outside", "garden", "yard", "terrace", "balcony")
