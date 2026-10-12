"""Read selected Home Assistant observations; never register equipment services."""
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import ComfortCoordinator
from .websocket import async_setup_websocket

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass, config):
    async_setup_websocket(hass)
    return True


async def async_setup_entry(hass, entry):
    coordinator = ComfortCoordinator(hass, entry)
    await coordinator.async_start()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])


async def _reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)
