"""Workspace tests from the actual beta-2 failures, without household data."""
from copy import deepcopy
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch
from test_ha_adapter import AdapterFixture
from homeassistant.helpers import area_registry as ar, entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.exceptions import Unauthorized
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from custom_components.niak_comfort.configuration import Configuration
from custom_components.niak_comfort.discovery import catalog, suggestions
from custom_components.niak_comfort.exterior import exterior_reading
from custom_components.niak_comfort.engine.assessment import assess
from custom_components.niak_comfort.engine.sources import normalize
from custom_components.niak_comfort.websocket import ws_configuration, ws_discover, ws_validate, ws_save, ws_remove


class WorkspaceTests(AdapterFixture):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service=Configuration(self.hass);await self.service.load()
        self.hass.config.language='fr'
        self.now=dt_util.utcnow()
        ar.async_get(self.hass).async_create('Cuisine')
        ar.async_get(self.hass).async_create('Extérieur')
        self.register('sensor.local','temperature',unit='°C')

    def register(self,entity_id,kind,area='salon',unit=None,value='21',platform='fixture',attrs=None,category=None):
        domain,name=entity_id.split('.')
        entry=er.async_get(self.hass).async_get_or_create(domain,platform,name,suggested_object_id=name,
            original_name=name,original_device_class=kind,entity_category=category)
        if area:er.async_get(self.hass).async_update_entity(entry.entity_id,area_id=area)
        self.hass.states.async_set(entity_id,value,{'device_class':kind,**({'unit_of_measurement':unit} if unit else {}),**(attrs or {})})
        return entry

    def config(self,**extra):
        return {'area_id':'salon','name':'Salon','sources':{'indoor_temperature':'sensor.local'},'windows':[], 'settings':{'minimum':20,'maximum':24},**extra}

    async def test_health_suggestions_keep_full_catalog_results_without_scanning_other_rooms(self):
        from custom_components.niak_comfort import health
        from custom_components.niak_comfort.discovery import candidate
        self.register('sensor.local_humidity','humidity',unit='%')
        self.register('sensor.cuisine_humidity','humidity',area='cuisine',unit='%')
        self.register('sensor.local_co2','carbon_dioxide',unit='ppm')
        self.register('binary_sensor.local_window','window',value='off')
        self.register('binary_sensor.fridge','door',value='off')
        config=self.config()
        self.hass.config_entries._entries[self.entry.entry_id]=self.entry
        self.hass.config_entries.async_update_entry(self.entry,data=config)
        self.service.entries=lambda:[self.entry]
        expected=suggestions(catalog(self.hass,'salon',config['sources']),'salon')
        expected={k:v for k,v in expected.items() if k in ('indoor_humidity','co2','windows','heating')}
        with patch.object(health,'get_configuration',AsyncMock(return_value=self.service)), \
             patch('custom_components.niak_comfort.discovery.candidate',wraps=candidate) as calls:
            facts=await health.facts(self.hass,'test')
        self.assertEqual(set(facts.rooms[0].available),set(expected))
        self.assertNotIn('binary_sensor.fridge',expected.get('windows',[]))
        # The configured room's health only requests four useful roles, on local entities.
        health_calls=[c for c in calls.call_args_list if len(c.args)>3 and c.args[3]=='salon']
        self.assertTrue(health_calls)
        self.assertTrue(all(c.args[1]!='sensor.cuisine_humidity' for c in health_calls))
        self.assertTrue(all(c.args[2] in ('indoor_humidity','co2','windows','heating') for c in health_calls))

    async def test_alias_in_another_room_is_explained_not_suggested(self):
        self.register('sensor.real_co2','carbon_dioxide',area='salon',unit='ppm',value='700')
        self.register('sensor.plant_co2','carbon_dioxide',area='cuisine',unit='ppm',platform='plant',attrs={'external_sensor':'sensor.real_co2'})
        found=catalog(self.hass,'cuisine')
        alias=next(c for c in found['co2'] if c['entity_id']=='sensor.plant_co2')
        self.assertIn('other_area',alias['warnings']);self.assertIn('alias',alias['warnings'])
        self.assertEqual(alias['provenance'][-1]['entity_id'],'sensor.real_co2')
        self.assertNotIn('co2',suggestions(found,'cuisine'))

    async def test_fridge_door_never_becomes_an_automatic_window(self):
        self.register('binary_sensor.physical_window','window',value='off')
        self.register('binary_sensor.fridge','door',value='off')
        found=catalog(self.hass,'salon')
        self.assertEqual(suggestions(found,'salon')['windows'],['binary_sensor.physical_window'])
        _,warnings=self.service.validate(self.config(windows=['binary_sensor.fridge']))
        with self.assertRaises(ValueError):self.service.ensure_acknowledged(warnings,[])
        self.service.ensure_acknowledged(warnings,['windows:binary_sensor.fridge'])

    async def test_ambiguous_measurements_and_absence_stay_unselected(self):
        self.register('sensor.second','temperature',unit='°C')
        self.assertNotIn('indoor_temperature',suggestions(catalog(self.hass,'salon'),'salon'))
        self.assertEqual(catalog(self.hass,'cuisine')['co2'],[])
        ar.async_get(self.hass).async_update('salon',temperature_entity_id='sensor.local')
        self.assertEqual(suggestions(catalog(self.hass,'salon'),'salon')['indoor_temperature'],'sensor.local')

    async def test_precipitation_rates_exclude_cumulative_rain_and_diagnostics(self):
        self.register('sensor.rain','precipitation_intensity',area='exterieur',unit='mm/h',value='0.8')
        self.register('sensor.rain_day','precipitation',area='exterieur',unit='mm',value='5')
        self.register('binary_sensor.sentinel','problem',category=EntityCategory.DIAGNOSTIC,value='off')
        found=catalog(self.hass)
        self.assertEqual([c['entity_id'] for c in found['rain']],['sensor.rain'])
        config,_=self.service.validate({'sources':{'rain':{'entity_id':'sensor.rain','adapter':'rain_rate'}}},home=True)
        reading=exterior_reading(self.hass.states.get('sensor.rain'),'rain',config['sources']['rain'],now=self.now,max_age=1800)
        self.assertTrue(reading.value)
        self.assertEqual(reading.detail,'rain_rate_observed')
        with self.assertRaises(ValueError):self.service.validate({'sources':{'rain':{'entity_id':'binary_sensor.sentinel','adapter':'binary'}}},home=True)

    async def test_atmo_daily_index_checks_the_precaution_and_blocks_above_threshold(self):
        attrs={'Libellé':'Moyen','Date de mise à jour':(self.now-timedelta(minutes=1)).isoformat()}
        self.register('sensor.atmo_day',None,area=None,value='2',platform='atmofrance',attrs=attrs)
        self.register('sensor.atmo_day_j_1',None,area=None,value='2',platform='atmofrance',attrs=attrs)
        self.assertEqual([c['entity_id'] for c in catalog(self.hass)['pollution']],['sensor.atmo_day'])
        spec={'entity_id':'sensor.atmo_day','adapter':'atmo_daily','block_from':4}
        r=exterior_reading(self.hass.states.get('sensor.atmo_day'),'pollution',spec,now=self.now,max_age=1800)
        self.assertEqual((r.quality,r.value),('estimated',False))
        ti=normalize('temperature',25,'°C',source='sensor.t',reported_at=self.now,now=self.now)
        te=normalize('temperature',18,'°C',source='sensor.te',reported_at=self.now,now=self.now)
        rain=normalize('rain',False,source='sensor.rain',reported_at=self.now,now=self.now)
        result=assess({'indoor_temperature':ti,'outdoor_temperature':te,'rain':rain,'pollution':r})
        # Below the chosen threshold the precaution is checked: it neither blocks nor makes the bilan partial.
        self.assertEqual(result.reason,'cooling_possible');self.assertFalse(result.partial)
        r=exterior_reading(self.hass.states.get('sensor.atmo_day'),'pollution',{**spec,'block_from':2},now=self.now,max_age=1800)
        self.assertIn('pollution',assess({'indoor_temperature':ti,'outdoor_temperature':te,'rain':rain,'pollution':r}).constraints)

    async def test_a_contact_unchanged_for_hours_is_still_known(self):
        later=self.now+timedelta(hours=5)
        contact=normalize('window','on',source='binary_sensor.w',reported_at=self.now,now=later,max_age=None)
        self.assertEqual((contact.quality,contact.value),('valid',True))
        self.assertEqual(normalize('temperature',20,'°C',source='sensor.t',reported_at=self.now,now=later).quality,'stale')

    async def test_atmo_index_published_yesterday_still_covers_today(self):
        local=dt_util.as_local(self.now).replace(hour=0,minute=5)
        def reading(published):
            self.register('sensor.atmo_day',None,area=None,value='2',platform='atmofrance',
                attrs={'Libellé':'Moyen','Date de mise à jour':published.isoformat()})
            spec={'entity_id':'sensor.atmo_day','adapter':'atmo_daily','block_from':4}
            return exterior_reading(self.hass.states.get('sensor.atmo_day'),'pollution',spec,now=local,max_age=1800)
        self.assertEqual(reading(local-timedelta(hours=9)).quality,'estimated')
        self.assertEqual(reading(local-timedelta(days=2)).quality,'stale')

    async def test_home_save_is_explicit_and_room_preservation_is_real(self):
        self.hass.config_entries._entries[self.entry.entry_id]=self.entry
        before=deepcopy(dict(self.entry.data))
        snapshot=self.service.snapshot()
        self.assertFalse(snapshot['home']['configured'])
        await self.service.save({'sources':{}},snapshot['revision'],home=True)
        self.assertTrue(self.service.home['configured'])
        self.assertEqual(dict(self.entry.data),before)
        self.assertFalse(self.service.snapshot()['rooms'][0]['config'].get('use_home',False))

    async def test_stale_revision_rejects_save_without_mutation(self):
        before=deepcopy(self.service.home)
        with self.assertRaises(ValueError):await self.service.save({'sources':{}},'old',home=True)
        self.assertEqual(self.service.home,before)

    async def test_invalid_payload_and_unconfirmed_ambiguity_never_modify_options(self):
        self.hass.config_entries._entries[self.entry.entry_id]=self.entry
        before=deepcopy(dict(self.entry.options))
        self.register('binary_sensor.fridge','door',value='off')
        with self.assertRaises(ValueError):await self.service.save(self.config(windows=['binary_sensor.fridge']),self.service.revision(),self.entry.entry_id)
        self.assertEqual(dict(self.entry.options),before)
        with self.assertRaises(ValueError):self.service.validate(self.config(settings={'minimum':30,'maximum':20}))

    async def test_existing_sources_can_be_removed_without_redetection(self):
        self.hass.config_entries._entries[self.entry.entry_id]=self.entry
        result=await self.service.save(self.config(),self.service.revision(),self.entry.entry_id)
        self.assertEqual(self.entry.options['sources'],{'indoor_temperature':'sensor.local'})
        self.assertNotIn('co2',result['rooms'][0]['config']['sources'])

    async def test_a_room_can_be_deleted_but_never_the_home_or_with_a_stale_revision(self):
        self.hass.config_entries._entries[self.entry.entry_id]=self.entry
        with patch.object(self.hass.config_entries,'async_remove',new=AsyncMock()) as remove:
            with self.assertRaises(ValueError):await self.service.remove(self.entry.entry_id,'old')
            with self.assertRaises(ValueError):await self.service.remove('missing',self.service.revision())
            home=ConfigEntry(version=1,minor_version=1,domain='niak_comfort',title='Mon logement',data={'home':True},source='user',options={},unique_id='niak_home',discovery_keys={},subentries_data=[])
            self.hass.config_entries._entries[home.entry_id]=home
            with self.assertRaises(ValueError):await self.service.remove(home.entry_id,self.service.revision())
            remove.assert_not_awaited()
            await self.service.remove(self.entry.entry_id,self.service.revision())
            remove.assert_awaited_once_with(self.entry.entry_id)

    async def test_rooms_join_the_shared_exterior_even_before_it_is_configured(self):
        cleaned,_=self.service.validate(self.config())
        self.assertTrue(cleaned['use_home'])
        await self.service.save({'sources':{}},self.service.revision(),home=True)
        self.assertTrue(self.service.uses_home(cleaned))

    async def test_all_configuration_commands_require_admin(self):
        conn=Mock(user=Mock(is_admin=False))
        for cmd,msg in ((ws_configuration,{'id':1}),(ws_discover,{'id':2}),(ws_validate,{'id':3}),(ws_save,{'id':4}),(ws_remove,{'id':5})):
            with self.assertRaises(Unauthorized):
                cmd(self.hass,conn,msg)
        self.assertNotIn('niak_comfort_configuration',self.hass.data)

    async def test_home_assistant_reference_is_proposed_but_alias_is_still_reviewed(self):
        self.register('sensor.reference','temperature',unit='°C',platform='template')
        ar.async_get(self.hass).async_update('salon',temperature_entity_id='sensor.reference')
        self.assertEqual(suggestions(catalog(self.hass,'salon'),'salon')['indoor_temperature'],'sensor.reference')
        self.register('sensor.reference','temperature',unit='°C',platform='template',attrs={'external_sensor':'sensor.local'})
        self.assertNotEqual(suggestions(catalog(self.hass,'salon'),'salon').get('indoor_temperature'),'sensor.reference')

    async def test_problem_binary_is_rejected_even_without_diagnostic_category(self):
        self.register('binary_sensor.battery','battery',value='off')
        with self.assertRaises(ValueError):
            self.service.validate({'sources':{'rain':{'entity_id':'binary_sensor.battery','adapter':'binary'}}},home=True)
