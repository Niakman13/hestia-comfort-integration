"""Read-only view v1 for the future Lit card; no command endpoint."""
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import callback

from .const import DOMAIN
from .engine.home import synthesis


@callback
def async_setup_websocket(hass):
    websocket_api.async_register_command(hass, ws_view)
    websocket_api.async_register_command(hass, ws_entries)
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_home_subscribe)
    for command in (ws_configuration, ws_discover, ws_overview, ws_validate, ws_save):
        websocket_api.async_register_command(hass, command)


def loaded_entries(hass):
    return sorted((e for e in hass.config_entries.async_entries(DOMAIN)
                   if e.state is ConfigEntryState.LOADED and not e.data.get("home")), key=lambda e: e.title)


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/entries"})
@callback
def ws_entries(hass, connection, msg):
    connection.send_result(msg["id"], [{"entry_id": e.entry_id, "title": e.title,
        "area_id": {**e.data, **e.options}.get("area_id")} for e in loaded_entries(hass)])


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
        views = [c.data for c in coordinators if c.last_update_success and c.data]
        connection.send_message(websocket_api.event_message(msg["id"], {"version": 1, "rooms": views, "home": synthesis(views)}))

    @callback
    def stopped():
        connection.send_message(websocket_api.event_message(msg["id"], {"version": 1, "reload": True}))

    removers = [c.async_add_listener(send) for c in coordinators]
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
