"""Bundled admin panel and Lovelace card: one installation, no resource to declare.

The settings live in the shared « Niak » panel (socle, see socle.py), as the « Confort » tab.
"""
from pathlib import Path
import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from . import health, weather_link
from .configuration import get_configuration
from .const import DOMAIN, VERSION
from .socle import async_register_brick

ASSETS = "/niak_comfort-assets"


async def async_setup_panel(hass):
    if not hass.http or not hasattr(hass.http, "async_register_static_paths"):
        return  # Isolated engine tests and headless HA setups have no frontend.
    if not hass.data.get(DOMAIN + "_panel_asset"):
        await hass.http.async_register_static_paths([StaticPathConfig(
            ASSETS, str(Path(__file__).parent / "frontend"), False)])
        # The card is loaded on every dashboard, like a declared resource would be.
        frontend.add_extra_js_url(hass, f"{ASSETS}/niak-comfort-card.js?v={VERSION}")
        websocket_api.async_register_command(hass, ws_health)
        hass.data[DOMAIN + "_panel_asset"] = True
    await async_register_brick(hass, {
        "domain": DOMAIN, "name": "Niak Confort", "slug": "confort", "version": VERSION,
        "icon": "mdi:home-thermometer-outline", "module_url": f"{ASSETS}/panel.js?v={VERSION}",
        "element": "niak-comfort-setup", "status": comfort_status, "legacy_path": "niak-confort",
    }, f"{ASSETS}/niak-socle.js?v={VERSION}")


def _plural(n, word):
    return f"{n} {word}{'s' if n > 1 else ''}"


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
    incomplete = []
    for room in rooms:
        data = getattr(getattr(room["entry"], "runtime_data", None), "data", None)
        if isinstance(data, dict) and data.get("assessment", {}).get("reason") == "incomplete_data":
            incomplete.append(room["title"])
    if incomplete:
        todo.append("Information incomplète : " + ", ".join(incomplete) + " (un capteur ne répond pas)")
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
