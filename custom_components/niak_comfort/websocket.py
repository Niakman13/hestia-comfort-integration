"""Read-only view v1 for the future Lit card; no command endpoint."""
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import callback

from .const import DOMAIN


@callback
def async_setup_websocket(hass):
    websocket_api.async_register_command(hass, ws_view)
    websocket_api.async_register_command(hass, ws_entries)
    websocket_api.async_register_command(hass, ws_subscribe)


def loaded_entries(hass):
    return sorted((e for e in hass.config_entries.async_entries(DOMAIN)
                   if e.state is ConfigEntryState.LOADED), key=lambda e: e.title)


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


@websocket_api.websocket_command({vol.Required("type"): "niak_comfort/view", vol.Required("entry_id"): str})
@callback
def ws_view(hass, connection, msg):
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "Pièce Niak Comfort non chargée")
        return
    connection.send_result(msg["id"], entry.runtime_data.data)
