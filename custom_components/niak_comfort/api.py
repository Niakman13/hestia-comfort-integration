"""The interface Hestia Confort publishes for the other Hestia bricks (version 1).

Other bricks read `hass.data["niak_comfort_api"]` and check `version` before using it. It only grows
compatibly within a major version. First reader in view: a « Maison » brick, for the house as a whole.
"""
from .configuration import DATA_CONFIG, get_configuration
from .const import DOMAIN

API_KEY = "niak_comfort_api"
API_VERSION = 1


class NiakComfortApi:
    version = API_VERSION

    def __init__(self, hass):
        self.hass = hass

    def _loaded(self):
        return [e for e in self.hass.config_entries.async_entries(DOMAIN)
                if not e.data.get("home") and getattr(e.state, "value", e.state) == "loaded" and getattr(e, "runtime_data", None)]

    def rooms(self):
        """The rooms followed, with their Home Assistant area and the rooms sharing their air."""
        return [{"entry_id": e.entry_id, "title": e.title, "area_id": e.runtime_data.config.get("area_id"),
                 "volume": [p["entry_id"] for p in e.runtime_data.partners]} for e in self._loaded()]

    def weather(self):
        """The Hestia Weather place linked to the home (its entry_id), or None. Hestia Weather shows the same link."""
        service = self.hass.data.get(DATA_CONFIG)
        return service.weather() if service else None

    async def set_weather(self, entry_id):
        """Links the home to this Hestia Weather place, or unlinks it with None: turned off on one side, off on both.
        Raises ValueError with a sentence to show when the place is not available."""
        await (await get_configuration(self.hass)).set_weather(entry_id)
        return self.weather()

    def twin(self, entry_id):
        """What the room's twin has learned. None for an unknown room; `status` « learning » until it can tell.

        `room`: inertia_hours (hours to follow the outside), sun_degrees (above outside at 500 W/m²),
        heating_degrees, household_degrees (steady gains), window_half_minutes (an open window halves the gap
        with the outside), air_changes_per_hour (windows shut) and window_air_changes_per_hour, water_per_hour
        (g/m³ produced each hour). `precision`: mean gap over the last 24 hours replayed (°C, % humidity).
        `model`: the raw coefficients, half-hour steps (engine/twin.py)."""
        entry = next((e for e in self._loaded() if e.entry_id == entry_id), None)
        if entry is None:
            return None
        learned = entry.runtime_data.twin
        if not learned:
            return {"version": 1, "status": "learning", "samples": 0, "days": 0, "room": None, "precision": None, "model": None}
        precision = learned.get("precision")
        return {**{k: v for k, v in learned.items() if k != "precision"},
                "precision": {k: precision[k] for k in ("hours", "temperature", "humidity")} if precision else None}
