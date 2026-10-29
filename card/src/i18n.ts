// The card's words follow Home Assistant's language, with the hub's own method (socle i18n.ts): French is the source,
// written in the code, and t() gives the user's language. The card's dictionaries are added to the hub's below.
import {html,type TemplateResult} from 'lit';
import {t,fr,setLanguage,addDictionary,currentLanguage,currentLocale} from '../../frontend/socle/i18n';
import {EN} from './i18n/en';

addDictionary('en',EN);
export {t,fr,setLanguage,currentLanguage,currentLocale};

/** t() for a sentence with parts set apart (a value in bold): `{name}` takes `vars.name`, text or template. */
export function th(french:string,vars:Record<string,string|number|TemplateResult>):TemplateResult{
 const parts=t(french).split(/\{(\w+)\}/);
 return html`${parts.map((part,i)=>i%2?(part in vars?vars[part]:`{${part}}`):part)}`;
}
/** Before the card gets Home Assistant (the « Add card » list is written at load): the language the page was opened in. */
export function guessLanguage():void{
 let lang:string|undefined;
 try{lang=(document.querySelector('home-assistant') as unknown as {hass?:{language?:string}}|null)?.hass?.language;}catch{/* not in Home Assistant */}
 try{lang??=JSON.parse(localStorage.getItem('selectedLanguage')??'null')??undefined;}catch{/* private browsing */}
 setLanguage(lang||document.documentElement.lang||navigator.language);
}
/** « Pluie : 2 mm » in French, « Rain: 2 mm » in English. */
export const colon=(label:string,text:string)=>t('{label} : {text}',{label,text});

/** French texts the card builds in its computations (titles, « À savoir », tiles) are translated where shown: tx()
 *  finds a whole text in the dictionary, or a template it was made from (« Encore {n} min d’aération »), its parts
 *  translated in turn; a list (« a · b », « a, b ») is translated item by item. The computations stay in French, so
 *  their comparisons and the engine's parity tests never depend on the language. */
// What a template's part may hold, by its name: a count only a number, a measure a number and its unit, an hour an hour.
// Any other name (a room, a window, a reason) holds any text. Without it « {n} pièce » would read « …la pièce ».
const NUMBER='[-+]?\\d[\\d.,\\s\u202f\u00a0]*',MEASURE=NUMBER+'(?:\\s?(?:°C/h|°C|%|ppm|W/m²|min|h))?|—',TIME='\\d{1,2}(?::\\d{2}| h(?: \\d{2})?)?|minuit|midi';
const KINDS:Record<string,string>={n:NUMBER,i:NUMBER,m:NUMBER,min:NUMBER,max:NUMBER,days:NUMBER,gain:NUMBER,h:NUMBER,
 value:MEASURE,low:MEASURE,high:MEASURE,before:MEASURE,after:MEASURE,temp:MEASURE,target:MEASURE,hour:TIME,time:TIME,from:TIME,to:TIME};
let compiled:{lang:string;size:number;list:[RegExp,string[],string][]}|null=null;
function templates(words:Record<string,string>):[RegExp,string[],string][]{
 const lang=currentLanguage(),size=Object.keys(words).length;
 if(compiled&&compiled.lang===lang&&compiled.size===size)return compiled.list;
 const list=Object.entries(words).filter(([fr])=>/\{\w+\}/.test(fr)).map(([fr,en]):[RegExp,string[],string]=>{
  const names:string[]=[];
  const source=fr.split(/(\{\w+\})/).map(part=>{const m=part.match(/^\{(\w+)\}$/);if(m){names.push(m[1]);return '('+(KINDS[m[1]]??'.+?')+')';}return part.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');}).join('');
  return [new RegExp('^'+source+'$'),names,en];});
 // The most specific first: the longer its fixed words, the sooner it is tried.
 list.sort((x,y)=>y[0].source.replace(/\(\.\+\?\)/g,'').length-x[0].source.replace(/\(\.\+\?\)/g,'').length);
 compiled={lang,size,list};return list;
}
const SEPARATORS:[string,string][]=[[' · ',' · '],[', ',', '],[' : ',': '],[' et ',' and ']];
/** The dictionary entries the card used, for the test that finds the unused ones. */
export const used=new Set<string>();
/** The texts with words the dictionary could not translate, for the test that finds them. */
export const missing=new Set<string>();
function back(text:string,words:Record<string,string>,first=true):string{
 if(text in words){used.add(text);return words[text];}
 if(/^[\d\s.,:+\-–→/%°]*$/.test(text))return text;
 for(const [re,names,en] of templates(words)){const m=text.match(re);
  if(m){used.add(Object.keys(words).find(k=>words[k]===en&&re.test(text))??'');return names.reduce((out,name,i)=>out.split('{'+name+'}').join(back(m[i+1],words)),en);}}
 for(const [fr,en] of SEPARATORS)if(text.includes(fr))return text.split(fr).map(part=>back(part,words)).join(en);
 // A capital first letter the dictionary has in lower case (« Très humide » shown « très humide »).
 const lower=text[0]?.toLowerCase()+text.slice(1);
 if(lower!==text&&lower in words){used.add(lower);const w=words[lower];return w[0].toUpperCase()+w.slice(1);}
 const upper=text[0]?.toUpperCase()+text.slice(1);
 if(upper!==text&&upper in words){used.add(upper);const w=words[upper];return w[0].toLowerCase()+w.slice(1);}
 // A text shown in lower case (« aérez 5 à 10 min » under a room): its capitalised template, lower case again.
 if(first&&text[0]!==text[0].toUpperCase()){const up=back(text[0].toUpperCase()+text.slice(1),words,false);if(up!==text[0].toUpperCase()+text.slice(1))return up[0].toLowerCase()+up.slice(1);}
 if(first&&/\p{L}{2}/u.test(text))missing.add(text);
 return text;
}
export function tx(text:string|null|undefined):string{
 if(!text)return text??'';
 const lang=currentLanguage();
 return lang==='fr'?text:back(text,WORDS[lang]??WORDS.en);
}
const WORDS:Record<string,Record<string,string>>={en:EN};

/** A line built as a Lit template (« L’air du dehors est ${b('plus sec')} »), translated where shown: its fixed words
 *  become a dictionary entry with numbered parts (« L’air du dehors est {0} »), and each part is translated in turn. */
export function tl<T>(x:T):T{
 if(currentLanguage()==='fr')return x;
 if(typeof x==='string')return tx(x) as T;
 if(Array.isArray(x))return x.map(tl) as T;
 if(x&&typeof x==='object'&&'strings' in x&&'values' in x){
  const r=x as unknown as TemplateResult,values=r.values.map(tl);
  // Markup only (<b>…</b>): its parts are translated, the markup stays.
  if(!r.strings.some(part=>/\p{L}/u.test(part.replace(/<[^>]*>/g,''))))return {...r,values} as T;
  const key=r.strings.map((part,i)=>i?`{${i-1}}${part}`:part).join('');
  const words=WORDS[currentLanguage()]??WORDS.en,en=words[key];
  if(en===undefined){missing.add(key);return {...r,values} as T;}
  used.add(key);
  return html`${en.split(/\{(\d+)\}/).map((part,i)=>i%2?values[Number(part)]:part)}` as T;
 }
 return x;
}
