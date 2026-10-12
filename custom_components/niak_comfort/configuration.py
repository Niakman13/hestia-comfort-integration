"""Admin configuration API: drafts, provenance review and optimistic concurrency."""
import asyncio
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json

from homeassistant.helpers.storage import Store
from homeassistant.helpers import area_registry as ar
from .const import DOMAIN, SOURCES
from .discovery import INDOOR, OUTDOOR, candidate, catalog, suggestions
from .engine.assessment import Settings

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
            entries.append({"entry_id": e.entry_id, "title": e.title, "loaded": e.state.value == "loaded", "config": config})
        areas = [{"area_id": a.id, "name": a.name} for a in ar.async_get(self.hass).areas.values()]
        return {"version": 1, "revision": self.revision(), "home": {"sources": self.home_sources(), "configured": bool(self.home.get("configured"))}, "rooms": entries, "areas": sorted(areas, key=lambda a: (a["name"].casefold() != "salon", a["name"].casefold()))}

    def discover(self, area_id=None, entry_id=None):
        if area_id and not ar.async_get(self.hass).async_get_area(area_id):
            raise ValueError("Pièce Home Assistant introuvable.")
        selected = {}
        if entry_id:
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry or entry.domain != DOMAIN or entry.data.get("home"):
                raise ValueError("Pièce Niak Confort introuvable.")
            config = {**entry.data, **entry.options}
            selected = {**config.get("sources", {}), "windows": config.get("windows", [])}
        for key, spec in self.home_sources().items():
            selected.setdefault(key, spec["entity_id"])
        candidates = catalog(self.hass, area_id, selected)
        return {"version": 1, "revision": self.revision(), "candidates": candidates,
                "suggestions": suggestions(candidates, area_id) if area_id else {}}

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
                if c["adapter"] == "atmo_daily" and (isinstance(threshold, bool) or not isinstance(threshold, int) or not 2 <= threshold <= 6):
                    raise ValueError("Choisissez un niveau ATMO entre Moyen et Extrêmement mauvais.")
                cleaned["sources"][key] = {"entity_id": c["entity_id"], "adapter": c["adapter"]}
                if c["adapter"] == "atmo_daily":
                    cleaned["sources"][key]["block_from"] = threshold
                if c["warnings"]:
                    warnings.append({"key": key, "entity_id": c["entity_id"], "warnings": c["warnings"]})
            return cleaned, warnings
        area_id = payload.get("area_id")
        area = ar.async_get(self.hass).async_get_area(area_id) if isinstance(area_id, str) else None
        if not area:
            raise ValueError("Choisissez une pièce Home Assistant.")
        sources = payload.get("sources", {})
        if not isinstance(sources, dict) or set(sources) - set(SOURCES):
            raise ValueError("Sources de pièce invalides.")
        if not sources.get("indoor_temperature"):
            raise ValueError("Choisissez la température intérieure de cette pièce.")
        windows = payload.get("windows", [])
        if not isinstance(windows, list) or any(not isinstance(e, str) for e in windows):
            raise ValueError("Contacts de fenêtres invalides.")
        name = payload.get("name", area.name)
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError("Le nom doit contenir entre 1 et 100 caractères.")
        settings = payload.get("settings", {})
        if not isinstance(settings, dict):
            raise ValueError("Préférences de confort invalides.")
        settings = asdict(Settings(**settings))
        use_home = payload.get("use_home", False)
        exposed = payload.get("rain_exposed", True)
        if not isinstance(use_home, bool) or not isinstance(exposed, bool):
            raise ValueError("Préférences extérieures invalides.")
        if use_home and not self.home.get("configured"):
            raise ValueError("Configurez les données extérieures communes avant de les activer pour cette pièce.")
        cleaned_sources = {}
        for key, value in {**sources, "windows": windows}.items():
            if key in OUTDOOR and use_home:
                continue
            ids = value if key == "windows" else [value]
            for entity_id in ids:
                if not isinstance(entity_id, str):
                    raise ValueError("Choisissez une entité existante pour chaque source.")
                c = candidate(self.hass, entity_id, key, area_id, include_legacy=True)
                if not c:
                    raise ValueError("Capteur incompatible ou retiré : " + entity_id)
                if c["warnings"]:
                    warnings.append({"key": key, "entity_id": entity_id, "warnings": c["warnings"]})
            if key != "windows":
                cleaned_sources[key] = value
        return {"name": name.strip(), "area_id": area_id, "sources": cleaned_sources,
                "windows": list(dict.fromkeys(windows)), "settings": settings,
                "use_home": use_home, "rain_exposed": exposed}, warnings

    @staticmethod
    def ensure_acknowledged(warnings, acknowledged):
        if not isinstance(acknowledged, list) or any(not isinstance(item, str) for item in acknowledged):
            raise ValueError("Confirmez les sources dont le rôle est à vérifier.")
        needed = {w["key"] + ":" + w["entity_id"] for w in warnings}
        if needed - set(acknowledged):
            raise ValueError("Confirmez la provenance et le rôle des sources signalées avant d’enregistrer.")

    async def save(self, payload, revision, entry_id=None, *, home=False, acknowledged=None):
        async with self.lock:
            if revision != self.revision():
                raise ValueError("La configuration a changé ailleurs. Rechargez les pièces avant d’enregistrer.")
            cleaned, warnings = self.validate(payload, home=home)
            self.ensure_acknowledged(warnings, acknowledged or [])
            if home:
                updated = {**cleaned, "configured": True, "revision": self.home["revision"] + 1}
                await self.store.async_save(updated)
                self.home = updated
                for entry in self.entries():
                    if {**entry.data, **entry.options}.get("use_home") and entry.state.value == "loaded":
                        await self.hass.config_entries.async_reload(entry.entry_id)
                return self.snapshot()
            if entry_id:
                entry = self.hass.config_entries.async_get_entry(entry_id)
                if not entry or entry.domain != DOMAIN or entry.data.get("home"):
                    raise ValueError("Cette pièce Niak Confort n’existe plus.")
                if cleaned["area_id"] != entry.data.get("area_id"):
                    raise ValueError("La pièce d’une configuration existante ne peut pas être changée.")
                # Preserve unknown future settings only at the top level; explicit sources
                # and windows replace their prior selections, including deliberate clears.
                options = {**entry.data, **entry.options, **cleaned}
                self.hass.config_entries.async_update_entry(entry, title=cleaned["name"], options=options)
            else:
                if any(e.unique_id == cleaned["area_id"] for e in self.entries()):
                    raise ValueError("Cette pièce est déjà configurée. Ouvrez Modifier.")
                result = await self.hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"}, data={"panel_config": cleaned, "acknowledged": acknowledged or []})
                if result["type"] != "create_entry":
                    raise ValueError("La pièce n’a pas pu être ajoutée.")
            return self.snapshot()

    def effective_sources(self, config):
        if config.get("use_home"):
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
