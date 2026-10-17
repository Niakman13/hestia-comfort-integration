"""Stable keys for the first observation-only alpha."""
DOMAIN = "niak_comfort"
VERSION = "0.9.0-beta.10"
VIEW_VERSION = 1
# A contact that opens for less than this is a bounce, not an opening to advise about.
OPEN_DEBOUNCE_SECONDS = 60
# Seven-day outdoor mean (hourly statistics), refreshed at most this often.
SEASON_REFRESH_SECONDS = 3600
SOURCES = {
    "indoor_temperature": "temperature", "outdoor_temperature": "temperature",
    "indoor_humidity": "humidity", "outdoor_humidity": "humidity", "co2": "co2",
    "illuminance": "illuminance", "pm25": "pm25", "voc": "voc", "purifier": "purifier", "ventilation": "ventilation",
    "rain": "rain", "pollution": "pollution", "heating": "heating",
    "wind_gust": "wind", "wind_bearing": "bearing", "solar": "irradiance",
}
# Home Assistant areas that describe the outside: offered for exterior sources, never as rooms.
OUTDOOR_AREAS = ("exterieur", "extérieur", "dehors", "jardin", "terrasse", "balcon", "cour", "patio",
                 "outdoor", "outside", "garden", "yard", "terrace", "balcony")
