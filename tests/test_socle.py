"""Shared « Niak » panel (socle v1): registration, newest copy wins, home page states."""
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
from custom_components.niak_comfort import socle
from custom_components.niak_comfort.configuration import get_configuration
from custom_components.niak_comfort.panel import comfort_status


def brick(status=None, **extra):
    async def ok(hass):
        return {"level": "ok", "summary": "Tout va bien.", "details": [], "links": []}
    return {"domain": "niak_comfort", "name": "Niak Confort", "slug": "confort", "version": "1.0",
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
        self.assertEqual(panels["niak"].sidebar_title, "Niak")
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


class ComfortStatusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
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
        self.assertEqual(status["summary"], "2 pièces suivies, 3 points à régler.")
        self.assertIn("Calcul arrêté : Cuisine", status["details"])
        self.assertIn("Extérieur à configurer", status["details"])
        self.assertTrue(any(d.startswith("Information incomplète : Salon") for d in status["details"]))


if __name__ == "__main__":
    unittest.main()
