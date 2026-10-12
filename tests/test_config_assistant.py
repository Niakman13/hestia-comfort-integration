"""Real HA registries, fictitious rooms modeled after a mixed installation."""
from copy import deepcopy
import test_ha_adapter
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from custom_components.niak_comfort.config_flow import ComfortConfigFlow, ComfortOptionsFlow, proposals, room_candidates


class AssistantTests(test_ha_adapter.AdapterFixture):
    def register(self, entity_id, kind, area='salon', category=None, value='21', unit='°C', device_id=None):
        domain, name = entity_id.split('.')
        entry = er.async_get(self.hass).async_get_or_create(domain, 'fixture', name,
            suggested_object_id=name, original_device_class=kind, original_name=name, entity_category=category, device_id=device_id)
        if area:
            er.async_get(self.hass).async_update_entity(entry.entity_id, area_id=area)
        self.hass.states.async_set(entity_id, value, {'device_class':kind, 'unit_of_measurement':unit})
        return entry

    def flow(self):
        flow=ComfortConfigFlow(); flow.hass=self.hass; flow.context={'source':'user'}
        return flow

    def options(self):
        self.hass.config_entries._entries[self.entry.entry_id]=self.entry
        flow=ComfortOptionsFlow();flow.hass=self.hass;flow.handler=self.entry.entry_id
        return flow

    async def test_salon_default_and_area_name(self):
        flow=self.flow()
        result=await flow.async_step_user()
        marker=next(k for k in result['data_schema'].schema if k.schema=='area_id')
        self.assertEqual(marker.description['suggested_value'],'salon')
        await flow.async_step_user({'area_id':'salon'})
        self.assertEqual(flow.values['name'],'Salon')

    async def test_reference_beats_multiple_candidates_and_diagnostics_are_excluded(self):
        self.register('sensor.room','temperature')
        self.register('sensor.plant','temperature')
        self.register('sensor.device','temperature',category=EntityCategory.DIAGNOSTIC)
        self.assertNotIn('indoor_temperature',proposals(self.hass,'salon'))
        ar.async_get(self.hass).async_update('salon',temperature_entity_id='sensor.room')
        self.assertEqual(proposals(self.hass,'salon')['indoor_temperature'],'sensor.room')
        self.assertNotIn('sensor.device',room_candidates(self.hass,'salon')['indoor_temperature'])

    async def test_device_area_and_entity_override(self):
        ar.async_get(self.hass).async_create('Extérieur')
        self.hass.config_entries._entries[self.entry.entry_id]=self.entry
        device=dr.async_get(self.hass).async_get_or_create(config_entry_id=self.entry.entry_id,identifiers={('fixture','station')})
        dr.async_get(self.hass).async_update_device(device.id,area_id='salon')
        self.register('sensor.inherited','humidity',area=None,unit='%',device_id=device.id)
        self.assertEqual(proposals(self.hass,'salon')['indoor_humidity'],'sensor.inherited')
        er.async_get(self.hass).async_update_entity('sensor.inherited',area_id='exterieur')
        self.assertNotIn('indoor_humidity',proposals(self.hass,'salon'))

    async def test_mixed_station_can_be_chosen_outside_room(self):
        ar.async_get(self.hass).async_create('Extérieur')
        self.register('sensor.station_inside','temperature',area='exterieur')
        self.assertNotIn('indoor_temperature',proposals(self.hass,'salon'))
        flow=self.flow();await flow.async_step_user({'area_id':'salon'})
        result=await flow.async_step_indoor({'indoor_temperature':'sensor.station_inside'})
        self.assertEqual(result['step_id'],'outdoor')
        self.assertEqual(flow.values['sources']['indoor_temperature'],'sensor.station_inside')

    async def test_minimal_setup_and_summary_corrections(self):
        self.register('sensor.room','temperature')
        flow=self.flow();await flow.async_step_user({'area_id':'salon'})
        await flow.async_step_indoor({'indoor_temperature':'sensor.room'})
        await flow.async_step_outdoor({});await flow.async_step_windows({});await flow.async_step_heating({})
        result=await flow.async_step_preferences({'minimum':19,'maximum':24})
        self.assertEqual(result['step_id'],'review')
        await flow.async_step_indoor({'indoor_temperature':'sensor.room'})
        self.assertEqual((await flow.async_step_review())['description_placeholders']['co2'],'Not configured')
        result=await flow.async_step_finish({})
        self.assertEqual(result['data']['sources'],{'indoor_temperature':'sensor.room'})
        self.assertEqual(result['data']['settings']['minimum'],19)

    async def test_options_keep_manual_choices_and_clear_optional_sources(self):
        self.register('sensor.new','temperature')
        before=deepcopy(dict(self.entry.data))
        flow=self.options();result=await flow.async_step_init()
        self.assertEqual(result['type'],'menu')
        self.assertEqual(flow.values['sources']['indoor_temperature'],'sensor.inside')
        result=await flow.async_step_indoor({'indoor_temperature':'sensor.inside'})
        self.assertEqual(result['step_id'],'init')
        self.assertNotIn('co2',flow.values['sources'])
        await flow.async_step_init()
        self.assertNotIn('co2',flow.values['sources'])
        self.assertEqual(self.entry.data,before)
        result=await flow.async_step_finish({})
        self.assertNotIn('co2',result['data']['sources'])
        self.assertEqual(result['data']['sources']['outdoor_temperature'],'sensor.outside')

    async def test_explicit_research_never_overwrites_or_fills_without_selection(self):
        self.register('sensor.new_humidity','humidity',unit='%')
        self.register('sensor.new_temp','temperature')
        flow=self.options();await flow.async_step_init()
        await flow.async_step_discover({})
        self.assertNotIn('indoor_humidity',flow.values['sources'])
        await flow.async_step_discover({'indoor_humidity':True,'indoor_temperature':True})
        self.assertEqual(flow.values['sources']['indoor_humidity'],'sensor.new_humidity')
        self.assertEqual(flow.values['sources']['indoor_temperature'],'sensor.inside')

    async def test_next_room_reuses_exterior_but_not_rain(self):
        self.hass.config_entries._entries[self.entry.entry_id]=self.entry
        area=ar.async_get(self.hass).async_create('Chambre')
        flow=self.flow();await flow.async_step_user({'area_id':area.id})
        self.assertEqual(flow.values['sources']['outdoor_temperature'],'sensor.outside')
        self.assertNotIn('rain',flow.values['sources'])

    async def test_invalid_area_and_source_preserve_draft(self):
        flow=self.flow()
        self.assertEqual((await flow.async_step_user({'area_id':'missing'}))['errors'],{'area_id':'invalid_area'})
        await flow.async_step_user({'area_id':'salon'})
        before=deepcopy(flow.values)
        result=await flow.async_step_indoor({'indoor_temperature':'binary_sensor.rain'})
        self.assertEqual(result['errors'],{'indoor_temperature':'invalid_source'})
        self.assertEqual(flow.values,before)

    async def test_advanced_options_keep_temperature_preferences(self):
        flow=self.options();await flow.async_step_init()
        await flow.async_step_preferences({'minimum':18,'maximum':25})
        await flow.async_step_advanced({'humidity_high':65})
        self.assertEqual(flow.values['settings']['minimum'],18)
        self.assertEqual(flow.values['settings']['humidity_high'],65)

    async def test_already_configured_salon_is_not_proposed_again(self):
        self.hass.config_entries._entries[self.entry.entry_id]=self.entry
        result=await self.flow().async_step_user()
        marker=next(k for k in result['data_schema'].schema if k.schema=='area_id')
        self.assertFalse(marker.description and marker.description.get('suggested_value'))
