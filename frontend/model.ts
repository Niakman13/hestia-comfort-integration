export const labels:Record<string,string>={indoor_temperature:'Température de la pièce',indoor_humidity:'Humidité de la pièce',co2:'CO₂',windows:'Fenêtres et portes vers l’extérieur',heating:'Chauffage',outdoor_temperature:'Température dehors',outdoor_humidity:'Humidité dehors',rain:'Pluie actuelle',wind_gust:'Rafales de vent',solar:'Ensoleillement',pollution:'Qualité de l’air extérieur'};
export const indoor=['indoor_temperature','indoor_humidity'] as const;
export const outdoor=['outdoor_temperature','outdoor_humidity','rain','wind_gust','solar','pollution'] as const;
export const multiple=new Set(['windows']);
export const exposures:[string,string][]=[['N','Nord'],['NE','Nord-est'],['E','Est'],['SE','Sud-est'],['S','Sud'],['SO','Sud-ouest'],['O','Ouest'],['NO','Nord-ouest']];
export const kinds:[string,string][]=[['window','Fenêtre'],['french','Porte-fenêtre ou baie'],['skylight','Vasistas ou petite fenêtre'],['door','Porte']];
export interface Candidate {
 entity_id:string;name:string;value:string;unit:string|null;area_id:string|null;
 local:boolean;outside:boolean;reference:boolean;available:boolean;adapter:string;warnings:string[];
 provenance:{entity_id:string;name:string;area_id:string|null}[];device_class:string|null;atmo_label:string|null;
}
export interface Spec {entity_id:string;adapter:string;block_from?:number}
export interface OpeningMeta {exposure:string|null;kind:string;sheltered:boolean}
export interface RoomConfig {area_id:string|null;name:string;sources:Record<string,string>;windows:string[];openings:Record<string,OpeningMeta>;settings:Record<string,number>;acknowledged?:string[];use_home?:boolean;rain_exposed?:boolean}
export interface Room {entry_id:string;title:string;loaded:boolean;config:RoomConfig}
export interface Area {area_id:string;name:string;outdoor:boolean}
export interface Snapshot {version:1;revision:string;areas:Area[];rooms:Room[];home:{configured:boolean;sources:Record<string,Spec>;acknowledged?:string[]}}
export interface Discovery {version:1;revision:string;candidates:Record<string,Candidate[]>;suggestions:Record<string,string|string[]>}
export interface Hass {callWS<T>(msg:Record<string,unknown>):Promise<T>;user?:{is_admin:boolean};themes?:{darkMode?:boolean};connection?:unknown}
export const warningText:Record<string,string>={
 alias:'Cette entité recopie une autre mesure. Vérifiez sa provenance ci-dessous.',
 other_area:'La mesure ou sa source est rattachée à une autre pièce. Confirmez qu’elle représente bien celle-ci.',
 contact_role:'Ce contact peut être une porte d’appareil, de meuble ou une porte intérieure. Gardez-le seulement s’il donne sur l’extérieur.',
 derived:'Il s’agit d’une donnée calculée ou regroupée. Vérifiez ce qu’elle mesure réellement.',
 no_hvac_action:'Cet équipement ne dit pas s’il chauffe réellement. Niak pourra seulement afficher son état comme inconnu.',
 binary_meaning:'Signal avancé : « actif » doit signifier pluie ou aération déconseillée. Un diagnostic de panne ne convient pas.',
 outdoor_role:'Ce capteur n’est pas rattaché à une pièce extérieure. Vérifiez qu’il mesure bien l’air du dehors.',
 used_indoor:'Ce capteur sert déjà de mesure intérieure pour une de vos pièces : il ne mesure sans doute pas l’air du dehors.',
 daily_forecast:'Indice régional prévu pour la journée. Il peut déclencher votre précaution, mais ne prouve pas la qualité de l’air maintenant à vos fenêtres.'
};
// Names of Home Assistant areas that usually mean "living room".
const livingNames=['salon','séjour','sejour','living','living room','pièce de vie','piece de vie'];
export function livingArea(areas:Area[],used:Set<string>):Area|undefined {return areas.find(a=>!a.outdoor&&!used.has(a.area_id)&&livingNames.includes(a.name.trim().toLowerCase()));}
export function measurement(c:Candidate):string {
 if(!c.available)return 'Ne répond pas en ce moment';
 if(c.atmo_label)return c.atmo_label+' · indice du jour';
 if(c.value==='on'||c.value==='off')return c.device_class==='window'||c.device_class==='door'||c.device_class==='opening'?(c.value==='on'?'Ouvert':'Fermé'):(c.value==='on'?'Actif':'Inactif');
 const n=Number(c.value);
 return (c.value!==''&&Number.isFinite(n)?new Intl.NumberFormat('fr-FR',{maximumFractionDigits:1}).format(n):c.value)+(c.unit?' '+c.unit:'');
}
export function defaultOpening():OpeningMeta {return {exposure:null,kind:'window',sheltered:false};}
export function newRoom(area:{area_id:string;name:string}|null,name:string,d:Discovery):RoomConfig {
 const sources:Record<string,string>={};for(const key of [...indoor,'co2','heating']){const value=d.suggestions[key];if(typeof value==='string')sources[key]=value;}
 const windows=Array.isArray(d.suggestions.windows)?[...d.suggestions.windows]:[];
 return {area_id:area?.area_id??null,name:area?.name??name,sources,windows,openings:Object.fromEntries(windows.map(id=>[id,defaultOpening()])),settings:{minimum:20,maximum:24},acknowledged:[]};
}
export function coverage(room:RoomConfig):string {
 const parts=[];if(room.sources.indoor_temperature)parts.push('Température');if(room.sources.indoor_humidity)parts.push('humidité');if(room.sources.co2)parts.push('CO₂');
 const n=room.windows.length;
 return (parts.join(', ')||'Mesures à compléter')+' · '+(n?n+' ouvrant'+(n>1?'s':''):'fenêtres non mesurées');
}
const shortNames:Record<string,string>={outdoor_temperature:'température',outdoor_humidity:'humidité',rain:'pluie',wind_gust:'rafales',solar:'ensoleillement',pollution:'qualité de l’air'};
export function exteriorSummary(sources:Record<string,Spec>):string {
 const names=outdoor.filter(k=>sources[k]).map(k=>shortNames[k]);
 return names.length?names.join(', ').replace(/^./,c=>c.toUpperCase()):'Rien de configuré';
}
export function warningId(key:string,id:string){return key+':'+id;}
