import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const temp=await mkdtemp(join(tmpdir(),'niak-setup-'));
await build({entryPoints:['model.ts'],bundle:true,platform:'node',format:'esm',outfile:join(temp,'model.mjs')});
const {newRoom,measurement,coverage}=await import(pathToFileURL(join(temp,'model.mjs')));
after(()=>rm(temp,{recursive:true,force:true}));
test('new room copies proposals without mixing them with exterior and freezes no data',()=>{
 const d={suggestions:{indoor_temperature:'sensor.room',windows:['binary_sensor.window']}};
 const room=newRoom({area_id:'salon',name:'Salon'},d,true);
 assert.deepEqual(room.sources,{indoor_temperature:'sensor.room'});assert.equal(room.use_home,true);
 room.windows.push('binary_sensor.second');assert.equal(d.suggestions.windows.length,1);
 assert.equal(room.sources.co2,undefined);
});
test('binary contact and ATMO daily values are readable and never 1 or off',()=>{
 assert.equal(measurement({available:true,value:'off',device_class:'window'}),'Fermé');
 assert.equal(measurement({available:true,value:'2',atmo_label:'Moyen'}),'Moyen · indice du jour');
 assert.equal(measurement({available:false}),'Temporairement indisponible');
});
test('coverage describes absent windows rather than implying a fault',()=>{
 assert.match(coverage({sources:{indoor_temperature:'sensor.room'},windows:[]}),/fenêtres non mesurées/);
});
