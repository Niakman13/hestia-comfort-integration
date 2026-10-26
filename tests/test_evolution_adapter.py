"""Real HA adapter boundaries for blocks 7–9; no running household connection."""
from datetime import timedelta
from unittest.mock import patch
from types import SimpleNamespace
from test_ha_adapter import AdapterFixture
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from custom_components.niak_comfort.configuration import Configuration
from custom_components.niak_comfort.coordinator import ComfortCoordinator
from custom_components.niak_comfort.discovery import catalog, suggestions, candidate
from custom_components.niak_comfort.air_references import apply_air_references, AIR_DEFAULTS


class EvolutionAdapterTests(AdapterFixture):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = Configuration(self.hass)
        self.now = dt_util.utcnow()
        self.register('sensor.t', 'temperature', '°C', '25')
        self.register('binary_sensor.w', 'window', value='off')
        self.register('binary_sensor.occupied', 'occupancy', value='on')
        self.register('binary_sensor.motion', 'motion', value='off')
        self.register('sensor.pm', 'pm25', 'mg/m³', '0.03')
        self.register('sensor.voc', 'volatile_organic_compounds_parts', 'ppb', '200')
        self.register('sensor.light', 'illuminance', 'lx', '90')
        self.register('fan.purifier', None, value='on', attrs={'percentage': 40})
        self.register('cover.shutter', 'shutter', value='closed', attrs={'current_position': 0})
        self.register('switch.override', None, value='on')

    def register(self, eid, kind, unit=None, value='off', attrs=None):
        domain, name = eid.split('.')
        item = er.async_get(self.hass).async_get_or_create(domain, 'fixture', name, suggested_object_id=name, original_device_class=kind)
        er.async_get(self.hass).async_update_entity(item.entity_id, area_id='salon')
        self.hass.states.async_set(eid, value, {'device_class': kind, 'unit_of_measurement': unit, **(attrs or {})})

    def config(self, **extra):
        return {'name': 'Salon', 'area_id': 'salon', 'sources': {'indoor_temperature': 'sensor.t', 'pm25': 'sensor.pm', 'voc': 'sensor.voc', 'illuminance': 'sensor.light', 'purifier': 'fan.purifier'}, 'windows': ['binary_sensor.w'], 'presence': ['binary_sensor.occupied', 'binary_sensor.motion'], 'openings': {'binary_sensor.w': {'shutter': 'connected', 'cover_entity': 'cover.shutter', 'override_entity': 'switch.override', 'width': 1.2, 'height': 1.4}}, 'evolution': {'voc_threshold': {'value': 300, 'unit': 'ppb'}, 'presence_delay_minutes': 5}, **extra}

    def coordinator(self, config=None):
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        self.hass.config_entries.async_update_entry(self.entry, options=config or self.config())
        return ComfortCoordinator(self.hass, self.entry)

    async def test_zigbee2mqtt_voc_index_without_class_is_local_selectable_and_interpreted(self):
        registry = er.async_get(self.hass)
        # Reproduce the live IKEA discovery metadata, using an arbitrary user name.
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        device = dr.async_get(self.hass).async_get_or_create(
            config_entry_id=self.entry.entry_id, identifiers={('mqtt', 'fixture-voc')},
            manufacturer='IKEA', model='VINDSTYRKA air quality and humidity sensor')
        dr.async_get(self.hass).async_update_device(device.id, area_id='salon')
        item = registry.async_get_or_create('sensor', 'mqtt',
            '0x0011223344556677_voc_index_zigbee2mqtt', suggested_object_id='renamed_sensor', device_id=device.id)
        self.assertIsNone(item.area_id)  # The room is inherited from the device.
        self.hass.states.async_set(item.entity_id, '144', {'state_class': 'measurement', 'friendly_name': 'Capteur renommé'})
        found = catalog(self.hass, 'salon')
        self.assertIn(item.entity_id, [c['entity_id'] for c in found['voc']])
        # Two local VOC sensors must remain a choice. Once the other is elsewhere,
        # this index becomes the room's sole automatic suggestion.
        self.assertNotIn('voc', suggestions(found, 'salon'))
        registry.async_update_entity('sensor.voc', area_id=None)
        self.assertEqual(suggestions(catalog(self.hass, 'salon'), 'salon')['voc'], item.entity_id)
        selected = candidate(self.hass, item.entity_id, 'voc', 'salon')
        self.assertTrue(selected['local'])
        self.assertEqual(selected['device_class'], 'volatile_organic_compounds_index')
        self.assertIsNone(selected['unit'])
        self.assertEqual(selected['voc_reference'], {'id': 'sensirion_index', 'value': 150, 'unit': ''})
        # A unitless index alone is not enough to apply Sensirion's example.
        dr.async_get(self.hass).async_update_device(device.id, manufacturer='Other')
        self.assertIsNone(candidate(self.hass, item.entity_id, 'voc', 'salon')['voc_reference'])
        dr.async_get(self.hass).async_update_device(device.id, manufacturer='IKEA')
        legacy = self.config(evolution={'voc_threshold': {'value': 200, 'unit': ''}})
        legacy['sources']['voc'] = item.entity_id
        self.hass.config_entries.async_update_entry(self.entry, options=legacy)
        self.hass.states.async_remove(item.entity_id)
        self.assertTrue(apply_air_references(self.hass, self.entry))
        self.assertEqual(self.entry.options['evolution']['voc_threshold'], {'value': 150, 'unit': ''})
        customized = {**self.entry.options, 'evolution': {'voc_threshold': {'value': 180, 'unit': ''}}}
        self.hass.config_entries.async_update_entry(self.entry, options=customized)
        self.assertFalse(apply_air_references(self.hass, self.entry))
        self.assertEqual(self.entry.options['evolution']['voc_threshold']['value'], 180)
        cleared = {**self.entry.options, 'evolution': {}}
        self.hass.config_entries.async_update_entry(self.entry, options=cleared)
        self.assertFalse(apply_air_references(self.hass, self.entry))
        self.assertNotIn('voc_threshold', self.entry.options['evolution'])
        self.hass.states.async_set(item.entity_id, '144', {'state_class': 'measurement'})
        config = self.config(evolution={'voc_threshold': {'value': 150, 'unit': ''}})
        config['sources']['voc'] = item.entity_id
        cleaned, _ = self.service.validate(config)
        coordinator = self.coordinator(cleaned)
        view = await coordinator._async_update_data()
        self.assertEqual(view['observations']['voc']['value'], 144)
        self.assertIsNone(view['observations']['voc']['unit'])
        self.assertEqual(view['assessment']['features']['air']['voc_status'], 'ok')
        self.hass.states.async_set(item.entity_id, '180', {'state_class': 'measurement'})
        view = await coordinator._async_update_data()
        self.assertEqual(view['assessment']['features']['air']['voc_status'], 'high')
        self.assertIn('air', view['assessment']['needs'])

    async def test_a_voc_name_or_unrelated_mqtt_id_does_not_prove_an_index(self):
        coordinator = self.coordinator()
        for platform, uid in [('fixture', '0x0011223344556677_voc_index_zigbee2mqtt'), ('mqtt', 'unrelated_voc_index')]:
            item = er.async_get(self.hass).async_get_or_create('sensor', platform, uid)
            self.hass.states.async_set(item.entity_id, '144', {'friendly_name': 'IKEA VOC index'})
            self.assertIsNone(candidate(self.hass, item.entity_id, 'voc'))
            self.assertFalse(coordinator._reading(item.entity_id, 'voc', self.now).usable)

    async def test_atmo_pollen_is_not_a_room_voc_even_with_a_voc_device_class(self):
        item = er.async_get(self.hass).async_get_or_create('sensor', 'atmofrance',
            'fixture-Concentration Ambroisie', suggested_object_id='pollen_misclassified')
        self.hass.states.async_set(item.entity_id, '0.0', {
            'device_class': 'volatile_organic_compounds', 'unit_of_measurement': 'μg/m³'})
        self.assertIsNone(candidate(self.hass, item.entity_id, 'voc'))
        self.assertFalse(self.coordinator()._reading(item.entity_id, 'voc', self.now).usable)

    async def test_discovery_and_presence_lists(self):
        found = catalog(self.hass, 'salon')
        for key, eid in [('pm25', 'sensor.pm'), ('voc', 'sensor.voc'), ('illuminance', 'sensor.light'), ('purifier', 'fan.purifier'), ('covers', 'cover.shutter'), ('shutter_override', 'switch.override')]:
            self.assertIn(eid, [c['entity_id'] for c in found[key]])
        self.assertEqual(set(suggestions(found, 'salon')['presence']), {'binary_sensor.occupied', 'binary_sensor.motion'})

    async def test_air_references_migrate_once_then_preserve_personal_edits(self):
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        old = self.config(settings={'minimum': 19, 'maximum': 25, 'co2_action': 1300, 'gust_max': 55})
        self.hass.config_entries.async_update_entry(self.entry, options=old)
        self.assertTrue(apply_air_references(self.hass, self.entry))
        for key, value in AIR_DEFAULTS.items():
            self.assertEqual(self.entry.options['settings'][key], value)
        self.assertEqual(self.entry.options['settings']['minimum'], 19)
        self.assertEqual(self.entry.options['settings']['gust_max'], 55)
        # Unknown ppb device: preserve its configured threshold, never use index 150.
        self.assertEqual(self.entry.options['evolution']['voc_threshold'], {'value': 300, 'unit': 'ppb'})
        customized = {**self.entry.options, 'settings': {**self.entry.options['settings'], 'co2_action': 1100}}
        self.hass.config_entries.async_update_entry(self.entry, options=customized)
        self.assertFalse(apply_air_references(self.hass, self.entry))
        self.assertEqual(self.entry.options['settings']['co2_action'], 1100)
        saved, _ = self.service.validate(customized)
        self.assertEqual(saved['air_reference_version'], 1)
        self.assertEqual(saved['settings']['co2_action'], 1100)

    async def test_new_saved_room_gets_references_unless_explicitly_customized(self):
        config = self.config(settings={'minimum': 20, 'maximum': 24})
        cleaned, _ = self.service.validate(config)
        for key, value in AIR_DEFAULTS.items():
            self.assertEqual(cleaned['settings'][key], value)

    async def test_configuration_roundtrip_and_invalid_dimensions(self):
        cleaned, _ = self.service.validate(self.config())
        self.assertEqual(cleaned['presence'], self.config()['presence'])
        self.assertEqual(cleaned['evolution']['voc_threshold']['unit'], 'ppb')
        self.assertEqual(cleaned['openings']['binary_sensor.w']['cover_entity'], 'cover.shutter')
        for bad in (True, -1, float('nan'), 200):
            with self.assertRaises(ValueError):
                self.service.validate(self.config(openings={'binary_sensor.w': {'width': bad}}))
        for bad in ('binary_sensor.motion', ['sensor.t']):
            with self.assertRaises(ValueError): self.service.validate(self.config(presence=bad))
        for bad in ({'glazing_factor': 2}, {'presence_delay_minutes': -1}, {'voc_threshold': {'value': 2, 'unit': 'ppm'}}, {'voc_threshold': {'value': True, 'unit': 'ppb'}}):
            with self.assertRaises(ValueError): self.service.validate(self.config(evolution=bad))

    async def test_manual_shutter_needs_no_cover(self):
        cleaned, _ = self.service.validate(self.config(openings={'binary_sensor.w': {'shutter': 'manual'}}))
        self.assertEqual(cleaned['openings']['binary_sensor.w']['shutter'], 'manual')
        self.assertNotIn('cover_entity', cleaned['openings']['binary_sensor.w'])

    async def test_readings_and_duration_context(self):
        coord = self.coordinator()
        calls = []
        def capture(*args, **kwargs):
            calls.append((args, kwargs)); return SimpleNamespace(to_dict=lambda: {})
        with patch('custom_components.niak_comfort.coordinator.assess', side_effect=capture):
            data = await coord._async_update_data()
        obs = data['observations']
        self.assertEqual(obs['pm25']['value'], 30)
        self.assertEqual(obs['voc']['unit'], 'ppb')
        self.assertEqual(obs['presence:binary_sensor.motion']['detail'], 'motion')
        self.assertEqual(obs['cover:binary_sensor.w']['value'], 0)
        self.assertEqual(obs['purifier_speed']['value'], 40)
        self.assertIsNone(calls[-1][1]['context']['opening_minutes']['binary_sensor.w'])

    async def test_transition_timers_never_use_reported_time_or_recovery(self):
        coord = self.coordinator()
        async def event(eid, value, old_value):
            self.hass.states.async_set(eid, value, dict(self.hass.states.get(eid).attributes))
            await coord._changed(SimpleNamespace(data={'entity_id': eid, 'old_state': SimpleNamespace(state=old_value), 'new_state': self.hass.states.get(eid)}))
        with patch.object(coord, 'async_request_refresh'), patch('custom_components.niak_comfort.coordinator.dt_util.utcnow', return_value=self.now):
            await event('binary_sensor.w', 'on', 'off')
            await event('binary_sensor.occupied', 'off', 'on')
            await event('binary_sensor.motion', 'off', 'on')
        with patch('custom_components.niak_comfort.coordinator.dt_util.utcnow', return_value=self.now + timedelta(minutes=12)):
            context = coord._context(self.now + timedelta(minutes=12), {})
        self.assertEqual(context['opening_minutes']['binary_sensor.w'], 12)
        # Read from Home Assistant's own last change (right after a restart too): to the second.
        self.assertAlmostEqual(context['presence_off_minutes']['binary_sensor.occupied'], 12, delta=0.02)
        self.assertIsNone(context['presence_off_minutes']['binary_sensor.motion'])
        with patch.object(coord, 'async_request_refresh'):
            await event('binary_sensor.w', 'unavailable', 'on')
            await event('binary_sensor.w', 'on', 'unavailable')
        self.assertIsNone(coord._context(self.now, {})['opening_minutes']['binary_sensor.w'])

    async def test_histories_are_bounded_and_only_usable(self):
        coord = self.coordinator()
        from custom_components.niak_comfort.engine.sources import Reading
        for index in range(800):
            coord._context(self.now + timedelta(seconds=index * 30), {'indoor_temperature': Reading(25, 'valid', received_at=(self.now + timedelta(seconds=index * 30)).isoformat())})
        self.assertLessEqual(len(coord._context(self.now + timedelta(seconds=800 * 30), {})['temperature_history']), 360)

    async def test_startup_history_does_not_backdate_coverage(self):
        coord = self.coordinator()
        from custom_components.niak_comfort.engine.sources import Reading
        previous = (self.now - timedelta(minutes=20)).isoformat()
        context = coord._context(self.now, {'indoor_temperature': Reading(25, 'valid', received_at=previous)})
        self.assertEqual(context['temperature_history'], [(self.now.isoformat(), 25)])
        context = coord._context(self.now + timedelta(minutes=2), {'indoor_temperature': Reading(25, 'valid', received_at=previous)})
        self.assertEqual(len(context['temperature_history']), 1)

    async def test_metadata_callbacks_and_sun_are_observed(self):
        from homeassistant.config_entries import ConfigEntryState
        coord = self.coordinator()
        self.entry._async_set_state(self.hass, ConfigEntryState.SETUP_IN_PROGRESS, None)
        with patch('custom_components.niak_comfort.coordinator.async_track_state_change_event', return_value=lambda: None) as track:
            await coord.async_start()
        ids = track.call_args.args[1]
        for eid in ('cover.shutter', 'switch.override', 'binary_sensor.occupied', 'binary_sensor.motion', 'sun.sun', 'fan.purifier'):
            self.assertIn(eid, ids)
        await self.entry._async_process_on_unload(self.hass)
        await coord.async_shutdown()

    async def test_health_handles_lost_optional_sources(self):
        from custom_components.niak_comfort.health import facts, report
        from custom_components.niak_comfort.configuration import DATA_CONFIG
        self.coordinator()
        self.hass.data[DATA_CONFIG] = self.service
        self.hass.states.async_set('sensor.pm', 'unavailable')
        result = report(await facts(self.hass, 'test'))
        self.assertTrue(any('PM2.5' in line['text'] for line in result['todo']))

    async def test_unitless_voc_requires_explicit_index_class(self):
        self.register('sensor.voc_mass', 'volatile_organic_compounds', value='40')
        self.register('sensor.voc_index', 'volatile_organic_compounds_index', value='40')
        found = [c['entity_id'] for c in catalog(self.hass)['voc']]
        self.assertNotIn('sensor.voc_mass', found)
        self.assertIn('sensor.voc_index', found)
        coord = self.coordinator()
        self.assertFalse(coord._reading('sensor.voc_mass', 'voc', self.now).usable)
        self.assertTrue(coord._reading('sensor.voc_index', 'voc', self.now).usable)
        self.assertIsNone(coord._reading('sensor.voc_index', 'voc', self.now).unit)

    async def test_shutter_source_warnings_use_discovery_roles(self):
        from homeassistant.helpers import area_registry as ar
        ar.async_get(self.hass).async_create('Bureau')
        er.async_get(self.hass).async_update_entity('cover.shutter', area_id='bureau')
        er.async_get(self.hass).async_update_entity('switch.override', area_id='bureau')
        _, warnings = self.service.validate(self.config())
        keys = {w['key'] + ':' + w['entity_id'] for w in warnings}
        self.assertIn('covers:cover.shutter', keys)
        self.assertIn('shutter_override:switch.override', keys)
        with self.assertRaises(ValueError): self.service.ensure_acknowledged(warnings, [])
        self.service.ensure_acknowledged(warnings, sorted(keys))

    async def test_unitless_index_threshold_is_explicit_and_cannot_follow_concentration(self):
        self.register('sensor.voc', 'volatile_organic_compounds_index', value='200')
        config = self.config(evolution={'voc_threshold': {'value': 100, 'unit': ''}})
        cleaned, _ = self.service.validate(config)
        self.assertEqual(cleaned['evolution']['voc_threshold']['unit'], '')
        coordinator = self.coordinator(cleaned)
        assessment = (await coordinator._async_update_data())['assessment']
        self.assertEqual(assessment['features']['air']['voc_status'], 'high')
        # The same unitless threshold must not apply when the entity changes nature.
        self.register('sensor.voc', 'volatile_organic_compounds_parts', 'ppb', '200')
        with self.assertRaises(ValueError): self.service.validate(config)
        assessment = (await coordinator._async_update_data())['assessment']
        self.assertEqual(assessment['features']['air']['voc_status'], 'uninterpreted')

    async def test_on_off_purifier_without_speed_does_not_make_room_partial(self):
        self.hass.states.async_set('sensor.t', '21', {'device_class': 'temperature', 'unit_of_measurement': '°C'})
        base = self.config(sources={'indoor_temperature': 'sensor.t', 'outdoor_temperature': 'sensor.outside', 'rain': 'binary_sensor.rain', 'pollution': 'binary_sensor.pollution', 'purifier': 'fan.purifier'}, windows=[], openings={}, presence=[])
        coordinator = self.coordinator(base)
        for state in ('on', 'off'):
            self.hass.states.async_set('fan.purifier', state, {})
            data = await coordinator._async_update_data()
            self.assertNotIn('purifier_speed', data['observations'])
            self.assertIsNone(data['assessment']['features']['air']['purifier']['speed'])
            self.assertFalse(data['assessment']['partial'])
        self.hass.states.async_set('fan.purifier', 'unavailable')
        data = await coordinator._async_update_data()
        self.assertIn('purifier', data['assessment']['missing'])

    async def test_cover_state_without_position_does_not_make_room_partial(self):
        self.hass.states.async_set('sensor.t', '21', {'device_class': 'temperature', 'unit_of_measurement': '°C'})
        base = self.config(sources={'indoor_temperature': 'sensor.t', 'outdoor_temperature': 'sensor.outside', 'rain': 'binary_sensor.rain', 'pollution': 'binary_sensor.pollution'}, presence=[], openings={'binary_sensor.w': {'shutter': 'connected', 'cover_entity': 'cover.shutter'}})
        coordinator = self.coordinator(base)
        for state in ('open', 'closed'):
            self.hass.states.async_set('cover.shutter', state, {})
            data = await coordinator._async_update_data()
            self.assertNotIn('cover:binary_sensor.w', data['observations'])
            self.assertEqual(data['observations']['cover_state:binary_sensor.w']['value'], state)
            self.assertIsNone(data['assessment']['features']['shutters'][0]['position'])
            self.assertFalse(data['assessment']['partial'])
        self.hass.states.async_set('cover.shutter', 'unavailable')
        data = await coordinator._async_update_data()
        self.assertIn('cover_state:binary_sensor.w', data['assessment']['missing'])
