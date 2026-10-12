"""Isolated HA 2026.10 checks; no connection to the user's running instance."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import timedelta
from homeassistant.util import dt as dt_util

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.config_entries import ConfigEntry, ConfigEntries, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from custom_components.niak_comfort.config_flow import source_schema, settings_schema, ComfortOptionsFlow, ComfortConfigFlow
from custom_components.niak_comfort.coordinator import ComfortCoordinator
from custom_components.niak_comfort.sensor import ComfortSensor, DESCRIPTIONS
from custom_components.niak_comfort import async_setup


class AdapterFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.directory.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        await ar.async_load(self.hass)
        dr.async_setup(self.hass)
        await dr.async_load(self.hass)
        await er.async_load(self.hass)
        ar.async_get(self.hass).async_create("Salon")
        self.entry = ConfigEntry(domain="niak_comfort", title="Salon", unique_id="salon", version=1, minor_version=1,
            source="user", data={"name": "Salon", "area_id": "salon", "sources": {
                "indoor_temperature": "sensor.inside", "outdoor_temperature": "sensor.outside",
                "co2": "sensor.co2", "rain": "binary_sensor.rain", "pollution": "binary_sensor.pollution",
                "heating": "climate.test"}, "windows": ["binary_sensor.window"]},
            options={}, discovery_keys={}, subentries_data=[])
        for entity, value, attributes in (
            ("sensor.inside", "72", {"unit_of_measurement": "°F", "device_class": "temperature"}),
            ("sensor.outside", "10", {"unit_of_measurement": "°C", "device_class": "temperature"}),
            ("sensor.co2", "1700", {"unit_of_measurement": "ppm"}),
            ("binary_sensor.rain", "off", {}), ("binary_sensor.pollution", "off", {}),
            ("binary_sensor.window", "off", {}), ("climate.test", "heat", {"hvac_action": "idle"}),
        ):
            self.hass.states.async_set(entity, value, attributes)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.directory.cleanup()


class AdapterTests(AdapterFixture):
    async def test_real_state_mapping_and_sensor_output(self):
        coordinator = ComfortCoordinator(self.hass, self.entry)
        coordinator.data = await coordinator._async_update_data()
        result = coordinator.data["assessment"]
        self.assertEqual((result["level"], result["action"], result["heating_action"]), ("urgent", "ouvrir", "idle"))
        self.assertAlmostEqual(coordinator.data["observations"]["indoor_temperature"]["value"], 200/9)
        sensor = ComfortSensor(coordinator, self.entry, DESCRIPTIONS[0])
        self.assertEqual(sensor.native_value, "urgent")
        self.assertEqual(coordinator.data["area_id"], "salon")

    async def test_unavailable_co2_and_heating_action(self):
        self.hass.states.async_set("sensor.co2", "unavailable")
        self.hass.states.async_set("climate.test", "heat", {})
        result = (await ComfortCoordinator(self.hass, self.entry)._async_update_data())["assessment"]
        self.assertEqual(result["heating_action"], "unknown")
        self.assertNotIn("air", result["needs"])
        self.assertTrue(result["partial"])

    async def test_configuration_schema_and_options_constructor(self):
        source_schema()({"indoor_temperature": "sensor.inside", "outdoor_temperature": "sensor.outside"})
        self.assertEqual(settings_schema()({})["co2_action"], 1200)
        self.assertIsInstance(ComfortOptionsFlow(), ComfortOptionsFlow)

    async def test_only_read_websocket_no_equipment_service(self):
        before = self.hass.services.async_services()
        await async_setup(self.hass, {})
        self.assertEqual(self.hass.services.async_services(), before)

    async def test_flow_steps_create_one_zone(self):
        flow = ComfortConfigFlow()
        flow.hass = self.hass
        flow.context = {"source": "user"}
        result = await flow.async_step_user({"name": "Salon", "area_id": "salon"})
        self.assertEqual(result["step_id"], "indoor")
        result = await flow.async_step_indoor({"indoor_temperature": "sensor.inside"})
        self.assertEqual(result["step_id"], "outdoor")
        await flow.async_step_outdoor({})
        await flow.async_step_windows({})
        await flow.async_step_heating({})
        result = await flow.async_step_preferences({"minimum": 30, "maximum": 20})
        self.assertEqual(result["errors"], {"base": "invalid_settings"})
        await flow.async_step_preferences({"minimum": 20, "maximum": 24})
        result = await flow.async_step_finish({})
        self.assertEqual(result["data"]["area_id"], "salon")
        self.assertNotIn("co2", result["data"]["sources"])

    async def test_clock_expires_unchanged_values(self):
        coordinator = ComfortCoordinator(self.hass, self.entry)
        first = await coordinator._async_update_data()
        self.assertEqual(first["assessment"]["level"], "urgent")
        with patch("custom_components.niak_comfort.coordinator.dt_util.utcnow", return_value=dt_util.utcnow()+timedelta(hours=1)):
            expired = await coordinator._async_update_data()
        self.assertEqual(expired["observations"]["co2"]["quality"], "stale")
        self.assertEqual(expired["assessment"]["action"], "unknown")
        self.assertNotIn("air", expired["assessment"]["needs"])

    async def test_options_can_remove_optional_source(self):
        # Register the fixture without bootstrapping platforms or a server.
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        self.hass.config_entries.async_update_entry(self.entry, options={"sources": {
            "indoor_temperature": "sensor.inside", "outdoor_temperature": "sensor.outside"}})
        result = await ComfortCoordinator(self.hass, self.entry)._async_update_data()
        self.assertNotIn("co2", result["observations"])
        self.assertTrue(result["assessment"]["partial"])

    async def test_state_changes_and_unload_remove_listeners(self):
        self.entry._async_set_state(self.hass, ConfigEntryState.SETUP_IN_PROGRESS, None)
        coordinator = ComfortCoordinator(self.hass, self.entry)
        await coordinator.async_start()
        self.assertEqual(coordinator.data["assessment"]["action"], "ouvrir")
        self.hass.states.async_set("binary_sensor.rain", "on")
        await self.hass.async_block_till_done()
        self.assertEqual(coordinator.data["assessment"]["action"], "attendre")
        await self.entry._async_process_on_unload(self.hass)
        await coordinator.async_shutdown()


if __name__ == "__main__":
    unittest.main()
