"""Bundled admin panel and Lovelace card: one installation, nothing to declare by hand.

The settings live in the shared « Niak » panel (socle, see socle.py), as the « Confort » tab.
"""
from pathlib import Path
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback
from . import health, weather_link
from .engine import feedback
from homeassistant.util import dt as dt_util
from .configuration import get_configuration
from .const import DOMAIN, VERSION
from .socle import async_register_brick, async_register_card

ASSETS = "/niak_comfort-assets"
CARD_URL = f"{ASSETS}/niak-comfort-card.js"


async def async_setup_panel(hass):
    if not hass.http or not hasattr(hass.http, "async_register_static_paths"):
        return  # Isolated engine tests and headless HA setups have no frontend.
    if not hass.data.get(DOMAIN + "_panel_asset"):
        await hass.http.async_register_static_paths([StaticPathConfig(
            ASSETS, str(Path(__file__).parent / "frontend"), False)])
        # The versioned dashboard resource, with a guarded extra module only as fallback.
        await async_register_card(hass, CARD_URL, VERSION)
        websocket_api.async_register_command(hass, ws_health)
        websocket_api.async_register_command(hass, ws_twins)
        websocket_api.async_register_command(hass, ws_answer)
        hass.data[DOMAIN + "_panel_asset"] = True
    await async_register_brick(hass, {
        "domain": DOMAIN, "name": "Niak Confort", "slug": "confort", "version": VERSION,
        "icon": "mdi:home-thermometer-outline", "navigation": 1, "module_url": f"{ASSETS}/panel.js?v={VERSION}",
        "element": "niak-comfort-setup", "status": comfort_status, "legacy_path": "niak-confort",
    }, f"{ASSETS}/niak-socle.js?v={VERSION}")


def _plural(n, word):
    return f"{n} {word}{'s' if n > 1 else ''}"


SILENT_LABELS = {"pollution": "la qualité de l’air dehors", "heating": "le chauffage", "rain": "la pluie",
                 "outdoor_temperature": "la température dehors", "outdoor_humidity": "l’humidité dehors",
                 "wind_gust": "les rafales", "window": "un contact d’ouvrant"}


async def comfort_status(hass):
    """What the « Niak » home page says about Niak Confort, from its own settings only."""
    service = await get_configuration(hass)
    rooms = [{"title": e.title, "loaded": e.state.value == "loaded", "entry": e} for e in service.entries()]
    weather = weather_link.status(hass)
    if not rooms:
        return {"level": "action", "summary": "Aucune pièce suivie pour l’instant.",
                "details": ["Commencez par le Salon dans l’onglet Confort."], "links": []}
    followed = _plural(len(rooms), "pièce") + (" suivies" if len(rooms) > 1 else " suivie")
    todo, details, links = [], [], []
    stopped = [r["title"] for r in rooms if not r["loaded"]]
    if stopped:
        todo.append("Calcul arrêté : " + ", ".join(stopped))
    incomplete, silent = [], {}
    for room in rooms:
        data = getattr(getattr(room["entry"], "runtime_data", None), "data", None)
        if not isinstance(data, dict):
            continue
        assessment = data.get("assessment", {})
        if assessment.get("reason") == "incomplete_data":
            incomplete.append(room["title"])
        # A configured source that stopped answering is a point to fix, whatever the advice became.
        for key in assessment.get("missing", []):
            if key in data.get("observations", {}):
                silent.setdefault(SILENT_LABELS.get(key.split(":", 1)[0], "un capteur"), []).append(room["title"])
    if incomplete:
        todo.append("Information incomplète : " + ", ".join(incomplete) + " (un capteur ne répond pas)")
    for label, titles in silent.items():
        where = "toutes les pièces" if len(titles) == len(rooms) and len(rooms) > 1 else ", ".join(dict.fromkeys(titles))
        todo.append(f"{label[0].upper() + label[1:]} ne répond pas ({where})")
    if not service.home.get("configured"):
        todo.append("Extérieur à configurer")
    linked = next((p for p in weather.get("places", []) if p["entry_id"] == service.home.get("weather")), None)
    if linked:
        links.append(f"Relié à Niak Weather · {linked['title']}")
    elif weather.get("installed") and weather.get("places"):
        details.append("Niak Weather est installé : il peut remplir l’extérieur pour vous.")
    if todo:
        return {"level": "action", "summary": f"{followed}, " + _plural(len(todo), "point") + " à régler.",
                "details": todo + details, "links": links}
    return {"level": "ok", "summary": f"{followed}, rien à régler.", "details": details, "links": links}


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/health"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_health(hass, connection, msg):
    """The home page of the « Confort » tab: what works, what to fix, what could be set better."""
    connection.send_result(msg["id"], health.report(await health.facts(hass, VERSION)))


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/twins"})
@websocket_api.require_admin
@callback
def ws_twins(hass, connection, msg):
    """« Ce que Niak a appris » : each room's twin, with its last 24 hours replayed against the measures."""
    rooms = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if entry.data.get("home") or coordinator is None:
            continue
        learned = getattr(coordinator, "twin", None) or {"status": "learning", "samples": 0, "days": 0}
        week = feedback.summarize(getattr(coordinator, "feedback", []), dt_util.utcnow())["week"]
        air = (learned.get("model") or {}).get("air") or {}
        rooms.append({"entry_id": entry.entry_id, "title": entry.title,
                      "twin": {k: v for k, v in learned.items() if k != "model"}, "week": week,
                      "progress": coordinator.learning_progress() if hasattr(coordinator, "learning_progress") else None,
                      # The air it has learned: CO₂ and VOC with enough open half hours to promise a result.
                      "air": [name for name, model in air.items() if model and model.get("open_samples", 0) >= 6],
                      "questions": coordinator.questions() if hasattr(coordinator, "questions") else []})
    connection.send_result(msg["id"], {"version": 1, "rooms": rooms})


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/answer", vol.Required("entry_id"): str,
                                  vol.Required("key"): str, vol.Required("answer"): vol.In(("yes", "no", "unknown"))})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_answer(hass, connection, msg):
    """An answer to a learning question: it names a cause, or stops a window being taken for an oversight."""
    try:
        await (await get_configuration(hass)).answer(msg["entry_id"], msg["key"], msg["answer"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if (coordinator := getattr(entry, "runtime_data", None)) is not None:
        await coordinator.async_request_refresh()
    connection.send_result(msg["id"], {"saved": True})
