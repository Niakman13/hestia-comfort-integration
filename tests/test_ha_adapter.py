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
from homeassistant.helpers import area_registry as ar, floor_registry as fr, device_registry as dr, entity_registry as er
from custom_components.niak_comfort.config_flow import ComfortOptionsFlow, ComfortConfigFlow
from custom_components.niak_comfort.coordinator import ComfortCoordinator
from custom_components.niak_comfort.sensor import ComfortSensor, DESCRIPTIONS
from custom_components.niak_comfort import async_setup


class AdapterFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.directory.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        await fr.async_load(self.hass)
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
    async def test_the_thermostat_mode_reaches_the_card(self):
        coordinator = ComfortCoordinator(self.hass, self.entry)
        data = await coordinator._async_update_data()
        self.assertEqual((data["observations"]["heating_mode"]["value"], data["observations"]["heating_mode"]["detail"]), ("heat", "hvac"))
        self.hass.states.async_set("climate.test", "heat", {"hvac_action": "idle", "preset_mode": "frost"})
        data = await coordinator._async_update_data()
        self.assertEqual((data["observations"]["heating_mode"]["value"], data["observations"]["heating_mode"]["detail"]), ("frost", "preset"))

    async def test_an_unchanged_value_is_current_when_its_device_just_spoke(self):
        from types import SimpleNamespace
        coordinator = ComfortCoordinator(self.hass, self.entry)
        five_hours = (dt_util.utcnow() - timedelta(hours=5)).timestamp()
        self.hass.states.async_set("sensor.hum", "72", {"unit_of_measurement": "%", "device_class": "humidity"}, timestamp=five_hours)
        self.hass.states.async_set("sensor.thermo", "19.9", {"unit_of_measurement": "°C", "device_class": "temperature"})
        now = dt_util.utcnow()
        registry = SimpleNamespace(async_get=lambda eid: SimpleNamespace(device_id="probe"))
        siblings = [SimpleNamespace(entity_id="sensor.hum"), SimpleNamespace(entity_id="sensor.thermo")]
        with patch("custom_components.niak_comfort.coordinator.er.async_get", return_value=registry), \
             patch("custom_components.niak_comfort.coordinator.er.async_entries_for_device", return_value=siblings):
            self.assertEqual(coordinator._reading("sensor.hum", "humidity", now).quality, "valid")
        lonely = SimpleNamespace(async_get=lambda eid: SimpleNamespace(device_id=None))
        with patch("custom_components.niak_comfort.coordinator.er.async_get", return_value=lonely):
            self.assertEqual(coordinator._reading("sensor.hum", "humidity", now).quality, "stale")

    async def test_a_contact_shows_at_once_but_advice_waits_for_a_real_opening(self):
        coordinator = ComfortCoordinator(self.hass, self.entry)
        self.hass.states.async_set("binary_sensor.window", "on")
        coordinator.opened_since["binary_sensor.window"] = dt_util.utcnow()
        data = await coordinator._async_update_data()
        self.assertTrue(data["observations"]["window:binary_sensor.window"]["value"])
        self.assertFalse(data["assessment"]["openings"][0]["open"])
        coordinator.opened_since["binary_sensor.window"] = dt_util.utcnow() - timedelta(seconds=45)
        data = await coordinator._async_update_data()
        self.assertTrue(data["assessment"]["openings"][0]["open"])

    async def test_past_openings_are_learned_and_remembered(self):
        from homeassistant.core import State
        sources = {**self.entry.data["sources"], "indoor_humidity": "sensor.hum", "outdoor_humidity": "sensor.out_hum"}
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        self.hass.config_entries.async_update_entry(self.entry, options={"sources": sources})
        self.hass.config.components.add("recorder")
        now = dt_util.utcnow()
        start = now - timedelta(hours=5)
        def row(entity_id, state, minutes):
            return State(entity_id, state, last_changed=start + timedelta(minutes=minutes))
        # Two hours open: the humidity falls from 80 % to 65 % at 20 °C, with 12 °C and 80 % outside.
        history = {"binary_sensor.window": [row("binary_sensor.window", "off", 0), row("binary_sensor.window", "on", 30),
                                            row("binary_sensor.window", "off", 150)],
                   "sensor.inside": [row("sensor.inside", "68", 0)],
                   "sensor.hum": [row("sensor.hum", str(80 - min(15, m / 8)), m) for m in range(0, 300, 5)],
                   "sensor.outside": [row("sensor.outside", "12", 0)], "sensor.out_hum": [row("sensor.out_hum", "80", 0)]}
        class FakeRecorder:
            async def async_add_executor_job(self, function, *args):
                return history
        coordinator = ComfortCoordinator(self.hass, self.entry)
        with patch("homeassistant.components.recorder.get_instance", return_value=FakeRecorder()):
            await coordinator._learn(now)
        self.assertEqual(coordinator.drying_model["openings"], 1)
        self.assertEqual(len((await coordinator._learning_store.async_load())["episodes"]), 1)
        # Without the recorder, what was stored is still known.
        self.hass.config.components.remove("recorder")
        again = ComfortCoordinator(self.hass, self.entry)
        await again._learn(now)
        self.assertEqual(again.drying_model, coordinator.drying_model)

    async def _season(self, rows):
        class FakeRecorder:
            async def async_add_executor_job(self, function, *args):
                return {"sensor.outside": rows}
        coordinator = ComfortCoordinator(self.hass, self.entry)
        with patch("homeassistant.components.recorder.get_instance", return_value=FakeRecorder()):
            data = await coordinator._async_update_data()
        return data["assessment"]["features"]["season"]

    async def test_the_comfort_range_follows_the_recorded_outdoor_mean(self):
        season = await self._season([{"mean": 21.0}] * 100)
        self.assertTrue(season["known"])
        self.assertEqual(season["maximum"], 26)

    async def test_too_few_statistics_keep_the_saved_range(self):
        season = await self._season([{"mean": 21.0}] * 10)
        self.assertFalse(season["known"])
        self.assertEqual(season["maximum"], 24)

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

    async def test_options_constructor(self):
        self.assertIsInstance(ComfortOptionsFlow(), ComfortOptionsFlow)

    async def test_only_read_websocket_no_equipment_service(self):
        before = self.hass.services.async_services()
        await async_setup(self.hass, {})
        self.assertEqual(self.hass.services.async_services(), before)

    async def test_panel_room_creates_one_zone(self):
        er.async_get(self.hass).async_get_or_create("sensor", "fixture", "room", suggested_object_id="room")
        self.hass.states.async_set("sensor.room", "21", {"unit_of_measurement": "°C", "device_class": "temperature"})
        flow = ComfortConfigFlow()
        flow.hass = self.hass
        flow.context = {"source": "user"}
        result = await flow.async_step_user({"panel_config": {"name": "Salon", "area_id": "salon",
            "sources": {"indoor_temperature": "sensor.room"}, "windows": [], "settings": {"minimum": 20, "maximum": 24}}})
        self.assertEqual(result["data"]["area_id"], "salon")
        self.assertNotIn("co2", result["data"]["sources"])

    async def test_clock_expires_unchanged_values(self):
        coordinator = ComfortCoordinator(self.hass, self.entry)
        first = await coordinator._async_update_data()
        self.assertEqual(first["assessment"]["level"], "urgent")
        # Beyond the three-hour expiry with no news from the sensor or its device, a measure is no longer current.
        with patch("custom_components.niak_comfort.coordinator.dt_util.utcnow", return_value=dt_util.utcnow()+timedelta(hours=4)):
            expired = await coordinator._async_update_data()
        self.assertEqual(expired["observations"]["co2"]["quality"], "stale")
        self.assertEqual(expired["assessment"]["action"], "unknown")
        self.assertNotIn("air", expired["assessment"]["needs"])
        # The window contact and the heating action are states: hours without change keep them known.
        self.assertEqual(expired["observations"]["window:binary_sensor.window"]["quality"], "valid")
        self.assertEqual(expired["observations"]["heating"]["quality"], "valid")

    async def test_options_can_remove_optional_source(self):
        # Register the fixture without bootstrapping platforms or a server.
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        self.hass.config_entries.async_update_entry(self.entry, options={"sources": {
            "indoor_temperature": "sensor.inside", "outdoor_temperature": "sensor.outside"}})
        result = await ComfortCoordinator(self.hass, self.entry)._async_update_data()
        self.assertNotIn("co2", result["observations"])
        self.assertEqual(tuple(result["assessment"]["unverified"]), ("pollution", "rain"))

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
