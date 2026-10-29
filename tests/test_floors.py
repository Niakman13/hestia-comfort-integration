"""Floors and single-level homes share the same conservative room decisions."""
from test_home import view, opening
from engine.home import synthesis
from test_ha_adapter import AdapterFixture
from homeassistant.helpers import area_registry as ar, floor_registry as fr
from custom_components.hestia_comfort.floors import room_floor, floor_catalog
from custom_components.hestia_comfort.configuration import Configuration
import unittest


def room(name, t=27, floor_id='upper', level=1, exposure='E', wind=None, opened=False):
    v = view(name, name, 'action', 'ouvrir', t, ('cool',), [opening(name, opened, exposure)], outdoor=20)
    v['floor'] = {'floor_id': floor_id, 'name': floor_id, 'level': level} if floor_id else None
    v['assessment'].update(opportunities=['cool'], constraints=[])
    v['assessment']['openings'][0]['wind_side'] = wind
    return v


class FloorSynthesis(unittest.TestCase):
    def test_coverage_and_hottest_do_not_hide_a_missing_room(self):
        rooms = [room('a'), room('b', 29), room('c')]
        rooms[2]['observations']['indoor_temperature']['quality'] = 'stale'
        f = synthesis(rooms)['floors'][0]
        self.assertEqual((f['mean'], f['measured'], f['total'], f['hottest']['title']), (28, 2, 3, 'b'))
        self.assertTrue(f['partial'])

    def test_all_missing_and_non_finite_are_unknown(self):
        for value in (None, float('nan'), float('inf'), True):
            v = room('a'); v['observations']['indoor_temperature']['value'] = value
            self.assertIsNone(synthesis([v])['floors'][0]['mean'])

    def test_levels_order_basement_and_unassigned_last(self):
        result = synthesis([room('a'), room('b', floor_id='basement', level=-1), room('c', floor_id=None)])
        self.assertEqual([f['floor_id'] for f in result['floors']], ['basement', 'upper', None])

    def test_identical_names_do_not_merge_ids(self):
        a,b=room('a'),room('b',floor_id='other');b['floor']['name']=a['floor']['name']
        self.assertEqual(len(synthesis([a,b])['floors']),2)

    def test_plain_pied_retains_priority_and_cross_ventilation(self):
        result = synthesis([room('a', exposure='O'), room('b', 28)])
        self.assertEqual(result['start_with'], 'b')
        self.assertEqual(result['ventilation']['kind'], 'cross')
        self.assertIsNone(result['floor_contrast'])

    def test_no_floor_does_not_mean_plain_pied_or_block_cross(self):
        result = synthesis([room('a', floor_id=None, exposure='O'), room('b', floor_id=None)])
        self.assertIsNone(result['floors'][0]['floor_id'])
        self.assertEqual(result['ventilation']['kind'], 'cross')

    def test_stack_even_without_wind_and_warmest_can_be_downstairs(self):
        result = synthesis([room('a', 29, 'lower', 0), room('b')])
        self.assertEqual(result['start_floor']['floor_id'], 'lower')
        self.assertEqual(result['ventilation']['kind'], 'stack')
        self.assertEqual(result['floor_contrast']['warmer'], 'lower')
        self.assertFalse(result['ventilation']['path_confirmed'])

    def test_same_level_number_does_not_create_stack(self):
        result = synthesis([room('a', floor_id='x'), room('b', floor_id='y')])
        self.assertIsNone(result['ventilation'])

    def test_constraints_and_incomplete_data_veto_house_advice(self):
        for change in ({'constraints':['gust']},{'constraints':['heating_running']},{'partial':True},{'action':'fermer'}, {'opportunities':[]}):
            a,b=room('a',floor_id='lower',level=0),room('b')
            a['assessment'].update(change)
            self.assertIsNone(synthesis([a,b])['ventilation'])

    def test_hot_exterior_cold_room_or_unknown_contact_veto_pair(self):
        for field, value in [('outside',30),('inside',20.5),('contact',None)]:
            a,b=room('a',floor_id='lower',level=0),room('b')
            if field=='contact':a['assessment']['openings'][0]['open']=value
            else:a['observations']['outdoor_temperature' if field=='outside' else 'indoor_temperature']['value']=value
            self.assertIsNone(synthesis([a,b])['ventilation'])

    def test_wind_combines_only_with_upward_flow(self):
        a,b=room('a',floor_id='lower',level=0,exposure='O',wind='windward'),room('b',wind='leeward')
        self.assertEqual(synthesis([a,b])['ventilation']['kind'],'combined')
        a['assessment']['openings'][0]['wind_side']='leeward';b['assessment']['openings'][0]['wind_side']='windward'
        self.assertEqual(synthesis([a,b])['ventilation']['kind'],'cross')

    def test_engaged_keeps_heat_visible(self):
        result=synthesis([room('a',floor_id='lower',level=0,opened=True),room('b',opened=True)])
        self.assertTrue(result['ventilation']['engaged'])
        self.assertEqual(result['level'],'action')


class FloorRegistryTests(AdapterFixture):
    async def test_area_is_authoritative_and_changes_are_live(self):
        registry=fr.async_get(self.hass)
        low=registry.async_create('Bas',level=0); high=registry.async_create('Haut',level=1)
        ar.async_get(self.hass).async_update('salon',floor_id=low.floor_id)
        config={'area_id':'salon','floor_id':high.floor_id}
        self.assertEqual(room_floor(self.hass,config)['floor_id'],low.floor_id)
        ar.async_get(self.hass).async_update('salon',floor_id=high.floor_id)
        registry.async_update(high.floor_id,name='Premier')
        self.assertEqual(room_floor(self.hass,config)['name'],'Premier')
        registry.async_delete(high.floor_id)
        self.assertIsNone(room_floor(self.hass,config))

    async def test_free_room_optional_floor_validation(self):
        f=fr.async_get(self.hass).async_create('RDC',level=0)
        service=Configuration(self.hass)
        from unittest.mock import patch
        config={'name':'Libre','sources':{'indoor_temperature':'sensor.inside'},'floor_id':f.floor_id}
        with patch('custom_components.hestia_comfort.configuration.candidate',return_value={'warnings':[]}):
            clean,_=service.validate(config);self.assertEqual(clean['floor_id'],f.floor_id)
            clean,_=service.validate({**config,'floor_id':None});self.assertIsNone(clean['floor_id'])
            with self.assertRaises(ValueError):service.validate({**config,'floor_id':'removed'})
        self.assertEqual(floor_catalog(self.hass)[0]['level'],0)

    async def test_free_floor_is_saved_and_can_be_cleared(self):
        from unittest.mock import patch
        floor = fr.async_get(self.hass).async_create('Premier', level=1)
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        service = Configuration(self.hass)
        payload = {'name': 'Libre', 'area_id': None, 'floor_id': floor.floor_id,
                   'sources': {'indoor_temperature': 'sensor.inside'}}
        with patch('custom_components.hestia_comfort.configuration.candidate', return_value={'warnings': []}):
            saved = await service.save(payload, service.revision(), self.entry.entry_id)
            self.assertEqual(self.entry.options['floor_id'], floor.floor_id)
            self.assertEqual(saved['rooms'][0]['floor']['name'], 'Premier')
            await service.save({**payload, 'floor_id': None}, service.revision(), self.entry.entry_id)
            self.assertIsNone(self.entry.options['floor_id'])
            self.assertIsNone(room_floor(self.hass, dict(self.entry.options)))

