"""Admin configuration API: drafts, provenance review and optimistic concurrency."""
import asyncio
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math

from homeassistant.helpers.storage import Store
from homeassistant.helpers import area_registry as ar
from . import weather_link
from .floors import floor_catalog, room_floor
from .const import DOMAIN, OUTDOOR_AREAS, SOURCES
from .discovery import INDOOR, OUTDOOR, candidate, catalog, overview, suggestions, voc_device_class
from .engine.assessment import EXPOSURES, KINDS, Settings
from .air_references import AIR_DEFAULTS, AIR_REFERENCE_VERSION

DATA_CONFIG = DOMAIN + "_configuration"


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
        return hashlib.sha256(json.dumps([self.home, values], sort_keys=True, default=str).encode()).hexdigest()

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
        return {"version": 1, "revision": self.revision(), "home": {"sources": self.home_sources(), "configured": bool(self.home.get("configured")), "acknowledged": self.home.get("acknowledged", []), "weather": self.home.get("weather")}, "niak_weather": weather_link.status(self.hass), "integrations": {"atmofrance": bool(self.hass.config_entries.async_entries("atmofrance"))}, "rooms": entries, "floors": floor_catalog(self.hass), "areas": sorted(areas, key=lambda a: (a["name"].casefold() != "salon", a["name"].casefold()))}

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
                "suggestions": suggestions(candidates, area_id) if area_id else {}}

    def weather_proposal(self, entry_id=None):
        """Niak Weather's station as exterior sources, ready for the exterior page."""
        found = weather_link.exterior(self.hass, entry_id)
        if not found:
            raise ValueError("Niak Weather n’a pas de lieu disponible.")
        sources = {}
        for key, entity_id in found["proposals"].items():
            if c := candidate(self.hass, entity_id, key):
                sources[key] = {"entity_id": entity_id, "adapter": c["adapter"], **({"block_from": 4} if c["adapter"] == "niak_index" else {})}
        return {"entry_id": found["entry_id"], "title": found["title"], "sources": sources}

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
                c = candidate(self.hass, spec["entity_id"], key, include_legacy=True)
                if not c or spec.get("adapter") != c["adapter"]:
                    raise ValueError("Source extérieure incompatible : " + key)
                threshold = spec.get("block_from", 4)
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
        if not isinstance(evolution, dict) or set(evolution) - {"voc_threshold", "glazing_factor", "presence_delay_minutes"}:
            raise ValueError("Préférences avancées invalides.")
        cleaned_evolution = {}
        for key, default, low, high in (("glazing_factor", 0.7, 0, 1), ("presence_delay_minutes", 5, 0, 120)):
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
                   "air_reference_version": AIR_REFERENCE_VERSION}
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
                updated = {**cleaned, "acknowledged": remembered, "configured": True, "revision": self.home["revision"] + 1}
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
                # Preserve unknown future settings only at the top level; explicit sources
                # and windows replace their prior selections, including deliberate clears.
                options = {**entry.data, **entry.options, **cleaned}
                options.pop("rain_exposed", None)
                self.hass.config_entries.async_update_entry(entry, title=cleaned["name"], options=options,
                                                            unique_id=unique_id or entry.unique_id)
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
            await self.hass.config_entries.async_remove(entry_id)
            return self.snapshot()

    def uses_home(self, config):
        if self.home.get("configured") or config.get("use_home") is True:
            return True
        return not any(config.get("sources", {}).get(k) for k in OUTDOOR)

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
