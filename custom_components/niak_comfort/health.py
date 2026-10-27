"""The technical state of the home, for the home page of the « Confort » tab: what works, what needs the user, what could be set better.

Same shape as Niak Weather's (engine/health.py there): orange (`bad`) only for what stops something from working, a better setting
is a tip, grey (`none`) is what is not used. Read from this brick's own settings and Home Assistant only.
"""
from dataclasses import dataclass, field

from homeassistant.util import dt as dt_util

from . import cover_link, weather_link
from .socle import SOCLE_VERSION
from .engine import people, thermostat as thermostats
from .configuration import get_configuration
from homeassistant.helpers import entity_registry as er

from .discovery import INDOOR, catalog, effective_area, overview, suggestions

GONE = ("unavailable", "unknown")
COLUMNS = (("indoor_temperature", "Température"), ("indoor_humidity", "Humidité"), ("co2", "CO₂"), ("windows", "Ouvrants"), ("heating", "Chauffage"))
# « Cuisine : le CO₂ ne répond pas »
SUBJECTS = {"indoor_temperature": "la température", "indoor_humidity": "l’humidité", "co2": "le CO₂", "windows": "un ouvrant", "heating": "le chauffage", "illuminance": "la luminosité", "pm25": "les PM2.5", "voc": "les COV", "purifier": "le purificateur", "ventilation": "la ventilation", "ventilation_boost": "la grande vitesse de la ventilation", "presence": "la présence", "covers": "le volet", "shutter_auto": "l’automatisation du volet", "shutter_override": "la dérogation du volet",
            "outdoor_temperature": "la température", "outdoor_humidity": "l’humidité", "rain": "la pluie", "wind_gust": "les rafales",
            "wind_bearing": "la direction du vent", "solar": "l’ensoleillement", "pollution": "la pollution", "season": "la saison"}
LOSS = {"indoor_temperature": "Le confort de la pièce n’est plus évalué.", "indoor_humidity": "L’humidité de la pièce est inconnue.",
        "co2": "Le conseil d’aération est en pause.", "windows": "On ne sait plus s’il est ouvert.", "heating": "On ne sait plus si le chauffage tourne."}
LOSS.update({"illuminance": "La lumière intérieure est inconnue.", "pm25": "Les particules intérieures ne sont plus mesurées.", "voc": "Les COV ne sont plus mesurés.", "purifier": "Le fonctionnement du purificateur est inconnu.", "ventilation": "Le fonctionnement de la ventilation est inconnu.", "ventilation_boost": "La grande vitesse de la ventilation est inconnue.", "presence": "La présence reste inconnue.", "covers": "La position du volet est inconnue.", "shutter_auto": "L’automatisation est inconnue.", "shutter_override": "La dérogation est inconnue."})
GAINS = {"indoor_humidity": "repérer un air trop humide et savoir si aérer l’assèche",
         "co2": "savoir quand renouveler l’air", "heating": "ne pas conseiller d’ouvrir pendant que le chauffage tourne"}


@dataclass
class Sensor:
    key: str
    name: str
    status: str
    """« ok », « silent », « stale » (Home Assistant has it, the advice cannot use it) or « missing »."""
    age: float | None = None
    entity_id: str = ""


@dataclass
class Room:
    entry_id: str
    title: str
    loaded: bool = True
    sensors: list = field(default_factory=list)
    available: dict = field(default_factory=dict)
    """Sensors Home Assistant has in this room for what is not chosen: key → name."""
    shared: dict = field(default_factory=dict)
    """Sources read from the room it shares its air with: key → that room's name."""
    thermostat: bool = False
    """Its heating is a Versatile Thermostat (engine/thermostat.py)."""
    driven_covers: int = 0
    """Its covers driven by Adaptive Cover Pro."""
    windows_intended: bool = False
    """No contact on its windows, on purpose: not suggested again."""


@dataclass
class Facts:
    rooms: list = field(default_factory=list)
    exterior: list = field(default_factory=list)
    """The home's exterior sensors (Sensor)."""
    configured: bool = False
    weather: str = ""
    """The Niak Weather place the exterior comes from, "" when not linked."""
    weather_installed: bool = False
    free_areas: list = field(default_factory=list)
    """Home Assistant rooms with a thermometer that no Niak room follows: (area_id, name)."""
    version: str = ""
    alarm: str = ""
    """The home's alarm as read: « Alarmo · désarmée », "" without one."""
    installed: frozenset = frozenset()
    """The integrations of EXTENSIONS and OTHERS that Home Assistant has loaded."""
    disabled: frozenset = frozenset()
    """The extensions turned off in the general settings."""


def ago(minutes):
    if minutes is None:
        return ""
    if minutes < 1.5:
        return "à l’instant"
    if minutes < 60:
        return f"il y a {round(minutes)} min"
    return f"il y a {round(minutes / 60)} h" if minutes < 48 * 60 else f"il y a {round(minutes / 1440)} j"


def _plural(n, word, plural=None):
    return f"{n} {word if n == 1 else plural or word + 's'}"


def _line(level, text, why="", target=None):
    return {"level": level, "text": text, "why": why, "target": target}


def _since(age):
    text = ago(age)
    return f"Depuis {text.removeprefix('il y a ')}. " if text.startswith("il y a") else ""


def _broken(s):
    return {"missing": "n’existe plus", "stale": "ne donne pas de mesure exploitable"}.get(s.status, "ne répond pas")


def report(f):
    todo, tips = [], []
    for room in f.rooms:
        target = {"kind": "room", "entry_id": room.entry_id, "label": room.title}
        if not room.loaded:
            todo.append(_line("bad", f"{room.title} : calcul arrêté",
                              "Home Assistant n’a pas pu démarrer cette pièce : vérifiez ses capteurs ou les journaux (cherchez « niak »).", target))
        for s in room.sensors:
            if s.status != "ok":
                todo.append(_line("bad", f"{room.title} : {SUBJECTS[s.key]} {_broken(s)}", f"{_since(s.age)}{s.name} · {LOSS[s.key]}", target))
        chosen = {s.key for s in room.sensors}
        for key in ("indoor_humidity", "co2", "heating"):
            if key not in chosen and key not in room.shared and key in room.available:
                tips.append(_line("tip", f"{room.title} : ajouter {SUBJECTS[key]}", f"« {room.available[key]} » est disponible : {GAINS[key]}.", target))
        if "windows" not in chosen and not room.windows_intended:
            found = room.available.get("windows")
            tips.append(_line("tip", f"{room.title} : ouvrants non mesurés", (f"« {found} » est disponible. " if found else "")
                              + "Un contact sur la fenêtre dirait si elle est ouverte : le conseil d’ouvrir ne viserait plus une fenêtre déjà ouverte."
                              + " Pas de contact voulu ici : Modifier → Ouvertures.", target))
    exterior_target = {"kind": "exterior", "label": "Extérieur"}
    if not f.configured:
        todo.append(_line("bad", "Extérieur à configurer", "Sans l’extérieur, impossible de dire s’il vaut mieux ouvrir ou fermer.", exterior_target))
    for s in f.exterior:
        if s.status != "ok":
            todo.append(_line("bad", f"Extérieur : {SUBJECTS[s.key]} {_broken(s)}", f"{_since(s.age)}{s.name} · toutes les pièces sont concernées.", exterior_target))
    for area_id, name in f.free_areas:
        tips.append(_line("tip", f"{name} pas encore suivie", "Pièce Home Assistant avec un thermomètre : elle peut être suivie.",
                          {"kind": "area", "area_id": area_id, "label": "Ajouter"}))
    if f.weather_installed and not f.weather:
        tips.append(_line("tip", "Reprendre l’extérieur de Niak Weather", "Sa station, ses alertes et ses prévisions, sans rien choisir à nouveau.", exterior_target))

    # ---- Sources ----
    bad = [s for s in f.exterior if s.status != "ok"]
    silent = f" · {len(bad)} capteur{'s' if len(bad) > 1 else ''} ne répond{'ent' if len(bad) > 1 else ''} pas" if bad else ""
    if f.weather:
        exterior = {"label": "Extérieur", "level": "bad" if bad else "ok", "text": f"Niak Weather · {f.weather}{silent}"}
    elif f.configured:
        exterior = {"label": "Extérieur", "level": "bad" if bad else "ok",
                    "text": _plural(len(f.exterior), "capteur") + (silent or (", tous répondent" if f.exterior else ""))}
    else:
        exterior = {"label": "Extérieur", "level": "bad", "text": "pas encore configuré"}
    pollution = next((s for s in f.exterior if s.key == "pollution"), None)
    heated = [r for r in f.rooms if any(s.key == "heating" for s in r.sensors)]
    sources = [exterior,
               {"label": "Pollution", "level": "none" if not pollution else "ok" if pollution.status == "ok" else "bad",
                "text": "aucune source" if not pollution else pollution.name + ("" if pollution.status == "ok" else " · ne répond pas")},
               {"label": "Chauffage", "level": "ok" if heated else "none",
                "text": f"suivi dans {_plural(len(heated), 'pièce')} · rien n’est commandé" if heated else "non suivi"}]

    # ---- Sensors by room ----
    rooms = []
    for room in f.rooms:
        cells = []
        for key, _ in COLUMNS:
            mine = [s for s in room.sensors if s.key == key]
            broken = [s for s in mine if s.status != "ok"]
            if not mine and key in room.shared:
                # Heated by the living room it opens onto, breathing the air its sensor measures.
                cells.append({"level": "shared", "text": room.shared[key]})
            elif not mine:
                cells.append({"level": "none", "text": "non mesurés" if key == "windows" else "—"})
            elif broken:
                cells.append({"level": "bad", "text": f"{len(broken)} sur {len(mine)} ne répondent pas" if len(mine) > 1 else "ne répond pas"})
            else:
                cells.append({"level": "ok", "text": _plural(len(mine), "contact") if key == "windows" else "répond"})
        rooms.append({"entry_id": room.entry_id, "title": room.title, "cells": cells})

    # Extensions: Niak's own bricks, then other integrations Niak reads by itself, each making the advice better where it is used.
    vt = [r.title for r in f.rooms if r.thermostat]
    acp = [r.title for r in f.rooms if r.driven_covers]
    linked = {"niak_weather": [f.weather] if f.weather else [], thermostats.PLATFORM: vt, "adaptive_cover_pro": acp, people.PLATFORM: [f.alarm] if f.alarm else []}
    installed = {"niak_weather": f.weather_installed}
    extensions = []
    for ext in EXTENSIONS:
        found = linked[ext["key"]]
        state = "off" if ext["key"] in f.disabled else "linked" if found else "found" if installed.get(ext["key"], ext["key"] in f.installed) else "missing"
        text = (f"relié · {f.weather}" if ext["key"] == "niak_weather" else f.alarm if ext["key"] == people.PLATFORM
                else f"{_plural(len(found), 'pièce')} · " + ", ".join(found)) if found and state != "off" else "désactivée" if state == "off" else ext[state]
        extensions.append({**{k: ext[k] for k in ("key", "name", "official", "role", "use", "without", "url")},
                           "state": state, "level": "ok" if found else "none", "text": text, "rooms": found if ext["key"] in (thermostats.PLATFORM, "adaptive_cover_pro") else []})
    # Installed integrations Confort does not read yet: shown so that the person can ask for them.
    others = [dict(o) for o in OTHERS if o["key"] in f.installed]
    versions = [{"level": "ok", "text": f"Intégration {f.version}", "why": "avec sa carte"},
                {"level": "ok", "text": f"Relié à Niak Weather · {f.weather}", "why": "l’extérieur vient de sa station et de ses prévisions"} if f.weather else
                {"level": "none", "text": "Pas relié à Niak Weather", "why": "installé : il peut remplir l’extérieur" if f.weather_installed else "non installé"}]
    # One count everywhere: every sensor checked here, in the rooms (a shared one once) and outside.
    checked = [s for r in f.rooms for s in r.sensors] + list(f.exterior)
    sensors = {"answering": sum(1 for s in checked if s.status == "ok"), "total": len(checked)}
    return {"level": "action" if todo else "ok", "sensors": sensors, "summary": _plural(len(todo), "point") + " à régler" if todo else "Tout est suivi",
            "tips_summary": _plural(len(tips), "réglage") + " à améliorer" if tips else "",
            "rooms_summary": _plural(len(f.rooms), "pièce suivie", "pièces suivies"),
            "todo": todo, "tips": tips, "sources": sources, "extensions": extensions, "others": others, "socle": ".".join(map(str, SOCLE_VERSION)), "columns": [label for _, label in COLUMNS], "rooms": rooms, "versions": versions}


EXTENSIONS = (
    {"key": "niak_weather", "name": "Niak Weather", "official": True, "url": "https://github.com/Niakman13/niak-weather-integration",
     "role": "Extérieur, prévisions, pluie, vigilances",
     "use": "Le dehors pour toutes les pièces : température, humidité, pluie, vent, soleil, saison, pollution, alertes et prévisions.",
     "without": "Sans lui : vos propres capteurs, sans prévisions ni alertes.",
     "found": "installé, pas relié", "missing": "non installé"},
    {"key": thermostats.PLATFORM, "name": thermostats.NAME, "official": False, "url": "https://github.com/jmcollin78/versatile_thermostat",
     "role": "Consigne confort, raison d’un arrêt, présets, pente",
     "use": "Consigne de confort, raison d’un arrêt (fenêtre, absence), préréglage et pente de chauffe : plus de conseil de chauffer quand le thermostat s’en charge.",
     "without": "Sans lui : le chauffage est lu sur le thermostat de Home Assistant seulement.",
     "found": "installé, aucun chauffage choisi dans une pièce", "missing": "non installé"},
    {"key": "adaptive_cover_pro", "name": cover_link.NAME, "official": False, "url": "https://github.com/jrhubott/adaptive-cover-pro",
     "role": "Volets pilotés avec le soleil",
     "use": "Volets pilotés avec le soleil : Confort sait quand ils se ferment et nomme les volets à fermer avant la chaleur.",
     "without": "Sans lui : le soleil est estimé par la façade de chaque ouvrant.",
     "found": "installé, aucun volet relié à un ouvrant", "missing": "non installé"},
    {"key": people.PLATFORM, "name": people.NAME, "official": False, "url": "https://github.com/nielsfaber/alarmo",
     "role": "Maison vide, nuit, fenêtre ouverte alarme armée",
     "use": "Maison vide, nuit, vacances : pas d’aération conseillée quand personne n’est là, et un avertissement si une fenêtre reste ouverte alarme armée.",
     "without": "Sans elle : l’absence est lue sur les personnes de la maison.",
     "found": "installée, pas utilisée", "missing": "non installée"},
)
# Integrations Confort could read one day: listed only when Home Assistant has them.
OTHERS = (
    {"key": "better_thermostat", "name": "Better Thermostat", "use": "Pourrait donner la consigne et l’arrêt fenêtre ouverte."},
    {"key": "smartir", "name": "SmartIR", "use": "Pourrait dire si la climatisation tourne, et dans quel mode."},
    {"key": "scheduler", "name": "Scheduler", "use": "Pourrait dire quand le chauffage va reprendre."},
)
DOMAINS = frozenset(e["key"] for e in EXTENSIONS + OTHERS) | set(cover_link.PLATFORMS)


def _weather_air(spec):
    return Sensor("pollution", f"Niak Weather · {spec.get('provider') or 'qualité de l’air'}", "ok" if spec.get("index") else "silent")


def _sensor(hass, key, entity_id, now):
    state = hass.states.get(entity_id)
    if state is None:
        return Sensor(key, entity_id, "missing", entity_id=entity_id)
    name = str(state.attributes.get("friendly_name") or entity_id)
    if state.state in GONE:
        return Sensor(key, name, "silent", (now - state.last_changed).total_seconds() / 60, entity_id)
    seen = getattr(state, "last_reported", None) or state.last_updated
    return Sensor(key, name, "ok", (now - seen).total_seconds() / 60, entity_id)


def _unusable(coordinator):
    """Entities whose reading the room's last advice could not use: listed in its `missing`."""
    data = getattr(coordinator, "data", None)
    if not isinstance(data, dict):
        return set()
    assessment, observations = data.get("assessment") or {}, data.get("observations") or {}
    found = set()
    for key in assessment.get("missing") or ():
        source = (observations.get(key) or {}).get("source") if isinstance(observations.get(key), dict) else None
        if isinstance(source, str):
            found.add(source)
    return found


async def facts(hass, version):
    service, now = await get_configuration(hass), dt_util.utcnow()
    rooms, used, stale = [], set(), set()
    indoor_ids = {{**e.data, **e.options}.get("sources", {}).get(k) for e in service.entries() for k in ("indoor_temperature", "indoor_humidity")} - {None}
    # Only local, unselected suggestions are used here. Index the registry once,
    # rather than scanning every entity for every role for every configured room.
    local_entries = {}
    for entity in er.async_get(hass).entities.values():
        local_entries.setdefault(effective_area(hass, entity), []).append(entity)
    # Alarmo off is no alarm; the others are listed by key.
    disabled = set(service.home.get("disabled") or []) | ({people.PLATFORM} if service.home.get("alarm") == "" else set())
    for entry in service.entries():
        config = {**entry.data, **entry.options}
        sources, windows = config.get("sources", {}), config.get("windows", [])
        room = Room(entry.entry_id, entry.title, entry.state.value == "loaded")
        coordinator = getattr(entry, "runtime_data", None)
        room.shared = coordinator.inherited() if hasattr(coordinator, "inherited") else {}
        heating = er.async_get(hass).async_get(sources["heating"]) if sources.get("heating") else None
        room.thermostat = bool(heating and heating.platform == thermostats.PLATFORM and thermostats.PLATFORM not in disabled)
        room.driven_covers = sum(1 for w in windows if w in (getattr(coordinator, "drivers", None) or {}))
        room.windows_intended = config.get("windows_unmeasured") is True
        room.sensors = [_sensor(hass, key, sources[key], now) for key in ("indoor_temperature", "indoor_humidity", "co2", "heating", "illuminance", "pm25", "voc", "purifier", "ventilation", "ventilation_boost") if sources.get(key)]
        room.sensors += [_sensor(hass, "windows", w, now) for w in windows]
        room.sensors += [_sensor(hass, "presence", e, now) for e in config.get("presence", [])]
        for meta in config.get("openings", {}).values():
            if meta.get("shutter") == "connected":
                for field, role in (("cover_entity", "covers"), ("auto_entity", "shutter_auto"), ("override_entity", "shutter_override")):
                    if meta.get(field):
                        room.sensors.append(_sensor(hass, role, meta[field], now))
        if area_id := config.get("area_id"):
            used.add(area_id)
            selected = {**sources, "windows": windows}
            candidates = {key: [] for key in INDOOR}
            candidates.update(catalog(hass, area_id, selected, indoor_ids,
                                      keys=("indoor_humidity", "co2", "heating", "windows"),
                                      entries=local_entries.get(area_id, ())))
            for key, value in suggestions(candidates, area_id).items():
                entity_id = value[0] if isinstance(value, list) and value else value
                if isinstance(entity_id, str) and not selected.get(key):
                    state = hass.states.get(entity_id)
                    room.available[key] = str(state.attributes.get("friendly_name") or entity_id) if state else entity_id
        # What Home Assistant still shows but the advice cannot use (too old, wrong unit): the same as the room's card says.
        unusable = _unusable(coordinator)
        stale |= unusable
        for sensor in room.sensors:
            if sensor.status == "ok" and sensor.entity_id in unusable:
                sensor.status = "stale"
        rooms.append(room)
    home = service.live_sources()
    exterior = [_weather_air(spec) if spec.get("adapter") == "niak_air" else _sensor(hass, key, spec["entity_id"], now)
                for key, spec in home.items() if spec.get("entity_id")]
    for sensor in exterior:
        if sensor.status == "ok" and sensor.entity_id and sensor.entity_id in stale:
            sensor.status = "stale"
    link = weather_link.status(hass)
    weather = next((p["title"] for p in link.get("places", []) if p["entry_id"] == service.home.get("weather")), "")
    free = [(a["area_id"], a["name"]) for a in overview(hass, used) if isinstance(a["suggestions"].get("indoor_temperature"), str)]
    # The alarm as the rooms read it (engine/people.py): the one chosen in the general settings, else Alarmo.
    coordinator = next((c for e in service.entries() if (c := getattr(e, "runtime_data", None)) is not None and hasattr(c, "_alarm")), None)
    found = coordinator._alarm() if coordinator is not None else None
    states = {"disarmed": "désarmée", "armed_away": "absence", "armed_home": "à la maison", "armed_night": "nuit",
              "armed_vacation": "vacances", "armed_custom_bypass": "personnalisée", "triggered": "déclenchée"}
    alarm = f"{found['name']} · {states.get(found['state'], found['state'])}" if found else ""
    loaded = getattr(getattr(hass, "config", None), "components", None) or set()
    # The original Adaptive Cover is read like the Pro one.
    installed = {d for d in DOMAINS if d in loaded} | ({"adaptive_cover_pro"} if any(p in loaded for p in cover_link.PLATFORMS) else set())
    return Facts(alarm=alarm, installed=frozenset(installed), disabled=frozenset(disabled), rooms=rooms, exterior=exterior, configured=bool(service.home.get("configured")), weather=weather,
                 weather_installed=bool(link.get("installed") and link.get("places")), free_areas=free, version=version)
