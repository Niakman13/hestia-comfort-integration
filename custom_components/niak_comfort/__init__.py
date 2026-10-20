"""Read selected Home Assistant observations; never register equipment services."""
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import ComfortCoordinator
from .websocket import async_setup_websocket
from .configuration import get_configuration
from .panel import CARD_URL, async_setup_panel
from .socle import async_remove_card
from .air_references import apply_air_references, apply_freshness
from .api import API_KEY, NiakComfortApi

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass, config):
    # What Niak Confort publishes for the other bricks (the rooms and what their twins learned).
    hass.data.setdefault(API_KEY, NiakComfortApi(hass))
    async_setup_websocket(hass)
    await get_configuration(hass)
    await async_setup_panel(hass)
    return True


async def async_setup_entry(hass, entry):
    await get_configuration(hass)
    await async_setup_panel(hass)
    if entry.data.get("home"):
        return True
    apply_air_references(hass, entry)
    apply_freshness(hass, entry)
    coordinator = ComfortCoordinator(hass, entry)
    await coordinator.async_start()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def async_unload_entry(hass, entry):
    if entry.data.get("home"):
        return True
    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])


async def async_remove_entry(hass, entry):
    """With the last room gone, the card's dashboard resource goes too."""
    if not [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]:
        await async_remove_card(hass, CARD_URL)


async def _reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)
