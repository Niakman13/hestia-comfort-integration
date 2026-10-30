"""« Lumières »: the one thing Hestia Confort commands. A coloured light chosen in the hub takes the advice's colour.

The person chose the light, when it may act (already on, or woken for a gesture or an alert; never at night; only when
someone is home) and its look for each state. What the light was before Hestia changed it is kept, and put back when the
advice calms down or a safeguard stops it. A light switched off by hand is left alone until the advice changes.
A WLED segment is a light of its own; when the strip has several, its main light is turned on with it, and put back."""
from datetime import timedelta
import logging

from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .engine import light_plan
from .engine.verdict import strongest
from .entities import partner_coordinators, units
from .websocket import loaded_entries

_LOGGER = logging.getLogger(__name__)
DRIVER = "hestia_comfort_lights"


class LightDriver:
    def __init__(self, hass, configuration):
        self.hass = hass
        self.configuration = configuration
        self.listening = {}
        # By light: how it was before Hestia, the last decision taken, and whether the person switched it off by hand.
        self.kept, self.decided, self.silenced, self.mains = {}, {}, {}, {}

    @callback
    def start(self):
        self.stop = async_track_time_interval(self.hass, callback(lambda _now: self._tick()), timedelta(seconds=60))
        self._tick()

    @callback
    def _tick(self):
        """Every minute: listen to rooms loaded since, and look again at the night and the presence."""
        current = {id(e.runtime_data): e.runtime_data for e in loaded_entries(self.hass) if getattr(e, "runtime_data", None)}
        for key in [k for k in self.listening if k not in current]:
            self.listening.pop(key)()
        for key, coordinator in current.items():
            if key not in self.listening:
                self.listening[key] = coordinator.async_add_listener(self.refresh)
        self.refresh()

    def rules(self):
        lights = self.configuration.home.get("lights") or {}
        if lights.get("mode") == "rooms":
            found = [{**rule, "follow": entry_id} for entry_id, rule in (lights.get("rooms") or {}).items()]
        else:
            found = [lights["home"]] if lights.get("home") else []
        # WLED turned off in Extensions: its lights are no longer driven.
        if "wled" in (self.configuration.home.get("disabled") or []):
            registry = er.async_get(self.hass)
            found = [r for r in found if getattr(registry.async_get(r["entity_id"]), "platform", None) != "wled"]
        return found

    def verdict(self, follow):
        if follow == "home":
            return strongest([v for _, v in units(self.hass, loaded_entries(self.hass))])
        entry = self.hass.config_entries.async_get_entry(follow)
        coordinator = getattr(entry, "runtime_data", None)
        if coordinator is None or not getattr(coordinator, "data", None):
            return None
        views = [coordinator.data, *(c.data for c in partner_coordinators(self.hass, coordinator))]
        return strongest([v["verdict"] for v in views if v and v.get("verdict")])

    def someone_home(self):
        zone = self.hass.states.get("zone.home")
        try:
            return zone is None or float(zone.state) > 0
        except ValueError:
            return True

    @callback
    def refresh(self):
        """Each light's state, decided again; nothing is sent while the decision stays the same."""
        rules = self.rules()
        driven = {rule["entity_id"] for rule in rules}
        # A light no longer chosen goes back to how it was.
        for entity_id in [e for e in self.kept if e not in driven]:
            self._send_restore(entity_id)
        hour, home = dt_util.now().hour, self.someone_home()
        for rule in rules:
            entity_id = rule["entity_id"]
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                continue
            key = light_plan.state_key(self.verdict(rule.get("follow", "home")))
            decision = (key, light_plan.blocked(rule, hour, home), rule.get("states", {}).get(key) if key else None, rule.get("wake"))
            ours = entity_id in self.kept
            # A light the person turns on while a gesture waits takes its colour then: its own on/off counts until Hestia changes it.
            decision = (*decision, None if ours else state.state == "on")
            if ours and self.decided.get(entity_id, (None,))[0] == "on" and state.state == "off":
                # Switched off by hand while Hestia had changed it: the person's choice, kept until the advice changes.
                self.kept.pop(entity_id, None)
                self.silenced[entity_id] = key
                ours = False
            if self.silenced.get(entity_id) is not None and self.silenced[entity_id] == key:
                continue
            self.silenced.pop(entity_id, None)
            if self.decided.get(entity_id, (None, None))[1] == decision:
                continue
            action = light_plan.plan(rule, key, is_on=state.state == "on", hour=hour, someone_home=home, ours=ours)
            self.decided[entity_id] = (action[0] if action else None, decision)
            if action is None:
                continue
            if action[0] == "restore":
                self._send_restore(entity_id)
                continue
            if not ours:
                self.kept[entity_id] = light_plan.snapshot(state.state, state.attributes)
            if action[0] == "off":
                self._call("turn_off", entity_id, {})
            else:
                self._wake_main(entity_id)
                self._call("turn_on", entity_id, light_plan.fit(action[1], state.attributes))

    def _main_of(self, entity_id):
        """The main light of a WLED strip cut into segments: a segment alone does not light the strip."""
        registry = er.async_get(self.hass)
        entry = registry.async_get(entity_id)
        if entry is None or entry.platform != "wled" or "_" not in (entry.unique_id or ""):
            return None
        return registry.async_get_entity_id("light", "wled", entry.unique_id.rsplit("_", 1)[0])

    def _wake_main(self, entity_id):
        main = self._main_of(entity_id)
        if not main:
            return
        state = self.hass.states.get(main)
        if main not in self.mains and state is not None:
            self.mains[main] = {"kept": light_plan.snapshot(state.state, state.attributes), "users": set()}
        if main in self.mains:
            self.mains[main]["users"].add(entity_id)
            if state is not None and state.state == "off":
                self._call("turn_on", main, {})

    def _send_restore(self, entity_id):
        kept = self.kept.pop(entity_id, None)
        self.decided.pop(entity_id, None)
        if kept is not None:
            service, data = light_plan.restore(kept)
            self._call(service, entity_id, data)
        for main, held in list(self.mains.items()):
            held["users"].discard(entity_id)
            if not held["users"]:
                service, data = light_plan.restore(self.mains.pop(main)["kept"])
                if service == "turn_off":
                    self._call(service, main, data)

    def _call(self, service, entity_id, data):
        self.hass.async_create_task(self.hass.services.async_call("light", service, {"entity_id": entity_id, **data}, blocking=False))


async def async_start_lights(hass, configuration):
    """Started once Home Assistant runs; the hub's « Lumières » settings refresh it at once."""
    if DRIVER not in hass.data:
        driver = LightDriver(hass, configuration)
        hass.data[DRIVER] = driver
        driver.start()
    return hass.data[DRIVER]
