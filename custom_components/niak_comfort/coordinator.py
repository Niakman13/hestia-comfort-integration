"""Event-driven inputs plus a clock tick for freshness, per configured zone."""
from dataclasses import asdict
from datetime import timedelta
import logging

from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SOURCES, VIEW_VERSION
from .engine.assessment import Settings, assess
from .engine.sources import normalize, Reading
from .configuration import DATA_CONFIG
from .exterior import exterior_reading


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
        if self.home_configuration and self.config.get("use_home"):
            ids |= {s["entity_id"] for s in self.home_configuration.home_sources().values()}
        ids.discard("")
        if ids:
            self.config_entry.async_on_unload(async_track_state_change_event(self.hass, sorted(ids), self._changed))
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
        if self.config.get("rain_exposed") is False:
            readings["rain"] = Reading(False, "valid", source="declared:rain_sheltered", received_at=now.isoformat(), detail="user_declared")
        for entity_id in self.config.get("windows", []):
            readings[f"window:{entity_id}"] = self._reading(entity_id, "window", now)
        self.previous = assess(readings, self.settings, self.previous)
        return {"version": VIEW_VERSION, "entry_id": self.entry_id,
                "area_id": self.config.get("area_id"), "title": self.config.get("name"),
                "computed_at": now.isoformat(), "assessment": self.previous.to_dict(),
                "observations": {k: asdict(v) for k, v in readings.items()}}

    def _reading(self, entity_id, kind, now):
        state = self.hass.states.get(entity_id)
        raw = state.attributes.get("hvac_action") if state and kind == "heating" else state.state if state else None
        # HA last_reported tracks reception even when the measured value is unchanged.
        # It is not the sensor's physical sampling time.
        return normalize(kind, raw, state.attributes.get("unit_of_measurement") if state else None,
                         source=entity_id, reported_at=state.last_reported if state else None,
                         now=now, max_age=self.settings.max_age_seconds)
