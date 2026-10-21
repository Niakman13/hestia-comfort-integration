export const LEVELS = ['calm','benefit','action','urgent','neutral'] as const;
export const ACTIONS = ['ok','ouvrir','fermer','attendre','unknown'] as const;
export const MODULES = ['windows','air','temperature','humidity','shutters','coordination'] as const;
export type Level = typeof LEVELS[number];
export type Module = typeof MODULES[number];
/** Like Niak Weather: full, tile (folds), intermediate (the tile unfolded), mini (one line), measures (the tiles alone),
 *  alert (only while a gesture is asked, hidden otherwise). */
export const FORMATS = ['full','tile','intermediate','mini','measures','alert'] as const;
export type Format = typeof FORMATS[number];
/** What scrolls after the advice of the moment: remedies at work (purifier, ventilation), a better moment later. */
export const BANNER_BLOCKS = ['remedies','later'] as const;
export type BannerBlock = typeof BANNER_BLOCKS[number];
/** Marks of the temperature scale; none removes the scale. */
export const SCALE_MARKS = ['band','day','out'] as const;
export type ScaleMark = typeof SCALE_MARKS[number];
/** Chips under the advice of a folded tile, and values on a mini line. */
export const CHIPS = ['temperature','humidity','co2'] as const;
export type Chip = typeof CHIPS[number];
/** What an unfolded tile shows, in this order. */
export const TILE_BLOCKS = ['scale','measures','details'] as const;
export type TileBlock = typeof TILE_BLOCKS[number];
/** A long press (a tap on mini and alert): the full card in a window, a dashboard page, or nothing. */
export const HOLD_ACTIONS = ['popup','page','none'] as const;
export type HoldAction = typeof HOLD_ACTIONS[number];
export const moduleLabels:Record<Module,string>={windows:'Fenêtres',air:'Qualité de l’air',temperature:'Température',humidity:'Humidité',shutters:'Soleil et volets',coordination:'Chauffage'};
export interface Config {
  type: 'custom:niak-comfort-card'; entry_id?: string; title?: string; format?: Format;
  modules?: Module[]; animations?: boolean; glass_effect?: boolean; theme?: 'auto'|'light'|'dark';
  /** What the card shows and how it opens: the scale, the measures, the details, and whether advices scroll by themselves. */
  show_scale?: boolean; show_measures?: boolean; show_details?: boolean; measures_open?: boolean; details_open?: boolean; rotate?: boolean;
  banner_blocks?: BannerBlock[]; scale_marks?: ScaleMark[]; tile_chips?: Chip[]; tile_blocks?: TileBlock[]; mini_values?: Chip[];
  hold_action?: HoldAction; hold_path?: string;
}
/** A list setting: only known values, each once, in the given order. */
function list<T extends string>(value:unknown,known:readonly T[],name:string):T[]|undefined{
  if(value===undefined)return undefined;
  if(!Array.isArray(value)||value.some(v=>!known.includes(v)))throw new Error(`Réglage « ${name} » invalide.`);
  return [...new Set(value as T[])];
}
function hold(input:{hold_action?:unknown;hold_path?:unknown}){
  if(input.hold_action!==undefined&&!HOLD_ACTIONS.includes(input.hold_action as HoldAction))throw new Error('Appui long inconnu.');
  if(input.hold_path!==undefined&&typeof input.hold_path!=='string')throw new Error('La page à ouvrir doit être un chemin.');
}
export interface Reading {
  value: number|boolean|string|null; quality:'valid'|'unknown'|'stale'|'estimated';
  source:string|null; received_at:string|null; detail:string|null; unit:string|null;
}
export interface Features {
 shutters?:{entity_id:string;mode:'none'|'manual'|'connected';position:number|null;state:string|null;advice:'close'|'open'|null;message:string;shade_fraction:number|null;shade_model:'geometry'|'simple'|'unknown';manual_override:boolean|null;automatic:boolean|null;
  cover?:string|null;driver?:'adaptive_cover_pro'|null;sun_front?:boolean|null;target?:number|null;sun_start?:string|null;sun_end?:string|null;soon?:boolean;driving?:boolean;off?:'disabled'|'auto'|'tracking'|null;detection?:boolean|null;climate?:boolean|null;reason?:string|null;override_end?:string|null}[];
 presence?:{state:'occupied'|'empty'|'unknown'|'not_configured';message:string};
 air?:{co2_status?:'high'|'ok'|'unknown'|'not_configured';pm25_status:'high'|'ok'|'unknown'|'not_configured';voc_status:'high'|'ok'|'uninterpreted'|'unknown'|'not_configured';voc_unit:string|null;purifier:{on:boolean|null;speed:number|null};pm25_treated?:boolean;ventilation?:{on:boolean|null;boost?:boolean}|null;coverage:string;message:string};
 ventilation?:{opened_minutes:number|null;duration_minutes:{min:number;max:number}|null;message:string;capacity:number|null};
 humidity?:{dew_point:number|null;incoming_relative:number|null;glass_temperature:number|null;condensation_risk:boolean|null;message:string;
  /** Air against the coldest spot of the outer walls (%), mould risk, water above outdoors (g/m³), where it comes from, best reachable by airing (%). */
  surface?:number|null;mould?:boolean;excess?:number|null;local?:number|null;source?:'inside'|'outside'|null;reachable?:number|null};
 /** What airing would really bring, from the room's past openings: humidity now and after, lasting gain in points. */
 rain_ahead?:{minutes:number;precise:boolean}|null;
 /** A gesture whose result the room's twin predicts, once it has proved itself in this room. */
 learned?:{now:number;after:number;minutes:number;measure:'humidity'|'temperature'|'co2'|'voc';openings:number;days:number;precision:{temperature:number;humidity:number}}|null;
 volume?:{lead:string;reason:string;action:string;assessment?:Partial<Assessment>&{reason:string};observations?:Record<string,Reading>};
 warmth?:{occupied:boolean|null;heating:'on'|'off'|null}|null;
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
  assessment:Assessment; observations:Record<string,Reading>; names?:Record<string,string>; /** Rooms open onto this one: one air, shared openings. */ volume?:{entry_id:string;title:string}[]; /** « Salon · Cuisine », the best equipped first. */ volume_name?:string|null;
  /** The feedback loop: the last airing followed (within a day) and the week (engine/feedback.py). */
  feedback?:{last:{measure:'humidity'|'temperature'|'co2'|'voc';before:number;after:number;predicted:number|null;minutes:number}|null;week:{followed:number;ignored:number;evaluated:number;held:number;gains:Record<string,number>}};
  /** A humidity habit the person confirmed, going on now: the words for « À savoir ». */ habit?:string|null;
  /** What the room's twin has learned so far (engine/twin.py). */ twin?:{status:'learning'|'ready';days:number;samples:number;next_hour:{temperature:number;humidity:number}|null;precision:{hours:number;temperature:number;humidity:number}|null;
    /** How much of the room is learned: 100 % once everything it has is seen. */ progress?:{percent:number;complete:boolean;parts:Partial<Record<'days'|'precision'|'sun'|'windows'|'heating'|'air',number>>;seen:{days:number;airings:number}}}; /** Home Assistant (or the room) has just started: silent sensors are still loading. */ starting?:boolean;
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
export interface Entry {entry_id:string; title:string; area_id:string|null; volume?:string[]; volume_name?:string|null}
export function cleanConfig(input:Config):Config {
  if(!input || input.type!=='custom:niak-comfort-card') throw new Error('Type de carte Niak Comfort invalide.');
  if(input.format && !FORMATS.includes(input.format)) throw new Error('Format de carte inconnu.');
  if(input.entry_id!==undefined && typeof input.entry_id!=='string') throw new Error('Choisissez une pièce Niak Comfort.');
  if(input.title!==undefined && typeof input.title!=='string') throw new Error('Le titre doit être un texte.');
  if(input.theme && !['auto','light','dark'].includes(input.theme)) throw new Error('Thème inconnu.');
  for(const key of ['animations','glass_effect','show_scale','show_measures','show_details','measures_open','details_open','rotate'] as const)
    if(input[key]!==undefined && typeof input[key]!=='boolean') throw new Error('Réglage d’affichage invalide.');
  if(input.modules && (!Array.isArray(input.modules) || input.modules.some(m=>!MODULES.includes(m)))) throw new Error('Rubrique inconnue.');
  hold(input);
  const lists={banner_blocks:list(input.banner_blocks,BANNER_BLOCKS,'bandeau'),scale_marks:list(input.scale_marks,SCALE_MARKS,'échelle'),
    tile_chips:list(input.tile_chips,CHIPS,'pastilles'),tile_blocks:list(input.tile_blocks,TILE_BLOCKS,'tuile dépliée'),mini_values:list(input.mini_values,CHIPS,'ligne')};
  return {...input,...Object.fromEntries(Object.entries(lists).filter(([,v])=>v!==undefined)), format:input.format??'tile', modules:[...new Set(input.modules??MODULES)]};
}

/** The home card's settings: the same display choices as a room card, rooms instead of measures. */
export const HOME_FORMATS = ['full','tile','list','mini','alert'] as const;
export type HomeFormat = typeof HOME_FORMATS[number];
/** What scrolls in the home banner: the rooms' advice, and gestures for the whole house (cross ventilation). */
export const HOME_BANNER = ['rooms','house'] as const;
export interface HomeConfig {type:'custom:niak-comfort-home-card';title?:string;theme?:'auto'|'light'|'dark';format?:HomeFormat;
  rotate?:boolean;show_scale?:boolean;show_rooms?:boolean;rooms_open?:boolean;show_details?:boolean;details_open?:boolean;
  animations?:boolean;glass_effect?:boolean;banner_blocks?:(typeof HOME_BANNER[number])[];list_order?:'urgent'|'floor';
  hold_action?:HoldAction;hold_path?:string}
export const HOME_FLAGS=['rotate','show_scale','show_rooms','rooms_open','show_details','details_open','animations','glass_effect'] as const;
export function cleanHomeConfig(input:HomeConfig):HomeConfig {
  if(!input||input.type!=='custom:niak-comfort-home-card')throw new Error('Type de carte invalide.');
  if(input.title!==undefined&&typeof input.title!=='string')throw new Error('Le titre doit être un texte.');
  if(input.theme&&!['auto','light','dark'].includes(input.theme))throw new Error('Thème inconnu.');
  for(const k of HOME_FLAGS)if(input[k]!==undefined&&typeof input[k]!=='boolean')throw new Error('Réglage d’affichage invalide.');
  if(input.format&&!HOME_FORMATS.includes(input.format))throw new Error('Format de carte inconnu.');
  if(input.list_order!==undefined&&!['urgent','floor'].includes(input.list_order))throw new Error('Ordre des pièces inconnu.');
  hold(input);
  const banner=list(input.banner_blocks,HOME_BANNER,'bandeau');
  return {...input,...(banner?{banner_blocks:banner}:{})};
}
/** What a long press does on the home card: a page when one is set, else a window, except on the full card (nothing). */
export const homeAction=(c:HomeConfig)=>c.hold_action??(c.hold_path?'page':(c.format??'full')==='full'?'none':'popup');
