export const labels:Record<string,string>={indoor_temperature:'Température de la pièce',indoor_humidity:'Humidité de la pièce',co2:'CO₂',pm25:'Particules fines PM2.5',voc:'Composés organiques volatils (COV)',purifier:'Purificateur',ventilation:'Ventilation (VMC)',ventilation_boost:'Vitesse rapide de la VMC (Turbo)',presence:'Présence dans la pièce',illuminance:'Luminosité',windows:'Fenêtres et portes vers l’extérieur',heating:'Chauffage',outdoor_temperature:'Température dehors',outdoor_humidity:'Humidité dehors',rain:'Pluie actuelle',wind_gust:'Rafales de vent',wind_bearing:'Direction du vent',solar:'Ensoleillement',pollution:'Qualité de l’air extérieur'};
export const indoor=['indoor_temperature','indoor_humidity'] as const;
export const outdoor=['outdoor_temperature','outdoor_humidity','rain','wind_gust','wind_bearing','solar','pollution'] as const;
export const multiple=new Set(['windows','presence']);
export const exposures:[string,string][]=[['N','Nord'],['NE','Nord-est'],['E','Est'],['SE','Sud-est'],['S','Sud'],['SO','Sud-ouest'],['O','Ouest'],['NO','Nord-ouest']];
export const kinds:[string,string][]=[['window','Fenêtre'],['french','Porte-fenêtre ou baie'],['skylight','Vasistas ou petite fenêtre'],['door','Porte']];
export interface Candidate {
 entity_id:string;name:string;value:string;unit:string|null;area_id:string|null;
 local:boolean;outside:boolean;reference:boolean;available:boolean;adapter:string;warnings:string[];
 provenance:{entity_id:string;name:string;area_id:string|null}[];device_class:string|null;atmo_label:string|null;
 voc_reference?:{id:'sensirion_index';value:number;unit:string}|null;
}
export interface Spec {entity_id:string;adapter:string;block_from?:number}
export interface OpeningMeta {exposure:string|null;kind:string;sheltered:boolean;shutter?:'none'|'manual'|'connected';cover_entity?:string;auto_entity?:string;override_entity?:string;width?:number;height?:number;overhang_depth?:number;overhang_gap?:number}
export interface EvolutionConfig {voc_threshold?:{value:number;unit:string};glazing_factor?:number;presence_delay_minutes?:number}
export interface RoomConfig {presence?:string[];evolution?:EvolutionConfig;floor_id?:string|null;area_id:string|null;name:string;sources:Record<string,string>;windows:string[];openings:Record<string,OpeningMeta>;settings:Record<string,number>;acknowledged?:string[];use_home?:boolean;rain_exposed?:boolean;heated?:boolean;open_to?:string[]}
export interface Room {entry_id:string;title:string;loaded:boolean;config:RoomConfig}
export interface Area {floor_id?:string|null;area_id:string;name:string;outdoor:boolean}
export interface Snapshot {version:1;revision:string;floors?:{floor_id:string;name:string;level:number|null}[];areas:Area[];rooms:Room[];home:{configured:boolean;sources:Record<string,Spec>;acknowledged?:string[];weather?:string|null};niak_weather?:{installed:boolean;places:{entry_id:string;title:string}[]};integrations?:{atmofrance?:boolean}}
export interface Discovery {version:1;revision:string;candidates:Record<string,Candidate[]>;suggestions:Record<string,string|string[]>;drivers?:Record<string,Driver>}
export interface DriverSignal {entity_id:string;name:string;on:boolean}
export interface Driver {name:string;auto:string|null;override:string|null;signals?:Partial<Record<'enabled'|'auto'|'tracking'|'detection'|'override'|'sun'|'climate',DriverSignal|null>>;azimuth?:number|null;exposure?:string|null;width?:number|null;height?:number|null}
// The technical state of the home (health.py): orange (bad) stops something, tip could be better, none is not used.
export type Level='ok'|'bad'|'tip'|'none';
export type Target={kind:'room';entry_id:string;label:string}|{kind:'exterior';label:string}|{kind:'area';area_id:string;label:string};
/** « Ce que Niak a appris » : what each room's twin learned, and how well it replays the last 24 hours. */
export interface TwinRoom {inertia_hours:number;sun_degrees:number|null;heating_degrees:number|null;household_degrees:number;window_half_minutes:number|null;air_changes_per_hour:number;window_air_changes_per_hour:number|null;water_per_hour:number}
export interface Twin {status:'learning'|'ready';samples:number;days:number;open_samples?:number;room?:TwinRoom|null;
 precision?:{hours:number;temperature:number;humidity:number;curve:{time:string;temperature:number;measured_temperature:number;humidity:number;measured_humidity:number}[]}|null;next_hour?:{temperature:number;humidity:number}|null}
export interface Twins {version:1;rooms:{entry_id:string;title:string;twin:Twin}[]}
export interface HealthLine {level:Level;text:string;why:string;target?:Target|null}
export interface Health {level:'ok'|'action';summary:string;tips_summary:string;rooms_summary:string;todo:HealthLine[];tips:HealthLine[];
 sources:{label:string;level:Level;text:string}[];columns:string[];rooms:{entry_id:string;title:string;cells:{level:Level;text:string}[]}[];versions:HealthLine[]}
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
 const sources:Record<string,string>={};for(const key of [...indoor,'illuminance','co2','pm25','voc','purifier','ventilation','ventilation_boost','heating']){const value=d.suggestions[key];if(typeof value==='string')sources[key]=value;}
 const windows=Array.isArray(d.suggestions.windows)?[...d.suggestions.windows]:[];
 const voc= d.candidates?.voc?.find(c=>c.entity_id===sources.voc),preset=vocPreset(voc);
 return {area_id:area?.area_id??null,name:area?.name??name,sources,presence:Array.isArray(d.suggestions.presence)?[...d.suggestions.presence]:[],windows,openings:Object.fromEntries(windows.map(id=>[id,defaultOpening()])),settings:{minimum:20,maximum:24,summer_maximum:26,...airReferenceDefaults},...(preset?{evolution:{voc_threshold:preset}}:{}),acknowledged:[]};
}
// New rooms use these explained operating choices. Existing settings are never
// replaced when opening the editor; backend defaults preserve older rooms.
export const airReferenceDefaults={co2_potential:800,co2_action:1000,co2_urgent:1500,pm25_action:15,humidity_high:60};
export function vocPreset(c?:Candidate):{value:number;unit:string}|undefined {
 const r=c?.voc_reference;
 return r?.id==='sensirion_index'&&r.unit===(c?.unit??'')?{value:r.value,unit:r.unit}:undefined;
}
export const thresholdSources={
 co2:'https://www.hcsp.fr/hcspi/Explore.cgi/avisrapportsdomaine?clefr=1154',
 pm25:'https://www.who.int/fr/news-room/questions-and-answers/item/who-global-air-quality-guidelines',
 voc:'https://sensirion.com/en/media/documents/02232963/6294E043/Info_Note_VOC_Index.pdf',
 tvoc:'https://www.umweltbundesamt.de/en/topics/health/commissions-working-groups/german-committee-on-indoor-air-guide-values',
 humidity:'https://agirpourlatransition.ademe.fr/particuliers/proteger-sante/eviter-polluants/respirer-air-sain-chez-soi',
};
export function coverage(room:RoomConfig):string {
 const parts=[];if(room.sources.indoor_temperature)parts.push('Température');if(room.sources.indoor_humidity)parts.push('humidité');if(room.sources.co2)parts.push('CO₂');
 const n=room.windows.length;
 return (parts.join(', ')||'Mesures à compléter')+' · '+(n?n+' ouvrant'+(n>1?'s':''):'fenêtres non mesurées');
}
const shortNames:Record<string,string>={outdoor_temperature:'température',outdoor_humidity:'humidité',rain:'pluie',wind_gust:'rafales',wind_bearing:'direction du vent',solar:'ensoleillement',pollution:'qualité de l’air'};
export function exteriorSummary(sources:Record<string,Spec>):string {
 const names=outdoor.filter(k=>sources[k]).map(k=>shortNames[k]);
 return names.length?names.join(', ').replace(/^./,c=>c.toUpperCase()):'Rien de configuré';
}
export function warningId(key:string,id:string){return key+':'+id;}

// The steps of a room, named by what they set (charte des onglets de réglage, ECOSYSTEME.md § 8).
export const stages=['Température et humidité','Fenêtres et portes','Qualité de l’air','Chauffage','La pièce et ses réglages','Récapitulatif'];
// What each step is for, shown on top of it in a frame that folds: one idea per line.
export const intros:Record<string,string[]>={
 0:['La température de la pièce : la seule mesure obligatoire.',
  'L’humidité est facultative : elle repère un air trop humide.',
  'Niak propose les capteurs de la pièce ; vous les gardez, les changez ou les retirez.'],
 1:['Les contacts des fenêtres et portes qui donnent dehors.',
  'Niak sait ce qui est ouvert ; l’exposition dit quand le soleil entre.',
  'Facultatif : sans contact, les conseils ne savent pas ce qui est ouvert.'],
 2:['Le CO₂, les particules et les COV suivent chacun une partie de la qualité de l’air.',
  'Tout est facultatif. Un purificateur ne retire pas le CO₂.'],
 3:['Le thermostat ou la vanne de la pièce, pour savoir si le chauffage tourne.',
  'Niak évite alors de conseiller d’ouvrir pendant qu’il chauffe. Il ne commande rien.',
  'Facultatif.'],
 4:['Le nom de la pièce et sa pièce Home Assistant.',
  'Les précautions et les autres paramètres de fonctionnement, facultatifs.',
  'Chaque seuil d’interprétation se règle avec son capteur, dans les étapes précédentes.'],
 5:['Tout ce que vous avez choisi, onglet par onglet.',
  'Rien ne change tant que vous n’avez pas enregistré ; un oubli, revenez à l’onglet voulu.'],
 exterior:['Les mesures du dehors : température, pluie, vent, soleil, qualité de l’air.',
  'Choisies une fois, elles servent à toutes vos pièces.',
  'Toutes sont facultatives ; chacune rend les conseils plus justes.'],
};
// The exterior sensors, by frame: title and keys.
export const outdoorGroups:[string,string[]][]=[['Température et humidité',['outdoor_temperature','outdoor_humidity']],['Pluie et vent',['rain','wind_gust','wind_bearing']],['Soleil',['solar']]];
// Only the settings still displayed inside the "Autres réglages" advanced frame.
export const advancedDefaults:Record<string,number>={illuminance_low:100,gust_max:45,frost:1,sun_facade:250,max_age_seconds:10800};
export function changedAdvanced(settings:Record<string,number>):number{return Object.entries(advancedDefaults).filter(([k,v])=>settings[k]!==undefined&&settings[k]!==v).length;}
// One source in a list chosen by integration: its name, what it gives, and how to install it when missing.
export interface Choice {value:string;label:string;hint:string;available:boolean;missing?:string;url?:string}
export const links={atmofrance:'https://github.com/sebcaps/atmofrance',niak_weather:'https://github.com/Niakman13/niak-weather-integration'};
// The integration behind an outdoor air quality source.
export function airSource(spec?:Spec):string{return !spec?'none':spec.adapter==='atmo_daily'?'atmo':spec.adapter==='niak_index'?'niak':'other';}
// The air quality sources, by integration, « Pas de … » last.
export function airChoices(s:Pick<Snapshot,'niak_weather'|'integrations'>,all:Candidate[],current:string):Choice[]{
 const atmo=all.some(c=>c.adapter==='atmo_daily'),niak=all.some(c=>c.adapter==='niak_index'),nw=!!s.niak_weather?.installed;
 const list:Choice[]=[
  {value:'atmo',label:'Atmo France',hint:'L’indice ATMO du jour, pour votre zone.',available:atmo,
   ...(atmo?{}:s.integrations?.atmofrance?{missing:'Aucune zone trouvée : ajoutez-en une dans l’intégration Atmo France.'}:{missing:'Pas encore installée',url:links.atmofrance})},
  {value:'niak',label:'Niak Weather',hint:'L’indice de qualité de l’air de votre lieu Niak Weather.',available:niak,
   ...(niak?{}:nw?{missing:'Activez la qualité de l’air dans l’onglet Météo.'}:{missing:'Pas encore installée',url:links.niak_weather})}];
 if(current==='other')list.push({value:'other',label:'Autre signal',hint:'Un capteur choisi avant cette version.',available:true});
 list.push({value:'none',label:'Pas de qualité de l’air',hint:'Les conseils ne tiennent pas compte de la pollution.',available:true});
 return list;
}
// Where the exterior measures come from: Niak Weather's station, or the person's own sensors.
export function exteriorChoices(s:Pick<Snapshot,'niak_weather'>):Choice[]{
 const nw=s.niak_weather,ready=!!nw?.installed&&!!nw.places.length;
 return [{value:'weather',label:'Niak Weather',hint:'Reprend la station de votre lieu, ses alertes et ses prévisions.',available:ready,
   ...(ready?{}:nw?.installed?{missing:'Aucun lieu dans l’onglet Météo pour l’instant.'}:{missing:'Pas encore installée',url:links.niak_weather})},
  {value:'own',label:'Vos propres capteurs',hint:'Choisissez-les un par un ci-dessous ; tous sont facultatifs.',available:true}];
}
