import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const temp=await mkdtemp(join(tmpdir(),'niak-setup-'));
await build({entryPoints:['model.ts'],bundle:true,platform:'node',format:'esm',outfile:join(temp,'model.mjs')});
const {newRoom,measurement,coverage,livingArea,exteriorSummary}=await import(pathToFileURL(join(temp,'model.mjs')));
after(()=>rm(temp,{recursive:true,force:true}));
test('new room copies proposals, describes each opening and freezes no data',()=>{
 const d={suggestions:{indoor_temperature:'sensor.room',windows:['binary_sensor.window']}};
 const room=newRoom({area_id:'salon',name:'Salon'},'',d);
 assert.deepEqual(room.sources,{indoor_temperature:'sensor.room'});
 assert.deepEqual(room.openings['binary_sensor.window'],{exposure:null,kind:'window',sheltered:false});
 room.windows.push('binary_sensor.second');assert.equal(d.suggestions.windows.length,1);
 assert.equal(room.sources.co2,undefined);
});
test('a free room has a name and no Home Assistant area',()=>{
 const room=newRoom(null,'Étage',{suggestions:{}});
 assert.equal(room.area_id,null);assert.equal(room.name,'Étage');assert.deepEqual(room.windows,[]);
});
test('the living room is found by its usual names but never outside or twice',()=>{
 const areas=[{area_id:'ext',name:'Extérieur',outdoor:true},{area_id:'sejour',name:'Séjour',outdoor:false}];
 assert.equal(livingArea(areas,new Set()).area_id,'sejour');
 assert.equal(livingArea(areas,new Set(['sejour'])),undefined);
});
test('exterior summary names what is configured',()=>{
 assert.equal(exteriorSummary({outdoor_temperature:{},rain:{}}),'Température, pluie');
 assert.equal(exteriorSummary({}),'Rien de configuré');
});
test('binary contact and ATMO daily values are readable and never 1 or off',()=>{
 assert.equal(measurement({available:true,value:'off',device_class:'window'}),'Fermé');
 assert.equal(measurement({available:true,value:'2',atmo_label:'Moyen'}),'Moyen · indice du jour');
 assert.equal(measurement({available:false}),'Temporairement indisponible');
});
test('coverage describes absent windows rather than implying a fault',()=>{
 assert.match(coverage({sources:{indoor_temperature:'sensor.room'},windows:[]}),/fenêtres non mesurées/);
 assert.match(coverage({sources:{indoor_temperature:'sensor.room'},windows:['a','b']}),/2 ouvrants/);
});
