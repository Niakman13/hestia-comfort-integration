"""« Télécharger les diagnostics »: one file that explains a room's advice, without the home's coordinates."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, floor_registry as fr
from custom_components.niak_comfort.configuration import get_configuration
from custom_components.niak_comfort.diagnostics import async_get_config_entry_diagnostics


class Diagnostics(unittest.IsolatedAsyncioTestCase):
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
        await get_configuration(self.hass)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    async def test_one_file_with_the_advice_the_sensors_and_what_was_learned(self):
        self.hass.states.async_set("sensor.t", "18.2", {"unit_of_measurement": "°C", "device_class": "temperature", "entity_picture": "x"})
        self.hass.states.async_set("climate.vt", "off", {"hvac_mode": "off", "preset_mode": "eco", "temperature": 17,
                                                          "specific_states": {"hvac_off_reason": "hvac_off_manual"}})
        entry = ConfigEntry(domain="niak_comfort", title="Chambre P", unique_id="p", version=1, minor_version=1, source="user",
                            data={"name": "Chambre P", "area_id": None, "sources": {"indoor_temperature": "sensor.t", "heating": "climate.vt",
                                                                                     "co2": "sensor.gone"},
                                  "windows": ["binary_sensor.w"]},
                            options={}, discovery_keys={}, subentries_data=[])
        slot = {"kind": "close", "time": "2026-10-26T18:00:00+01:00", "temperature": 19.7, "wind_bearing": None}
        entry.runtime_data = SimpleNamespace(
            data={"assessment": {"reason": "heat_needed", "slot": slot, "missing": []}, "observations": {}},
            twin={"status": "ready", "days": 9, "samples": 400, "mass": 18.4, "model": {"thermal": {"a": 0.01, "z": 0.05}, "water": {}, "samples": 400},
                  "precision": {"hours": 24, "temperature": 0.3, "humidity": 2, "curve": [1, 2, 3]}},
            feedback=[], drying_model={"tau": 40}, home_configuration=None,
            _thermostat=lambda: {"name": "Versatile Thermostat", "preset": "eco", "target": 17},
            _weather_place=lambda: None)
        self.hass.config_entries._entries[entry.entry_id] = entry
        entry._async_set_state(self.hass, ConfigEntryState.LOADED, None)
        result = await async_get_config_entry_diagnostics(self.hass, entry)
        json.dumps(result)  # Home Assistant writes it as JSON.
        self.assertEqual(result["view"]["assessment"]["slot"], slot)
        self.assertEqual(result["thermostat"]["target"], 17)
        self.assertEqual(result["learning"]["twin"]["mass"], 18.4)
        self.assertNotIn("curve", result["learning"]["twin"]["precision"])
        self.assertEqual(result["states"]["source:indoor_temperature"]["attributes"], {"unit_of_measurement": "°C", "device_class": "temperature"})
        self.assertEqual(result["states"]["source:heating"]["attributes"]["specific_states"]["hvac_off_reason"], "hvac_off_manual")
        self.assertTrue(result["states"]["source:co2"]["missing"])
        self.assertIn("binary_sensor.w", result["states"]["window:binary_sensor.w"]["entity_id"])

    async def test_the_alarm_setting_is_kept_apart(self):
        config = await get_configuration(self.hass)
        before = config.revision()
        snapshot = await config.set_alarm("alarm_control_panel.maison")
        self.assertEqual(snapshot["home"]["alarm"], "alarm_control_panel.maison")
        # Choosing the alarm never blocks a room being edited at the same time.
        self.assertEqual(config.revision(), before)
        self.assertEqual((await config.set_alarm(""))["home"]["alarm"], "")
        with self.assertRaises(ValueError):
            await config.set_alarm("light.salon")

    async def test_an_extension_is_turned_off_for_every_room(self):
        """Alarmo off is no alarm, on is Alarmo found by itself; Versatile Thermostat and Adaptive Cover Pro are listed when off."""
        config = await get_configuration(self.hass)
        self.assertEqual((await config.set_extension("alarmo", False))["home"]["alarm"], "")
        self.assertIsNone((await config.set_extension("alarmo", True))["home"]["alarm"])
        self.assertEqual((await config.set_extension("versatile_thermostat", False))["home"]["disabled"], ["versatile_thermostat"])
        self.assertEqual((await config.set_extension("adaptive_cover_pro", False))["home"]["disabled"], ["versatile_thermostat", "adaptive_cover_pro"])
        self.assertEqual((await config.set_extension("versatile_thermostat", True))["home"]["disabled"], ["adaptive_cover_pro"])
        with self.assertRaises(ValueError):
            await config.set_extension("scheduler", False)
        # Turned off, the room reads neither the thermostat's setpoints nor the covers' driver.
        from custom_components.niak_comfort.coordinator import ComfortCoordinator
        room = SimpleNamespace(home_configuration=config, hass=self.hass, sources={"heating": "climate.vt"}, config={"openings": {}}, logger=None)
        room._uses = lambda key: ComfortCoordinator._uses(room, key)
        self.assertFalse(room._uses("adaptive_cover_pro"))
        self.assertTrue(room._uses("versatile_thermostat"))
        self.assertEqual(ComfortCoordinator._drivers(room), {})

    async def test_coordinates_are_removed(self):
        from custom_components.niak_comfort.diagnostics import TO_REDACT
        from homeassistant.components.diagnostics import async_redact_data
        self.assertEqual(async_redact_data({"latitude": 43.5, "x": {"longitude": 5.4}}, TO_REDACT),
                         {"latitude": "**REDACTED**", "x": {"longitude": "**REDACTED**"}})

    async def test_people_are_counted_not_named_nor_placed(self):
        """A person's zone may be a town or an address (issue #41): only « at home » or « away » is kept."""
        from custom_components.niak_comfort.diagnostics import TO_REDACT, _state, _without_names
        from homeassistant.components.diagnostics import async_redact_data
        self.hass.states.async_set("person.frank", "Bureau Marseille")
        self.hass.states.async_set("person.lea", "home")
        self.assertEqual(_state(self.hass, "person.frank")["state"], "not_home")
        self.assertEqual(_state(self.hass, "person.lea")["state"], "home")
        view = {"assessment": {"extended": {"people": {"home": ["Léa"], "away": ["Frank"]}}}, "context": [{"people": {"home": []}}]}
        self.assertEqual(_without_names(view), {"assessment": {"extended": {"people": {"home": 1, "away": 1}}},
                                                "context": [{"people": {"home": 0}}]})
        self.assertEqual(async_redact_data({"config": {"persons": ["person.frank"]}}, TO_REDACT), {"config": {"persons": "**REDACTED**"}})


if __name__ == "__main__":
    unittest.main()
