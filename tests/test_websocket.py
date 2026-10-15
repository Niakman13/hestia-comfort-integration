"""Real HA command wrappers with an isolated registry and connection fixture."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, floor_registry as fr
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from custom_components.niak_comfort.coordinator import ComfortCoordinator
from custom_components.niak_comfort.websocket import ws_entries, ws_subscribe


class WebsocketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        await fr.async_load(self.hass)
        await ar.async_load(self.hass)
        self.conn = Mock(subscriptions={})

    async def asyncTearDown(self):
        for remove in list(self.conn.subscriptions.values()):
            remove()
        await self.hass.async_stop()
        self.temp.cleanup()

    async def add(self, area):
        entry = ConfigEntry(domain="niak_comfort", title=area, unique_id=area, version=1, minor_version=1,
            source="user", data={"name": area, "area_id": area}, options={}, discovery_keys={}, subentries_data=[])
        coordinator = ComfortCoordinator(self.hass, entry)
        coordinator.data = await coordinator._async_update_data()
        entry.runtime_data = coordinator
        self.hass.config_entries._entries[entry.entry_id] = entry
        entry._async_set_state(self.hass, ConfigEntryState.LOADED, None)
        return entry

    async def test_no_entry(self):
        ws_subscribe(self.hass, self.conn, {"id": 1, "type": "niak_comfort/subscribe"})
        self.assertEqual(self.conn.send_error.call_args.args[1], "not_configured")

    async def test_multiple_requires_explicit_room(self):
        await self.add("salon")
        await self.add("bureau")
        ws_subscribe(self.hass, self.conn, {"id": 1, "type": "niak_comfort/subscribe"})
        self.assertEqual(self.conn.send_error.call_args.args[1], "choose_entry")

    async def test_initial_push_updates_unavailable_and_cleanup(self):
        entry = await self.add("salon")
        coordinator = entry.runtime_data
        ws_subscribe(self.hass, self.conn, {"id": 1, "type": "niak_comfort/subscribe", "entry_id": entry.entry_id})
        self.assertEqual(self.conn.send_message.call_args.args[0]["event"]["view"]["area_id"], "salon")
        self.assertEqual(len(coordinator.stop_listeners), 1)
        coordinator.async_set_update_error(ValueError("fixture unavailable"))
        self.assertTrue(self.conn.send_message.call_args.args[0]["event"]["unavailable"])
        coordinator.async_stopped()
        self.assertTrue(self.conn.send_message.call_args.args[0]["event"]["reload"])
        self.conn.subscriptions[1]()
        self.assertEqual(len(coordinator.stop_listeners), 0)

    async def test_entry_picker_and_removed_room(self):
        entry = await self.add("salon")
        ws_entries(self.hass, self.conn, {"id": 1, "type": "niak_comfort/entries"})
        self.assertEqual(self.conn.send_result.call_args.args[1][0]["entry_id"], entry.entry_id)
        ws_subscribe(self.hass, self.conn, {"id": 2, "type": "niak_comfort/subscribe", "entry_id": "missing"})
        self.assertEqual(self.conn.send_error.call_args.args[1], "not_found")

    async def test_registry_changes_refresh_and_failed_room_remains(self):
        from custom_components.niak_comfort.websocket import ws_home_subscribe
        entry = await self.add('salon')
        ar.async_get(self.hass).async_create('Salon')
        floor = fr.async_get(self.hass).async_create('RDC', level=0)
        ws_home_subscribe(self.hass, self.conn, {'id':2,'type':'niak_comfort/home_subscribe'})
        self.assertIsNone(self.conn.send_message.call_args.args[0]['event']['home']['floors'][0]['floor_id'])
        ar.async_get(self.hass).async_update('salon',floor_id=floor.floor_id)
        await self.hass.async_block_till_done()
        self.assertEqual(self.conn.send_message.call_args.args[0]['event']['home']['floors'][0]['name'],'RDC')
        entry.runtime_data.async_set_update_error(ValueError('fixture unavailable'))
        event=self.conn.send_message.call_args.args[0]['event']
        self.assertEqual(len(event['rooms']),1)
        self.assertTrue(event['home']['partial'])
        self.assertEqual(event['home']['floors'][0]['measured'],0)
        self.conn.subscriptions[2]()
        count=self.conn.send_message.call_count
        fr.async_get(self.hass).async_update(floor.floor_id,name='Renommé')
        await self.hass.async_block_till_done()
        self.assertEqual(self.conn.send_message.call_count,count)


if __name__ == "__main__":
    unittest.main()
