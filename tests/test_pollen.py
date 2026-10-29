"""Pollens, only for a household that said it is allergic (« Réglages généraux »): a short airing, early or after the rain,
never an airing withheld that the humidity or the CO₂ needs. Without the setting, nothing changes (29 October 2026)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.assessment import POLLEN_AIRING, Settings, assess
from engine.sources import Reading

NOW = datetime(2026, 5, 12, 9, tzinfo=timezone.utc)
HIGH = {"level": 3, "high": True, "main": "Graminées"}


def run(co2=1400, window=False, **context):
    values = {"indoor_temperature": 22.0, "outdoor_temperature": 18.0, "indoor_humidity": 50, "outdoor_humidity": 55,
              "co2": co2, "rain": False, "pollution": False, "window:w": window}
    readings = {k: Reading(v, "valid", "sensor.x") for k, v in values.items()}
    return assess(readings, Settings(minimum=20, maximum=24), None, {}, None, {}, NOW, context={"heated": True, **context})


class Engine(unittest.TestCase):
    def test_without_the_setting_nothing_changes(self):
        plain = run()
        self.assertEqual((plain.action, plain.reason), ("ouvrir", "air_needed"))
        self.assertIsNone(plain.features["pollen"])
        # Pollens low, or not given (setting off): the same advice, the same airing.
        for pollen in (None, {"level": 2, "high": False}):
            a = run(pollen=pollen)
            self.assertEqual((a.action, a.reason, a.level), (plain.action, plain.reason, plain.level))
            self.assertEqual(a.features["ventilation"]["duration_minutes"], plain.features["ventilation"]["duration_minutes"])
            self.assertIsNone(a.features["pollen"])

    def test_high_pollens_keep_a_needed_airing_but_short(self):
        plain, a = run(), run(pollen=HIGH)
        self.assertGreater(plain.features["ventilation"]["duration_minutes"]["max"], POLLEN_AIRING)
        self.assertEqual((a.action, a.reason, a.level), (plain.action, plain.reason, plain.level))
        self.assertLessEqual(a.features["ventilation"]["duration_minutes"]["max"], POLLEN_AIRING)
        self.assertEqual(a.features["pollen"], {"level": 3, "main": "Graminées", "after_rain": False, "airing": True})

    def test_just_after_the_rain_is_the_moment(self):
        self.assertTrue(run(pollen=HIGH, rained_at=(NOW - timedelta(minutes=20)).isoformat()).features["pollen"]["after_rain"])
        self.assertFalse(run(pollen=HIGH, rained_at=(NOW - timedelta(hours=3)).isoformat()).features["pollen"]["after_rain"])

    def test_an_airing_nothing_calls_for_is_not_proposed(self):
        plain = run(co2=1100)
        if plain.reason != "optional_air_change":
            self.skipTest("no optional airing at this CO₂ with the default thresholds")
        self.assertEqual(run(co2=1100, pollen=HIGH).reason, "within_comfort")


class Setting(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from homeassistant.config_entries import ConfigEntries
        from homeassistant.core import HomeAssistant
        from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, floor_registry as fr
        from custom_components.hestia_comfort.configuration import get_configuration
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

    async def test_off_by_default_kept_apart_and_read_only_when_on(self):
        self.assertFalse(self.config.snapshot()["home"]["pollen_allergy"])
        asked = []
        api = type("Api", (), {"version": 1, "places": lambda self: [], "pollen": lambda self, entry_id: asked.append(entry_id) or HIGH})()
        self.hass.data["hestia_weather_api"] = api
        self.config.home = {**self.config.home, "configured": True, "weather": "place"}
        before = self.config.revision()
        self.assertIsNone(self.config.pollen())  # nobody said they are allergic: Hestia Weather is not even asked
        self.assertEqual(asked, [])
        snapshot = await self.config.set_pollen_allergy(True)
        self.assertTrue(snapshot["home"]["pollen_allergy"])
        # Like the alarm, the setting never blocks a room being edited at the same time.
        self.assertEqual(self.config.revision(), before)
        self.assertEqual(self.config.pollen(), HIGH)
        self.assertEqual(asked, ["place"])
        self.assertFalse((await self.config.set_pollen_allergy(False))["home"]["pollen_allergy"])
        with self.assertRaises(ValueError):
            await self.config.set_pollen_allergy("oui")


if __name__ == "__main__":
    unittest.main()
