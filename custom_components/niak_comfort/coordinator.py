"""Event-driven inputs plus a clock tick for freshness, per configured zone."""
from collections import deque
from functools import partial
from dataclasses import asdict, replace
from datetime import datetime, timedelta
import logging

from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LEARNING_REFRESH_SECONDS, OPEN_DEBOUNCE_SECONDS, SEASON_REFRESH_SECONDS, SOURCES, STARTUP_GRACE_SECONDS, VIEW_VERSION
from .engine.assessment import Opening, Settings, Sun, assess
from .engine import feedback, habits, learning, sunlight, twin
from .engine.volume import arbitrate
from .engine.sources import normalize, Reading
from .configuration import DATA_CONFIG
from .exterior import exterior_reading
from .discovery import voc_device_class
from . import cover_link, weather_link

STATE_KINDS = ("window", "heating", "rain", "pollution", "presence", "purifier", "ventilation", "cover", "cover_state", "shutter_auto", "shutter_override", "shutter_sun", "shutter_target", "purifier_speed")
# The sunshine is read as its mean over this long: clouds come and go faster than a shutter is moved.
SUN_SMOOTHING = timedelta(minutes=15)
# Twin samples stored before 1.2.9 counted the other room's windows as this room's own: rebuilt from the history.
TWIN_FORMAT = 3
# What belongs to an air shared by rooms open onto each other: a room without its own reads its partner's.
SHARED_SOURCES = ("heating", "co2", "voc", "pm25", "purifier", "ventilation", "ventilation_boost")


class ComfortCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        logger = logging.getLogger(__name__)
        # A contact or a sensor that changes is shown within a second, not after the default 10 s grouping.
        super().__init__(hass, logger, name=DOMAIN, config_entry=entry, update_interval=timedelta(seconds=30),
                         request_refresh_debouncer=Debouncer(hass, logger, cooldown=1.0, immediate=True))
        self.config = {**entry.data, **entry.options}
        self.settings = Settings(**self.config.get("settings", {}))
        self.home_configuration = hass.data.get(DATA_CONFIG)
        self.previous = None
        self.entry_id = entry.entry_id
        self.stop_listeners = set()
        self.opened_since = {}
        # Windows opened while the advice said « open »: the gesture was followed, no bounce delay to wait for.
        self.followed = set()
        self.started = dt_util.utcnow()
        self.absent_since = {}
        self.history_reports = {}
        self.histories = {"temperature_history": deque(maxlen=360), "outdoor_history": deque(maxlen=360)}
        # The sun of the last quarter of an hour: a passing cloud does not make « Soleil » come and go.
        self._sun_samples = deque(maxlen=120)
        # Where the station's sensor is shaded, learned from its history; the sky's share seen just before the shade.
        self.sun_shade = None
        self._sun_before = self._sky_bias = None
        # (computed at, seven-day outdoor mean or None): the seasonal comfort range follows it.
        self.season = (None, None)
        self.day_range = None
        self.humidity_floor = None
        self._season_failed = False
        # What airing really does in this room, learned from its past openings (engine/learning.py).
        self.drying_model = learning.fit([])
        self._learning_due = None
        self._learning_failed = False
        self._learning_store = Store(hass, 1, f"{DOMAIN}.learning.{entry.entry_id}")
        # The room's twin (engine/twin.py): it observes and learns, it never decides an advice.
        self._twin_store = Store(hass, 1, f"{DOMAIN}.twin.{entry.entry_id}")
        self.twin = None
        self._twin_failed = False
        # The feedback loop (engine/feedback.py): airings followed and measured, advice left aside.
        self._feedback_store = Store(hass, 1, f"{DOMAIN}.feedback.{entry.entry_id}")
        self.feedback = []
        self._experiment = None
        self._advice_since = None
        self._advice_followed = False
        # Habits found in the twin's half hours (engine/habits.py), asked about in the hub.
        self.habits = []
        # The season the home lives in (Niak Weather's, or a season sensor): hours of airing, answers by season.
        self.season_name = None
        # Rooms open onto this one (no wall between them): their openings are this room's too.
        self.partners = self._partners()
        self.windows = list(dict.fromkeys([*self.config.get("windows", []), *(e for p in self.partners for e in p["windows"])]))
        # The sources read for this room: its own, completed by what belongs to its shared air (engine/volume.py).
        self.sources = self._sources()
        # This room's advice as computed alone, before the volume settles opposite gestures.
        self.own = None
        self._own_gesture = None

    def _partners(self):
        if not self.home_configuration or not hasattr(self.home_configuration, "volume"):
            return []
        found = []
        for entry_id in self.home_configuration.volume(self.entry_id):
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry is None:
                continue
            config = {**entry.data, **entry.options}
            sheltered = config.get("rain_exposed") is False
            declared = config.get("openings", {})
            # Only what the weather needs: the partner room keeps its covers to itself.
            found.append({"entry_id": entry_id, "title": config.get("name") or entry.title, "windows": list(config.get("windows", [])),
                          "sources": len(config.get("sources", {})),
                          "shared": {k: v for k, v in config.get("sources", {}).items() if k in SHARED_SOURCES and v},
                          # Its own temperature and humidity: the twin learns how much they weigh here.
                          "indoor": [config.get("sources", {}).get(k) for k in ("indoor_temperature", "indoor_humidity")],
                          "openings": {e: Opening(**{"sheltered": sheltered, **{k: v for k, v in declared.get(e, {}).items()
                                                                               if k in ("exposure", "kind", "sheltered")}})
                                       for e in config.get("windows", [])}})
        return found

    def _sources(self):
        """Its own sources, plus those of the shared air it has none of: the kitchen open onto the living room is heated
        by its thermostat and breathes the air its CO₂ sensor measures. Its temperature and humidity stay its own."""
        own = dict(self.config.get("sources", {}))
        for partner in self.partners:
            for key, entity_id in partner.get("shared", {}).items():
                if key == "heating" and self.config.get("heated") is False:
                    continue
                own.setdefault(key, entity_id)
        return own

    def inherited(self):
        """The sources this room reads from its shared air, by key: {"heating": "Salon"}."""
        own = self.config.get("sources", {})
        return {key: p["title"] for p in reversed(self.partners) for key in p.get("shared", {}) if key not in own and key in self.sources}

    @property
    def volume_name(self):
        """« Salon · Cuisine »: the rooms sharing one air, the best equipped first; None for a room on its own."""
        if not self.partners:
            return None
        rooms = [(len(self.config.get("sources", {})), self.config.get("name") or self.config_entry.title),
                 *((p["sources"], p["title"]) for p in self.partners)]
        return " · ".join(title for _, title in sorted(rooms, key=lambda r: (-r[0], r[1].casefold())))

    async def async_start(self):
        self.config_entry.async_on_unload(self.async_stopped)
        ids = set(self.sources.values()) | set(self.windows) | set(self.config.get("presence", []))
        for meta in self.config.get("openings", {}).values():
            ids.update(meta[k] for k in ("cover_entity", "auto_entity", "override_entity") if meta.get(k))
        # Covers driven by Adaptive Cover Pro: its signals are read without being chosen by hand.
        self.drivers = self._drivers()
        for roles in self.drivers.values():
            ids.update(v for k, v in roles.items() if k in cover_link.ROLES)
        ids.add("sun.sun")
        if self.home_configuration:
            ids |= {s["entity_id"] for s in self.home_configuration.effective_sources(self.config).values()}
        # Who is at home: the alarm panels (Alarmo) and the home zone.
        ids |= set(self._occupancy_entities())
        ids.discard("")
        if ids:
            self.config_entry.async_on_unload(async_track_state_change_event(self.hass, sorted(ids), self._changed))
        # Linked to Niak Weather: recompute when its forecasts or alerts change.
        if weather_link.api(self.hass) and (place := self._weather_place()):
            self.config_entry.async_on_unload(weather_link.listen(self.hass, place, lambda: self.hass.async_create_task(self.async_request_refresh())))
        stored = await self._feedback_store.async_load() or {}
        self.feedback = feedback.keep(stored.get("records"), dt_util.utcnow())
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
        if entity_id in self.windows:
            if after != "on" or before not in ("on", "off"):
                self.opened_since.pop(entity_id, None)
                self.followed.discard(entity_id)
            elif before == "off":
                self.opened_since[entity_id] = now
                shown = (self.data or {}).get("assessment") or {}
                if shown.get("action") == "ouvrir":
                    self.followed.add(entity_id)
                    self._advice_followed = True
                    # The advice followed becomes an experiment: the measure now, and what was predicted.
                    if self._experiment is None:
                        values = {k: (v or {}).get("value") for k, v in ((self.data or {}).get("observations") or {}).items()}
                        self._experiment = feedback.start(shown, values, now)
            if before == "on" and after == "off":
                # Learn from this opening once the room has had time to give its water back.
                self._learning_due = now + learning.REBOUND_AFTER + timedelta(minutes=5)
                # Recompute right when the bounce delay ends, not at the next periodic refresh.
                cancel = async_call_later(self.hass, OPEN_DEBOUNCE_SECONDS + 1, self._bounce_over)
                self.stop_listeners.add(cancel)
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
        # The season first: the hours of airing and the answers about a window open at night depend on it.
        self._remember_season(weather_link.season(self.hass, self._weather_place()) or self._season(readings))
        return {**self.config.get("evolution", {}), "occupied": self._occupied(), "volume": self._volume_air(readings),
                "intended_open": self._intended_open(now), "zone": dt_util.get_default_time_zone(),
                # The season: Niak Weather's when it is the exterior source, else a season sensor chosen in « Extérieur ».
                "season_name": self.season_name,
                "heated": self.config.get("heated", True), "outdoor_mean_7d": self.season[1],
                "indoor_day_range": self.day_range, "drying_model": self.drying_model,
                "humidity_floor_3h": self.humidity_floor,
                "opening_minutes": {e: minutes(e, self.opened_since, "on") for e in self.windows},
                "presence_off_minutes": {e: minutes(e, self.absent_since, "off") for e in self.config.get("presence", [])},
                **{k: list(v) for k, v in self.histories.items()}}

    async def _async_update_data(self):
        now = dt_util.utcnow()
        readings = {}
        selected = self.sources
        for key, kind in SOURCES.items():
            entity_id = selected.get(key)
            # Optional unselected sources do not fabricate a missing measurement.
            if not entity_id:
                continue
            readings[key] = self._reading(entity_id, kind, now)
        if self.home_configuration:
            for key, spec in self.home_configuration.live_sources(self.config).items():
                readings[key] = exterior_reading(self.hass.states.get(spec["entity_id"]), key, spec, now=now, max_age=self.settings.max_age_seconds)
        windows = self.config.get("windows", [])
        declared = self.config.get("openings", {})
        # Older rooms declared rain shelter for the whole room instead of per opening.
        sheltered = self.config.get("rain_exposed") is False
        openings = {e: o for p in self.partners for e, o in p["openings"].items()}
        openings.update({e: Opening(**{"sheltered": sheltered, **declared.get(e, {})}) for e in windows})
        drivers = getattr(self, "drivers", None)
        if drivers is None:
            drivers = self.drivers = self._drivers()
        for e, roles in drivers.items():
            if e in openings:
                o, known = openings[e], cover_link.facts(self.hass, roles)
                # An angle typed by the person wins over the one Adaptive Cover Pro was given.
                openings[e] = replace(o, driver="adaptive_cover_pro", auto_entity=o.auto_entity or roles.get("auto"),
                                      override_entity=o.override_entity or roles.get("override"),
                                      azimuth=o.azimuth if o.azimuth is not None else known["azimuth"],
                                      exposure=o.exposure or cover_link.exposure(known["azimuth"]),
                                      width=o.width if o.width is not None else known["width"],
                                      height=o.height if o.height is not None else known["height"])
                if known["reason"]:
                    readings[f"shutter_reason:{e}"] = Reading(known["reason"], "valid", roles.get("target"), now.isoformat())
        for entity_id in self.windows:
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
            opening = openings[entity_id]
            for field, kind in (("auto_entity", "shutter_auto"), ("override_entity", "shutter_override")):
                if getattr(opening, field):
                    readings[f"{kind}:{getattr(opening, field)}"] = self._reading(getattr(opening, field), kind, now)
            roles = drivers.get(entity_id) or {}
            # Adaptive Cover Pro's own signals are extras: one it leaves unavailable (a disabled
            # feature) is simply not read, never counted as a sensor that stopped answering.
            live = lambda role: roles.get(role) and (s := self.hass.states.get(roles[role])) and s.state not in ("unknown", "unavailable")
            for role, kind in (("sun", "shutter_sun"), ("target", "shutter_target")):
                if live(role):
                    readings[f"{kind}:{entity_id}"] = self._reading(roles[role], kind, now)
            # Its own switches: on, following the sun, watching for a hand on the cover, closing against heat.
            for role in ("enabled", "tracking", "detection", "climate"):
                if live(role):
                    readings[f"shutter_{role}:{entity_id}"] = self._reading(roles[role], "shutter_auto", now)
            for role in ("sun_start", "sun_end", "override_end"):
                state = self.hass.states.get(roles[role]) if roles.get(role) else None
                moment = dt_util.parse_datetime(state.state) if state else None
                # In local time, so that « 13 h 50 » reads as the person's clock.
                if moment:
                    readings[f"shutter_{role}:{entity_id}"] = Reading(dt_util.as_local(moment).isoformat(), "valid", roles[role], state.last_reported.isoformat())
        if selected.get("purifier"):
            state = self.hass.states.get(selected["purifier"])
            # A purifier's on/off state is useful even without speed reporting.
            if state and state.attributes.get("percentage") is not None:
                readings["purifier_speed"] = self._reading(selected["purifier"], "purifier_speed", now)
        if selected.get("heating"):
            # The thermostat's mode (frost protection, eco, comfort…), shown on the card; the advice does not use it.
            state = self.hass.states.get(selected["heating"])
            if state and state.state not in ("unknown", "unavailable"):
                preset = state.attributes.get("preset_mode")
                mode, detail = (preset, "preset") if preset and preset != "none" else (state.state, "hvac")
                readings["heating_mode"] = Reading(mode, "valid", selected["heating"], state.last_reported.isoformat(), detail)
        outlook = weather_link.outlook(self.hass, self._weather_place())
        # The sun: estimated where the station is shaded (engine/sunlight.py), then averaged over a quarter of an hour.
        if (solar := readings.get("solar")) is not None:
            readings["solar"] = self._steady_sun(self._unshaded_sun(solar, now, outlook), now)
        await self._refresh_season(now)
        if self._learning_due is None or now >= self._learning_due:
            self._learning_due = now + timedelta(seconds=LEARNING_REFRESH_SECONDS)
            self.config_entry.async_create_background_task(self.hass, self._learn(now), f"{DOMAIN} learning {self.entry_id}")
        # The card shows a contact as it is; the advice ignores an opening younger than the bounce delay.
        advice_readings = {k: (replace(r, value=False, detail="debounce") if k.startswith("window:") and self._bouncing(k[7:], r, now) else r)
                           for k, r in readings.items()}
        self.previous = assess(advice_readings, self.settings, self.previous, openings, self._sun(), outlook, now, context=self._context(now, readings))
        def now_value(key):
            reading = readings.get(key)
            return reading.value if reading and reading.usable and isinstance(reading.value, (int, float)) and not isinstance(reading.value, bool) else None
        current = {"ti": now_value("indoor_temperature"), "hi": now_value("indoor_humidity"), "te": now_value("outdoor_temperature"),
                   "he": now_value("outdoor_humidity"), "sun": self._sun_now(now_value("solar")),
                   "opened": 1.0 if any(r.usable and r.value is True for k, r in advice_readings.items() if k.startswith("window:")) else 0.0,
                   "heated": 1.0 if readings.get("heating") and readings["heating"].value == "heating" else 0.0,
                   "co2": now_value("co2"), "voc": now_value("voc")}
        # Only the windows of the room sharing this air open: the twin weighs them as it learned.
        mine = set(self.config.get("windows", []))
        open_now = {k[7:] for k, r in advice_readings.items() if k.startswith("window:") and r.usable and r.value is True}
        current["far"] = 1.0 if self.partners and open_now and not open_now & mine else 0.0
        current["beside"] = self._beside_now()
        own = self.previous.to_dict()
        # The room's own learning, once optimal, gives the advised gesture its predicted result.
        summary = feedback.summarize(self.feedback, now)
        own.setdefault("features", {})["learned"] = twin.learned_advice(own, self.twin, current, (self.drying_model or {}).get("openings", 0), summary)
        assessment = self._settle(own)
        self._track(assessment, current, now)
        learned = self.twin or {}
        precision = learned.get("precision") or {}
        twin_view = {"status": learned.get("status", "learning"), "days": learned.get("days", 0), "samples": learned.get("samples", 0),
                     "next_hour": twin.next_hour(learned, current),
                     "precision": {k: precision[k] for k in ("hours", "temperature", "humidity")} if precision else None,
                     "progress": self.learning_progress()}
        return {"version": VIEW_VERSION, "entry_id": self.entry_id,
                "area_id": self.config.get("area_id"), "title": self.config.get("name"),
                "comfort_minimum": self.settings.minimum,
                "computed_at": now.isoformat(), "assessment": assessment,
                "volume": [{"entry_id": p["entry_id"], "title": p["title"]} for p in self.partners], "volume_name": self.volume_name,
                # Measures read from the room sharing this air: the card shows them once, under the room that has them.
                "inherited": self.inherited(),
                "twin": twin_view,
                "feedback": {"last": summary["last"], "week": summary["week"]},
                "habit": habits.now_habit(self.habits, self._answers(), dt_util.as_local(now), self.config.get("name") or "", self.config.get("area_id")),
                "observations": {k: asdict(v) for k, v in readings.items()},
                "names": {e: (state.name if (state := self.hass.states.get(e)) else e) for e in self.windows},
                "starting": (now - self.started).total_seconds() < STARTUP_GRACE_SECONDS}

    def _occupancy_entities(self):
        entities = getattr(er.async_get(self.hass), "entities", None) or {}
        panels = [e.entity_id for e in entities.values() if e.domain == "alarm_control_panel" and e.platform == "alarmo"]
        return [*panels, "zone.home"]

    def _occupied(self):
        """True when someone is at home, False when nobody is, None when nothing says it.

        An Alarmo panel armed « away » or « vacation » means an empty home; otherwise the home zone counts the
        people inside; an Alarmo panel disarmed or armed « home » / « night » still says someone is there."""
        panels = [self.hass.states.get(e) for e in self._occupancy_entities() if e.startswith("alarm_control_panel.")]
        states = {s.state for s in panels if s}
        if states & {"armed_away", "armed_vacation"}:
            return False
        zone = self.hass.states.get("zone.home")
        if zone and zone.attributes.get("persons"):
            try:
                return float(zone.state) > 0
            except (TypeError, ValueError):
                pass
        if states & {"disarmed", "armed_home", "armed_night", "armed_custom_bypass"}:
            return True
        return None

    def _volume_air(self, readings):
        """The air shared with the rooms open onto this one: mean water and temperature, and the drying model learned
        from the most openings. None without partners or without humidity on both sides."""
        if not self.partners:
            return None
        def water(t, h):
            return 6.112 * 2.718281828 ** (17.67 * t / (t + 243.5)) * h * 2.1674 / (273.15 + t)
        samples, models = [], [self.drying_model]
        own_t, own_h = readings.get("indoor_temperature"), readings.get("indoor_humidity")
        if own_t and own_h and own_t.usable and own_h.usable:
            samples.append((own_t.value, own_h.value))
        for partner in self.partners:
            entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
            coordinator = getattr(entry, "runtime_data", None)
            data = getattr(coordinator, "data", None) or {}
            obs = data.get("observations", {})
            t, h = obs.get("indoor_temperature") or {}, obs.get("indoor_humidity") or {}
            if t.get("quality") == "valid" and h.get("quality") == "valid" and isinstance(t.get("value"), (int, float)) and isinstance(h.get("value"), (int, float)):
                samples.append((t["value"], h["value"]))
            if coordinator is not None and getattr(coordinator, "drying_model", None):
                models.append(coordinator.drying_model)
        if len(samples) < 2:
            return None
        return {"water": sum(water(t, h) for t, h in samples) / len(samples), "temperature": sum(t for t, _ in samples) / len(samples),
                "rooms": len(samples), "drying_model": max(models, key=lambda m: m.get("openings", 0))}

    def _beside_now(self):
        """The temperature and humidity measured now in the rooms sharing this air, averaged; None without them."""
        found = []
        for partner in self.partners:
            entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
            obs = (getattr(getattr(entry, "runtime_data", None), "data", None) or {}).get("observations", {})
            t, h = obs.get("indoor_temperature") or {}, obs.get("indoor_humidity") or {}
            if t.get("quality") == "valid" and h.get("quality") == "valid" and isinstance(t.get("value"), (int, float)) and isinstance(h.get("value"), (int, float)):
                found.append((t["value"], h["value"]))
        return (sum(t for t, _ in found) / len(found), sum(h for _, h in found) / len(found)) if found else None

    def _settle(self, own):
        """One gesture per shared air: this room follows a partner whose reason outweighs its own."""
        self.own = own
        gesture = (own.get("action"), own.get("reason"))
        if gesture != self._own_gesture and self._own_gesture is not None:
            # The partners settle against this room's new advice at once, not at their next refresh.
            for partner in self.partners:
                entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
                if (coordinator := getattr(entry, "runtime_data", None)) is not None:
                    self.hass.async_create_task(coordinator.async_request_refresh())
        self._own_gesture = gesture
        others = []
        for partner in self.partners:
            entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
            coordinator = getattr(entry, "runtime_data", None)
            if coordinator is not None and getattr(coordinator, "own", None):
                others.append((partner["title"], coordinator.own))
        settled = arbitrate(own, others)
        lead = (settled.get("features", {}).get("volume") or {}).get("lead")
        if lead:
            # The card writes the leading room's advice with its own measures (its CO₂, its humidity).
            partner = next(p for p in self.partners if p["title"] == lead)
            entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
            data = getattr(getattr(entry, "runtime_data", None), "data", None) or {}
            settled["features"]["volume"]["observations"] = {k: v for k, v in data.get("observations", {}).items()
                                                             if not k.startswith(("shutter", "cover"))}
        return settled

    def _outdoor_entity(self):
        return self._source_entity("outdoor_temperature")

    async def _refresh_season(self, now):
        stamp = self.season[0]
        if stamp and (now - stamp).total_seconds() < SEASON_REFRESH_SECONDS:
            return
        self.season = (now, await self._outdoor_mean(now))
        self.day_range = await self._indoor_range(now)
        self.humidity_floor = await self._humidity_floor(now)

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

    def _source_entity(self, key):
        """The entity behind a room source, chosen in the room or shared by the home (outdoor ones)."""
        if self.home_configuration and (spec := self.home_configuration.effective_sources(self.config).get(key)):
            return spec["entity_id"]
        return self.sources.get(key)

    async def _learn(self, now):
        """Refit the room's airing model from the stored openings plus the recorder's recent history."""
        stored = await self._learning_store.async_load() or {}
        episodes = stored.get("episodes") if isinstance(stored.get("episodes"), list) else []
        keys = ("indoor_temperature", "indoor_humidity", "outdoor_temperature", "outdoor_humidity")
        sources = {k: self._source_entity(k) for k in keys}
        # The partner rooms' windows air this room too: their openings teach it as well.
        windows = self.windows
        if windows and all(sources.values()) and "recorder" in self.hass.config.components:
            try:
                from homeassistant.components.recorder import get_instance, history
                states = await get_instance(self.hass).async_add_executor_job(
                    history.get_significant_states, self.hass, now - timedelta(days=10), now,
                    [*windows, *sources.values()], None, True, False, False, True)
                points = lambda entity_id: self._points(states, entity_id)
                contacts = {e: [(row.last_changed, {"on": True, "off": False}.get(row.state)) for row in states.get(e, [])] for e in windows}
                fresh = await self.hass.async_add_executor_job(learning.episodes, contacts, *(points(sources[k]) for k in keys))
                episodes = learning.merge(episodes, fresh, now)
                await self._learning_store.async_save({"episodes": episodes})
            except Exception:  # the room then keeps what it learned before, or the default model
                if not self._learning_failed:
                    self._learning_failed = True
                    self.logger.warning("Past openings could not be read for %s", self.config.get("name"), exc_info=True)
        model = learning.fit(episodes)
        # The twin only observes: the next periodic refresh shows it, no extra one that would delay a sensor change.
        await self._learn_twin(now)
        if model != self.drying_model:
            self.drying_model = model
            await self.async_request_refresh()

    def _sun_history(self, states, entity_id):
        """The station's sunshine over the last days, with the hours it is shaded learned and estimated."""
        points, latitude, longitude = self._points(states, entity_id), self.hass.config.latitude, self.hass.config.longitude
        self.sun_shade = sunlight.learn(points, latitude, longitude, dt_util.get_default_time_zone())
        return sunlight.corrected(points, latitude, longitude, self.sun_shade)

    def _points(self, states, entity_id):
        """Numeric (time, value) points of one entity from a recorder answer, in °C for temperatures."""
        state = self.hass.states.get(entity_id)
        fahrenheit = bool(state) and state.attributes.get("unit_of_measurement") == "°F"
        out = []
        for row in states.get(entity_id, []):
            try:
                value = float(row.state)
            except (TypeError, ValueError):
                continue
            out.append((row.last_changed, (value - 32) * 5 / 9 if fahrenheit else value))
        return out

    async def _learn_twin(self, now):
        """Add the last ten days to the twin's half-hour samples (thirty days kept) and refit it."""
        stored = await self._twin_store.async_load() or {}
        # Samples kept before the sun was counted on the windows and the air was learned are rebuilt from the history.
        rows = stored.get("samples") if isinstance(stored.get("samples"), list) and stored.get("format") == TWIN_FORMAT else []
        keys = ("indoor_temperature", "indoor_humidity", "outdoor_temperature", "outdoor_humidity")
        sources = {k: self._source_entity(k) for k in keys}
        if all(sources.values()) and "recorder" in self.hass.config.components:
            try:
                from homeassistant.components.recorder import get_instance, history
                solar, heating = self._source_entity("solar"), self.sources.get("heating")
                # The air as well: how CO₂ and VOC go down, windows shut and open.
                air = {k: self.sources.get(k) for k in ("co2", "voc")}
                start = now - timedelta(days=10)
                recorder = get_instance(self.hass)
                beside = [p["indoor"] for p in self.partners if all(p.get("indoor") or [None])]
                states = await recorder.async_add_executor_job(
                    history.get_significant_states, self.hass, start, now,
                    [*self.windows, *sources.values(), *([solar] if solar else []), *(e for e in air.values() if e),
                     *(e for pair in beside for e in pair)], None, True, False, False, True)
                # The thermostat's running state is an attribute: its own query keeps them.
                running = await recorder.async_add_executor_job(
                    history.get_significant_states, self.hass, start, now, [heating], None, True, False, False, False) if heating else {}
                contacts = {e: [(row.last_changed, {"on": True, "off": False}.get(row.state)) for row in states.get(e, [])] for e in self.windows}
                heat = [(row.last_updated, row.attributes.get("hvac_action") == "heating") for row in running.get(heating, [])
                        if hasattr(row, "attributes")]
                fresh = await self.hass.async_add_executor_job(
                    partial(twin.samples, start, now, *(self._points(states, sources[k]) for k in keys),
                            self._sun_history(states, solar) if solar else [], contacts, heat,
                            facades=self._facades(), location=(self.hass.config.latitude, self.hass.config.longitude),
                            co2=self._points(states, air["co2"]) if air["co2"] else [], voc=self._points(states, air["voc"]) if air["voc"] else [],
                            near=set(self.config.get("windows", [])) if self.partners else None,
                            beside=[(self._points(states, t), self._points(states, h)) for t, h in beside]))
                rows = twin.merge(rows, fresh, now)
                await self._twin_store.async_save({"samples": rows, "format": TWIN_FORMAT})
            except Exception:  # the twin then keeps what it learned before
                if not self._twin_failed:
                    self._twin_failed = True
                    self.logger.warning("The twin of %s could not read the history", self.config.get("name"), exc_info=True)
        self.twin = await self.hass.async_add_executor_job(twin.summary, rows, now)
        self.habits = await self.hass.async_add_executor_job(habits.detect, rows, dt_util.get_default_time_zone())

    async def _humidity_floor(self, now):
        """Lowest indoor humidity of the last three full hours: above the threshold, the excess lasts."""
        entity_id = self.config.get("sources", {}).get("indoor_humidity")
        rows = await self._statistics(entity_id, now - timedelta(hours=4), now, {"min"}) if entity_id else None
        lows = [row["min"] for row in rows or [] if isinstance(row.get("min"), (int, float))][-3:]
        return min(lows) if len(lows) == 3 else None

    async def _bounce_over(self, _now):
        # A coroutine, so Home Assistant runs it in its own loop (a plain function would run in a worker thread).
        await self.async_refresh()

    def _bouncing(self, entity_id, reading, now):
        since = self.opened_since.get(entity_id)
        return (reading.value is True and since is not None and entity_id not in self.followed
                and (now - since).total_seconds() < OPEN_DEBOUNCE_SECONDS)

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

    def _unshaded_sun(self, reading, now, outlook):
        """The sun at the station, estimated while its sensor is in the shade of the house (engine/sunlight.py)."""
        if reading.quality != "valid" or not isinstance(reading.value, (int, float)) or not self.sun_shade:
            return reading
        latitude, longitude = self.hass.config.latitude, self.hass.config.longitude
        sky = sunlight.sky_factor(sunlight.nearest_hour((outlook or {}).get("hours"), now))
        seen = sunlight.share(float(reading.value), now, latitude, longitude, self.sun_shade)
        if seen is not None:
            # In the open, the station is the truth: it also says how far the forecast cloud cover is from it.
            self._sun_before = (now, seen)
            if sky is not None and sky >= 0.1:
                self._sky_bias = (now, max(0.3, min(2.0, seen / sky)))
            return reading
        recent = lambda kept: kept[1] if kept and now - kept[0] <= timedelta(hours=3) else None
        bias, before = recent(self._sky_bias), recent(self._sun_before)
        # In the shade: Niak Weather's cloud cover, set right by what the station measured in the open just before.
        factor = sky * bias if sky is not None and bias is not None else sky
        value, estimated = sunlight.estimate(float(reading.value), now, latitude, longitude, self.sun_shade, factor, before)
        return replace(reading, value=value, detail="shaded_estimate") if estimated else reading

    def _steady_sun(self, reading, now):
        """The sunshine averaged over the last 15 minutes (SUN_SMOOTHING): the advice and the card's tile read the same."""
        if reading.quality != "valid" or not isinstance(reading.value, (int, float)):
            return reading
        self._sun_samples.append((now, float(reading.value)))
        while self._sun_samples and now - self._sun_samples[0][0] > SUN_SMOOTHING:
            self._sun_samples.popleft()
        mean = sum(v for _, v in self._sun_samples) / len(self._sun_samples)
        return replace(reading, value=round(mean, 1), detail=reading.detail if reading.detail == "shaded_estimate" else "mean_15_min")

    def _remember_season(self, name):
        self.season_name = name
        return name

    @staticmethod
    def _season(readings):
        reading = readings.get("season")
        return reading.value if reading and reading.quality == "valid" else None

    def _weather_place(self):
        home = self.home_configuration.home if self.home_configuration else {}
        return home.get("weather") if home.get("configured") else None

    def _drivers(self):
        """{opening: Adaptive Cover Pro's entities} for each connected cover it drives."""
        try:
            driven = cover_link.find_all(self.hass)
        except Exception:  # A changed Adaptive Cover Pro must never stop the room.
            self.logger.warning("Adaptive Cover Pro could not be read", exc_info=True)
            return {}
        return {e: driven[m["cover_entity"]] for e, m in self.config.get("openings", {}).items()
                if m.get("shutter") == "connected" and m.get("cover_entity") in driven}

    def _answers(self):
        """The person's answers to this room's questions (Oui / Non / Je ne sais pas), kept with the home settings."""
        home = getattr(self.home_configuration, "home", None) or {}
        return (home.get("answers") or {}).get(self.entry_id, {})

    def learning_progress(self, alone=False):
        """How much of the room is learned: only what it has (a window, a heating, CO₂ or VOC sensors) is asked.

        Rooms sharing one air are learned together: one percentage for all of them, complete once each one is."""
        # The airings are learned for the whole air (the volume reads the model learned from the most openings).
        airings = max([(self.drying_model or {}).get("openings", 0)]
                      + [(getattr(getattr(self.hass.config_entries.async_get_entry(p["entry_id"]), "runtime_data", None), "drying_model", None)
                          or {}).get("openings", 0) for p in self.partners])
        air = tuple(k for k in ("co2", "voc") if self.sources.get(k))
        own = twin.progress(self.twin, airings, windows=bool(self.windows), heating=bool(self.sources.get("heating")), air=air)
        # What the advice can already promise, measure by measure, before the whole room is learned.
        own["ready"] = twin.categories(self.twin, airings, air)
        if alone or not self.partners:
            return own
        others = []
        for partner in self.partners:
            entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
            if (coordinator := getattr(entry, "runtime_data", None)) is not None and hasattr(coordinator, "learning_progress"):
                others.append(coordinator.learning_progress(alone=True))
        return twin.together([own, *others])

    def questions(self):
        return habits.questions(self.config.get("name") or self.config_entry.title, self.config.get("area_id"), self.habits, self._answers(),
                                self.season_name)

    def _intended_open(self, now):
        """At night, a window the person said is open on purpose is not an oversight."""
        local = dt_util.as_local(now)
        # The answer holds for the season it was given in (an older answer, without one, for the summer).
        answers = self._answers()
        given = answers.get(habits.night_key(self.season_name)) or (answers.get("night_open") if habits.season_group(self.season_name) == "summer" else None)
        # In winter a window open at night is always said: no answer covers it.
        return given == "yes" and habits.season_group(self.season_name) != "winter" and (local.hour >= 21 or local.hour < 8)

    def _track(self, assessment, current, now):
        """The feedback loop: close an airing followed, and note an advice left aside half an hour."""
        opened = current.get("opened", 0.0) > 0
        if self._experiment and opened:
            # Opened again before the result was read: the same airing goes on.
            self._experiment.pop("closed", None)
        elif self._experiment:
            # The result is read a few minutes after closing: a slow sensor has spoken again by then.
            closed = datetime.fromisoformat(self._experiment.setdefault("closed", now.isoformat()))
            if now - closed >= feedback.SETTLE:
                values = {"indoor_humidity": current.get("hi"), "indoor_temperature": current.get("ti"), "co2": current.get("co2"), "voc": current.get("voc")}
                record = feedback.finish(self._experiment, values, now)
                self._experiment = None
                if record:
                    self._remember(record, now)
        if assessment.get("action") == "ouvrir" and not opened:
            self._advice_since = self._advice_since or now
        else:
            since, followed = self._advice_since, self._advice_followed
            self._advice_since, self._advice_followed = None, False
            if since and not followed and not opened and now - since >= feedback.IGNORED_AFTER:
                self._remember(feedback.ignored(since, now), now)

    def _remember(self, record, now):
        self.feedback = feedback.keep([*self.feedback, record], now)
        self._feedback_store.async_delay_save(lambda: {"records": self.feedback}, 5)

    def _facades(self):
        """The bearings the room's windows face: the exact angle when known, else the declared exposure."""
        from .engine.assessment import EXPOSURES
        declared = {**{e: o for p in self.partners for e, o in p["openings"].items()}}
        out = []
        for entity_id in self.windows:
            meta = self.config.get("openings", {}).get(entity_id)
            opening = declared.get(entity_id)
            azimuth = (meta or {}).get("azimuth") if meta else getattr(opening, "azimuth", None)
            exposure = (meta or {}).get("exposure") if meta else getattr(opening, "exposure", None)
            if azimuth is None and getattr(self, "drivers", None) and entity_id in self.drivers:
                azimuth = cover_link.facts(self.hass, self.drivers[entity_id]).get("azimuth")
            bearing = azimuth if isinstance(azimuth, (int, float)) else EXPOSURES.get(exposure)
            if bearing is not None:
                out.append(float(bearing))
        return out

    def _sun_now(self, solar):
        """The sun on the room's windows now, in kW/m², counted as the twin learned it."""
        sun = self._sun()
        light = solar or 0.0
        return (twin.on_facades(light, sun.elevation, sun.azimuth, self._facades()) if sun else light) / 1000

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
        return reading
