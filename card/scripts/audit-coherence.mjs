// « À savoir » never contradicts itself nor the banner: every situation of the real engine (scripts/audit_card_situations.py)
// through the card's own advice and lines, checked for words that say opposite things. Exits 1 on the first kind found.
import {mkdtemp,readFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';import {pathToFileURL,fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';import {build} from 'esbuild';
const card=fileURLToPath(new URL('../',import.meta.url)),temp=await mkdtemp(join(tmpdir(),'nc-audit-'));
execFileSync(process.env.PYTHON??'python3',['-I',join(card,'../scripts/audit_card_situations.py'),join(temp,'cases.json')],{stdio:'inherit'});
await build({entryPoints:[join(card,'src/views/room.ts')],outdir:temp,bundle:true,platform:'node',format:'esm',outExtension:{'.js':'.mjs'},logLevel:'silent'});
const {advice,factList}=await import(pathToFileURL(join(temp,'room.mjs')));
const flat=t=>t==null?'':typeof t!=='object'?String(t):Array.isArray(t)?t.map(flat).join(''):t.strings?t.strings.map((s,i)=>s+(i<t.values.length?flat(t.values[i]):'')).join(''):'';
const cases=JSON.parse(await readFile(join(temp,'cases.json'),'utf8'));
const num=(v,k)=>v.observations[k]?.value;
const RULES=[
 ['refermer et laisser ouvert',(b,f)=>/refermer|Refermez/.test(b+f.join('|'))&&/laisser ouvert|Laissez ouvert/.test(b+f.join('|'))],
 ['refroidirait alors qu’il fait plus doux dehors',(b,f,rs)=>rs.every(v=>num(v,'outdoor_temperature')-num(v,'indoor_temperature')>0.5)&&/refroidi/.test(f.join('|')+b)],
 ['réchauffe alors qu’il fait plus frais dehors',(b,f,rs)=>rs.every(v=>num(v,'outdoor_temperature')-num(v,'indoor_temperature')<-0.5)&&/dehors[^|]*réchauffe/.test(f.join('|')+b)],
 ['« ne change rien » mais une ligne dit le contraire',(b,f)=>/ne change rien/.test(b)&&/réchauffe la pièce|laisser ouvert|la réchauffe/.test(f.join('|'))],
 ['« n’apporterait rien » mais une ligne invite à ouvrir',(b,f)=>/apporterait rien/.test(b)&&/bon moment pour aérer|la baissera|réchaufferait|laisser ouvert|Ouvrez /.test(f.join('|'))],
 ['geste d’ouvrir mais une ligne dit fermé ou inutile',(b,f)=>/^(Ouvrez|Aérez|Laissez ouvert|Encore|Aération en cours)/.test(b)&&f.some(x=>!/^Pas /.test(x)&&/refermer|à garder fermées|refroidirait|n’aiderait pas|ne suffirait pas|ne ferait pas baisser|ne gagnerait|ne change rien|n’apporterait/.test(x))],
 ['geste de fermer mais une ligne invite à ouvrir',(b,f)=>/^(Refermez|Fermez|Gardez fermé)/.test(b)&&/laisser ouvert|bon moment pour aérer|Ouvrez |la baissera peu/.test(f.join('|'))],
 ['deux lignes sur l’humidité',(b,f)=>f.filter(x=>/^(Humidité|Air humide|Très humide|Légèrement humide|Humidité élevée|Air humide dehors|Air sec|Très sec|Légèrement sec)\b/.test(x)).length>1],
 ['une même raison dite deux fois',(b,f)=>f.some(x=>{const n=x.match(/(\d+) points?/g);return n&&n.length>1&&new Set(n).size<n.length;})||f.some(x=>{const p=x.split(', ');return new Set(p).size<p.length;})],
 ['« Fenêtre ouverte » sans fenêtre ouverte',(b,f,rs)=>f.some(x=>/^Fenêtre ouverte · (elle|sans)/.test(x))&&!rs.some(v=>Object.entries(v.observations).some(([k,r])=>k.startsWith('window:')&&r.value===true))],
];
const found=new Map();let n=0;
for(const c of cases)for(let i=0;i<c.rooms.length;i++){const v=c.rooms[i],partners=c.rooms.filter((_,j)=>j!==i),a=advice(v);n++;
  const b=`${a.title} · ${flat(a.line)}`,f=factList(v,partners).map(x=>`${x.title} · ${flat(x.text)}`);
  for(const [name,bad] of RULES)if(bad(b,f,c.rooms)){const l=found.get(name)??[];l.push({case:c.case,room:v.title,reason:v.assessment.reason,banner:b,facts:f});found.set(name,l);}}
await rm(temp,{recursive:true,force:true});
console.log(n,'cartes vérifiées,',found.size?`${found.size} sortes de contradictions`:'aucune contradiction');
for(const [name,l] of found){console.log(`\n## ${name} : ${l.length}`);const seen=new Set();for(const x of l){const k=x.reason+x.banner+x.facts.join();if(seen.has(k))continue;seen.add(k);if(seen.size>4)break;
  console.log(' ',JSON.stringify(x.case),x.room,x.reason,'\n   ',x.banner,'\n    -',x.facts.join('\n    - '));}}
process.exitCode=found.size?1:0;
