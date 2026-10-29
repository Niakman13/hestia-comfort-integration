import '../../custom_components/hestia_comfort/frontend/hestia-comfort-card.js';
const fixtures=await (await fetch('./card-fixtures.json')).json();
const $=id=>document.getElementById(id);
const listeners=new Set();
let scene=fixtures[0],stream='normal',config={type:'custom:hestia-comfort-card',entry_id:'demo-salon',format:'full',theme:'dark'};
let starts=0,stops=0;
const result=entry=>{
  const v=structuredClone(scene.view);
  v.entry_id=stream==='wrong_room'?'wrong-room':entry??'demo-salon';v.area_id=v.entry_id;v.title=v.entry_id==='demo-bureau'?'Bureau':'Salon';
  v.computed_at=new Date(Date.now()-(stream==='stale'?120000:0)).toISOString();
  if(stream==='version')v.version=99;
  return {version:1,view:v};
};
const connection={async subscribeMessage(callback,message){
  if(stream==='missing')throw {code:'unknown_command'};
  const subscription={callback,entry:message.entry_id};listeners.add(subscription);starts++;
  callback(stream==='reload'?{version:1,reload:true}:result(message.entry_id));status();
  return ()=>{listeners.delete(subscription);stops++;status();};
}};
const hass={connection,themes:{darkMode:true},async callWS(){if(stream==='missing')throw {code:'unknown_command'};return [{entry_id:'demo-salon',area_id:'demo-salon',title:'Salon'},{entry_id:'demo-bureau',area_id:'demo-bureau',title:'Bureau'}];}};
function status(){$('bench-status').textContent=`Scénario calculé par le moteur Python · ${listeners.size} abonnement(s) actif(s) · ${starts} ouvert(s), ${stops} fermé(s). Flux fictif, aucun lien avec votre installation.`;}
function push(){for(const s of listeners)s.callback(stream==='reload'?{version:1,reload:true}:result(s.entry));status();}
function apply(){$('primary').setConfig(config);$('editor').setConfig(config);}
$('scenario').innerHTML=fixtures.map(f=>`<option value="${f.id}">${f.name}</option>`).join('');
apply();$('secondary').setConfig({type:'custom:hestia-comfort-card',entry_id:'demo-salon',format:'tile',theme:'dark'});
for(const id of ['primary','secondary','editor'])$(id).hass=hass;
$('scenario').addEventListener('change',e=>{scene=fixtures.find(f=>f.id===e.target.value);push();});
$('format').addEventListener('change',e=>{config={...config,format:e.target.value};apply();});
$('theme').addEventListener('change',e=>{
  const theme=e.target.value;document.documentElement.dataset.theme=theme;config={...config,theme};apply();
  $('secondary').setConfig({type:'custom:hestia-comfort-card',entry_id:'demo-salon',format:'tile',theme});
});
$('stream').addEventListener('change',e=>{
  stream=e.target.value;
  if(stream==='missing'){for(const s of listeners)s.callback({version:1,unavailable:true});}
  else push();
  // A new connection object exercises reconnection, as HA does after reconnect.
  hass.connection={...connection};for(const id of ['primary','secondary','editor'])$(id).hass={...hass};
});
$('editor').addEventListener('config-changed',e=>{config=e.detail.config;$('primary').setConfig(config);$('format').value=config.format??'tile';});
setInterval(()=>{if(stream==='normal')push();},30000);
queueMicrotask(status);
