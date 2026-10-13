"""Bundled admin panel and Lovelace card: one installation, no resource to declare."""
from pathlib import Path
from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from .const import DOMAIN, VERSION


async def async_setup_panel(hass):
    if not hass.http or not hasattr(hass.http, "async_register_static_paths"):
        return  # Isolated engine tests and headless HA setups have no frontend.
    if not hass.data.get(DOMAIN + "_panel_asset"):
        await hass.http.async_register_static_paths([StaticPathConfig(
            "/niak_comfort-assets", str(Path(__file__).parent / "frontend"), False)])
        # The card is loaded on every dashboard, like a declared resource would be.
        frontend.add_extra_js_url(hass, f"/niak_comfort-assets/niak-comfort-card.js?v={VERSION}")
        hass.data[DOMAIN + "_panel_asset"] = True
    if not frontend.async_panel_exists(hass, "niak-confort"):
        await async_register_panel(hass, frontend_url_path="niak-confort", webcomponent_name="niak-comfort-setup",
            sidebar_title="Niak Confort", sidebar_icon="mdi:home-thermometer-outline",
            module_url=f"/niak_comfort-assets/panel.js?v={VERSION}", require_admin=True,
            config_panel_domain=DOMAIN)
