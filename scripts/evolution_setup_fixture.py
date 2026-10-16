"""Export real HA configuration/discovery payloads for the local UI bench."""
import asyncio,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntries,ConfigEntry,ConfigEntryState
from homeassistant.helpers import area_registry as ar,floor_registry as fr,device_registry as dr,entity_registry as er
from custom_components.niak_comfort.configuration import Configuration

async def main():
 with tempfile.TemporaryDirectory() as tmp:
  hass=HomeAssistant(tmp);hass.config_entries=ConfigEntries(hass,{})
  await hass.config_entries.async_initialize();await fr.async_load(hass);await ar.async_load(hass);dr.async_setup(hass);await dr.async_load(hass);await er.async_load(hass)
  area=ar.async_get(hass).async_create('Salon');floor=fr.async_get(hass).async_create('Rez-de-chaussée',level=0);ar.async_get(hass).async_update(area.id,floor_id=floor.floor_id)
  rows=[('sensor.demo_temperature','temperature','27','°C'),('sensor.demo_humidity','humidity','50','%'),('sensor.demo_co2','carbon_dioxide','850','ppm'),('sensor.demo_pm25','pm25','18','µg/m³'),('sensor.demo_voc','volatile_organic_compounds_index','160',None),('sensor.demo_lux','illuminance','350','lx'),('binary_sensor.demo_window','window','off',None),('binary_sensor.demo_presence','occupancy','on',None),('cover.demo_shutter','shutter','open',None),('fan.demo_purifier',None,'on',None),('switch.demo_auto',None,'on',None),('binary_sensor.demo_override',None,'off',None)]
  # Entity metadata, not names, defines the offered role.
  for eid,dc,value,unit in rows:
   domain,obj=eid.split('.')
   entity=er.async_get(hass).async_get_or_create(domain,'demo',obj,suggested_object_id=obj,original_name=obj.replace('demo_','').replace('_',' ').title(),original_device_class=dc)
   er.async_get(hass).async_update_entity(entity.entity_id,area_id=area.id)
   attrs={**({'device_class':dc} if dc else {}),**({'unit_of_measurement':unit} if unit else {})}
   if domain=='cover':attrs['current_position']=60
   if domain=='fan':attrs['percentage']=65
   hass.states.async_set(eid,value,attrs)
  config={'name':'Salon','area_id':area.id,'sources':{'indoor_temperature':'sensor.demo_temperature','indoor_humidity':'sensor.demo_humidity','co2':'sensor.demo_co2'},'windows':['binary_sensor.demo_window'],'openings':{'binary_sensor.demo_window':{'exposure':'O','kind':'window','sheltered':False,'shutter':'manual'}},'settings':{'minimum':20,'maximum':24},'presence':[],'evolution':{}}
  service=Configuration(hass);cleaned,_=service.validate(config)
  entry=ConfigEntry(domain='niak_comfort',title='Salon',unique_id=area.id,version=1,minor_version=1,source='user',data=cleaned,options={},discovery_keys={},subentries_data=[])
  hass.config_entries._entries[entry.entry_id]=entry;entry._async_set_state(hass,ConfigEntryState.LOADED,None)
  result={'snapshot':service.snapshot(),'discovery':service.discover(area.id,entry.entry_id)}
  (ROOT/'card/preview/evolution/setup-fixture.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
  await hass.async_stop()
asyncio.run(main())
