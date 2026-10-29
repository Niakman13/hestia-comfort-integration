"""Shared « Hestia » panel (socle v1): registration, newest copy wins, home page states."""
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from homeassistant.components.frontend import DATA_PANELS
from homeassistant.components.websocket_api import DOMAIN as WS_DOMAIN
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, floor_registry as fr
from custom_components.niak_comfort import socle
from custom_components.niak_comfort.configuration import get_configuration
from custom_components.niak_comfort.panel import comfort_status


def brick(status=None, **extra):
    async def ok(hass):
        return {"level": "ok", "summary": "Tout va bien.", "details": [], "links": []}
    return {"domain": "niak_comfort", "name": "Hestia Confort", "slug": "confort", "version": "1.0",
            "icon": "mdi:home", "module_url": "/a/panel.js", "element": "niak-comfort-setup",
            "status": status or ok, "legacy_path": "niak-confort", **extra}


class SocleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    def module(self):
        return self.hass.data[DATA_PANELS]["niak"].config["_panel_custom"]["module_url"]

    async def test_one_brick_opens_the_niak_panel_and_keeps_its_old_address(self):
        await socle.async_register_brick(self.hass, brick(), "/a/niak-socle.js")
        panels = self.hass.data[DATA_PANELS]
        self.assertEqual(panels["niak"].sidebar_title, "Hestia")
        self.assertEqual(self.module(), "/a/niak-socle.js")
        self.assertTrue(panels["niak"].require_admin)
        legacy = panels["niak-confort"]
        self.assertIsNone(legacy.sidebar_title)  # hidden from the sidebar
        self.assertEqual(legacy.config["redirect"], "/niak/confort")
        self.assertEqual(legacy.config_panel_domain, "niak_comfort")  # « Configurer » still works
        self.assertIn("niak/overview", self.hass.data[WS_DOMAIN])

    async def test_registering_again_changes_nothing(self):
        await socle.async_register_brick(self.hass, brick(), "/a/niak-socle.js")
        await socle.async_register_brick(self.hass, brick(), "/a/niak-socle.js")
        self.assertEqual(len(self.hass.data[socle.KEY]["bricks"]), 1)

    async def test_the_newest_copy_shows_the_panel(self):
        await socle.async_register_brick(self.hass, brick(domain="niak_old", slug="old", legacy_path=None), "/old/niak-socle.js")
        self.hass.data[socle.KEY]["panel"]["socle"] = (0, 9)  # as written by an older copy
        await socle.async_register_brick(self.hass, brick(), "/new/niak-socle.js")
        self.assertEqual(self.module(), "/new/niak-socle.js")
        self.assertEqual(set(self.hass.data[socle.KEY]["bricks"]), {"niak_old", "niak_comfort"})

    async def test_an_older_copy_never_replaces_a_newer_panel(self):
        await socle.async_register_brick(self.hass, brick(), "/new/niak-socle.js")
        self.hass.data[socle.KEY]["panel"]["socle"] = (2, 0)
        await socle.async_register_brick(self.hass, brick(domain="niak_weather", slug="meteo", legacy_path=None), "/old/niak-socle.js")
        self.assertEqual(self.module(), "/new/niak-socle.js")

    async def test_home_page_lists_bricks_and_published_ones_not_yet_in_the_panel(self):
        await socle.async_register_brick(self.hass, brick(), "/a/niak-socle.js")
        self.hass.config.components.add("niak_weather")
        overview = await socle.async_overview(self.hass)
        self.assertEqual([b["slug"] for b in overview["bricks"]], ["confort"])
        self.assertFalse(any(callable(v) for v in overview["bricks"][0].values()))  # sendable as JSON
        self.assertEqual(overview["bricks"][0]["status"]["level"], "ok")
        weather = next(o for o in overview["others"] if o["domain"] == "niak_weather")
        self.assertTrue(weather["installed"])
        self.assertEqual(weather["settings_path"], "/config/integrations/integration/niak_weather")
        self.assertNotIn("niak_comfort", [o["domain"] for o in overview["others"]])

    async def test_a_failing_brick_is_unknown_and_never_hides_the_others(self):
        async def broken(hass):
            raise RuntimeError("boom")
        await socle.async_register_brick(self.hass, brick(broken), "/a/niak-socle.js")
        with self.assertLogs("custom_components.niak_comfort.socle", "ERROR"):
            overview = await socle.async_overview(self.hass)
        self.assertEqual(overview["bricks"][0]["status"]["level"], "unknown")

    async def test_unknown_levels_are_never_shown_as_fine(self):
        async def odd(hass):
            return {"level": "great", "summary": "?"}
        await socle.async_register_brick(self.hass, brick(odd), "/a/niak-socle.js")
        self.assertEqual((await socle.async_overview(self.hass))["bricks"][0]["status"]["level"], "unknown")

    async def test_the_sidebar_entry_can_be_hidden_and_the_panel_stays_open(self):
        await socle.async_register_brick(self.hass, brick(), "/a/niak-socle.js")
        self.assertTrue((await socle.async_overview(self.hass))["sidebar"])
        await socle.async_set_sidebar(self.hass, False)
        panel = self.hass.data[DATA_PANELS]["niak"]
        self.assertIsNone(panel.sidebar_title)  # gone from the sidebar, still served at /niak
        self.assertEqual(self.module(), "/a/niak-socle.js")
        self.assertFalse((await socle.async_overview(self.hass))["sidebar"])
        await socle.async_set_sidebar(self.hass, True)
        self.assertEqual(self.hass.data[DATA_PANELS]["niak"].sidebar_title, "Hestia")

    async def test_the_choice_survives_a_restart_and_applies_to_the_next_brick(self):
        await socle.async_register_brick(self.hass, brick(), "/a/niak-socle.js")
        await socle.async_set_sidebar(self.hass, False)
        self.hass.data.pop(socle.KEY)  # as after a restart: the file is all that remains
        await socle.async_register_brick(self.hass, brick(), "/a/niak-socle.js")
        self.assertIsNone(self.hass.data[DATA_PANELS]["niak"].sidebar_title)
        self.assertIn("niak/set_sidebar", self.hass.data[WS_DOMAIN])

    async def test_theme_and_sidebar_survive_restart_without_overwriting_each_other(self):
        await socle.async_register_brick(self.hass, brick(), "/a/niak-socle.js")
        self.assertEqual((await socle.async_overview(self.hass))["theme"], "niak")
        self.assertIn("niak/set_theme", self.hass.data[WS_DOMAIN])
        await socle.async_set_theme(self.hass, "ha")
        await socle.async_set_sidebar(self.hass, False)
        self.hass.data.pop(socle.KEY)
        await socle.async_register_brick(self.hass, brick(), "/a/niak-socle.js")
        overview = await socle.async_overview(self.hass)
        self.assertEqual(overview["theme"], "ha")
        self.assertFalse(overview["sidebar"])
        await socle.async_set_theme(self.hass, "niak")
        self.assertFalse((await socle.async_overview(self.hass))["sidebar"])
        with self.assertRaises(ValueError):
            await socle.async_set_theme(self.hass, "unknown")
        self.assertEqual((await socle.async_overview(self.hass))["theme"], "niak")

    async def test_old_settings_keep_the_existing_niak_appearance(self):
        from homeassistant.helpers.storage import Store
        await Store(self.hass, socle.STORE_VERSION, socle.KEY).async_save({"sidebar": False})
        await socle.async_register_brick(self.hass, brick(), "/a/niak-socle.js")
        overview = await socle.async_overview(self.hass)
        self.assertEqual(overview["theme"], "niak")
        self.assertFalse(overview["sidebar"])

    async def test_old_copy_loading_first_does_not_erase_stored_theme(self):
        from homeassistant.helpers.storage import Store
        await Store(self.hass, socle.STORE_VERSION, socle.KEY).async_save({"sidebar": False, "theme": "ha"})
        # Socle 1.5/1.6 only imports the sidebar field before the newest copy starts.
        self.hass.data[socle.KEY] = {"bricks": {}, "panel": None, "settings": {"sidebar": False}}
        await socle.async_register_brick(self.hass, brick(), "/new/niak-socle.js")
        self.assertEqual((await socle.async_overview(self.hass))["theme"], "ha")
        self.assertFalse((await socle.async_overview(self.hass))["sidebar"])

    async def test_older_weather_copy_cannot_replace_theme_handler_or_preference(self):
        from unittest.mock import patch
        await socle.async_register_brick(self.hass, brick(), "/new/niak-socle.js")
        await socle.async_set_theme(self.hass, "ha")
        handler = self.hass.data[WS_DOMAIN]["niak/set_theme"]
        with patch.object(socle, "SOCLE_VERSION", (1, 4)):
            await socle.async_register_brick(self.hass, brick(domain="niak_weather", slug="meteo", legacy_path=None), "/old/niak-socle.js")
        self.assertEqual(self.module(), "/new/niak-socle.js")
        self.assertIs(self.hass.data[WS_DOMAIN]["niak/set_theme"], handler)
        self.assertEqual((await socle.async_overview(self.hass))["theme"], "ha")



class ComfortStatusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        await fr.async_load(self.hass)
        await ar.async_load(self.hass)
        dr.async_setup(self.hass)
        await dr.async_load(self.hass)
        await er.async_load(self.hass)
        self.config = await get_configuration(self.hass)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    def room(self, name, state=ConfigEntryState.LOADED, reason="ventilate"):
        entry = ConfigEntry(domain="niak_comfort", title=name, unique_id=name, version=1, minor_version=1,
            source="user", data={"name": name, "area_id": None}, options={}, discovery_keys={}, subentries_data=[])
        entry.runtime_data = SimpleNamespace(data={"assessment": {"reason": reason}})
        self.hass.config_entries._entries[entry.entry_id] = entry
        entry._async_set_state(self.hass, state, None)

    async def test_no_room_asks_to_start_with_the_living_room(self):
        status = await comfort_status(self.hass)
        self.assertEqual(status["level"], "action")
        self.assertIn("Salon", status["details"][0])

    async def test_everything_followed_is_blue(self):
        self.room("Salon")
        self.room("Cuisine")
        self.config.home = {"configured": True, "sources": {}, "revision": 1}
        status = await comfort_status(self.hass)
        self.assertEqual(status["level"], "ok")
        self.assertEqual(status["summary"], "2 pièces suivies, rien à régler.")

    async def test_what_to_fix_is_named(self):
        self.room("Salon", reason="incomplete_data")
        self.room("Cuisine", state=ConfigEntryState.SETUP_ERROR)
        status = await comfort_status(self.hass)
        self.assertEqual(status["level"], "action")
        # The same points as the « Confort » tab: a stopped room and the exterior.
        self.assertEqual(status["summary"], "2 pièces suivies, 2 points à régler.")
        self.assertIn("Cuisine : calcul arrêté", status["details"])
        self.assertIn("Extérieur à configurer", status["details"])

    async def test_a_silent_source_is_a_point_to_fix_even_when_advice_stands(self):
        for name in ("Salon", "Chambre"):
            self.room(name, reason="drying_possible")
        self.hass.states.async_set("sensor.atmo", "2")
        silent = {"value": None, "quality": "unknown", "source": "sensor.atmo"}
        for entry in self.hass.config_entries._entries.values():
            entry.runtime_data.data = {"assessment": {"reason": "drying_possible", "missing": ["pollution"]}, "observations": {"pollution": silent}}
        self.config.home = {"configured": True, "sources": {"pollution": {"entity_id": "sensor.atmo", "adapter": "binary"}}, "revision": 1}
        status = await comfort_status(self.hass)
        self.assertEqual(status["level"], "action")
        # Home Assistant still shows it, the advice cannot use it: one point, the same on the tab and on the home page.
        self.assertIn("Extérieur : la pollution ne donne pas de mesure exploitable", status["details"])


class Resources:
    """Dashboard resources as the user interface keeps them (lovelace's storage collection), not loaded yet."""
    def __init__(self, *urls):
        self.loaded, self.items = False, [{"id": str(i), "type": "module", "url": u} for i, u in enumerate(urls)]
    async def async_load(self):
        pass
    def async_items(self):
        return list(self.items)
    async def async_create_item(self, data):
        self.items.append({"id": f"n{len(self.items)}", "type": data["res_type"], "url": data["url"]})
    async def async_update_item(self, item_id, data):
        next(i for i in self.items if i["id"] == item_id)["url"] = data["url"]
    async def async_delete_item(self, item_id):
        self.items = [i for i in self.items if i["id"] != item_id]


class CardResourceTests(unittest.IsolatedAsyncioTestCase):
    URL = "/niak_comfort-assets/niak-comfort-card.js"

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    def urls(self, resources):
        return [i["url"] for i in resources.items]

    async def test_the_card_becomes_a_dashboard_resource_at_its_version(self):
        resources = self.hass.data["lovelace"] = SimpleNamespace(resources=Resources("/hacsfiles/other/other.js"))
        await socle._card_resource(self.hass, self.URL, self.URL + "?v=1.0")
        self.assertTrue(resources.resources.loaded)
        self.assertEqual(self.urls(resources.resources), ["/hacsfiles/other/other.js", self.URL + "?v=1.0"])

    async def test_a_new_version_updates_it_and_duplicates_go(self):
        resources = Resources(self.URL + "?v=0.9", "/other.js", self.URL)
        self.hass.data["lovelace"] = SimpleNamespace(resources=resources)
        await socle._card_resource(self.hass, self.URL, self.URL + "?v=1.0")
        self.assertEqual(self.urls(resources), [self.URL + "?v=1.0", "/other.js"])
        await socle._card_resource(self.hass, self.URL, self.URL + "?v=1.0")
        self.assertEqual(self.urls(resources), [self.URL + "?v=1.0", "/other.js"])

    async def test_resources_written_in_yaml_are_left_alone(self):
        self.hass.data["lovelace"] = SimpleNamespace(resources=SimpleNamespace(async_items=lambda: []))
        await socle._card_resource(self.hass, self.URL, self.URL + "?v=1.0")  # nothing to create there: no error
        await socle.async_remove_card(self.hass, self.URL)

    async def test_removing_the_card_keeps_the_other_resources(self):
        resources = Resources("/other.js", self.URL + "?v=1.0")
        self.hass.data["lovelace"] = SimpleNamespace(resources=resources)
        await socle.async_remove_card(self.hass, self.URL)
        self.assertEqual(self.urls(resources), ["/other.js"])


if __name__ == "__main__":
    unittest.main()
