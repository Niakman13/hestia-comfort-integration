// The card in English: every French text given to t(), th() or fr() in card/src has its English words, with the same
// {names}. The texts built in French and translated where shown (tx, tl) are checked over every situation of the engine
// by `npm run test:i18n` (scripts/i18n-collect.mjs --check), which also finds the dictionary's unused words.
import {test,after} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync,statSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {build} from 'esbuild';

const src=fileURLToPath(new URL('../src/',import.meta.url));
const temp=mkdtempSync(join(tmpdir(),'comfort-i18n-'));
after(()=>rmSync(temp,{recursive:true,force:true}));
await build({entryPoints:[join(src,'i18n/en.ts')],bundle:true,platform:'node',format:'esm',outfile:join(temp,'en.mjs'),logLevel:'silent'});
const {EN}=await import(pathToFileURL(join(temp,'en.mjs')).href);

/** The French literals given to t(), th() and fr(): both sides of a ternary, never a template string. */
function frenchTexts(source){
 const found=[],call=/\b(?:t|th|fr)\(/g;
 for(let m=call.exec(source);m;m=call.exec(source)){
  let depth=0,i=m.index+m[0].length;
  for(;i<source.length;i++){const c=source[i];
   if(c==="'"||c==='"'){let j=i+1,text='';while(source[j]!==c){if(source[j]==='\\')j++;text+=source[j++];}found.push(text);i=j;}
   else if(c==='`')break;else if('([{'.includes(c))depth++;else if(')]}'.includes(c)){if(!depth--)break;}else if(c===','&&!depth)break;}
 }
 return found;
}
const files=dir=>readdirSync(dir).flatMap(f=>statSync(join(dir,f)).isDirectory()?(f==='i18n'?[]:files(join(dir,f))):f.endsWith('.ts')?[join(dir,f)]:[]);
const texts=new Set(files(src).flatMap(f=>frenchTexts(readFileSync(f,'utf8'))).filter(Boolean));

test('every French text of the card has its English words',()=>{
 const missing=[...texts].filter(x=>!(x in EN));
 // I18N_LIST=1 prints them, to write the dictionary.
 if(process.env.I18N_LIST)console.log(JSON.stringify(missing));
 assert.deepEqual(missing,[]);
});
test('a translation keeps the same {names} as its French',()=>{
 const names=x=>[...x.matchAll(/\{(\w+)\}/g)].map(m=>m[1]).sort().join();
 assert.deepEqual(Object.entries(EN).filter(([fr,en])=>names(fr)!==names(en)).map(([fr])=>fr),[]);
});
