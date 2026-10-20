import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {build} from 'esbuild';
const root=new URL('../',import.meta.url),temp=await mkdtemp(join(tmpdir(),'niak-comfort-card-'));
await build({entryPoints:['src/types.ts','src/view.ts','src/live.ts','src/views/room.ts'].map(p=>fileURLToPath(new URL(p,root))),outdir:temp,
  bundle:true,platform:'node',format:'esm',outExtension:{'.js':'.mjs'},logLevel:'silent'});
const {cleanConfig,cleanHomeConfig,homeAction}=await import(pathToFileURL(join(temp,'types.mjs')));
const {isView,numeric,summary,readingStatus,coverageText,windFrom,evolutionLines,co2Metric,solarMetric}=await import(pathToFileURL(join(temp,'view.mjs')));
const {LiveView}=await import(pathToFileURL(join(temp,'live.mjs')));
const {outsideGaps,advice,slides,roomCard}=await import(pathToFileURL(join(temp,'views/room.mjs')));
const fixtures=JSON.parse(await readFile(new URL('../preview/card-fixtures.json',import.meta.url),'utf8'));
const fresh=()=>({...structuredClone(fixtures[0].view),computed_at:new Date().toISOString()});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
after(()=>rm(temp,{recursive:true,force:true}));

test('the twelve Python snapshots conform to the card contract',()=>{for(const f of fixtures)assert.equal(isView(f.view),true,f.id);});
test('reject incompatible versions, invalid levels and non-finite measures',()=>{
  for(const mutate of [v=>v.version=2,v=>v.assessment.level='normal',v=>v.observations.co2.value=Infinity,v=>v.assessment.needs=null,v=>v.computed_at='bad']){
    const v=fresh();mutate(v);assert.equal(isView(v),false);
  }
});
test('unavailable or estimated measures never become current numeric readings',()=>{
  assert.equal(numeric({value:600,quality:'stale'}),null);
  assert.equal(numeric({value:600,quality:'estimated'}),null);
  assert.equal(numeric(undefined),null);
  assert.equal(numeric({value:600,quality:'valid'}),600);
});
test('config keeps hidden modules and order without mutating input',()=>{
  const input={type:'custom:niak-comfort-card',modules:['air','windows','air']};
  assert.deepEqual(cleanConfig(input).modules,['air','windows']);assert.equal(input.modules.length,3);
  assert.deepEqual(cleanConfig({...input,modules:[]}).modules,[]);
  assert.throws(()=>cleanConfig({...input,format:'bad'}));
});
test('an airing underway keeps the measured need and red situation',()=>{
  const v=fixtures.find(f=>f.id==='expired').view;
  assert.equal(summary(v)[0],'L’aération est en cours');assert.equal(v.assessment.level,'urgent');
});
test('an incomplete bilan names the measure that is out of date',()=>{
  const v=fresh();v.assessment={...v.assessment,reason:'incomplete_data',level:'neutral',action:'unknown',partial:true,missing:['pollution']};
  v.observations.pollution={value:null,quality:'stale',source:'sensor.atmo',received_at:null,detail:'expired',unit:null};
  const [title,body]=summary(v);
  assert.equal(title,'Une mesure n’est pas à jour');assert.match(body,/^Qualité de l’air dehors : /);
});
test('a stale contact is named as the person knows it',()=>{
  const v=fresh();v.names={'binary_sensor.w':'Fenêtre Ouest'};v.assessment={...v.assessment,missing:['window:binary_sensor.w']};
  v.observations['window:binary_sensor.w']={value:null,quality:'stale',source:'binary_sensor.w',received_at:null,detail:'expired',unit:null};
  assert.equal(coverageText(v),'Mesures à vérifier : Fenêtre Ouest');
});
test('late old-room callbacks and pending subscriptions cannot leak',async()=>{
  let finish,oldCallback,newCallback,removed=0,shown=[];
  const old={subscribeMessage:async cb=>{oldCallback=cb;return await new Promise(resolve=>finish=resolve);}};
  const next={subscribeMessage:async cb=>{newCallback=cb;return ()=>removed++;}};
  const live=new LiveView(v=>shown.push(v.entry_id),()=>{},()=>{});
  try {
    live.start(old,'old');live.start(next,'new');
    oldCallback({version:1,view:{...fresh(),entry_id:'old'}});
    newCallback({version:1,view:{...fresh(),entry_id:'new'}});
    finish(()=>removed++);await flush();
    assert.deepEqual(shown,['new']);assert.equal(removed,1);
    live.stop();await flush();assert.equal(removed,2);
  }finally{live.stop();}
});
test('same connection and room has one subscription',async()=>{
  let starts=0;const conn={subscribeMessage:async()=>{starts++;return ()=>{};}};
  const live=new LiveView(()=>{},()=>{},()=>{});
  try {live.start(conn,'salon');live.start(conn,'salon');await flush();assert.equal(starts,1);}finally{live.stop();}
});
test('reload immediately invalidates old callbacks during the retry delay',async()=>{
  let cb,starts=0,shown=0;const conn={subscribeMessage:async callback=>{starts++;cb=callback;return ()=>{};}};
  const live=new LiveView(()=>shown++,()=>{},()=>{});
  try {
    live.start(conn,'salon');await flush();
    cb({version:1,view:{...fresh(),entry_id:'salon'}});assert.equal(shown,1);
    cb({version:1,reload:true});cb({version:1,view:{...fresh(),entry_id:'salon'}});
    live.start(conn,'salon');assert.equal(shown,1);assert.equal(starts,1);
  }finally{live.stop();}
});
test('old, wrong-room, unavailable and malformed snapshots clear the view',async()=>{
  let cb,clears=0;const problems=[];
  const conn={subscribeMessage:async callback=>{cb=callback;return ()=>{};}};
  const live=new LiveView(()=>{},code=>problems.push(code),()=>clears++);
  try {
    live.start(conn,'salon');
    cb({version:1,view:{...fresh(),entry_id:'salon',computed_at:new Date(Date.now()-120000).toISOString()}});
    cb({version:1,view:{...fresh(),entry_id:'bureau'}});
    cb({version:1,unavailable:true});cb({version:1,view:{version:5}});
    assert.deepEqual(problems,['stale','version','unavailable','version']);assert.ok(clears>=4);
  }finally{live.stop();}
});
test('two cards own separate subscriptions and cleanup',async()=>{
  let active=0;const conn={subscribeMessage:async()=>{active++;return ()=>active--;}};
  const a=new LiveView(()=>{},()=>{},()=>{}),b=new LiveView(()=>{},()=>{},()=>{});
  try {a.start(conn,'salon');b.start(conn,'salon');await flush();assert.equal(active,2);a.stop();await flush();assert.equal(active,1);}
  finally{a.stop();b.stop();await flush();assert.equal(active,0);}
});

test('intentional absence differs from unavailable, stale and invalid readings',()=>{
  assert.equal(readingStatus(undefined),'Non configuré');
  assert.equal(readingStatus({quality:'unknown',detail:'unavailable'}),'Temporairement indisponible');
  assert.equal(readingStatus({quality:'stale'}),'Mesure trop ancienne');
  assert.equal(readingStatus({quality:'unknown',detail:'incompatible_unit'}),'Unité incompatible');
  const v=fresh();v.assessment.missing=['rain','pollution'];delete v.observations.rain;delete v.observations.pollution;
  assert.match(coverageText(v),/non configuré/);assert.doesNotMatch(coverageText(v),/à vérifier/);
  v.assessment.missing=['co2'];v.observations.co2={quality:'unknown',source:'sensor.co2',value:null};
  assert.match(coverageText(v),/Mesures à vérifier : CO₂/);
});
test('wind names say where the wind comes from, in plain French',()=>{
  assert.equal(windFrom(270),'vent d’ouest');
  assert.equal(windFrom(0),'vent du nord');
  assert.equal(windFrom(359),'vent du nord');
  assert.equal(windFrom(45),'vent de nord-est');
  assert.equal(windFrom(null),'');
});

const floorFixtures=JSON.parse(await readFile(new URL('../preview/floors.json',import.meta.url),'utf8'));
test('floor scenarios keep every room compatible with the card, including missing temperatures',()=>{
  for(const scene of floorFixtures)for(const room of scene.event.rooms)assert.equal(isView(room),true,scene.id+':'+room.title);
});

test('evolution preserves manual unknown positions, empty-room tracking and indicative estimates',()=>{
 const v=fresh();v.assessment.features={shutters:[{entity_id:'binary_sensor.w',mode:'manual',position:null,message:'Si le volet est ouvert, fermez-le.'}],presence:{state:'empty',message:'Pièce vide ; suivi maintenu.'},ventilation:{opened_minutes:null,duration_minutes:{min:5,max:10},message:'Durée indicative.'},air:{message:'Les polluants non mesurés restent inconnus.',coverage:'CO₂ uniquement'},humidity:{condensation_risk:null,message:'Risque non calculable.'}};
 const lines=evolutionLines(v,['shutters','air','windows','humidity']);
 const text=lines.map(l=>l.text).join(' ');assert.match(text,/Position non mesurée/);assert.match(text,/Pièce vide/);assert.match(text,/5–10 min/);assert.match(text,/indicati/);assert.match(text,/non mesurés/);assert.doesNotMatch(text,/depuis 0/);
 assert.deepEqual(evolutionLines(v,[]),[]);assert.deepEqual(evolutionLines({...v,assessment:{...v.assessment,features:undefined}},['air']),[]);
});

test('CO₂ verdict follows its own observation and verdict despite high particles',()=>{
 const v=fresh();v.assessment.needs=['air'];v.assessment.level='action';v.assessment.features={air:{co2_status:'ok',pm25_status:'high'}};
 v.observations.co2={value:500,quality:'valid'};
 assert.equal(co2Metric(v).state,'ok');assert.equal(co2Metric(v).note,'Dans vos repères CO₂');
 v.observations.co2={value:null,quality:'unknown'};v.assessment.features.air.co2_status='unknown';
 assert.equal(co2Metric(v).state,'off');assert.doesNotMatch(co2Metric(v).note,/renouveler/);
 v.observations.co2={value:1500,quality:'valid'};v.assessment.features.air.co2_status='high';
 assert.equal(co2Metric(v).state,'need');assert.match(co2Metric(v).note,/renouveler/);
});
test('condensation has three explicit estimated outcomes and empty histories stay honest',()=>{
 const v=fresh();for(const [risk,text] of [[true,'Risque de buée estimé'],[false,'Aucun risque de buée estimé'],[null,'Risque de buée inconnu']]){
  v.assessment.features={humidity:{condensation_risk:risk,message:'Modèle estimé.'},trends:{indoor:null,outdoor:null,message:'Pentes estimées.'},ventilation:{opened_minutes:null,duration_minutes:null,message:'Durée indicative.'}};
  const lines=evolutionLines(v,['humidity','temperature','windows']);assert.match(lines.find(l=>l.title==='Humidité et buée').text,new RegExp(text));
  assert.equal(lines.find(l=>l.title==='Évolution des températures').text,'Historique insuffisant pour estimer une tendance.');
  assert.equal(lines.some(l=>l.title==='Aération'),false);
 }
 v.assessment.sun=null;assert.equal(solarMetric(v).value,'—');assert.equal(solarMetric(v).note,'Position du soleil inconnue');
});
test('an open contact with no reliable timer keeps its unknown duration visible',()=>{
 const v=fresh();v.observations['window:binary_sensor.open']={value:true,quality:'valid',source:'binary_sensor.open',received_at:new Date().toISOString(),detail:null,unit:null};
 v.assessment.features={ventilation:{opened_minutes:null,duration_minutes:null,message:'Ouvert depuis une durée inconnue.'}};
 assert.match(evolutionLines(v,['windows']).map(l=>l.text).join(' '),/durée inconnue/);
});
test('humidity and shutter reasons introduced by the engine have readable summaries',()=>{
 const v=fresh();for(const reason of ['rehumidification_risk','shutter_protection']){v.assessment.reason=reason;assert.notEqual(summary(v)[0],'Conseil à vérifier');}
});
const evolutionFixtures=JSON.parse(await readFile(new URL('../preview/evolution/real-fixtures.json',import.meta.url),'utf8'));
test('the sixteen evolution engine scenes keep a readable compatible card',()=>{
 for(const scene of evolutionFixtures){assert.equal(isView(scene.view),true,scene.id);assert.notEqual(summary(scene.view)[0],'Conseil à vérifier',scene.id);}
});

test('an outdoor source that does not answer is « indisponible », a missing one « non suivi », the rest is not called outdoor',()=>{
  const v=fresh();v.assessment={...v.assessment,reason:'verify_exterior',missing:['heating','pollution'],unverified:[]};
  v.observations.pollution={value:null,quality:'unknown',source:'sensor.atmo',received_at:null,detail:'unavailable',unit:null};
  v.observations.heating={value:null,quality:'unknown',source:'climate.poele',received_at:null,detail:'unavailable',unit:null};
  assert.equal(outsideGaps(v),'Air extérieur indisponible');
  v.assessment.unverified=['rain'];
  assert.equal(outsideGaps(v),'Air extérieur indisponible, pluie non suivie');
  v.assessment.missing=[];v.assessment.unverified=['rain','pollution'];
  assert.equal(outsideGaps(v),'Pluie et air extérieur non suivis');
});
test('card display settings are booleans, kept as given',()=>{
  const c=cleanConfig({type:'custom:niak-comfort-card',measures_open:false,details_open:true,rotate:false,show_scale:false});
  assert.equal(c.measures_open,false);assert.equal(c.details_open,true);assert.equal(c.rotate,false);assert.equal(c.show_scale,false);
  assert.throws(()=>cleanConfig({type:'custom:niak-comfort-card',rotate:'non'}));
});

// A lit template read as plain text, as the banner shows it.
const flat=t=>t==null?'':typeof t==='string'||typeof t==='number'?String(t):Array.isArray(t)?t.map(flat).join(''):t.strings?t.strings.map((s,i)=>s+flat(t.values[i])).join(''):'';
const plain=t=>flat(t).replace(/<[^>]+>/g,'');
test('the drying advice speaks of what this room really gains, how long, and when it is better',()=>{
  const v=fresh(),drying={minutes:35,now:76,after:70,gain:6,tau:35,openings:7,later:null};
  v.observations.indoor_humidity={value:76,quality:'valid',source:'sensor.h',received_at:null,detail:null,unit:'%'};
  v.observations.outdoor_humidity={value:81,quality:'valid',source:'sensor.o',received_at:null,detail:null,unit:'%'};
  v.assessment={...v.assessment,reason:'drying_possible',action:'ouvrir',features:{...v.assessment.features,drying,ventilation:{opened_minutes:null,duration_minutes:{min:25,max:35},message:'',capacity:null}}};
  let a=advice(v);assert.equal(a.title,'Aérez 25 à 35 min');assert.match(plain(a.line),/environ 70 % après l’aération/);assert.doesNotMatch(plain(a.line),/il ferait/);
  v.assessment.features.drying={...drying,later:{minutes:35,now:76,after:62,gain:14,time:'2026-10-17T20:00:00+00:00'}};
  assert.equal(slides(v).filter(s=>s.title.startsWith('Encore mieux vers')).length,1);
  v.assessment={...v.assessment,reason:'drying_later',action:'attendre'};
  a=advice(v);assert.match(a.title,/^Aérez vers /);assert.match(plain(a.line),/environ 62 % après 35 min/);
  v.assessment={...v.assessment,reason:'ventilation_possible',level:'action',features:{...v.assessment.features,drying:{...drying,after:74,gain:2},air:{...(v.assessment.features?.air??{}),ventilation:{on:false,boost:false}}}};
  // Never the losing remedy's numbers under « Lancez la VMC » (20 Oct.: « 85 → 85 % seulement »).
  a=advice(v);assert.equal(a.title,'Lancez la VMC');assert.match(plain(a.line),/la fenêtre la baisse à peine/);assert.doesNotMatch(plain(a.line),/→/);
});
test('the weather’s own humidity, a shared air and a coming rain are said plainly',()=>{
  const v=fresh();
  v.assessment={...v.assessment,reason:'humid_outdoor',action:'ok',level:'calm',features:{...v.assessment.features,humidity:{dew_point:null,incoming_relative:null,glass_temperature:null,condensation_risk:null,message:'',surface:78,mould:false,excess:0.1,source:'outside',reachable:72}}};
  let a=advice(v);assert.equal(a.title,'Air humide dehors');assert.match(plain(a.line),/n’y changerait rien : 72 % au mieux/);
  v.assessment={...v.assessment,reason:'shared_volume',action:'ok',level:'action',features:{...v.assessment.features,volume:{lead:'Salon',reason:'air_needed',action:'ok'}}};
  a=advice(v);assert.equal(a.title,'Laissez ouvert');assert.match(plain(a.line),/Salon a besoin d’air/);
  v.assessment={...v.assessment,reason:'rain_soon',action:'fermer',rain_soon_minutes:12,features:{...v.assessment.features,rain_ahead:{minutes:12,precise:true}}};
  assert.match(plain(advice(v).line),/Pluie dans 12 min/);
  v.assessment.features.rain_ahead={minutes:0,precise:false};v.assessment.rain_soon_minutes=0;
  assert.match(plain(advice(v).line),/Pluie annoncée dans l’heure/);assert.doesNotMatch(plain(advice(v).line),/0 min/);
});
test('a « keep closed » that brings nothing leaves the banner calm',()=>{
  const v=fresh();
  for(const reason of ['drying_unavailable','drying_slow','opening_blocked','heat_needed','cooling_unavailable','precool_later']){
    v.assessment={...v.assessment,reason,level:'calm',action:'attendre'};
    const a=advice(v);assert.equal(a.title,'Rien à faire',reason);assert.match(plain(a.line),/n’apporterait rien/);
  }
  v.assessment={...v.assessment,reason:'opening_blocked',level:'action',action:'attendre'};
  assert.notEqual(advice(v).title,'Rien à faire');
});

test('the home card keeps its display settings and refuses wrong ones',()=>{
  const c=cleanHomeConfig({type:'custom:niak-comfort-home-card',rotate:false,show_rooms:false,rooms_open:true,animations:false,glass_effect:false});
  assert.equal(c.rotate,false);assert.equal(c.show_rooms,false);assert.equal(c.glass_effect,false);
  assert.throws(()=>cleanHomeConfig({type:'custom:niak-comfort-home-card',show_scale:'oui'}));
  assert.throws(()=>cleanHomeConfig({type:'custom:niak-comfort-card'}));
});

test('silent sensors are a state, not advice: loading after a start, then muted; one secondary sensor keeps the banner calm',()=>{
  const silent={value:null,quality:'unknown',source:'sensor.x',received_at:null,detail:'unavailable',unit:null};
  const v=fresh();v.observations={...v.observations,indoor_temperature:silent,indoor_humidity:silent,co2:silent};
  v.assessment={...v.assessment,reason:'incomplete_data',level:'neutral',action:'unknown',missing:['co2','indoor_humidity','indoor_temperature']};
  v.starting=true;let a=advice(v);assert.equal(a.title,'Mesures en chargement');assert.equal(a.pill,'Démarrage');
  v.starting=false;a=advice(v);assert.equal(a.title,'Mesures absentes');assert.match(plain(a.line),/3 capteurs ne répondent pas/);
  const w=fresh();w.observations={...w.observations,co2:silent};w.assessment={...w.assessment,reason:'incomplete_data',level:'neutral',missing:['co2']};
  a=advice(w);assert.equal(a.title,'Rien à faire');assert.equal(a.pill,'Un capteur muet');
});

test('the new formats and their settings: lists checked, alert hidden when nothing is asked',()=>{
  const c=cleanConfig({type:'custom:niak-comfort-card',format:'alert',banner_blocks:['later'],scale_marks:[],tile_chips:['humidity','humidity'],hold_action:'page',hold_path:'/confort'});
  assert.deepEqual(c.tile_chips,['humidity']);assert.equal(c.format,'alert');
  assert.throws(()=>cleanConfig({type:'custom:niak-comfort-card',format:'grand'}));
  assert.throws(()=>cleanConfig({type:'custom:niak-comfort-card',scale_marks:['nuit']}));
  assert.throws(()=>cleanConfig({type:'custom:niak-comfort-card',hold_action:'vibrer'}));
  const st={why:false,tilesOpen:false,detailsOpen:false,uid:'t',toggle(){}};
  const calm=fresh();calm.assessment={...calm.assessment,level:'calm',reason:'within_comfort'};
  assert.equal(roomCard(calm,cleanConfig({type:'custom:niak-comfort-card',format:'alert'}),st,'alert'),null);
  const asked=fresh();asked.assessment={...asked.assessment,level:'action',reason:'air_needed',action:'ouvrir'};
  assert.notEqual(roomCard(asked,cleanConfig({type:'custom:niak-comfort-card',format:'alert'}),st,'alert'),null);
  assert.match(flat(roomCard(asked,cleanConfig({type:'custom:niak-comfort-card',format:'mini'}),st,'mini')),/nc-line-card/);
  const h=cleanHomeConfig({type:'custom:niak-comfort-home-card',format:'list',list_order:'floor',banner_blocks:['rooms']});
  assert.equal(h.list_order,'floor');assert.throws(()=>cleanHomeConfig({type:'custom:niak-comfort-home-card',format:'grille'}));
});

test('right after a start, one or two late secondary sensors do not hide the advice',()=>{
  const silent={value:null,quality:'unknown',source:'sensor.fp2',received_at:null,detail:'unavailable',unit:null};
  const v=fresh();v.starting=true;v.observations={...v.observations,illuminance:silent,'presence:binary_sensor.fp2':silent};
  v.assessment={...v.assessment,reason:'drying_slow',level:'calm',action:'attendre',missing:['illuminance','presence:binary_sensor.fp2']};
  assert.notEqual(advice(v).title,'Mesures en chargement');
});

test('the home card can open a page on a long press, in every format',()=>{
  assert.equal(homeAction(cleanHomeConfig({type:'custom:niak-comfort-home-card'})),'none');
  assert.equal(homeAction(cleanHomeConfig({type:'custom:niak-comfort-home-card',hold_path:'/lovelace/maison'})),'page');
  assert.equal(homeAction(cleanHomeConfig({type:'custom:niak-comfort-home-card',format:'list'})),'popup');
  assert.equal(homeAction(cleanHomeConfig({type:'custom:niak-comfort-home-card',format:'list',hold_action:'page',hold_path:'/maison'})),'page');
});
test('a running ventilation or purifier is never counted out of your range',()=>{
  const v=fresh();v.assessment={...v.assessment,level:'calm',reason:'within_comfort',needs:[],features:{...v.assessment.features,air:{...(v.assessment.features?.air??{}),co2_status:'ok',ventilation:{on:true,boost:false}}}};
  v.observations={...v.observations,purifier:{value:true,quality:'valid',source:'fan.p'}};
  const st={why:false,tilesOpen:false,detailsOpen:false,uid:'t',toggle(){}};
  const text=plain(roomCard(v,cleanConfig({type:'custom:niak-comfort-card',format:'measures',modules:['air','humidity']}),st,'measures'));
  assert.match(text,/En marche/);assert.doesNotMatch(text,/hors de votre plage/);
});
test('the home card names what a room needs, as measured',async()=>{
  const {needs}=await import(pathToFileURL(join(temp,'views/room.mjs')));
  const v=fresh();v.observations={...v.observations,indoor_humidity:{value:68,quality:'valid',unit:'%'},voc:{value:282,quality:'valid',unit:'ppb'}};
  v.assessment={...v.assessment,level:'action',needs:['dry'],openings:[],features:{...v.assessment.features,air:{...(v.assessment.features?.air??{}),co2_status:'ok',voc_status:'high',ventilation:{on:true,boost:false}}}};
  assert.deepEqual(needs(v),['68 % trop humide','282 COV élevés']);
});
test('a cover driven by Adaptive Cover Pro has its own tile, and asks nothing while it drives',async()=>{
  const {tiles}=await import(pathToFileURL(join(temp,'views/room.mjs')));
  const v=fresh(),base={entity_id:'binary_sensor.w',mode:'connected',position:100,state:'open',advice:null,message:'',shade_fraction:null,shade_model:'unknown',manual_override:false,automatic:true,cover:'cover.v',driver:'adaptive_cover_pro',sun_front:true,target:30};
  v.assessment={...v.assessment,features:{...v.assessment.features,shutters:[base]}};
  const c=cleanConfig({type:'custom:niak-comfort-card',modules:['shutters']});
  let t=tiles(v,c).find(x=>x.label==='Volet');
  assert.deepEqual([t.value,t.note,t.out,t.entity],['Ouvert','automatique · soleil devant',false,'cover.v']);
  v.assessment.features.shutters=[{...base,automatic:false,advice:'close'}];
  t=tiles(v,c).find(x=>x.label==='Volet');assert.deepEqual([t.note,t.out,t.level],['à fermer',true,'action']);
  v.assessment.features.shutters=[{...base,automatic:false,advice:'close',soon:true,sun_start:'2026-10-19T13:50:00+02:00'}];
  t=tiles(v,c).find(x=>x.label==='Volet');assert.match(t.note,/^à fermer avant \d\d h \d\d$/);
});
