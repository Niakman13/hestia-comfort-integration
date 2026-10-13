import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {build} from 'esbuild';
const root=new URL('../',import.meta.url),temp=await mkdtemp(join(tmpdir(),'niak-comfort-card-'));
await build({entryPoints:['src/types.ts','src/view.ts','src/live.ts'].map(p=>fileURLToPath(new URL(p,root))),outdir:temp,
  bundle:true,platform:'node',format:'esm',outExtension:{'.js':'.mjs'},logLevel:'silent'});
const {cleanConfig}=await import(pathToFileURL(join(temp,'types.mjs')));
const {isView,numeric,summary,readingStatus,coverageText,windFrom}=await import(pathToFileURL(join(temp,'view.mjs')));
const {LiveView}=await import(pathToFileURL(join(temp,'live.mjs')));
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
