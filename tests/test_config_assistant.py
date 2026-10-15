"""Beta 4 room model: free rooms, exterior ranking, openings and remembered confirmations."""
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import EntityCategory
import test_ha_adapter
from custom_components.niak_comfort.config_flow import ComfortConfigFlow
from custom_components.niak_comfort.configuration import Configuration
from custom_components.niak_comfort.discovery import catalog, suggestions
from custom_components.niak_comfort import weather_link


class AssistantTests(test_ha_adapter.AdapterFixture):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = Configuration(self.hass)
        await self.service.load()
        ar.async_get(self.hass).async_create('Extérieur')

    def register(self, entity_id, kind, area='salon', category=None, value='21', unit='°C', device_id=None, platform='fixture'):
        domain, name = entity_id.split('.')
        entry = er.async_get(self.hass).async_get_or_create(domain, platform, name,
            suggested_object_id=name, original_device_class=kind, original_name=name, entity_category=category, device_id=device_id)
        if area:
            er.async_get(self.hass).async_update_entity(entry.entity_id, area_id=area)
        self.hass.states.async_set(entity_id, value, {'device_class': kind, 'unit_of_measurement': unit})
        return entry

    def proposals(self, area_id):
        return suggestions(catalog(self.hass, area_id), area_id)

    def flow(self):
        flow = ComfortConfigFlow(); flow.hass = self.hass; flow.context = {'source': 'user'}
        return flow

    def room(self, **extra):
        return {'area_id': 'salon', 'name': 'Salon', 'sources': {'indoor_temperature': 'sensor.room'},
                'windows': [], 'settings': {'minimum': 20, 'maximum': 24}, **extra}

    async def test_first_activation_then_rooms_are_added_from_the_page(self):
        result = await self.flow().async_step_user()
        self.assertEqual(result['step_id'], 'home')
        workspace = await self.flow().async_step_user({})
        self.assertTrue(workspace['data']['home'])
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        self.assertEqual((await self.flow().async_step_user())['reason'], 'use_panel')

    async def test_reference_beats_multiple_candidates_and_diagnostics_are_excluded(self):
        self.register('sensor.room', 'temperature')
        self.register('sensor.plant', 'temperature')
        self.register('sensor.device', 'temperature', category=EntityCategory.DIAGNOSTIC)
        self.assertNotIn('indoor_temperature', self.proposals('salon'))
        ar.async_get(self.hass).async_update('salon', temperature_entity_id='sensor.room')
        self.assertEqual(self.proposals('salon')['indoor_temperature'], 'sensor.room')
        self.assertNotIn('sensor.device', [c['entity_id'] for c in catalog(self.hass, 'salon')['indoor_temperature']])

    async def test_device_area_and_entity_override(self):
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        device = dr.async_get(self.hass).async_get_or_create(config_entry_id=self.entry.entry_id, identifiers={('fixture', 'station')})
        dr.async_get(self.hass).async_update_device(device.id, area_id='salon')
        self.register('sensor.inherited', 'humidity', area=None, unit='%', device_id=device.id)
        self.assertEqual(self.proposals('salon')['indoor_humidity'], 'sensor.inherited')
        er.async_get(self.hass).async_update_entity('sensor.inherited', area_id='exterieur')
        self.assertNotIn('indoor_humidity', self.proposals('salon'))

    async def test_mixed_station_indoor_probe_can_be_chosen_for_a_room(self):
        self.register('sensor.station_inside', 'temperature', area='exterieur')
        self.assertNotIn('indoor_temperature', self.proposals('salon'))
        cleaned, _ = self.service.validate(self.room(sources={'indoor_temperature': 'sensor.station_inside'}))
        self.assertEqual(cleaned['sources']['indoor_temperature'], 'sensor.station_inside')

    async def test_exterior_lists_outdoor_areas_first_and_flags_indoor_sensors(self):
        for i in range(8):
            self.register(f'sensor.aaa_plant_{i}', 'temperature', area=None)
        self.register('sensor.room', 'temperature')
        self.register('sensor.zz_station_outdoor', 'temperature', area='exterieur')
        found = catalog(self.hass, None, indoor_ids={'sensor.room'})['outdoor_temperature']
        self.assertEqual(found[0]['entity_id'], 'sensor.zz_station_outdoor')
        self.assertEqual(found[0]['warnings'], [])
        room = next(c for c in found if c['entity_id'] == 'sensor.room')
        self.assertIn('used_indoor', room['warnings'])
        mixed = catalog(self.hass, None, indoor_ids={'sensor.zz_station_outdoor'})['outdoor_temperature'][0]
        self.assertEqual(mixed['warnings'], ['used_indoor'])

    async def test_wind_gust_and_irradiance_are_exterior_sources(self):
        self.register('sensor.gust', 'wind_speed', area='exterieur', unit='m/s', value='14')
        self.register('sensor.solar', 'irradiance', area='exterieur', unit='W/m²', value='600')
        self.register('sensor.cumul', 'precipitation', area='exterieur', unit='mm', value='4')
        found = catalog(self.hass, None)
        self.assertEqual([c['entity_id'] for c in found['wind_gust']], ['sensor.gust'])
        self.assertEqual([c['entity_id'] for c in found['solar']], ['sensor.solar'])
        cleaned, _ = self.service.validate({'sources': {'wind_gust': {'entity_id': 'sensor.gust', 'adapter': 'direct'}}}, home=True)
        self.assertEqual(cleaned['sources']['wind_gust']['entity_id'], 'sensor.gust')

    async def test_outdoor_areas_are_flagged_so_they_are_never_offered_as_rooms(self):
        areas = {a['name']: a['outdoor'] for a in self.service.snapshot()['areas']}
        self.assertTrue(areas['Extérieur'])
        self.assertFalse(areas['Salon'])

    async def test_free_room_without_home_assistant_area(self):
        self.register('sensor.room', 'temperature')
        cleaned, _ = self.service.validate(self.room(area_id=None, name='Étage'))
        self.assertIsNone(cleaned['area_id'])
        flow = self.flow()
        result = await flow.async_step_user({'panel_config': self.room(area_id=None, name='Étage'), 'acknowledged': []})
        self.assertEqual(result['title'], 'Étage')
        self.assertTrue(flow.unique_id.startswith('room_'))
        with self.assertRaises(ValueError):
            self.service.validate(self.room(area_id=None, name='  '))

    async def test_openings_carry_exposure_type_and_shelter(self):
        self.register('sensor.room', 'temperature')
        self.register('binary_sensor.baie', 'window', unit=None, value='off')
        cleaned, _ = self.service.validate(self.room(windows=['binary_sensor.baie'],
            openings={'binary_sensor.baie': {'exposure': 'SO', 'kind': 'french', 'sheltered': True}}))
        self.assertEqual(cleaned['openings']['binary_sensor.baie'], {'exposure': 'SO', 'kind': 'french', 'sheltered': True})
        default, _ = self.service.validate(self.room(windows=['binary_sensor.baie']))
        self.assertEqual(default['openings']['binary_sensor.baie'], {'exposure': None, 'kind': 'window', 'sheltered': False})
        legacy, _ = self.service.validate(self.room(windows=['binary_sensor.baie'], rain_exposed=False))
        self.assertTrue(legacy['openings']['binary_sensor.baie']['sheltered'])
        for bad in ({'exposure': 'Sud'}, {'kind': 'garage'}, {'sheltered': 'oui'}):
            with self.assertRaises(ValueError):
                self.service.validate(self.room(windows=['binary_sensor.baie'], openings={'binary_sensor.baie': bad}))

    async def test_confirmations_are_remembered_only_while_they_apply(self):
        self.register('sensor.room', 'temperature')
        self.register('binary_sensor.fridge', 'door', unit=None, value='off')
        _, warnings = self.service.validate(self.room(windows=['binary_sensor.fridge']))
        remembered = self.service.ensure_acknowledged(warnings, ['windows:binary_sensor.fridge', 'co2:sensor.old'])
        self.assertEqual(remembered, ['windows:binary_sensor.fridge'])

    async def test_new_rooms_use_the_shared_exterior_and_old_rooms_keep_theirs(self):
        self.register('sensor.room', 'temperature')
        cleaned, _ = self.service.validate(self.room())
        self.assertTrue(cleaned['use_home'])
        self.assertTrue(self.service.uses_home(cleaned))
        old_room = {'sources': {'outdoor_temperature': 'sensor.outside'}}
        self.assertFalse(self.service.uses_home(old_room))
        self.service.home['configured'] = True
        self.assertTrue(self.service.uses_home(old_room))

    async def test_hidden_exterior_of_an_older_room_never_blocks_saving(self):
        self.register('sensor.room', 'temperature')
        self.register('sensor.station_outdoor', 'temperature', area='exterieur')
        cleaned, warnings = self.service.validate(self.room(sources={'indoor_temperature': 'sensor.room', 'outdoor_temperature': 'sensor.station_outdoor'}))
        self.assertEqual(cleaned['sources']['outdoor_temperature'], 'sensor.station_outdoor')
        self.assertEqual(warnings, [])

    async def test_overview_proposes_every_indoor_room_in_one_pass(self):
        ar.async_get(self.hass).async_create('Cuisine')
        ar.async_get(self.hass).async_create('Bureau')
        self.register('sensor.room', 'temperature')
        self.register('binary_sensor.salon_window', 'window', unit=None, value='off')
        self.register('sensor.kitchen', 'temperature', area='cuisine')
        self.register('sensor.desk_a', 'temperature', area='bureau')
        self.register('sensor.desk_b', 'temperature', area='bureau')
        self.register('sensor.station', 'temperature', area='exterieur')
        found = {a['name']: a for a in self.service.overview()['areas']}
        self.assertNotIn('Extérieur', found)
        self.assertEqual(found['Salon']['suggestions'], {'indoor_temperature': 'sensor.room', 'windows': ['binary_sensor.salon_window']})
        self.assertEqual(found['Cuisine']['suggestions']['indoor_temperature'], 'sensor.kitchen')
        self.assertNotIn('indoor_temperature', found['Bureau']['suggestions'])
        self.assertEqual(found['Bureau']['temperatures'], 2)
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        self.assertNotIn('salon', [a['area_id'] for a in self.service.overview()['areas']])

    def link_weather(self, sensors, hours=()):
        """A Niak Weather place as its published interface v1 presents it."""
        listeners = []
        class Api:
            version = 1
            def places(self): return [{"entry_id": "nw1", "title": "Gardanne"}]
            def station(self, entry_id=None): return {"entry_id": "nw1", "title": "Gardanne", "sensors": sensors}
            def hourly(self, entry_id=None): return list(hours)
            def add_listener(self, entry_id, cb): listeners.append(cb); return lambda: listeners.remove(cb)
        self.hass.data['niak_weather_api'] = Api()
        return listeners

    def niak_entity(self, domain, key, object_id, state, attrs=None):
        er.async_get(self.hass).async_get_or_create(domain, 'niak_weather', f'nw1_{key}', suggested_object_id=object_id)
        self.hass.states.async_set(f'{domain}.{object_id}', state, attrs or {})

    async def test_niak_weather_station_fills_the_exterior(self):
        self.register('sensor.gw_out', 'temperature', area='exterieur')
        self.register('sensor.gw_dir', 'wind_direction', area='exterieur', unit='°', value='270')
        self.link_weather({'temperature': 'sensor.gw_out', 'wind_bearing': 'sensor.gw_dir', 'pressure': 'sensor.p'})
        self.niak_entity('binary_sensor', 'pluie_en_cours', 'niak_weather_pluie_en_cours', 'off')
        self.niak_entity('sensor', 'qualite_air', 'niak_weather_qualite_air', '2')
        found = self.service.weather_proposal()
        self.assertEqual(found['title'], 'Gardanne')
        self.assertEqual(found['sources']['outdoor_temperature'], {'entity_id': 'sensor.gw_out', 'adapter': 'direct'})
        self.assertEqual(found['sources']['wind_bearing']['entity_id'], 'sensor.gw_dir')
        self.assertEqual(found['sources']['rain'], {'entity_id': 'binary_sensor.niak_weather_pluie_en_cours', 'adapter': 'binary'})
        self.assertEqual(found['sources']['pollution']['adapter'], 'niak_index')
        cleaned, _ = self.service.validate({'sources': found['sources'], 'weather': 'nw1'}, home=True)
        self.assertEqual(cleaned['weather'], 'nw1')
        with self.assertRaises(ValueError):
            self.service.validate({'sources': {}, 'weather': 'gone'}, home=True)

    async def test_niak_weather_knows_niak_comfort_listens(self):
        """Niak Weather 2.1+ is told who listens, so its settings show « Relié à Niak Confort »."""
        heard = []
        class Api:
            version = 1
            def add_listener(self, entry_id, update, brick=None): heard.append((entry_id, brick)); return lambda: None
        self.hass.data['niak_weather_api'] = Api()
        weather_link.listen(self.hass, 'nw1', lambda: None)
        self.assertEqual(heard, [('nw1', 'niak_comfort')])

    async def test_an_older_niak_weather_is_still_followed(self):
        listeners = self.link_weather({})
        stop = weather_link.listen(self.hass, 'nw1', lambda: None)
        self.assertEqual(len(listeners), 1)
        stop()
        self.assertEqual(listeners, [])

    async def test_without_niak_weather_nothing_is_invented(self):
        self.assertFalse(self.service.snapshot()['niak_weather']['installed'])
        with self.assertRaises(ValueError):
            self.service.weather_proposal()
        self.hass.data['niak_weather_api'] = type('Old', (), {'version': 2})()
        self.assertFalse(self.service.snapshot()['niak_weather']['installed'])

    async def test_outlook_reads_niak_weather_by_stable_keys(self):
        from custom_components.niak_comfort import weather_link
        self.link_weather({}, hours=[{'time': '2026-10-14T21:00:00+00:00', 'temperature': 18}])
        self.niak_entity('binary_sensor', 'orage', 'niak_weather_orage', 'on')
        self.niak_entity('sensor', 'vigilance', 'niak_weather_vigilance', 'orange')
        self.niak_entity('sensor', 'next_rain', 'niak_weather_pluie_dans', '0.5')
        self.niak_entity('sensor', 'maximale_demain', 'niak_weather_maximale_demain', '31.2')
        found = weather_link.outlook(self.hass, 'nw1')
        self.assertEqual((found['storm'], found['vigilance'], found['rain_in_hours'], found['tomorrow_max']), (True, 2, 0.5, 31.2))
        self.assertEqual(len(found['hours']), 1)
        self.assertEqual(weather_link.outlook(self.hass, None), {})
