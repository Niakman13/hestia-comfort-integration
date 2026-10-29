// The card in English over every situation of the real engine (scripts/audit_card_situations.py) and the preview's
// fixtures: prints the texts the dictionary does not translate yet. Used to write the dictionary, and by the tests.
import {mkdtemp,readFile,rm,writeFile} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';import {execFileSync} from 'node:child_process';import {build} from 'esbuild';
const card=fileURLToPath(new URL('../',import.meta.url)),temp=await mkdtemp(join(tmpdir(),'nc-i18n-'));
execFileSync(process.env.PYTHON??'python3',['-I',join(card,'../scripts/audit_card_situations.py'),join(temp,'cases.json')],{stdio:'ignore'});
// One bundle: the views and the translation share their module, so the language set here is theirs.
await writeFile(join(temp,'entry.ts'),`export * from ${JSON.stringify(join(card,"src/views/room.ts"))};export {needs as roomNeeds} from ${JSON.stringify(join(card,"src/views/room.ts"))};export * from ${JSON.stringify(join(card,'src/i18n.ts'))};export * from ${JSON.stringify(join(card,'src/view.ts'))};export {EN} from ${JSON.stringify(join(card,'src/i18n/en.ts'))};`);
await build({entryPoints:[join(temp,'entry.ts')],outfile:join(temp,'all.mjs'),bundle:true,platform:'node',format:'esm',logLevel:'silent'});
const m=await import(pathToFileURL(join(temp,'all.mjs')));
const cases=JSON.parse(await readFile(join(temp,'cases.json'),'utf8')).flatMap(c=>c.rooms.map((v,i)=>({v,partners:c.rooms.filter((_,j)=>j!==i)})));
const fixtures=JSON.parse(await readFile(join(card,'preview/card-fixtures.json'),'utf8')).map(f=>({v:f.view,partners:[]}));
const config={type:'custom:niak-comfort-card',modules:['temperature','humidity','air','windows','shutters','coordination']};
const st={why:true,tilesOpen:true,detailsOpen:true,toggle(){},uid:'x'};
m.setLanguage('en');
for(const {v,partners} of [...cases,...fixtures]){
 for(const format of ['full','tile','mini','measures','alert'])m.roomCard(v,config,st,format,partners);
 for(const s of m.slides(v,['remedies','later'])){m.tx(s.title);m.tx(s.cap);m.tx(s.pill);m.tl(s.line);}
 for(const f of m.factList(v,partners,config)){m.tx(f.title);m.tl(f.text);}
 for(const n of m.roomNeeds(v))m.tx(n);
 m.tx(m.coverageText(v));
}
await rm(temp,{recursive:true,force:true});
// Names are never translated: the rooms', the windows', and entity ids.
const names=new Set([...cases,...fixtures].flatMap(({v,partners})=>[v,...partners].flatMap(r=>[r.title,r.volume_name,...Object.values(r.names??{})])).filter(Boolean));
const out=[...m.missing].filter(x=>!names.has(x)&&!/^[a-z_]+\.[\w.]+$/.test(x)).sort();
if(process.argv.includes('--check')){
 // The French texts written in the code (t, th, fr): a dictionary word neither written nor used is left over.
 const {readdirSync,readFileSync,statSync}=await import('node:fs');
 const files=dir=>readdirSync(dir).flatMap(f=>statSync(join(dir,f)).isDirectory()?(f==='i18n'?[]:files(join(dir,f))):f.endsWith('.ts')?[join(dir,f)]:[]);
 const literals=new Set();
 for(const f of files(join(card,'src'))){const source=readFileSync(f,'utf8'),call=/\b(?:t|th|fr)\(/g;
  for(let x=call.exec(source);x;x=call.exec(source)){let depth=0,i=x.index+x[0].length;
   for(;i<source.length;i++){const c=source[i];
    if(c==="'"||c==='"'){let j=i+1,text='';while(source[j]!==c){if(source[j]==='\\')j++;text+=source[j++];}literals.add(text);i=j;}
    else if(c==='`')break;else if('([{'.includes(c))depth++;else if(')]}'.includes(c)){if(!depth--)break;}else if(c===','&&!depth)break;}}}
 // A word built in French by the code (« Encore ${left} min d’aération ») is found by its fixed words, in any case.
 const code=files(join(card,'src')).map(f=>readFileSync(f,'utf8')).join('\n').toLowerCase();
 // Word by word, a short gap allowed between two (a ternary, a plural « ${n>1?'s':''} » built apart).
 const inCode=k=>{const words=k.toLowerCase().replace(/\{\w+\}/g,' ').match(/[\p{L}’']+/gu)??[];
  if(!words.length)return true;
  const stem=w=>w.replace(/(es|s|e)$/,'').replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?:es|e|s)?';
  return new RegExp(words.map(stem).join('[\\s\\S]{0,60}?')).test(code);};
 const unused=Object.keys(m.EN).filter(k=>!literals.has(k)&&!m.used.has(k)&&!inCode(k));
 console.log(cases.length+fixtures.length,'cartes en anglais ·',out.length,'textes sans traduction ·',unused.length,'mots inutilisés');
 for(const x of out)console.log('  sans traduction :',x);
 for(const x of unused)console.log('  inutilisé :',x);
 process.exit(out.length||unused.length?1:0);
}
if(process.argv.includes('--json'))console.log(JSON.stringify({missing:out,used:[...m.used]}));
else{console.log(out.length,'textes sans traduction sur',cases.length+fixtures.length,'cartes');for(const x of out)console.log(x);}
