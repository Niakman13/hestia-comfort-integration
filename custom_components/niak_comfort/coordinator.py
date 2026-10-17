"""Event-driven inputs plus a clock tick for freshness, per configured zone."""
from collections import deque
from dataclasses import asdict, replace
from datetime import timedelta
import logging

from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, OPEN_DEBOUNCE_SECONDS, SEASON_REFRESH_SECONDS, SOURCES, VIEW_VERSION
from .engine.assessment import Opening, Settings, Sun, assess
from .engine.sources import normalize, Reading
from .configuration import DATA_CONFIG
from .exterior import exterior_reading
from .discovery import voc_device_class
from . import weather_link

STATE_KINDS = ("window", "heating", "rain", "pollution", "presence", "purifier", "ventilation", "cover", "cover_state", "shutter_auto", "shutter_override", "purifier_speed")


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
        self.opened_since = {}
        self.absent_since = {}
        self.history_reports = {}
        self.histories = {"temperature_history": deque(maxlen=360), "outdoor_history": deque(maxlen=360)}
        # (computed at, seven-day outdoor mean or None): the seasonal comfort range follows it.
        self.season = (None, None)
        self.day_range = None
        self._season_failed = False

    async def async_start(self):
        self.config_entry.async_on_unload(self.async_stopped)
        ids = set(self.config.get("sources", {}).values()) | set(self.config.get("windows", [])) | set(self.config.get("presence", []))
        for meta in self.config.get("openings", {}).values():
            ids.update(meta[k] for k in ("cover_entity", "auto_entity", "override_entity") if meta.get(k))
        ids.add("sun.sun")
        if self.home_configuration:
            ids |= {s["entity_id"] for s in self.home_configuration.effective_sources(self.config).values()}
        ids.discard("")
        if ids:
            self.config_entry.async_on_unload(async_track_state_change_event(self.hass, sorted(ids), self._changed))
        # Linked to Niak Weather: recompute when its forecasts or alerts change.
        if weather_link.api(self.hass) and (place := self._weather_place()):
            self.config_entry.async_on_unload(weather_link.listen(self.hass, place, lambda: self.hass.async_create_task(self.async_request_refresh())))
        await self.async_config_entry_first_refresh()

    @callback
    def async_stopped(self):
        for listener in tuple(self.stop_listeners):
            listener()
        self.stop_listeners.clear()

    async def _changed(self, event):
        entity_id = event.data.get("entity_id")
        old, new = event.data.get("old_state"), event.data.get("new_state")
        before, after = old.state if old else None, new.state if new else None
        now = dt_util.utcnow()
        if entity_id in self.config.get("windows", []):
            if after != "on" or before not in ("on", "off"):
                self.opened_since.pop(entity_id, None)
            elif before == "off":
                self.opened_since[entity_id] = now
        if entity_id in self.config.get("presence", []):
            kind = new.attributes.get("device_class") if new else None
            if kind not in ("occupancy", "presence") or after != "off" or before not in ("on", "off"):
                self.absent_since.pop(entity_id, None)
            elif before == "on":
                self.absent_since[entity_id] = now
        await self.async_request_refresh()

    def _context(self, now, readings):
        for key, source in (("temperature_history", "indoor_temperature"), ("outdoor_history", "outdoor_temperature")):
            history = self.histories[key]
            reading = readings.get(source)
            # Keep samples received during this session; repeated clock refreshes do not invent samples.
            if reading and reading.usable and reading.received_at:
                stamp = dt_util.parse_datetime(reading.received_at)
                if stamp and stamp.tzinfo and -60 <= (now - stamp).total_seconds() <= 1800:
                    previous_report = self.history_reports.get(key)
                    if previous_report is None or stamp > previous_report:
                        # Coverage starts when this session observed the source. A sensor
                        # last reported before startup must not fabricate a long history.
                        history.append((now.isoformat(), reading.value))
                        self.history_reports[key] = stamp
            while history and (now - dt_util.parse_datetime(history[0][0])).total_seconds() > 10800:
                history.popleft()
        def minutes(eid, starts, expected):
            state = self.hass.states.get(eid)
            if not state or state.state != expected:
                starts.pop(eid, None)
            start = starts.get(eid)
            return max(0, (now - start).total_seconds() / 60) if start else None
        return {**self.config.get("evolution", {}),
                "heated": self.config.get("heated", True), "outdoor_mean_7d": self.season[1],
                "indoor_day_range": self.day_range,
                "opening_minutes": {e: minutes(e, self.opened_since, "on") for e in self.config.get("windows", [])},
                "presence_off_minutes": {e: minutes(e, self.absent_since, "off") for e in self.config.get("presence", [])},
                **{k: list(v) for k, v in self.histories.items()}}

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
        for entity_id in self.config.get("presence", []):
            state = self.hass.states.get(entity_id)
            reading = self._reading(entity_id, "presence", now)
            readings[f"presence:{entity_id}"] = replace(reading, detail=state.attributes.get("device_class") if state else "unavailable")
        for entity_id in windows:
            meta = declared.get(entity_id, {})
            if meta.get("shutter") != "connected":
                continue
            cover = meta.get("cover_entity")
            if cover:
                state = self.hass.states.get(cover)
                # Some covers report only open/closed. Their absent position is an
                # optional capability, while cover_state still tracks availability.
                if state and state.attributes.get("current_position") is not None:
                    readings[f"cover:{entity_id}"] = self._reading(cover, "cover", now)
                readings[f"cover_state:{entity_id}"] = self._reading(cover, "cover_state", now)
            for field, kind in (("auto_entity", "shutter_auto"), ("override_entity", "shutter_override")):
                if meta.get(field):
                    readings[f"{kind}:{meta[field]}"] = self._reading(meta[field], kind, now)
        if selected.get("purifier"):
            state = self.hass.states.get(selected["purifier"])
            # A purifier's on/off state is useful even without speed reporting.
            if state and state.attributes.get("percentage") is not None:
                readings["purifier_speed"] = self._reading(selected["purifier"], "purifier_speed", now)
        outlook = weather_link.outlook(self.hass, self._weather_place())
        await self._refresh_season(now)
        self.previous = assess(readings, self.settings, self.previous, openings, self._sun(), outlook, now, context=self._context(now, readings))
        return {"version": VIEW_VERSION, "entry_id": self.entry_id,
                "area_id": self.config.get("area_id"), "title": self.config.get("name"),
                "comfort_minimum": self.settings.minimum,
                "computed_at": now.isoformat(), "assessment": self.previous.to_dict(),
                "observations": {k: asdict(v) for k, v in readings.items()},
                "names": {e: (state.name if (state := self.hass.states.get(e)) else e) for e in windows}}

    def _outdoor_entity(self):
        if self.home_configuration:
            sources = self.home_configuration.effective_sources(self.config)
        else:
            sources = {k: {"entity_id": v} for k, v in self.config.get("sources", {}).items()}
        spec = sources.get("outdoor_temperature")
        return spec["entity_id"] if spec else None

    async def _refresh_season(self, now):
        stamp = self.season[0]
        if stamp and (now - stamp).total_seconds() < SEASON_REFRESH_SECONDS:
            return
        self.season = (now, await self._outdoor_mean(now))
        self.day_range = await self._indoor_range(now)

    async def _statistics(self, entity_id, start, end, types):
        """Hourly statistics rows of one entity; None when the recorder cannot answer."""
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import statistics_during_period
            stats = await get_instance(self.hass).async_add_executor_job(
                statistics_during_period, self.hass, start, end, {entity_id}, "hour", None, types)
        except Exception:  # the card then simply shows less
            if not self._season_failed:
                self._season_failed = True
                self.logger.warning("Home Assistant statistics could not be read", exc_info=True)
            return None
        return stats.get(entity_id, [])

    async def _outdoor_mean(self, now):
        """Seven-day mean of the outdoor temperature from hourly statistics; None when not known."""
        entity_id = self._outdoor_entity()
        rows = await self._statistics(entity_id, now - timedelta(days=7), now, {"mean"}) if entity_id else None
        means = [row["mean"] for row in rows or [] if isinstance(row.get("mean"), (int, float))]
        # Three days of hourly means at least: a recent sensor must not set the season alone.
        if len(means) < 72:
            return None
        value = sum(means) / len(means)
        return value if -40 <= value <= 60 else None

    async def _indoor_range(self, now):
        """Lowest and highest hourly indoor temperature over the last 24 hours."""
        entity_id = self.config.get("sources", {}).get("indoor_temperature")
        rows = await self._statistics(entity_id, now - timedelta(hours=24), now, {"min", "max"}) if entity_id else None
        lows = [row["min"] for row in rows or [] if isinstance(row.get("min"), (int, float))]
        highs = [row["max"] for row in rows or [] if isinstance(row.get("max"), (int, float))]
        # Half a day of hours at least, so a fresh sensor does not draw a misleading range.
        if len(lows) < 12 or len(highs) < 12:
            return None
        return {"min": round(min(lows), 1), "max": round(max(highs), 1)}

    def _heard(self, entity_id, state):
        """When the device last spoke: an unchanged humidity is current if its thermometer just reported."""
        latest = state.last_reported
        registry = er.async_get(self.hass)
        entry = registry.async_get(entity_id)
        if entry and entry.device_id:
            for sibling in er.async_entries_for_device(registry, entry.device_id):
                other = self.hass.states.get(sibling.entity_id)
                if other and other.state not in ("unknown", "unavailable") and other.last_reported > latest:
                    latest = other.last_reported
        return latest

    def _weather_place(self):
        home = self.home_configuration.home if self.home_configuration else {}
        return home.get("weather") if home.get("configured") else None

    def _sun(self):
        state = self.hass.states.get("sun.sun")
        try:
            return Sun(float(state.attributes["elevation"]), float(state.attributes["azimuth"])) if state else None
        except (KeyError, TypeError, ValueError):
            return None

    # Contacts and heating report only when they change; Home Assistant marks them
    # unavailable when the device is lost, so their age says nothing about validity.
    def _reading(self, entity_id, kind, now):
        state = self.hass.states.get(entity_id)
        raw = state.state if state else None
        unit = state.attributes.get("unit_of_measurement") if state else None
        if state:
            if kind == "voc":
                voc_class = voc_device_class(self.hass, entity_id)
                if voc_class is None or (unit is None and voc_class != "volatile_organic_compounds_index"):
                    return Reading(None, "unknown", entity_id, state.last_reported.isoformat(), "incompatible_unit")
            if kind == "heating":
                raw = state.attributes.get("hvac_action")
            elif kind in ("cover", "purifier_speed"):
                raw = state.attributes.get("current_position" if kind == "cover" else "percentage") if state.state not in ("unknown", "unavailable") else None
                unit = "%"
        # HA last_reported tracks reception even when the measured value is unchanged.
        # It is not the sensor's physical sampling time.
        reading = normalize(kind, raw, unit,
                            source=entity_id, reported_at=self._heard(entity_id, state) if state else None,
                            now=now, max_age=None if kind in STATE_KINDS else self.settings.max_age_seconds)
        if kind == "window" and reading.value is True:
            since = self.opened_since.get(entity_id)
            # A contact that bounces (open for a few seconds) is not an opening: advice waits for a real one.
            if since and (now - since).total_seconds() < OPEN_DEBOUNCE_SECONDS:
                return replace(reading, value=False, detail="debounce")
        return reading
