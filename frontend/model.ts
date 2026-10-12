export const labels:Record<string,string>={indoor_temperature:'Température de la pièce',indoor_humidity:'Humidité de la pièce',co2:'CO₂',windows:'Fenêtres et portes vers l’extérieur',heating:'Chauffage',outdoor_temperature:'Température dehors',outdoor_humidity:'Humidité dehors',rain:'Pluie actuelle',pollution:'Qualité de l’air extérieur'};
export const indoor=['indoor_temperature','indoor_humidity','co2'] as const;
export const outdoor=['outdoor_temperature','outdoor_humidity','rain','pollution'] as const;
export interface Candidate {
 entity_id:string;name:string;value:string;unit:string|null;area_id:string|null;
 local:boolean;reference:boolean;available:boolean;adapter:string;warnings:string[];
 provenance:{entity_id:string;name:string;area_id:string|null}[];device_class:string|null;atmo_label:string|null;
}
export interface Spec {entity_id:string;adapter:string;block_from?:number}
export interface RoomConfig {area_id:string;name:string;sources:Record<string,string>;windows:string[];settings:Record<string,number>;use_home?:boolean;rain_exposed?:boolean}
export interface Room {entry_id:string;title:string;loaded:boolean;config:RoomConfig}
export interface Snapshot {version:1;revision:string;areas:{area_id:string;name:string}[];rooms:Room[];home:{configured:boolean;sources:Record<string,Spec>}}
export interface Discovery {version:1;revision:string;candidates:Record<string,Candidate[]>;suggestions:Record<string,string|string[]>}
export interface Hass {callWS<T>(msg:Record<string,unknown>):Promise<T>;user?:{is_admin:boolean};themes?:{darkMode?:boolean};connection?:unknown}
export const warningText:Record<string,string>={
 alias:'Cette entité reprend une autre mesure. Vérifiez sa provenance ci-dessous.',
 other_area:'La mesure ou sa source appartient à une autre pièce. Confirmez qu’elle représente bien celle-ci.',
 contact_role:'Ce contact peut être une porte d’appareil, de meuble ou une porte intérieure. Utilisez-le seulement s’il donne sur l’extérieur.',
 derived:'Il s’agit d’une donnée calculée ou regroupée. Vérifiez ce qu’elle mesure réellement.',
 no_hvac_action:'Cet équipement ne fournit pas actuellement son action réelle. Niak pourra seulement afficher une observation inconnue.',
 binary_meaning:'Signal avancé : actif doit signifier pluie ou aération déconseillée selon le champ. Un diagnostic de panne ne convient pas.',
 outdoor_role:'Vérifiez que cette mesure concerne bien l’air extérieur. L’emplacement de la station ne permet pas de distinguer ses capteurs intérieurs et extérieurs.',
 daily_forecast:'Indice régional prévu pour la journée. Il peut déclencher votre précaution, mais ne prouve pas la qualité de l’air maintenant à vos fenêtres.'
};
export function measurement(c:Candidate):string {
 if(!c.available)return 'Temporairement indisponible';
 if(c.atmo_label)return c.atmo_label+' · indice du jour';
 if(c.value==='on'||c.value==='off')return c.device_class==='window'||c.device_class==='door'||c.device_class==='opening'?(c.value==='on'?'Ouvert':'Fermé'):(c.value==='on'?'Actif':'Inactif');
 return c.value+(c.unit?' '+c.unit:'');
}
export function newRoom(area:{area_id:string;name:string},d:Discovery,shared:boolean):RoomConfig {
 const sources:Record<string,string>={};for(const key of [...indoor,'heating']){const value=d.suggestions[key];if(typeof value==='string')sources[key]=value;}
 return {area_id:area.area_id,name:area.name,sources,windows:Array.isArray(d.suggestions.windows)?[...d.suggestions.windows]:[],settings:{minimum:20,maximum:24},use_home:shared,rain_exposed:true};
}
export function coverage(room:RoomConfig):string {
 const parts=[];if(room.sources.indoor_temperature)parts.push('Température');if(room.sources.indoor_humidity)parts.push('humidité');if(room.sources.co2)parts.push('CO₂');
 return (parts.join(', ')||'Mesures à compléter')+' · '+(room.windows.length?room.windows.length+' contact'+(room.windows.length>1?'s':''):'fenêtres non mesurées');
}
export function warningId(key:string,id:string){return key+':'+id;}
