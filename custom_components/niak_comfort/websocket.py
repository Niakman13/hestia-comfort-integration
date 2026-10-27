"""Read-only view v1 for the future Lit card; no command endpoint."""
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import callback
from homeassistant.helpers import area_registry as ar, floor_registry as fr
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .engine.home import synthesis
from .engine.assessment import assess
from .floors import room_floor


@callback
def async_setup_websocket(hass):
    websocket_api.async_register_command(hass, ws_view)
    websocket_api.async_register_command(hass, ws_entries)
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_home_subscribe)
    websocket_api.async_register_command(hass, ws_review)
    for command in (ws_configuration, ws_discover, ws_overview, ws_weather, ws_validate, ws_save, ws_remove):
        websocket_api.async_register_command(hass, command)


def loaded_entries(hass):
    return sorted((e for e in hass.config_entries.async_entries(DOMAIN)
                   if e.state is ConfigEntryState.LOADED and not e.data.get("home")), key=lambda e: e.title)


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/entries"})
@callback
def ws_entries(hass, connection, msg):
    def volume(entry):
        coordinator = getattr(entry, "runtime_data", None)
        partners = getattr(coordinator, "partners", None) or []
        return [p["entry_id"] for p in partners], getattr(coordinator, "volume_name", None) if partners else None
    # Rooms sharing one air carry their volume, so that a card editor offers them as one choice.
    connection.send_result(msg["id"], [{"entry_id": e.entry_id, "title": e.title, "area_id": {**e.data, **e.options}.get("area_id"),
        "volume": volume(e)[0], "volume_name": volume(e)[1]} for e in loaded_entries(hass)])


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/subscribe", vol.Optional("entry_id"): str})
@callback
def ws_subscribe(hass, connection, msg):
    entries = loaded_entries(hass)
    wanted = msg.get("entry_id")
    entry = next((e for e in entries if e.entry_id == wanted), None) if wanted else entries[0] if len(entries) == 1 else None
    if entry is None:
        code = "not_found" if wanted else "choose_entry" if entries else "not_configured"
        connection.send_error(msg["id"], code, "Choisissez une pièce Niak Comfort chargée")
        return
    coordinator = entry.runtime_data

    @callback
    def send():
        if not coordinator.last_update_success or coordinator.data is None:
            connection.send_message(websocket_api.event_message(msg["id"], {"version": 1, "unavailable": True}))
            return
        connection.send_message(websocket_api.event_message(msg["id"], {"version": 1, "view": coordinator.data}))

    @callback
    def stopped():
        connection.send_message(websocket_api.event_message(msg["id"], {"version": 1, "reload": True}))

    remove_view = coordinator.async_add_listener(send)
    coordinator.stop_listeners.add(stopped)
    removed = False

    @callback
    def unsubscribe():
        nonlocal removed
        if removed:
            return
        removed = True
        remove_view()
        coordinator.stop_listeners.discard(stopped)

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    send()


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/home_subscribe"})
@callback
def ws_home_subscribe(hass, connection, msg):
    """The home card: every room view plus the synthesis, refreshed when any room changes."""
    entries = loaded_entries(hass)
    if not entries:
        connection.send_error(msg["id"], "not_configured", "Aucune pièce Niak Comfort chargée")
        return
    coordinators = [e.runtime_data for e in entries]

    @callback
    def send():
        views = []
        for entry in entries:
            c = entry.runtime_data
            view = c.data if c.last_update_success and c.data else {
                "version": 1, "entry_id": entry.entry_id, "title": entry.title,
                "area_id": {**entry.data, **entry.options}.get("area_id"),
                "computed_at": dt_util.utcnow().isoformat(),
                "observations": {}, "assessment": assess({}).to_dict()}
            views.append({**view, "floor": room_floor(hass, {**entry.data, **entry.options})})
        connection.send_message(websocket_api.event_message(msg["id"], {"version": 1, "rooms": views, "home": synthesis(views)}))

    @callback
    def stopped():
        connection.send_message(websocket_api.event_message(msg["id"], {"version": 1, "reload": True}))

    removers = [c.async_add_listener(send) for c in coordinators]
    removers.extend(hass.bus.async_listen(event, lambda _: send()) for event in
                    (ar.EVENT_AREA_REGISTRY_UPDATED, fr.EVENT_FLOOR_REGISTRY_UPDATED))
    for c in coordinators:
        c.stop_listeners.add(stopped)

    @callback
    def unsubscribe():
        for remove in removers:
            remove()
        removers.clear()
        for c in coordinators:
            c.stop_listeners.discard(stopped)

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    send()


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/view", vol.Required("entry_id"): str})
@callback
def ws_view(hass, connection, msg):
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "Pièce Niak Comfort non chargée")
        return
    connection.send_result(msg["id"], entry.runtime_data.data)


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/review"})
@websocket_api.async_response
async def ws_review(hass, connection, msg):
    """The comfort review of the home over the past year (review_source.py)."""
    from .review_source import async_review
    try:
        result = await async_review(hass)
    except Exception as err:  # the recorder may be missing or busy: the page says so instead of hanging
        connection.send_error(msg["id"], "not_available", str(err))
    else:
        connection.send_result(msg["id"], result)


from .configuration import get_configuration


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/configuration"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_configuration(hass, connection, msg):
    service = await get_configuration(hass)
    connection.send_result(msg["id"], service.snapshot())


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/discover", vol.Optional("area_id"): str, vol.Optional("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_discover(hass, connection, msg):
    service = await get_configuration(hass)
    try:
        result = service.discover(msg.get("area_id"), msg.get("entry_id"))
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
    else:
        connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/overview"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_overview(hass, connection, msg):
    service = await get_configuration(hass)
    connection.send_result(msg["id"], service.overview())


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/weather_proposal", vol.Optional("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_weather(hass, connection, msg):
    service = await get_configuration(hass)
    try:
        connection.send_result(msg["id"], service.weather_proposal(msg.get("entry_id")))
    except ValueError as err:
        connection.send_error(msg["id"], "not_available", str(err))


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/validate_config", vol.Required("config"): dict, vol.Optional("home", default=False): bool})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_validate(hass, connection, msg):
    service = await get_configuration(hass)
    try:
        config, warnings = service.validate(msg["config"], home=msg["home"])
    except (ValueError, TypeError) as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
    else:
        connection.send_result(msg["id"], {"config": config, "warnings": warnings, "revision": service.revision()})


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/save_config", vol.Required("config"): dict,
    vol.Required("revision"): str, vol.Optional("entry_id"): str, vol.Optional("home", default=False): bool,
    vol.Optional("acknowledged", default=[]): [str]})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_save(hass, connection, msg):
    service = await get_configuration(hass)
    try:
        result = await service.save(msg["config"], msg["revision"], msg.get("entry_id"), home=msg["home"], acknowledged=msg["acknowledged"])
    except (ValueError, TypeError) as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
    else:
        connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/remove_room", vol.Required("entry_id"): str, vol.Required("revision"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_remove(hass, connection, msg):
    service = await get_configuration(hass)
    try:
        result = await service.remove(msg["entry_id"], msg["revision"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
    else:
        connection.send_result(msg["id"], result)
