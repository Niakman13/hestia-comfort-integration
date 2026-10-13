"""Event-driven inputs plus a clock tick for freshness, per configured zone."""
from dataclasses import asdict
from datetime import timedelta
import logging

from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SOURCES, VIEW_VERSION
from .engine.assessment import Opening, Settings, Sun, assess
from .engine.sources import normalize, Reading
from .configuration import DATA_CONFIG
from .exterior import exterior_reading
from . import weather_link


class ComfortCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, logging.getLogger(__name__), name=DOMAIN,
                         config_entry=entry, update_interval=timedelta(seconds=30))
        self.config = {**entry.data, **entry.options}
        self.settings = Settings(**self.config.get("settings", {}))
        self.home_configuration = hass.data.get(DATA_CONFIG)
        self.previous = None
        self.entry_id = entry.entry_id
        self.stop_listeners = set()

    async def async_start(self):
        self.config_entry.async_on_unload(self.async_stopped)
        ids = set(self.config.get("sources", {}).values()) | set(self.config.get("windows", []))
        if self.home_configuration:
            ids |= {s["entity_id"] for s in self.home_configuration.effective_sources(self.config).values()}
        ids.discard("")
        if ids:
            self.config_entry.async_on_unload(async_track_state_change_event(self.hass, sorted(ids), self._changed))
        # Linked to Niak Weather: recompute when its forecasts or alerts change.
        if (link := weather_link.api(self.hass)) and (place := self._weather_place()):
            self.config_entry.async_on_unload(link.add_listener(place, lambda: self.hass.async_create_task(self.async_request_refresh())))
        await self.async_config_entry_first_refresh()

    @callback
    def async_stopped(self):
        for listener in tuple(self.stop_listeners):
            listener()
        self.stop_listeners.clear()

    async def _changed(self, event):
        await self.async_request_refresh()

    async def _async_update_data(self):
        now = dt_util.utcnow()
        readings = {}
        selected = self.config.get("sources", {})
        for key, kind in SOURCES.items():
            entity_id = selected.get(key)
            # Optional unselected sources do not fabricate a missing measurement.
            if not entity_id:
                continue
            readings[key] = self._reading(entity_id, kind, now)
        if self.home_configuration:
            for key, spec in self.home_configuration.effective_sources(self.config).items():
                readings[key] = exterior_reading(self.hass.states.get(spec["entity_id"]), key, spec, now=now, max_age=self.settings.max_age_seconds)
        windows = self.config.get("windows", [])
        declared = self.config.get("openings", {})
        # Older rooms declared rain shelter for the whole room instead of per opening.
        sheltered = self.config.get("rain_exposed") is False
        openings = {e: Opening(**{"sheltered": sheltered, **declared.get(e, {})}) for e in windows}
        for entity_id in windows:
            readings[f"window:{entity_id}"] = self._reading(entity_id, "window", now)
        outlook = weather_link.outlook(self.hass, self._weather_place())
        self.previous = assess(readings, self.settings, self.previous, openings, self._sun(), outlook, now)
        return {"version": VIEW_VERSION, "entry_id": self.entry_id,
                "area_id": self.config.get("area_id"), "title": self.config.get("name"),
                "computed_at": now.isoformat(), "assessment": self.previous.to_dict(),
                "observations": {k: asdict(v) for k, v in readings.items()},
                "names": {e: (state.name if (state := self.hass.states.get(e)) else e) for e in windows}}

    def _weather_place(self):
        home = self.home_configuration.home if self.home_configuration else {}
        return home.get("weather") if home.get("configured") else None

    def _sun(self):
        state = self.hass.states.get("sun.sun")
        try:
            return Sun(float(state.attributes["elevation"]), float(state.attributes["azimuth"])) if state else None
        except (KeyError, TypeError, ValueError):
            return None

    def _reading(self, entity_id, kind, now):
        state = self.hass.states.get(entity_id)
        raw = state.attributes.get("hvac_action") if state and kind == "heating" else state.state if state else None
        # HA last_reported tracks reception even when the measured value is unchanged.
        # It is not the sensor's physical sampling time.
        return normalize(kind, raw, state.attributes.get("unit_of_measurement") if state else None,
                         source=entity_id, reported_at=state.last_reported if state else None,
                         now=now, max_age=self.settings.max_age_seconds)
