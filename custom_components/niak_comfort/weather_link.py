"""Link with Niak Weather, through its published interface only (Écosystème Niak, rule 6).

Its entities are found by their stable unique id `<entry>_<key>`, never by name, and its
settings are read through `hass.data["niak_weather_api"]` (version 1), never directly.
"""
import inspect

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

API_KEY = "niak_weather_api"
API_VERSION = 1
# Niak Weather station roles → Niak Confort exterior sources.
ROLES = {"temperature": "outdoor_temperature", "humidity": "outdoor_humidity", "rain_rate": "rain",
         "wind_gust": "wind_gust", "wind_bearing": "wind_bearing", "solar_radiation": "solar"}
VIGILANCE = {"verte": 0, "jaune": 1, "orange": 2, "rouge": 3}


def api(hass):
    candidate = hass.data.get(API_KEY)
    return candidate if candidate is not None and getattr(candidate, "version", None) == API_VERSION else None


def status(hass):
    """What « Mon logement » shows: is Niak Weather there, and which places it offers."""
    link = api(hass)
    return {"installed": link is not None, "places": link.places() if link else []}


def listen(hass, entry_id, update):
    """Calls `update` when Niak Weather recomputes this place. Saying who listens lets Niak Weather
    show the link too; a Niak Weather older than 2.1 does not take `brick` yet."""
    link = api(hass)
    if link is None:
        return lambda: None
    parameters = inspect.signature(link.add_listener).parameters
    if "brick" in parameters or any(p.kind is p.VAR_KEYWORD for p in parameters.values()):
        return link.add_listener(entry_id, update, brick=DOMAIN)
    return link.add_listener(entry_id, update)


def entity(hass, entry_id, key):
    """A Niak Weather entity by its stable key, or None (absent, disabled or another place)."""
    if not entry_id:
        return None
    found = er.async_get(hass).async_get_entity_id
    for domain in ("sensor", "binary_sensor"):
        if entity_id := found(domain, "niak_weather", f"{entry_id}_{key}"):
            return entity_id
    return None


def exterior(hass, entry_id):
    """The exterior sources proposed from Niak Weather: its station by role, then its own signals."""
    link = api(hass)
    station = link.station(entry_id) if link else None
    if not station:
        return None
    proposals = {ROLES[role]: entity_id for role, entity_id in station["sensors"].items() if role in ROLES}
    # Without a rain rate sensor, Niak Weather's own « rain now » still tells when it rains.
    if "rain" not in proposals and (rain := entity(hass, station["entry_id"], "pluie_en_cours")):
        proposals["rain"] = rain
    if air := entity(hass, station["entry_id"], "qualite_air"):
        proposals["pollution"] = air
    return {"entry_id": station["entry_id"], "title": station["title"], "proposals": proposals}


def air(hass, entry_id):
    """Today's outdoor air from the source chosen in Niak Weather (Atmo France or a WAQI station), on Atmo's
    1 to 6 scale; None when not linked, without an air source, or before Niak Weather 2.5.7."""
    link = api(hass)
    if not link or not entry_id or not hasattr(link, "air"):
        return None
    return link.air(entry_id)


def _number(hass, entity_id):
    state = hass.states.get(entity_id) if entity_id else None
    try:
        return float(state.state) if state else None
    except (TypeError, ValueError):
        return None


def outlook(hass, entry_id):
    """Niak Weather's view of what is coming, for the engine. Unknown stays None."""
    link = api(hass)
    if not link or not entry_id:
        return {}
    storm = hass.states.get(entity(hass, entry_id, "orage") or "")
    vigilance = hass.states.get(entity(hass, entry_id, "vigilance") or "")
    return {"storm": {"on": True, "off": False}.get(storm.state) if storm else None,
            "vigilance": VIGILANCE.get(vigilance.state) if vigilance else None,
            "rain_in_hours": _number(hass, entity(hass, entry_id, "next_rain")),
            "tomorrow_max": _number(hass, entity(hass, entry_id, "maximale_demain")),
            "hours": link.hourly(entry_id)}
