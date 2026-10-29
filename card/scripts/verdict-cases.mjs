// The card's own banner for every view of a cases file, for tests/test_verdict_parity.py: the Python port
// (custom_components/hestia_comfort/engine/verdict.py) must say word for word the same. Usage: verdict-cases.mjs <cases.json>
import {mkdtemp,readFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';import {pathToFileURL,fileURLToPath} from 'node:url';
import {build} from 'esbuild';
const card=fileURLToPath(new URL('../',import.meta.url)),temp=await mkdtemp(join(tmpdir(),'nc-verdict-'));
await build({entryPoints:[join(card,'src/views/room.ts')],outdir:temp,bundle:true,platform:'node',format:'esm',outExtension:{'.js':'.mjs'},logLevel:'silent'});
const {advice,slides,humidityLabel}=await import(pathToFileURL(join(temp,'room.mjs')));
await rm(temp,{recursive:true,force:true});
const cases=JSON.parse(await readFile(process.argv[2],'utf8'));
process.stdout.write(JSON.stringify(cases.flatMap(c=>c.rooms.map(v=>{const a=advice(v),s=slides(v,[])[0];
  return {title:a.title,disk:a.disk,cap:a.cap??null,learned:a.learned??null,pill:s.pill,level:s.level,humidity:humidityLabel(v)};}))));
