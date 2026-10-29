import {LitElement,html,css,nothing} from 'lit';
import {property,state} from 'lit/decorators.js';
import {SECTIONS,SECTION_LABELS,SHOWN_SECTIONS,FOLDED_SECTIONS} from './views/homeboard';
import {t,th,fr,setLanguage} from './i18n';
import {cleanConfig,cleanHomeConfig,MODULES,moduleLabels,SCALE_MARKS,CHIPS,TILE_BLOCKS,HORIZON_SUBJECTS,INSIGHT_TOPICS,DETAIL_ROWS,homeAction,type Config,type HomeConfig,type HomeAssistant,type Entry} from './types';

/* The editors are built like Hestia Weather's: the room (or title) and the format on top, then folding groups that
   change with the format. The theme follows Home Assistant: it is no longer offered. */
type Item={name:string;title?:string};
const toggle=(name:string)=>({name,selector:{boolean:{}}});
const group=(title:string,icon:string,schema:unknown[],expanded=false)=>({type:'expandable',name:'',title:t(title),icon,flatten:true,expanded,schema});
const choices=(name:string,options:[string,string][])=>({name,selector:{select:{multiple:true,reorder:true,mode:'list',options:options.map(([value,label])=>({value,label:t(label)}))}}});
const dropdown=(name:string,options:[string,string][])=>({name,required:true,selector:{select:{mode:'dropdown',options:options.map(([value,label])=>({value,label:t(label)}))}}});
const look=(expanded=true)=>group(fr('Apparence'),'mdi:palette-outline',[toggle('animations'),toggle('glass_effect')],expanded);
/** On a full card, the full card in a window would show itself again: only a page, or nothing. */
const hold=(action:string,full=false)=>group(fr('Appui long'),'mdi:gesture-tap-hold',[
  dropdown('hold_action',full?[['none',fr('Rien')],['page',fr('Ouvrir une page')]]:[['popup',fr('Ouvrir la carte complète en fenêtre')],['page',fr('Ouvrir une page')],['none',fr('Rien')]]),
  ...(action==='page'?[{name:'hold_path',selector:{text:{}}}]:[])]);
const chipOptions:[string,string][]=[['temperature',fr('Température')],['humidity',fr('Humidité')],['co2','CO₂']];
const topicOptions:[string,string][]=[['humidity',fr('Humidité')],['heating',fr('Chauffage')],['sun',fr('Soleil')],['windows',fr('Fenêtres et aération')],['equipment',fr('Équipements (purificateur, VMC)')],
  ['household',fr('Personnes et alarme')],['forecast',fr('Prévisions (cette nuit)')],['learning',fr('Apprentissage (dernière aération)')]];
const detailOptions:[string,string][]=[['range',fr('Plage de confort')],['slot',fr('Créneau conseillé')],['windows',fr('Fenêtres')],['shutters',fr('Volets')],['people',fr('Présence, personnes, alarme')],
  ['drying',fr('Séchage et buée')],['trend',fr('Tendance')],['sensors',fr('Capteurs et sources')]];
/** The four sections of the card, in its order: the same number in the editor and on the card. */
// The advice itself is the card: it is never switched off. The scale and the graph are shown or not, nothing more.
const scaleToggle={name:'show_scale',title:fr('Échelle de température'),selector:{boolean:{}}};
const horizonMode=dropdown('horizon_mode',[['needed',fr('Seulement quand il aide le conseil')],['always',fr('Toujours (la tendance sans conseil)')]]);
const banner=(expanded=true)=>group(fr('1 · Bandeau conseil'),'mdi:numeric-1-circle',[toggle('rotate'),scaleToggle,toggle('show_horizon'),horizonMode],expanded);
const insights=()=>group(fr('2 · À savoir'),'mdi:numeric-2-circle',[toggle('show_insights'),choices('insight_topics',topicOptions),{name:'insight_max',selector:{number:{min:1,max:8,mode:'slider'}}}]);
const details=()=>group(fr('4 · Détails techniques'),'mdi:numeric-4-circle',[toggle('show_details'),choices('detail_rows',detailOptions),toggle('details_open')]);
/** One choice per air: rooms open onto each other are offered once, as « Salon · Cuisine ». A card already set on one of
    them keeps its room as the value, so that nothing moves. */
export function roomChoices(entries:Entry[],current?:string):{value:string;label:string}[] {
  const out:{value:string;label:string}[]=[],done=new Set<string>();
  for(const e of entries){
    if(done.has(e.entry_id))continue;
    const group=[e.entry_id,...(e.volume??[])];group.forEach(id=>done.add(id));
    // The best equipped room leads, as in the volume's name (« Salon · Cuisine »).
    const lead=entries.find(x=>group.includes(x.entry_id)&&x.title===e.volume_name?.split(' · ')[0])?.entry_id??e.entry_id;
    const value=current&&group.includes(current)?current:lead;
    out.push({value,label:e.volume?.length&&e.volume_name?e.volume_name:e.title});
  }
  return out.sort((a,b)=>a.label.localeCompare(b.label));
}
const labels:Record<string,string>={entry_id:fr('Pièce'),title:fr('Titre facultatif'),format:fr('Format'),animations:fr('Animations'),glass_effect:fr('Effet verre dépoli'),
  rotate:fr('Faire défiler les conseils'),banner_blocks:fr('Contenu du bandeau'),scale_marks:fr('Repères de l’échelle'),modules:fr('Rubriques'),measures_open:fr('Mesures dépliées au départ'),
  show_details:fr('Afficher la section'),details_open:fr('Dépliés au départ'),show_measures:fr('Afficher la section'),show_insights:fr('Afficher la section'),
  show_horizon:fr('Graphique « Prochaines heures »'),horizon_mode:fr('Quand l’afficher'),horizon_subjects:fr('Sujets du graphique'),insight_topics:fr('Sujets'),insight_max:fr('Lignes au plus'),detail_rows:fr('Lignes'),tile_chips:fr('Pastilles de la tuile repliée'),tile_blocks:fr('Contenu de la tuile dépliée'),
  mini_values:fr('Valeurs de la ligne'),hold_action:fr('Appui long'),hold_path:fr('Page à ouvrir'),show_scale:fr('Échelle des pièces'),show_rooms:fr('Section Pièces'),sections:fr('Sections affichées'),folded:fr('Dans « Plus de détails »'),more_open:fr('« Plus de détails » déplié au départ'),period:fr('Période au départ'),rooms_open:fr('Pièces dépliées au départ'),
  list_order:fr('Ordre des pièces')};
const helpers:Record<string,string>={
  animations:fr('Coupées, la lumière et l’anneau restent fixes et les conseils ne défilent plus seuls.'),
  glass_effect:fr('Le flou demande beaucoup de ressources : à couper sur un appareil lent. Coupé, le verre devient plus opaque.'),
  rotate:fr('Toutes les 4,5 s ; décoché, ils changent d’un appui.'),
  show_horizon:fr('Sous l’échelle : la pièce sans le geste et avec, et quand le faire.'),
  horizon_mode:fr('« Seulement quand il aide » : la carte change de taille en douceur. « Toujours » : sans geste à montrer, la température prévue sans rien faire.'),
  horizon_subjects:fr('Deux sujets : un onglet chacun, celui du conseil d’abord.'),insight_topics:fr('Ce qui explique le conseil, sous le bandeau. Faites glisser pour l’ordre de préférence.'),
  detail_rows:fr('Pour comprendre et vérifier. Tout décocher vide la section.'),
  banner_blocks:fr('Le conseil du moment reste toujours. Cochez ce qui défile après lui, dans l’ordre.'),
  scale_marks:fr('Tout décocher retire l’échelle.'),modules:fr('Tout décocher retire la section ; faites glisser pour l’ordre.'),
  measures_open:fr('Repliées, les mesures à surveiller restent visibles.'),
  tile_chips:fr('Sous le conseil ; une mesure à surveiller passe en ambre.'),tile_blocks:fr('Ce qui s’ouvre d’un appui, dans l’ordre.'),
  mini_values:fr('À droite du conseil.'),hold_action:fr('La carte complète par-dessus la page, une page de votre tableau de bord, ou rien.'),
  hold_path:fr('Le chemin de la page, par exemple /confort ou /lovelace/confort.'),rooms_open:fr('Repliées, les pièces qui demandent un geste restent visibles.'),
  folded:fr('Les sections cochées ici passent dans la partie dépliable, sous les autres.')};
const styles=css`.note{color:var(--secondary-text-color);font-size:13px;line-height:1.6;margin:0 0 16px}.note.warn{color:var(--primary-text-color)}a{color:var(--primary-color)}`;
/** A link inside Home Assistant opens there, without reloading the page. */
const follow=(e:MouseEvent)=>{e.preventDefault();history.pushState(null,'',(e.currentTarget as HTMLAnchorElement).getAttribute('href')??'/hestia/confort');
  window.dispatchEvent(new CustomEvent('location-changed',{bubbles:true,composed:true}));};
/** Mini and alert act on a simple tap; the other formats on a long press. */
const labelFor=(format:string|undefined)=>(item:Item)=>{const tap=item.name==='hold_action'&&['mini','alert'].includes(format??'');return t(item.title??(tap?fr('Appui'):labels[item.name]??item.name));};
const helperFor=(item:Item)=>helpers[item.name]?t(helpers[item.name]):'';
/** Drop empty values, a page path that no longer applies, and defaults the card did not hold: the YAML stays short. */
function tidy(next:Record<string,unknown>,before:Record<string,unknown>,defaults:Record<string,unknown>){
  if(next.hold_action!=='page')delete next.hold_path;
  for(const k of Object.keys(next)){
    if(next[k]===''||next[k]===undefined){delete next[k];continue;}
    if(!(k in before)&&k in defaults&&JSON.stringify(next[k])===JSON.stringify(defaults[k]))delete next[k];
  }
  return next;
}

/** Is the temperature scale shown: the switch, else the list of marks a card kept from before. */
export const scaleShown=(c:Config)=>c.show_scale??!(c.scale_marks?.length===0||(c.scale_marks===undefined&&c.format==='measures'));
/** The card after one change in the form. Home Assistant's form sends back every field it holds, the hidden ones too:
    only what really changed may replace a setting (the scale switch was undone by the list of marks it carries). */
export function nextConfig(config:Config,v:Record<string,unknown>):Record<string,unknown>{
  const next:Record<string,unknown>={...config,...v};
  // The scale needs the temperature module.
  if(Array.isArray(v.modules))next.modules=[...(v.modules as string[]),...((config.modules??MODULES).includes('temperature')?['temperature']:[])];
  if(typeof v.show_scale==='boolean'&&v.show_scale!==scaleShown(config)){next.show_scale=v.show_scale;delete next.scale_marks;}
  else{next.scale_marks=config.scale_marks;next.show_scale=config.show_scale;}
  if('modules' in v&&!('show_measures' in v))delete next.show_measures;
  return next;
}
export class ComfortEditor extends LitElement {
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:Config;
  /** The integration's rooms; null when it does not answer. */
  @state() private entries?:Entry[]|null;
  private asked=false;
  static styles=styles;
  protected willUpdate(){setLanguage(this.hass?.language);}
  setConfig(config:Config){const next=cleanConfig(config);if(this.config&&JSON.stringify(next)===JSON.stringify(this.config))return;this.config=next;}
  protected shouldUpdate(changed:Map<PropertyKey,unknown>){
    // Home Assistant pushes every state change to editors: nothing here depends on them.
    if(changed.has('hass')&&!this.asked&&this.hass){this.asked=true;
      this.hass.callWS<Entry[]>({type:'niak_comfort/entries'}).then(e=>{this.entries=e;},()=>{this.entries=null;});}
    return !(changed.size===1&&changed.has('hass'));
  }
  private schema(){
    const c=this.config!,f=c.format??'tile',action=c.hold_action??(c.hold_path?'page':'popup');
    const rooms=this.entries&&this.entries.length>1?[{name:'entry_id',selector:{select:{mode:'dropdown',options:roomChoices(this.entries,c.entry_id)}}}]:[];
    const format={name:'format',selector:{select:{mode:'list',options:[
      {value:'full',label:t('Complète : bandeau conseil, À savoir, mesures et détails')},{value:'tile',label:t('Tuile : le conseil et ses pastilles, se déplie d’un appui')},
      {value:'intermediate',label:t('Tuile dépliée : la même, ouverte au départ')},{value:'mini',label:t('Mini : une ligne, le conseil et la température')},
      {value:'measures',label:t('Mesures : les tuiles de la pièce, sans conseil')},{value:'alert',label:t('Alerte : visible seulement quand un geste est conseillé')}]}}};
    const head=[...rooms,{name:'title',selector:{text:{}}},format];
    const rubriques=choices('modules',MODULES.filter(m=>m!=='temperature').map(m=>[m,moduleLabels[m]]));
    if(f==='mini')return [...head,look(),group(fr('Contenu de la ligne'),'mdi:view-list-outline',[choices('mini_values',chipOptions)],true),hold(action)];
    if(f==='alert')return [...head,look(),group(fr('Bandeau'),'mdi:view-day-outline',[toggle('rotate')],true),hold(action)];
    if(f==='measures')return [...head,look(),group(fr('Contenu'),'mdi:view-grid-outline',[rubriques,scaleToggle],true),hold(action)];
    // The tile keeps its spirit: the advice and its chips, then what unfolds; each section keeps its own settings.
    if(f==='tile'||f==='intermediate')return [...head,
      group(fr('Tuile : bandeau et partie dépliable'),'mdi:view-day-outline',[choices('tile_chips',chipOptions),choices('tile_blocks',[['scale',fr('Échelle de température')],['horizon',fr('Graphique « Prochaines heures »')],['measures',fr('Mesures')],['details',fr('Détails techniques')]])],true),
      banner(false),insights(),group(fr('3 · Mesures'),'mdi:numeric-3-circle',[rubriques]),details(),look(false),hold(action)];
    return [...head,banner(),insights(),
      group(fr('3 · Mesures'),'mdi:numeric-3-circle',[toggle('show_measures'),rubriques,toggle('measures_open')]),
      details(),look(false)];
  }
  private changed(e:CustomEvent<{value:Record<string,unknown>}>){
    e.stopPropagation();if(!this.config)return;
    this.config=cleanConfig(tidy(nextConfig(this.config,e.detail.value),this.config as unknown as Record<string,unknown>,this.defaults(this.config)) as unknown as Config);
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));
  }
  private defaults(c:Config):Record<string,unknown>{
    return {animations:true,glass_effect:true,rotate:true,show_details:true,details_open:false,measures_open:false,show_measures:true,
      show_horizon:true,horizon_mode:'needed',horizon_subjects:[...HORIZON_SUBJECTS],show_insights:true,insight_topics:[...INSIGHT_TOPICS],insight_max:4,detail_rows:[...DETAIL_ROWS],
      banner_blocks:['remedies','later'],tile_chips:[...CHIPS],tile_blocks:[...TILE_BLOCKS],mini_values:['temperature'],hold_action:c.hold_path?'page':'popup',
      scale_marks:c.show_scale===false||c.format==='measures'?[]:[...SCALE_MARKS]};
  }
  protected render(){
    if(!this.config||!this.hass)return nothing;
    const c=this.config;
    const data={...this.defaults(c),hold_action:c.hold_action??(c.hold_path?'page':'popup'),
      ...c,show_scale:scaleShown(c),modules:(c.modules??MODULES).filter(m=>m!=='temperature')};
    const one=this.entries?.length===1?this.entries[0]:this.entries?.find(e=>e.entry_id===c.entry_id);
    return html`${this.entries===null?html`<p class="note warn">${t('L’intégration Hestia Confort ne répond pas : vérifiez qu’elle est installée et chargée.')}</p>`
      :this.entries?.length===0?html`<p class="note warn">${th('Aucune pièce : ouvrez {link} dans la barre latérale pour en ajouter une.',{link:html`<a href="/hestia/confort" @click=${follow}>${t('Hestia Confort')}</a>`})}</p>`
      :html`<p class="note">${one?html`${th('Pièce : {room}.',{room:html`<b>${one.volume?.length&&one.volume_name?one.volume_name:one.title}</b>`})} `:nothing}${th('Les capteurs et préférences se règlent dans {link}.',{link:html`<a href="/hestia/confort" @click=${follow}>${t('Hestia Confort')}</a>`})}</p>`}
      <ha-form .hass=${this.hass} .data=${data} .schema=${this.schema()} .computeLabel=${labelFor(c.format)} .computeHelper=${helperFor} @value-changed=${this.changed}></ha-form>`;
  }
}
if(!customElements.get('niak-comfort-card-editor'))customElements.define('niak-comfort-card-editor',ComfortEditor);

const HOME_DEFAULTS:Record<string,unknown>={format:'full',sections:[...SHOWN_SECTIONS],folded:[...FOLDED_SECTIONS],more_open:false,period:'day',animations:true,glass_effect:true,rotate:true,show_scale:true,show_rooms:true,rooms_open:false,show_details:true,details_open:false,
  banner_blocks:['rooms','house'],list_order:'urgent',hold_action:'popup'};
/** The home card's editor, built the same way. */
export class ComfortHomeEditor extends LitElement {
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:HomeConfig;
  static styles=styles;
  protected willUpdate(){setLanguage(this.hass?.language);}
  setConfig(config:HomeConfig){this.config=cleanHomeConfig(config);}
  protected shouldUpdate(changed:Map<PropertyKey,unknown>){return !(changed.size===1&&changed.has('hass')&&!!this.config);}
  private schema(){
    const c=this.config!,f=c.format??'full',action=homeAction(c);
    const format={name:'format',selector:{select:{mode:'list',options:[
      {value:'full',label:t('Complète : les conseils des pièces, puis le bilan du jour, de la semaine ou du mois')},{value:'tile',label:t('Tuile : le conseil de la pièce qui demande le plus, l’échelle des pièces')},
      {value:'list',label:t('Liste des pièces : une ligne par pièce')},{value:'mini',label:t('Mini : une ligne pour toute la maison')},
      {value:'alert',label:t('Alerte : visible seulement si une pièce demande un geste')}]}}};
    const head=[{name:'title',selector:{text:{}}},format];
    const banner=group(fr('Bandeau'),'mdi:view-day-outline',[choices('banner_blocks',[['rooms',fr('Conseils des pièces')],['house',fr('Gestes pour toute la maison (air traversant)')]]),toggle('rotate')],true);
    if(f==='mini')return [...head,look(),hold(action)];
    if(f==='alert')return [...head,look(),banner,hold(action)];
    if(f==='list')return [...head,look(),group(fr('Contenu'),'mdi:format-list-bulleted',[dropdown('list_order',[['urgent',fr('Celles qui demandent un geste d’abord')],['floor',fr('Par étage')]])],true),hold(action)];
    if(f==='tile')return [...head,look(),banner,group(fr('Pièces'),'mdi:view-grid-outline',[toggle('show_scale'),toggle('show_rooms'),toggle('rooms_open')]),hold(action)];
    const sections=SECTIONS.map(k=>[k,SECTION_LABELS[k]] as [string,string]);
    return [...head,look(),banner,
      group(fr('Bilan'),'mdi:chart-box-outline',[dropdown('period',[['day',fr('Jour')],['week',fr('Semaine')],['month',fr('Mois')]]),choices('sections',sections),choices('folded',sections),toggle('more_open')],true),
      group(fr('Pièces et détails'),'mdi:view-grid-outline',[toggle('rooms_open'),toggle('details_open')]),hold(action,true)];
  }
  private changed(e:CustomEvent<{value:Record<string,unknown>}>){
    e.stopPropagation();if(!this.config)return;
    const next={...this.config,...e.detail.value} as HomeConfig;
    // Changing format resets an action the new format does not offer (a window on the full card).
    if((next.format??'full')==='full'&&next.hold_action==='popup')delete next.hold_action;
    this.config=cleanHomeConfig(tidy(next as unknown as Record<string,unknown>,this.config as unknown as Record<string,unknown>,{...HOME_DEFAULTS,hold_action:homeAction({...next,hold_action:undefined,hold_path:undefined})}) as unknown as HomeConfig);
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));
  }
  protected render(){
    if(!this.config||!this.hass)return nothing;
    const c=this.config;
    const data={...HOME_DEFAULTS,...c,hold_action:homeAction(c)};
    return html`<p class="note">${th('Toutes les pièces de Hestia Confort. Elles se règlent dans {link}.',{link:html`<a href="/hestia/confort" @click=${follow}>${t('Hestia Confort')}</a>`})}</p>
      <ha-form .hass=${this.hass} .data=${data} .schema=${this.schema()} .computeLabel=${labelFor(c.format)} .computeHelper=${helperFor} @value-changed=${this.changed}></ha-form>`;
  }
}
if(!customElements.get('niak-comfort-home-card-editor'))customElements.define('niak-comfort-home-card-editor',ComfortHomeEditor);
