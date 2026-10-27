"""Admin configuration API: drafts, provenance review and optimistic concurrency."""
import asyncio
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math

from homeassistant.helpers.storage import Store
from homeassistant.helpers import area_registry as ar
from . import cover_link, weather_link
from .floors import floor_catalog, room_floor
from .const import DOMAIN, OUTDOOR_AREAS, SOURCES
from .discovery import INDOOR, OUTDOOR, candidate, catalog, overview, suggestions, voc_device_class
from .engine.assessment import EXPOSURES, KINDS, Settings
from .air_references import AIR_DEFAULTS, AIR_REFERENCE_VERSION

DATA_CONFIG = DOMAIN + "_configuration"


# The third-party integrations a person can turn off in the general settings.
SWITCHABLE = ("versatile_thermostat", "adaptive_cover_pro", "alarmo")

class Configuration:
    def __init__(self, hass):
        self.hass = hass
        self.store = Store(hass, 1, DOMAIN + ".home")
        self.home = {"sources": {}, "revision": 0}
        self.lock = asyncio.Lock()

    async def load(self):
        saved = await self.store.async_load()
        if saved:
            self.home = saved

    def entries(self):
        return [e for e in self.hass.config_entries.async_entries(DOMAIN) if not e.data.get("home")]

    def revision(self):
        values = [(e.entry_id, dict(e.data), dict(e.options)) for e in self.entries()]
        # The answers to the learning questions and the alarm, set on their own, never block a room being edited.
        home = {k: v for k, v in self.home.items() if k not in ("answers", "alarm")}
        return hashlib.sha256(json.dumps([home, values], sort_keys=True, default=str).encode()).hexdigest()

    def home_sources(self):
        if self.home.get("configured"):
            return deepcopy(self.home["sources"])
        # Migration is a proposal only. No existing room silently joins the shared profile.
        result = {}
        entries = self.entries()
        for key in OUTDOOR:
            selected = [{**e.data, **e.options}.get("sources", {}).get(key) for e in entries]
            if selected and all(v and v == selected[0] for v in selected):
                entity_id = selected[0]
                c = candidate(self.hass, entity_id, key, include_legacy=True)
                if c:
                    result[key] = {"entity_id": entity_id, "adapter": c["adapter"]}
        return result

    def snapshot(self):
        entries = []
        for e in self.entries():
            config = deepcopy({**e.data, **e.options})
            entries.append({"entry_id": e.entry_id, "title": e.title, "loaded": e.state.value == "loaded", "config": config, "floor": room_floor(self.hass, config)})
        areas = [{"area_id": a.id, "name": a.name, "floor_id": a.floor_id, "outdoor": a.name.strip().casefold() in OUTDOOR_AREAS}
                 for a in ar.async_get(self.hass).areas.values()]
        return {"version": 1, "revision": self.revision(), "home": {"sources": self.home_sources(), "configured": bool(self.home.get("configured")), "acknowledged": self.home.get("acknowledged", []), "weather": self.home.get("weather"), "alarm": self.home.get("alarm"), "disabled": list(self.home.get("disabled") or [])}, "niak_weather": weather_link.status(self.hass), "integrations": {"atmofrance": bool(self.hass.config_entries.async_entries("atmofrance"))}, "rooms": entries, "floors": floor_catalog(self.hass), "areas": sorted(areas, key=lambda a: (a["name"].casefold() != "salon", a["name"].casefold()))}

    def discover(self, area_id=None, entry_id=None):
        if area_id and not ar.async_get(self.hass).async_get_area(area_id):
            raise ValueError("Pièce Home Assistant introuvable.")
        selected = {}
        if entry_id:
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry or entry.domain != DOMAIN or entry.data.get("home"):
                raise ValueError("Pièce Niak Confort introuvable.")
            config = {**entry.data, **entry.options}
            selected = {**config.get("sources", {}), "windows": config.get("windows", []), "presence": config.get("presence", [])}
        for key, spec in self.home_sources().items():
            selected.setdefault(key, spec["entity_id"])
        indoor_ids = {{**e.data, **e.options}.get("sources", {}).get(k) for e in self.entries()
                      for k in ("indoor_temperature", "indoor_humidity")} - {None}
        candidates = catalog(self.hass, area_id, selected, indoor_ids)
        return {"version": 1, "revision": self.revision(), "candidates": candidates,
                "suggestions": suggestions(candidates, area_id) if area_id else {},
                # Covers driven by Adaptive Cover Pro: their signals are read without being chosen.
                "drivers": {cover: self._driver(roles) for cover, roles in cover_link.find_all(self.hass).items()}}

    def _driver(self, roles):
        """What the panel shows of Adaptive Cover Pro: each signal Niak reads, with its current state."""
        def signal(role):
            state = self.hass.states.get(roles[role]) if roles.get(role) else None
            available = state and state.state not in ("unknown", "unavailable")
            return {"entity_id": roles[role], "name": state.name, "on": state.state == "on"} if available else None
        known = cover_link.facts(self.hass, roles)
        return {"name": roles["name"], "auto": roles.get("auto"), "override": roles.get("override"),
                "signals": {role: signal(role) for role in ("enabled", "auto", "tracking", "detection", "override", "sun", "climate")},
                "azimuth": known["azimuth"], "exposure": cover_link.exposure(known["azimuth"]),
                "width": known["width"], "height": known["height"]}

    def weather_proposal(self, entry_id=None):
        """Niak Weather's station as exterior sources, ready for the exterior page."""
        found = weather_link.exterior(self.hass, entry_id)
        if not found:
            raise ValueError("Niak Weather n’a pas de lieu disponible.")
        sources = {}
        for key, entity_id in found["proposals"].items():
            if c := candidate(self.hass, entity_id, key):
                sources[key] = {"entity_id": entity_id, "adapter": c["adapter"], **({"block_from": 4} if c["adapter"] == "niak_index" else {})}
        # Niak Weather 2.5.7 gives its air through api.air() (Atmo France or a WAQI station), without an entity of its own.
        air = weather_link.air(self.hass, found["entry_id"])
        if "pollution" not in sources and air:
            sources["pollution"] = {"entity_id": air["entity_id"], "adapter": "niak_air", "block_from": 4}
        shown = {"provider": air["provider"], "index": air.get("index"), "label": air.get("label")} if air else None
        # Its season too (2.6.2): from its own Season sensor or the date, read through its interface.
        season = weather_link.season(self.hass, found["entry_id"])
        return {"entry_id": found["entry_id"], "title": found["title"], "sources": sources, "air": shown, "season": season}

    def overview(self):
        used = {{**e.data, **e.options}.get("area_id") for e in self.entries()}
        return {"version": 1, "revision": self.revision(), "areas": overview(self.hass, used)}

    def validate(self, payload, *, home=False):
        if not isinstance(payload, dict):
            raise ValueError("Configuration invalide.")
        warnings = []
        if home:
            sources = payload.get("sources", {})
            if not isinstance(sources, dict) or set(sources) - set(OUTDOOR):
                raise ValueError("Sources extérieures invalides.")
            cleaned = {"sources": {}}
            for key, spec in sources.items():
                if not isinstance(spec, dict) or not isinstance(spec.get("entity_id"), str):
                    raise ValueError("Choisissez une source extérieure existante.")
                threshold = spec.get("block_from", 4)
                if spec.get("adapter") == "niak_air":
                    # The air of the linked Niak Weather place, whatever its source; read again on every update.
                    air = weather_link.air(self.hass, payload.get("weather"))
                    if key != "pollution" or not air or air["entity_id"] != spec["entity_id"]:
                        raise ValueError("La qualité de l’air de Niak Weather n’est plus disponible : rechargez la page.")
                    if isinstance(threshold, bool) or not isinstance(threshold, int) or not 2 <= threshold <= 6:
                        raise ValueError("Choisissez un niveau ATMO entre Moyen et Extrêmement mauvais.")
                    cleaned["sources"][key] = {"entity_id": spec["entity_id"], "adapter": "niak_air", "block_from": threshold}
                    continue
                c = candidate(self.hass, spec["entity_id"], key, include_legacy=True)
                if not c or spec.get("adapter") != c["adapter"]:
                    raise ValueError("Source extérieure incompatible : " + key)
                daily = c["adapter"] in ("atmo_daily", "niak_index")
                if daily and (isinstance(threshold, bool) or not isinstance(threshold, int) or not 2 <= threshold <= 6):
                    raise ValueError("Choisissez un niveau ATMO entre Moyen et Extrêmement mauvais.")
                cleaned["sources"][key] = {"entity_id": c["entity_id"], "adapter": c["adapter"]}
                if daily:
                    cleaned["sources"][key]["block_from"] = threshold
                if c["warnings"]:
                    warnings.append({"key": key, "entity_id": c["entity_id"], "warnings": c["warnings"]})
            weather = payload.get("weather")
            if weather is not None and weather not in {p["entry_id"] for p in weather_link.status(self.hass)["places"]}:
                raise ValueError("Ce lieu Niak Weather n’est plus disponible.")
            cleaned["weather"] = weather
            return cleaned, warnings
        area_id = payload.get("area_id") or None
        area = ar.async_get(self.hass).async_get_area(area_id) if isinstance(area_id, str) else None
        if area_id is not None and not area:
            raise ValueError("Cette pièce Home Assistant n’existe plus. Choisissez-en une autre ou une pièce libre.")
        floor_id = payload.get("floor_id") or None
        if area_id:
            floor_id = None  # Home Assistant owns the floor of a linked area.
        elif floor_id is not None and (not isinstance(floor_id, str) or floor_id not in {f["floor_id"] for f in floor_catalog(self.hass)}):
            raise ValueError("Cet étage n’existe plus. Choisissez un étage existant ou aucun étage.")
        sources = payload.get("sources", {})
        if not isinstance(sources, dict) or set(sources) - set(SOURCES):
            raise ValueError("Sources de pièce invalides.")
        if not sources.get("indoor_temperature"):
            raise ValueError("Choisissez la température intérieure de cette pièce.")
        windows = payload.get("windows", [])
        if not isinstance(windows, list) or any(not isinstance(e, str) for e in windows):
            raise ValueError("Contacts de fenêtres invalides.")
        presence = payload.get("presence", [])
        if not isinstance(presence, list) or any(not isinstance(e, str) for e in presence):
            raise ValueError("Capteurs de présence invalides.")
        evolution = payload.get("evolution", {})
        if not isinstance(evolution, dict) or set(evolution) - {"voc_threshold", "glazing_factor", "presence_delay_minutes",
                                                                   "voc_delay_minutes", "voc_pause_minutes"}:
            raise ValueError("Préférences avancées invalides.")
        cleaned_evolution = {}
        for key, default, low, high in (("glazing_factor", 0.7, 0, 1), ("presence_delay_minutes", 5, 0, 120),
                                         ("voc_delay_minutes", 10, 0, 120), ("voc_pause_minutes", 45, 0, 240)):
            value = evolution.get(key, default)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError("Valeur avancée invalide : " + key)
            cleaned_evolution[key] = value
        threshold = evolution.get("voc_threshold")
        if threshold is not None:
            value = threshold.get("value") if isinstance(threshold, dict) else None
            unit = threshold.get("unit") if isinstance(threshold, dict) else None
            state = self.hass.states.get(sources.get("voc", ""))
            source_unit = state.attributes.get("unit_of_measurement") if state else None
            explicit_index = voc_device_class(self.hass, sources.get("voc", "")) == "volatile_organic_compounds_index"
            expected_unit = "" if source_unit is None and explicit_index else source_unit
            if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0
                or not isinstance(unit, str) or not state or unit != expected_unit):
                raise ValueError("Le seuil COV doit correspondre à l’unité exacte du capteur choisi.")
            cleaned_evolution["voc_threshold"] = {"value": value, "unit": unit}
        name = payload.get("name", area.name if area else "")
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError("Donnez un nom à la pièce (1 à 100 caractères).")
        settings = payload.get("settings", {})
        if not isinstance(settings, dict):
            raise ValueError("Préférences de confort invalides.")
        settings = asdict(Settings(**{**AIR_DEFAULTS, **settings}))
        heated = payload.get("heated", True)
        if not isinstance(heated, bool):
            raise ValueError("« Pièce chauffée » doit être oui ou non.")
        # A Versatile Thermostat's comfort temperature stands as the room's minimum unless the person says otherwise.
        thermostat_reference = payload.get("thermostat_reference", True)
        if not isinstance(thermostat_reference, bool):
            raise ValueError("« Minimum repris du thermostat » doit être oui ou non.")
        # The people the room is for (`person` entities): a bedroom's one, a living room's several, or none for everyone.
        persons = payload.get("persons", [])
        if not isinstance(persons, list) or any(not isinstance(p, str) or not p.startswith("person.") for p in persons):
            raise ValueError("Choisissez les personnes parmi celles de Home Assistant.")
        # No contact on the windows, on purpose (a garage, a room that is never aired): not suggested again.
        windows_unmeasured = payload.get("windows_unmeasured", False)
        if not isinstance(windows_unmeasured, bool):
            raise ValueError("« Pas de contact, c’est voulu » doit être oui ou non.")
        # Rooms with no wall between them (a salon open onto its kitchen) share one air.
        open_to = payload.get("open_to", [])
        known = {e.entry_id for e in self.entries()}
        if not isinstance(open_to, list) or any(not isinstance(e, str) for e in open_to):
            raise ValueError("Pièces ouvertes l’une sur l’autre invalides.")
        # A room removed since is simply forgotten.
        open_to = [e for e in open_to if e in known]
        legacy_sheltered = payload.get("rain_exposed") is False
        openings = payload.get("openings", {})
        if not isinstance(openings, dict):
            raise ValueError("Description des ouvrants invalide.")
        cleaned_openings = {}
        for entity_id in windows:
            meta = openings.get(entity_id, {})
            if not isinstance(meta, dict):
                raise ValueError("Description des ouvrants invalide.")
            exposure = meta.get("exposure")
            kind = meta.get("kind", "window")
            sheltered = meta.get("sheltered", legacy_sheltered)
            if exposure is not None and exposure not in EXPOSURES:
                raise ValueError("Exposition inconnue pour " + entity_id)
            if kind not in KINDS or not isinstance(sheltered, bool):
                raise ValueError("Type d’ouvrant invalide pour " + entity_id)
            shutter = meta.get("shutter", "none")
            if shutter not in ("none", "manual", "connected"):
                raise ValueError("Type de volet invalide pour " + entity_id)
            item = {"exposure": exposure, "kind": kind, "sheltered": sheltered}
            # A precise angle, when the person knows it: 0 north, 90 east, 180 south, 270 west.
            azimuth = meta.get("azimuth")
            if azimuth is not None:
                if isinstance(azimuth, bool) or not isinstance(azimuth, (int, float)) or not math.isfinite(azimuth) or not 0 <= azimuth < 360:
                    raise ValueError("Angle invalide pour " + entity_id + " : entre 0 et 359 degrés.")
                item["azimuth"] = azimuth
            if "shutter" in meta:
                item["shutter"] = shutter
            for field, role in (("cover_entity", "covers"), ("auto_entity", "shutter_auto"), ("override_entity", "shutter_override")):
                value = meta.get(field)
                if value:
                    found = candidate(self.hass, value, role, area_id) if isinstance(value, str) else None
                    if shutter != "connected" or not found:
                        raise ValueError("Source du volet incompatible : " + field)
                    if found["warnings"]:
                        warnings.append({"key": role, "entity_id": value, "warnings": found["warnings"]})
                    item[field] = value
            for field in ("width", "height", "overhang_depth", "overhang_gap"):
                value = meta.get(field)
                if value is not None:
                    minimum = 0 if field.startswith("overhang") else 0.01
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= 20:
                        raise ValueError("Dimension invalide : " + field)
                    item[field] = value
            cleaned_openings[entity_id] = item
        # Rooms use the shared exterior. Older rooms keep their own sources only until it is configured.
        legacy = not self.uses_home(payload)
        cleaned_sources = {}
        for key, value in {**sources, "windows": windows, "presence": presence}.items():
            if key in OUTDOOR and not legacy:
                continue
            ids = value if key in ("windows", "presence") else [value]
            for entity_id in ids:
                if not isinstance(entity_id, str):
                    raise ValueError("Choisissez une entité existante pour chaque source.")
                c = candidate(self.hass, entity_id, key, area_id, include_legacy=True)
                if not c:
                    raise ValueError("Capteur incompatible ou retiré : " + entity_id)
                # Exterior sources kept by an older room are not shown in the page: never ask to confirm them.
                if c["warnings"] and key not in OUTDOOR:
                    warnings.append({"key": key, "entity_id": entity_id, "warnings": c["warnings"]})
            if key not in ("windows", "presence"):
                cleaned_sources[key] = value
        cleaned = {"name": name.strip(), "area_id": area_id, "floor_id": floor_id, "sources": cleaned_sources,
                   "windows": list(dict.fromkeys(windows)), "openings": cleaned_openings, "settings": settings,
                   "presence": list(dict.fromkeys(presence)), "evolution": cleaned_evolution, "use_home": not legacy,
                   "air_reference_version": AIR_REFERENCE_VERSION, "heated": heated, "thermostat_reference": thermostat_reference,
                   "windows_unmeasured": windows_unmeasured and not windows,
                   "persons": list(dict.fromkeys(persons)), "open_to": list(dict.fromkeys(open_to))}
        return cleaned, warnings

    @staticmethod
    def ensure_acknowledged(warnings, acknowledged):
        if not isinstance(acknowledged, list) or any(not isinstance(item, str) for item in acknowledged):
            raise ValueError("Confirmez les sources dont le rôle est à vérifier.")
        needed = {w["key"] + ":" + w["entity_id"] for w in warnings}
        if needed - set(acknowledged):
            raise ValueError("Confirmez la provenance et le rôle des sources signalées avant d’enregistrer.")
        # Only confirmations that still apply are remembered, so a later change asks again.
        return sorted(needed)

    async def save(self, payload, revision, entry_id=None, *, home=False, acknowledged=None):
        async with self.lock:
            if revision != self.revision():
                raise ValueError("La configuration a changé ailleurs. Rechargez les pièces avant d’enregistrer.")
            cleaned, warnings = self.validate(payload, home=home)
            remembered = self.ensure_acknowledged(warnings, acknowledged or [])
            if home:
                updated = {**cleaned, "acknowledged": remembered, "configured": True, "revision": self.home["revision"] + 1,
                           "answers": self.home.get("answers", {}), "alarm": self.home.get("alarm")}
                await self.store.async_save(updated)
                self.home = updated
                for entry in self.entries():
                    if entry.state.value == "loaded":
                        await self.hass.config_entries.async_reload(entry.entry_id)
                return self.snapshot()
            cleaned["acknowledged"] = remembered
            unique_id = cleaned["area_id"]
            if unique_id and any(e.unique_id == unique_id and e.entry_id != entry_id for e in self.entries()):
                raise ValueError("Cette pièce Home Assistant est déjà utilisée par une autre pièce Niak Confort.")
            if entry_id:
                entry = self.hass.config_entries.async_get_entry(entry_id)
                if not entry or entry.domain != DOMAIN or entry.data.get("home"):
                    raise ValueError("Cette pièce Niak Confort n’existe plus.")
                cleaned["open_to"] = [e for e in cleaned["open_to"] if e != entry_id]
                before = set(self.volume(entry_id))
                # Preserve unknown future settings only at the top level; explicit sources
                # and windows replace their prior selections, including deliberate clears.
                options = {**entry.data, **entry.options, **cleaned}
                options.pop("rain_exposed", None)
                self.hass.config_entries.async_update_entry(entry, title=cleaned["name"], options=options,
                                                            unique_id=unique_id or entry.unique_id)
                # The rooms that join or leave this one's air are recomputed with it.
                await self._reload_rooms((before | set(self.volume(entry_id))) - {entry_id})
            else:
                result = await self.hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"}, data={"panel_config": cleaned, "acknowledged": acknowledged or []})
                if result["type"] != "create_entry":
                    raise ValueError("La pièce n’a pas pu être ajoutée.")
            return self.snapshot()

    async def remove(self, entry_id, revision):
        """Deletes one room; its Home Assistant area becomes a proposal again on the home page."""
        async with self.lock:
            if revision != self.revision():
                raise ValueError("La configuration a changé ailleurs. Rechargez les pièces avant de supprimer.")
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry or entry.domain != DOMAIN or entry.data.get("home"):
                raise ValueError("Cette pièce Niak Confort n’existe plus.")
            partners = set(self.volume(entry_id))
            await self.hass.config_entries.async_remove(entry_id)
            await self._reload_rooms(partners)
            return self.snapshot()

    async def set_alarm(self, value):
        """The home's alarm: None to find Alarmo by itself, "" for none, or an `alarm_control_panel` entity."""
        if value is not None and not (isinstance(value, str) and (value == "" or value.startswith("alarm_control_panel."))):
            raise ValueError("Choisissez une alarme de Home Assistant.")
        async with self.lock:
            self.home = {**self.home, "alarm": value}
            await self.store.async_save(self.home)
            for entry in self.entries():
                if entry.state.value == "loaded":
                    await self.hass.config_entries.async_reload(entry.entry_id)
            return self.snapshot()

    async def set_extension(self, key, enabled):
        """Uses a third-party integration or not, for every room: Alarmo found by itself or no alarm; the others listed when off."""
        if key not in SWITCHABLE:
            raise ValueError("Extension inconnue.")
        async with self.lock:
            if key == "alarmo":
                self.home = {**self.home, "alarm": None if enabled else ""}
            else:
                off = [k for k in self.home.get("disabled") or [] if k != key] + ([] if enabled else [key])
                self.home = {**self.home, "disabled": off}
            await self.store.async_save(self.home)
            for entry in self.entries():
                if entry.state.value == "loaded":
                    await self.hass.config_entries.async_reload(entry.entry_id)
            return self.snapshot()

    def weather(self):
        """The Niak Weather place that gives the outdoor to every room, or None: the one link both bricks show."""
        return self.home.get("weather") if self.home.get("configured") else None

    async def set_weather(self, entry_id):
        """Links the outdoor to a Niak Weather place (its measures replace the others), or unlinks it (the sensors stay,
        Niak Weather's air is dropped), as « Niak Weather » or « Vos propres capteurs » then Enregistrer would."""
        if entry_id == self.weather():
            return self.snapshot()
        sources = (self.weather_proposal(entry_id)["sources"] if entry_id
                   else {k: v for k, v in self.home_sources().items() if v.get("adapter") != "niak_air"})
        payload = {"sources": sources, "weather": entry_id}
        # Choosing the link is choosing its sensors: their roles need no second confirmation.
        _, warnings = self.validate(payload, home=True)
        return await self.save(payload, self.revision(), home=True, acknowledged=[w["key"] + ":" + w["entity_id"] for w in warnings])

    async def answer(self, entry_id, key, value):
        """Keeps the person's answer to a learning question (« yes », « no », « unknown »)."""
        if value not in ("yes", "no", "unknown") or not isinstance(key, str) or not key:
            raise ValueError("Réponse invalide.")
        if not any(e.entry_id == entry_id for e in self.entries()):
            raise ValueError("Cette pièce Niak Confort n’existe plus.")
        async with self.lock:
            answers = {**(self.home.get("answers") or {})}
            answers[entry_id] = {**answers.get(entry_id, {}), key: value}
            self.home = {**self.home, "answers": answers}
            await self.store.async_save(self.home)

    def volume(self, entry_id):
        """The other rooms sharing this room's air: « open onto » is mutual and passes from room to room."""
        links = {e.entry_id: set({**e.data, **e.options}.get("open_to", [])) for e in self.entries()}
        group, frontier = {entry_id}, [entry_id]
        while frontier:
            current = frontier.pop()
            for other in links.get(current, set()) | {k for k, v in links.items() if current in v}:
                if other in links and other not in group:
                    group.add(other)
                    frontier.append(other)
        return sorted(group - {entry_id})

    async def _reload_rooms(self, entry_ids):
        for entry_id in sorted(entry_ids):
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry and entry.state.value == "loaded":
                await self.hass.config_entries.async_reload(entry_id)

    def uses_home(self, config):
        if self.home.get("configured") or config.get("use_home") is True:
            return True
        return not any(config.get("sources", {}).get(k) for k in OUTDOOR)

    def live_sources(self, config=None):
        """The exterior sources as read now: those saved, with the outdoor air following the source chosen in
        Niak Weather when the home is linked to it, unless another kind of pollution sensor or no air at all was picked."""
        sources = self.effective_sources(config) if config is not None else (self.home_sources() if self.home.get("configured") else {})
        if config is not None and not self.uses_home(config):
            return sources
        spec = sources.get("pollution")
        if not spec or spec.get("adapter") not in ("atmo_daily", "niak_index", "niak_air"):
            return sources
        found = weather_link.air(self.hass, self.home.get("weather")) if self.home.get("configured") else None
        if found:
            sources["pollution"] = {"entity_id": found["entity_id"], "adapter": "niak_air", "block_from": (spec or {}).get("block_from", 4),
                                    "index": found.get("index"), "provider": found.get("provider"), "at": found.get("at")}
        return sources

    def effective_sources(self, config):
        if self.uses_home(config):
            return self.home_sources()
        return {key: {"entity_id": value, "adapter": "direct" if key in ("outdoor_temperature", "outdoor_humidity") else "binary"} for key, value in config.get("sources", {}).items() if key in OUTDOOR}


async def get_configuration(hass):
    if DATA_CONFIG not in hass.data:
        service = Configuration(hass)
        hass.data[DATA_CONFIG] = service
        hass.data[DATA_CONFIG + "_load"] = hass.async_create_task(service.load())
    if task := hass.data.get(DATA_CONFIG + "_load"):
        await task
    return hass.data[DATA_CONFIG]
