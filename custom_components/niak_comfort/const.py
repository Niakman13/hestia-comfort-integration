"""Stable keys for the first observation-only alpha."""
DOMAIN = "niak_comfort"
VERSION = "1.1.2"
VIEW_VERSION = 1
# A contact open for less than this is a bounce: shown at once, but advice waits for a real opening.
OPEN_DEBOUNCE_SECONDS = 30
# Seven-day outdoor mean (hourly statistics), refreshed at most this often.
SEASON_REFRESH_SECONDS = 3600
# Right after Home Assistant starts, sensors arrive one by one: silent ones are « loading », not broken.
STARTUP_GRACE_SECONDS = 300
# Past openings are read again from the recorder this often (and soon after each closing).
LEARNING_REFRESH_SECONDS = 6 * 3600
SOURCES = {
    "indoor_temperature": "temperature", "outdoor_temperature": "temperature",
    "indoor_humidity": "humidity", "outdoor_humidity": "humidity", "co2": "co2",
    "illuminance": "illuminance", "pm25": "pm25", "voc": "voc", "purifier": "purifier", "ventilation": "ventilation", "ventilation_boost": "ventilation",
    "rain": "rain", "pollution": "pollution", "heating": "heating",
    "wind_gust": "wind", "wind_bearing": "bearing", "solar": "irradiance",
}
# Home Assistant areas that describe the outside: offered for exterior sources, never as rooms.
OUTDOOR_AREAS = ("exterieur", "extérieur", "dehors", "jardin", "terrasse", "balcon", "cour", "patio",
                 "outdoor", "outside", "garden", "yard", "terrace", "balcony")
