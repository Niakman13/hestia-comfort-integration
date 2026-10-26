import {LitElement,html,css,nothing} from 'lit';
import {property,state} from 'lit/decorators.js';
import {cleanConfig,cleanHomeConfig,MODULES,moduleLabels,SCALE_MARKS,CHIPS,TILE_BLOCKS,HORIZON_SUBJECTS,INSIGHT_TOPICS,DETAIL_ROWS,homeAction,type Config,type HomeConfig,type HomeAssistant,type Entry} from './types';

/* The editors are built like Niak Weather's: the room (or title) and the format on top, then folding groups that
   change with the format. The theme follows Home Assistant: it is no longer offered. */
type Item={name:string;title?:string};
const toggle=(name:string)=>({name,selector:{boolean:{}}});
const group=(title:string,icon:string,schema:unknown[],expanded=false)=>({type:'expandable',name:'',title,icon,flatten:true,expanded,schema});
const choices=(name:string,options:[string,string][])=>({name,selector:{select:{multiple:true,reorder:true,mode:'list',options:options.map(([value,label])=>({value,label}))}}});
const dropdown=(name:string,options:[string,string][])=>({name,required:true,selector:{select:{mode:'dropdown',options:options.map(([value,label])=>({value,label}))}}});
const look=(expanded=true)=>group('Apparence','mdi:palette-outline',[toggle('animations'),toggle('glass_effect')],expanded);
/** On a full card, the full card in a window would show itself again: only a page, or nothing. */
const hold=(action:string,full=false)=>group('Appui long','mdi:gesture-tap-hold',[
  dropdown('hold_action',full?[['none','Rien'],['page','Ouvrir une page']]:[['popup','Ouvrir la carte complète en fenêtre'],['page','Ouvrir une page'],['none','Rien']]),
  ...(action==='page'?[{name:'hold_path',selector:{text:{}}}]:[])]);
const chipOptions:[string,string][]=[['temperature','Température'],['humidity','Humidité'],['co2','CO₂']];
const markOptions:[string,string][]=[['band','Votre plage'],['day','Min–max 24 h'],['out','Dehors']];
const bannerOptions:[string,string][]=[['remedies','Équipements en marche (purificateur, VMC)'],['later','Meilleur moment plus tard']];
const horizonOptions:[string,string][]=[['temperature','Température'],['humidity','Humidité']];
const topicOptions:[string,string][]=[['humidity','Humidité'],['heating','Chauffage'],['sun','Soleil'],['windows','Fenêtres et aération'],['equipment','Équipements (purificateur, VMC)'],
  ['household','Personnes et alarme'],['forecast','Prévisions (cette nuit)'],['learning','Apprentissage (dernière aération)']];
const detailOptions:[string,string][]=[['range','Plage de confort'],['slot','Créneau conseillé'],['windows','Fenêtres'],['shutters','Volets'],['people','Présence, personnes, alarme'],
  ['drying','Séchage et buée'],['trend','Tendance'],['sensors','Capteurs et sources']];
/** The four sections of the card, in its order: the same number in the editor and on the card. */
const banner=(expanded=true)=>group('1 · Bandeau conseil','mdi:numeric-1-circle',[toggle('rotate'),choices('banner_blocks',bannerOptions),choices('scale_marks',markOptions),toggle('show_horizon'),choices('horizon_subjects',horizonOptions)],expanded);
const insights=()=>group('2 · À savoir','mdi:numeric-2-circle',[toggle('show_insights'),choices('insight_topics',topicOptions),{name:'insight_max',selector:{number:{min:1,max:8,mode:'slider'}}}]);
const details=()=>group('4 · Détails techniques','mdi:numeric-4-circle',[toggle('show_details'),choices('detail_rows',detailOptions),toggle('details_open')]);
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
  return out.sort((a,b)=>a.label.localeCompare(b.label,'fr'));
}
const labels:Record<string,string>={entry_id:'Pièce',title:'Titre facultatif',format:'Format',animations:'Animations',glass_effect:'Effet verre dépoli',
  rotate:'Faire défiler les conseils',banner_blocks:'Contenu du bandeau',scale_marks:'Repères de l’échelle',modules:'Rubriques',measures_open:'Mesures dépliées au départ',
  show_details:'Afficher la section',details_open:'Dépliés au départ',show_measures:'Afficher la section',show_insights:'Afficher la section',
  show_horizon:'Graphique « Prochaines heures »',horizon_subjects:'Sujets du graphique',insight_topics:'Sujets',insight_max:'Lignes au plus',detail_rows:'Lignes',tile_chips:'Pastilles de la tuile repliée',tile_blocks:'Contenu de la tuile dépliée',
  mini_values:'Valeurs de la ligne',hold_action:'Appui long',hold_path:'Page à ouvrir',show_scale:'Échelle des pièces',show_rooms:'Section Pièces',rooms_open:'Pièces dépliées au départ',
  list_order:'Ordre des pièces'};
const helpers:Record<string,string>={
  animations:'Coupées, la lumière et l’anneau restent fixes et les conseils ne défilent plus seuls.',
  glass_effect:'Le flou demande beaucoup de ressources : à couper sur un appareil lent. Coupé, le verre devient plus opaque.',
  rotate:'Toutes les 4,5 s ; décoché, ils changent d’un appui.',
  show_horizon:'Sous l’échelle : la pièce sans le geste et avec, et quand le faire. Seulement quand il aide.',
  horizon_subjects:'Deux sujets : un onglet chacun, celui du conseil d’abord.',insight_topics:'Ce qui explique le conseil, sous le bandeau. Faites glisser pour l’ordre de préférence.',
  detail_rows:'Pour comprendre et vérifier. Tout décocher vide la section.',
  banner_blocks:'Le conseil du moment reste toujours. Cochez ce qui défile après lui, dans l’ordre.',
  scale_marks:'Tout décocher retire l’échelle.',modules:'Tout décocher retire la section ; faites glisser pour l’ordre.',
  measures_open:'Repliées, les mesures à surveiller restent visibles.',
  tile_chips:'Sous le conseil ; une mesure à surveiller passe en ambre.',tile_blocks:'Ce qui s’ouvre d’un appui, dans l’ordre.',
  mini_values:'À droite du conseil.',hold_action:'La carte complète par-dessus la page, une page de votre tableau de bord, ou rien.',
  hold_path:'Le chemin de la page, par exemple /confort ou /lovelace/confort.',rooms_open:'Repliées, les pièces qui demandent un geste restent visibles.'};
const styles=css`.note{color:var(--secondary-text-color);font-size:13px;line-height:1.6;margin:0 0 16px}.note.warn{color:var(--primary-text-color)}a{color:var(--primary-color)}`;
/** A link inside Home Assistant opens there, without reloading the page. */
const follow=(e:MouseEvent)=>{e.preventDefault();history.pushState(null,'',(e.currentTarget as HTMLAnchorElement).getAttribute('href')??'/niak/confort');
  window.dispatchEvent(new CustomEvent('location-changed',{bubbles:true,composed:true}));};
/** Mini and alert act on a simple tap; the other formats on a long press. */
const labelFor=(format:string|undefined)=>(item:Item)=>item.title??(item.name==='hold_action'&&['mini','alert'].includes(format??'')?'Appui':labels[item.name]??item.name);
const helperFor=(item:Item)=>helpers[item.name]??'';
/** Drop empty values, a page path that no longer applies, and defaults the card did not hold: the YAML stays short. */
function tidy(next:Record<string,unknown>,before:Record<string,unknown>,defaults:Record<string,unknown>){
  if(next.hold_action!=='page')delete next.hold_path;
  for(const k of Object.keys(next)){
    if(next[k]===''||next[k]===undefined){delete next[k];continue;}
    if(!(k in before)&&k in defaults&&JSON.stringify(next[k])===JSON.stringify(defaults[k]))delete next[k];
  }
  return next;
}

export class ComfortEditor extends LitElement {
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:Config;
  /** The integration's rooms; null when it does not answer. */
  @state() private entries?:Entry[]|null;
  private asked=false;
  static styles=styles;
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
      {value:'full',label:'Complète : bandeau conseil, À savoir, mesures et détails'},{value:'tile',label:'Tuile : le conseil et ses pastilles, se déplie d’un appui'},
      {value:'intermediate',label:'Tuile dépliée : la même, ouverte au départ'},{value:'mini',label:'Mini : une ligne, le conseil et la température'},
      {value:'measures',label:'Mesures : les tuiles de la pièce, sans conseil'},{value:'alert',label:'Alerte : visible seulement quand un geste est conseillé'}]}}};
    const head=[...rooms,{name:'title',selector:{text:{}}},format];
    const rubriques=choices('modules',MODULES.filter(m=>m!=='temperature').map(m=>[m,moduleLabels[m]]));
    if(f==='mini')return [...head,look(),group('Contenu de la ligne','mdi:view-list-outline',[choices('mini_values',chipOptions)],true),hold(action)];
    if(f==='alert')return [...head,look(),group('Bandeau','mdi:view-day-outline',[choices('banner_blocks',bannerOptions),toggle('rotate')],true),hold(action)];
    if(f==='measures')return [...head,look(),group('Contenu','mdi:view-grid-outline',[rubriques,choices('scale_marks',markOptions)],true),hold(action)];
    // The tile keeps its spirit: the advice and its chips, then what unfolds; each section keeps its own settings.
    if(f==='tile'||f==='intermediate')return [...head,
      group('Tuile : bandeau et partie dépliable','mdi:view-day-outline',[choices('tile_chips',chipOptions),choices('tile_blocks',[['scale','Échelle de température'],['horizon','Graphique « Prochaines heures »'],['measures','Mesures'],['details','Détails techniques']])],true),
      banner(false),insights(),group('3 · Mesures','mdi:numeric-3-circle',[rubriques]),details(),look(false),hold(action)];
    return [...head,banner(),insights(),
      group('3 · Mesures','mdi:numeric-3-circle',[toggle('show_measures'),rubriques,toggle('measures_open')]),
      details(),look(false)];
  }
  private changed(e:CustomEvent<{value:Record<string,unknown>}>){
    e.stopPropagation();if(!this.config)return;
    const v=e.detail.value,next:Record<string,unknown>={...this.config,...v};
    // The scale needs the temperature module; the lists replace the older on/off switches they cover.
    if(Array.isArray(v.modules))next.modules=[...(v.modules as string[]),...((this.config.modules??MODULES).includes('temperature')?['temperature']:[])];
    if('scale_marks' in v)delete next.show_scale;
    if('modules' in v&&!('show_measures' in v))delete next.show_measures;
    this.config=cleanConfig(tidy(next,this.config as unknown as Record<string,unknown>,this.defaults(this.config)) as unknown as Config);
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));
  }
  private defaults(c:Config):Record<string,unknown>{
    return {animations:true,glass_effect:true,rotate:true,show_details:true,details_open:false,measures_open:false,show_measures:true,
      show_horizon:true,horizon_subjects:[...HORIZON_SUBJECTS],show_insights:true,insight_topics:[...INSIGHT_TOPICS],insight_max:4,detail_rows:[...DETAIL_ROWS],
      banner_blocks:['remedies','later'],tile_chips:[...CHIPS],tile_blocks:[...TILE_BLOCKS],mini_values:['temperature'],hold_action:c.hold_path?'page':'popup',
      scale_marks:c.show_scale===false||c.format==='measures'?[]:[...SCALE_MARKS]};
  }
  protected render(){
    if(!this.config||!this.hass)return nothing;
    const c=this.config;
    const data={...this.defaults(c),hold_action:c.hold_action??(c.hold_path?'page':'popup'),
      ...c,scale_marks:c.scale_marks??(c.show_scale===false||c.format==='measures'?[]:[...SCALE_MARKS]),modules:(c.modules??MODULES).filter(m=>m!=='temperature')};
    const one=this.entries?.length===1?this.entries[0]:this.entries?.find(e=>e.entry_id===c.entry_id);
    return html`${this.entries===null?html`<p class="note warn">L’intégration Niak Confort ne répond pas : vérifiez qu’elle est installée et chargée.</p>`
      :this.entries?.length===0?html`<p class="note warn">Aucune pièce : ouvrez <a href="/niak/confort" @click=${follow}>Niak Confort</a> dans la barre latérale pour en ajouter une.</p>`
      :html`<p class="note">${one?html`Pièce : <b>${one.volume?.length&&one.volume_name?one.volume_name:one.title}</b>. `:nothing}Les capteurs et préférences se règlent dans <a href="/niak/confort" @click=${follow}>Niak Confort</a>.</p>`}
      <ha-form .hass=${this.hass} .data=${data} .schema=${this.schema()} .computeLabel=${labelFor(c.format)} .computeHelper=${helperFor} @value-changed=${this.changed}></ha-form>`;
  }
}
if(!customElements.get('niak-comfort-card-editor'))customElements.define('niak-comfort-card-editor',ComfortEditor);

const HOME_DEFAULTS:Record<string,unknown>={format:'full',animations:true,glass_effect:true,rotate:true,show_scale:true,show_rooms:true,rooms_open:false,show_details:true,details_open:false,
  banner_blocks:['rooms','house'],list_order:'urgent',hold_action:'popup'};
/** The home card's editor, built the same way. */
export class ComfortHomeEditor extends LitElement {
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:HomeConfig;
  static styles=styles;
  setConfig(config:HomeConfig){this.config=cleanHomeConfig(config);}
  protected shouldUpdate(changed:Map<PropertyKey,unknown>){return !(changed.size===1&&changed.has('hass')&&!!this.config);}
  private schema(){
    const c=this.config!,f=c.format??'full',action=homeAction(c);
    const format={name:'format',selector:{select:{mode:'list',options:[
      {value:'full',label:'Complète : bandeau, échelle des pièces, pièces et détails'},{value:'tile',label:'Tuile : le conseil de la pièce qui demande le plus, l’échelle des pièces'},
      {value:'list',label:'Liste des pièces : une ligne par pièce'},{value:'mini',label:'Mini : une ligne pour toute la maison'},
      {value:'alert',label:'Alerte : visible seulement si une pièce demande un geste'}]}}};
    const head=[{name:'title',selector:{text:{}}},format];
    const banner=group('Bandeau','mdi:view-day-outline',[choices('banner_blocks',[['rooms','Conseils des pièces'],['house','Gestes pour toute la maison (air traversant)']]),toggle('rotate')],true);
    if(f==='mini')return [...head,look(),hold(action)];
    if(f==='alert')return [...head,look(),banner,hold(action)];
    if(f==='list')return [...head,look(),group('Contenu','mdi:format-list-bulleted',[dropdown('list_order',[['urgent','Celles qui demandent un geste d’abord'],['floor','Par étage']])],true),hold(action)];
    if(f==='tile')return [...head,look(),banner,group('Pièces','mdi:view-grid-outline',[toggle('show_scale'),toggle('show_rooms'),toggle('rooms_open')]),hold(action)];
    return [...head,look(),banner,group('Échelle des pièces','mdi:thermometer',[toggle('show_scale')]),
      group('Pièces','mdi:view-grid-outline',[toggle('show_rooms'),toggle('rooms_open')]),group('Détails','mdi:text-box-outline',[toggle('show_details'),toggle('details_open')]),hold(action,true)];
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
    return html`<p class="note">Toutes les pièces de Niak Confort. Elles se règlent dans <a href="/niak/confort" @click=${follow}>Niak Confort</a>.</p>
      <ha-form .hass=${this.hass} .data=${data} .schema=${this.schema()} .computeLabel=${labelFor(c.format)} .computeHelper=${helperFor} @value-changed=${this.changed}></ha-form>`;
  }
}
if(!customElements.get('niak-comfort-home-card-editor'))customElements.define('niak-comfort-home-card-editor',ComfortHomeEditor);
