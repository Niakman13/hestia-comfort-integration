export const LEVELS = ['calm','benefit','action','urgent','neutral'] as const;
export const ACTIONS = ['ok','ouvrir','fermer','attendre','unknown'] as const;
export const MODULES = ['windows','air','temperature','humidity','shutters','coordination'] as const;
export type Level = typeof LEVELS[number];
export type Module = typeof MODULES[number];
export type Format = 'mini'|'tile'|'intermediate'|'full';
export const moduleLabels:Record<Module,string>={windows:'Fenêtres',air:'Qualité de l’air',temperature:'Température',humidity:'Humidité',shutters:'Soleil et volets',coordination:'Chauffage'};
export interface Config {
  type: 'custom:niak-comfort-card'; entry_id?: string; title?: string; format?: Format;
  modules?: Module[]; animations?: boolean; glass_effect?: boolean; theme?: 'auto'|'light'|'dark';
  /** What the card shows and how it opens: the scale, the measures, the details, and whether advices scroll by themselves. */
  show_scale?: boolean; show_measures?: boolean; show_details?: boolean; measures_open?: boolean; details_open?: boolean; rotate?: boolean;
}
export interface Reading {
  value: number|boolean|string|null; quality:'valid'|'unknown'|'stale'|'estimated';
  source:string|null; received_at:string|null; detail:string|null; unit:string|null;
}
export interface Features {
 shutters?:{entity_id:string;mode:'none'|'manual'|'connected';position:number|null;state:string|null;advice:'close'|'open'|null;message:string;shade_fraction:number|null;shade_model:'geometry'|'simple'|'unknown';manual_override:boolean|null;automatic:boolean|null}[];
 presence?:{state:'occupied'|'empty'|'unknown'|'not_configured';message:string};
 air?:{co2_status?:'high'|'ok'|'unknown'|'not_configured';pm25_status:'high'|'ok'|'unknown'|'not_configured';voc_status:'high'|'ok'|'uninterpreted'|'unknown'|'not_configured';voc_unit:string|null;purifier:{on:boolean|null;speed:number|null};pm25_treated?:boolean;ventilation?:{on:boolean|null;boost?:boolean}|null;coverage:string;message:string};
 ventilation?:{opened_minutes:number|null;duration_minutes:{min:number;max:number}|null;message:string;capacity:number|null};
 humidity?:{dew_point:number|null;incoming_relative:number|null;glass_temperature:number|null;condensation_risk:boolean|null;message:string};
 /** What airing would really bring, from the room's past openings: humidity now and after, lasting gain in points. */
 drying?:{minutes:number;now:number;after:number;gain:number;tau:number;openings:number;later:{minutes:number;now:number;after:number;gain:number;time:string}|null}|null;
 trends?:{indoor:number|null;outdoor:number|null;window_minutes:number;message:string};
 season?:{known:boolean;weight:number|null;outdoor_mean:number|null;minimum:number;maximum:number;heated:boolean};
 day_range?:{min:number;max:number}|null;
}
export interface Assessment {
  features?:Features;
  action:typeof ACTIONS[number]; level:Level; reason:string;
  needs:string[]; constraints:string[]; opportunities:string[]; partial:boolean; missing:string[];
  heating_action:string; indoor_absolute_humidity:number|null; outdoor_absolute_humidity:number|null;
  temperature_delta:number|null; coordination:string;
  openings?:Opening[]; sun?:{elevation:number;azimuth:number}|null; unverified?:string[]; wind_bearing?:number|null; crossing?:string|null; open_first?:string[];
  slot?:{kind:'open'|'close';time:string;temperature:number;wind_bearing:number|null}|null; rain_soon_minutes?:number|null;
}
export interface Opening {
  entity_id:string; open:boolean|null; exposure:string|null; kind:string; sheltered:boolean;
  sun_share:number; sun_wm2:number|null; wind_side?:string|null; flags:string[];
}
export interface View {
  version:1; entry_id:string; area_id:string|null; title:string; computed_at:string;
  assessment:Assessment; observations:Record<string,Reading>; names?:Record<string,string>;
}
export interface ViewEvent {version:1; view?:View; reload?:boolean; unavailable?:boolean}
export type Unsubscribe = () => Promise<void>|void;
export interface Connection {
  subscribeMessage<T>(callback:(event:T)=>void, message:Record<string,unknown>):Promise<Unsubscribe>;
}
export interface HomeAssistant {
  connection:Connection; user?:{is_admin:boolean}; themes?:{darkMode?:boolean};
  callWS<T>(message:Record<string,unknown>):Promise<T>;
}
export interface Entry {entry_id:string; title:string; area_id:string|null}
export function cleanConfig(input:Config):Config {
  if(!input || input.type!=='custom:niak-comfort-card') throw new Error('Type de carte Niak Comfort invalide.');
  if(input.format && !['mini','tile','intermediate','full'].includes(input.format)) throw new Error('Format de carte inconnu.');
  if(input.entry_id!==undefined && typeof input.entry_id!=='string') throw new Error('Choisissez une pièce Niak Comfort.');
  if(input.title!==undefined && typeof input.title!=='string') throw new Error('Le titre doit être un texte.');
  if(input.theme && !['auto','light','dark'].includes(input.theme)) throw new Error('Thème inconnu.');
  for(const key of ['animations','glass_effect','show_scale','show_measures','show_details','measures_open','details_open','rotate'] as const)
    if(input[key]!==undefined && typeof input[key]!=='boolean') throw new Error('Réglage d’affichage invalide.');
  if(input.modules && (!Array.isArray(input.modules) || input.modules.some(m=>!MODULES.includes(m)))) throw new Error('Rubrique inconnue.');
  return {...input, format:input.format??'tile', modules:[...new Set(input.modules??MODULES)]};
}

/** The home card's settings: the same display choices as a room card, rooms instead of measures. */
export interface HomeConfig {type:'custom:niak-comfort-home-card';title?:string;theme?:'auto'|'light'|'dark';
  rotate?:boolean;show_scale?:boolean;show_rooms?:boolean;rooms_open?:boolean;show_details?:boolean;details_open?:boolean;
  animations?:boolean;glass_effect?:boolean}
export const HOME_FLAGS=['rotate','show_scale','show_rooms','rooms_open','show_details','details_open','animations','glass_effect'] as const;
export function cleanHomeConfig(input:HomeConfig):HomeConfig {
  if(!input||input.type!=='custom:niak-comfort-home-card')throw new Error('Type de carte invalide.');
  if(input.title!==undefined&&typeof input.title!=='string')throw new Error('Le titre doit être un texte.');
  if(input.theme&&!['auto','light','dark'].includes(input.theme))throw new Error('Thème inconnu.');
  for(const k of HOME_FLAGS)if(input[k]!==undefined&&typeof input[k]!=='boolean')throw new Error('Réglage d’affichage invalide.');
  return {...input};
}
