import {LitElement,html,css,nothing} from 'lit';
import {property,state} from 'lit/decorators.js';
import {cleanConfig,cleanHomeConfig,MODULES,moduleLabels,SCALE_MARKS,CHIPS,TILE_BLOCKS,type Config,type HomeConfig,type HomeAssistant,type Entry} from './types';

/* The editors are built like Niak Weather's: the room (or title) and the format on top, then folding groups that
   change with the format. The theme follows Home Assistant: it is no longer offered. */
type Item={name:string;title?:string};
const toggle=(name:string)=>({name,selector:{boolean:{}}});
const group=(title:string,icon:string,schema:unknown[],expanded=false)=>({type:'expandable',name:'',title,icon,flatten:true,expanded,schema});
const choices=(name:string,options:[string,string][])=>({name,selector:{select:{multiple:true,reorder:true,mode:'list',options:options.map(([value,label])=>({value,label}))}}});
const dropdown=(name:string,options:[string,string][])=>({name,required:true,selector:{select:{mode:'dropdown',options:options.map(([value,label])=>({value,label}))}}});
const look=()=>group('Visuel et performance','mdi:palette-outline',[toggle('animations'),toggle('glass_effect')],true);
const hold=(action:string)=>group('Fonctionnalités','mdi:tune-variant',[
  dropdown('hold_action',[['popup','Ouvrir la carte complète en fenêtre'],['page','Ouvrir une page'],['none','Rien']]),
  ...(action==='page'?[{name:'hold_path',selector:{text:{}}}]:[])]);
const chipOptions:[string,string][]=[['temperature','Température'],['humidity','Humidité'],['co2','CO₂']];
const markOptions:[string,string][]=[['band','Votre plage'],['day','Min–max 24 h'],['out','Dehors']];
const bannerOptions:[string,string][]=[['remedies','Remèdes en cours (purificateur, VMC)'],['later','Plus tard (meilleur moment)']];
const labels:Record<string,string>={entry_id:'Pièce',title:'Titre facultatif',format:'Format',animations:'Animations',glass_effect:'Effet verre dépoli',
  rotate:'Faire défiler les conseils',banner_blocks:'Contenu du bandeau',scale_marks:'Repères de l’échelle',modules:'Rubriques',measures_open:'Mesures dépliées au départ',
  show_details:'Section Détails',details_open:'Détails dépliés au départ',tile_chips:'Pastilles de la tuile repliée',tile_blocks:'Contenu de la tuile dépliée',
  mini_values:'Valeurs de la ligne',hold_action:'Appui long',hold_path:'Page à ouvrir',show_scale:'Échelle des pièces',show_rooms:'Section Pièces',rooms_open:'Pièces dépliées au départ',
  list_order:'Ordre des pièces'};
const helpers:Record<string,string>={
  animations:'Coupées, la lumière et l’anneau restent fixes et les conseils ne défilent plus seuls.',
  glass_effect:'Le flou demande beaucoup de ressources : à couper sur un appareil lent. Coupé, le verre devient plus opaque.',
  rotate:'Toutes les 4,5 s ; décoché, ils changent d’un appui.',
  banner_blocks:'Le conseil du moment reste toujours. Cochez ce qui défile après lui, dans l’ordre.',
  scale_marks:'Tout décocher retire l’échelle.',modules:'Tout décocher retire la section ; faites glisser pour l’ordre.',
  measures_open:'Repliées, les mesures hors de votre plage restent visibles.',
  tile_chips:'Sous le conseil ; une mesure hors plage passe en ambre.',tile_blocks:'Ce qui s’ouvre d’un appui, dans l’ordre.',
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
    const rooms=this.entries&&this.entries.length>1?[{name:'entry_id',selector:{select:{mode:'dropdown',options:this.entries.map(e=>({value:e.entry_id,label:e.title}))}}}]:[];
    const format={name:'format',selector:{select:{mode:'list',options:[
      {value:'full',label:'Complète : bandeau, échelle, mesures et détails'},{value:'tile',label:'Tuile : le conseil et ses pastilles, se déplie d’un appui'},
      {value:'intermediate',label:'Tuile dépliée : la même, ouverte au départ'},{value:'mini',label:'Mini : une ligne, le conseil et la température'},
      {value:'measures',label:'Mesures : les tuiles de la pièce, sans conseil'},{value:'alert',label:'Alerte : visible seulement quand un geste est conseillé'}]}}};
    const head=[...rooms,{name:'title',selector:{text:{}}},format];
    const rubriques=choices('modules',MODULES.filter(m=>m!=='temperature').map(m=>[m,moduleLabels[m]]));
    if(f==='mini')return [...head,look(),group('Contenu de la ligne','mdi:view-list-outline',[choices('mini_values',chipOptions)],true),hold(action)];
    if(f==='alert')return [...head,look(),group('Bandeau','mdi:view-day-outline',[choices('banner_blocks',bannerOptions),toggle('rotate')],true),hold(action)];
    if(f==='measures')return [...head,look(),group('Contenu','mdi:view-grid-outline',[rubriques,choices('scale_marks',markOptions)],true),hold(action)];
    if(f==='tile'||f==='intermediate')return [...head,look(),
      group('Tuile repliée','mdi:view-day-outline',[choices('tile_chips',chipOptions),choices('banner_blocks',bannerOptions),toggle('rotate')],true),
      group('Tuile dépliée','mdi:view-grid-outline',[choices('tile_blocks',[['scale','Échelle de température'],['measures','Mesures'],['details','Détails']]),rubriques,choices('scale_marks',markOptions)]),
      hold(action)];
    return [...head,look(),
      group('Bandeau','mdi:view-day-outline',[choices('banner_blocks',bannerOptions),toggle('rotate')],true),
      group('Échelle de température','mdi:thermometer',[choices('scale_marks',markOptions)]),
      group('Mesures','mdi:view-grid-outline',[rubriques,toggle('measures_open')]),
      group('Détails','mdi:text-box-outline',[toggle('show_details'),toggle('details_open')])];
  }
  private changed(e:CustomEvent<{value:Record<string,unknown>}>){
    e.stopPropagation();if(!this.config)return;
    const v=e.detail.value,next:Record<string,unknown>={...this.config,...v};
    // The scale needs the temperature module; the lists replace the older on/off switches they cover.
    if(Array.isArray(v.modules))next.modules=[...(v.modules as string[]),...((this.config.modules??MODULES).includes('temperature')?['temperature']:[])];
    if('scale_marks' in v)delete next.show_scale;
    if('modules' in v)delete next.show_measures;
    this.config=cleanConfig(tidy(next,this.config as unknown as Record<string,unknown>,this.defaults(this.config)) as unknown as Config);
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));
  }
  private defaults(c:Config):Record<string,unknown>{
    return {animations:true,glass_effect:true,rotate:true,show_details:true,details_open:false,measures_open:false,
      banner_blocks:['remedies','later'],tile_chips:[...CHIPS],tile_blocks:[...TILE_BLOCKS],mini_values:['temperature'],hold_action:c.hold_path?'page':'popup',
      scale_marks:c.show_scale===false||c.format==='measures'?[]:[...SCALE_MARKS]};
  }
  protected render(){
    if(!this.config||!this.hass)return nothing;
    const c=this.config;
    const data={...this.defaults(c),hold_action:c.hold_action??(c.hold_path?'page':'popup'),
      ...c,scale_marks:c.scale_marks??(c.show_scale===false||c.format==='measures'?[]:[...SCALE_MARKS]),modules:c.show_measures===false?[]:(c.modules??MODULES).filter(m=>m!=='temperature')};
    const one=this.entries?.length===1?this.entries[0]:this.entries?.find(e=>e.entry_id===c.entry_id);
    return html`${this.entries===null?html`<p class="note warn">L’intégration Niak Confort ne répond pas : vérifiez qu’elle est installée et chargée.</p>`
      :this.entries?.length===0?html`<p class="note warn">Aucune pièce : ouvrez <a href="/niak/confort" @click=${follow}>Niak Confort</a> dans la barre latérale pour en ajouter une.</p>`
      :html`<p class="note">${one?html`Pièce : <b>${one.title}</b>. `:nothing}Les capteurs et préférences se règlent dans <a href="/niak/confort" @click=${follow}>Niak Confort</a>.</p>`}
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
    const c=this.config!,f=c.format??'full',action=c.hold_action??(c.hold_path?'page':'popup');
    const format={name:'format',selector:{select:{mode:'list',options:[
      {value:'full',label:'Complète : bandeau, échelle des pièces, pièces et détails'},{value:'tile',label:'Tuile : le conseil de la pièce qui demande le plus, l’échelle des pièces'},
      {value:'list',label:'Liste des pièces : une ligne par pièce'},{value:'mini',label:'Mini : une ligne pour toute la maison'},
      {value:'alert',label:'Alerte : visible seulement si une pièce demande un geste'}]}}};
    const head=[{name:'title',selector:{text:{}}},format];
    const banner=group('Bandeau','mdi:view-day-outline',[choices('banner_blocks',[['rooms','Conseils des pièces'],['house','Gestes pour toute la maison (air traversant)']]),toggle('rotate')],true);
    if(f==='mini')return [...head,look(),hold(action)];
    if(f==='alert')return [...head,look(),banner,hold(action)];
    if(f==='list')return [...head,look(),group('Contenu','mdi:format-list-bulleted',[dropdown('list_order',[['urgent','Celles qui demandent un geste d’abord'],['floor','Par étage']])],true)];
    if(f==='tile')return [...head,look(),banner,group('Pièces','mdi:view-grid-outline',[toggle('show_scale'),toggle('show_rooms'),toggle('rooms_open')]),hold(action)];
    return [...head,look(),banner,group('Échelle des pièces','mdi:thermometer',[toggle('show_scale')]),
      group('Pièces','mdi:view-grid-outline',[toggle('show_rooms'),toggle('rooms_open')]),group('Détails','mdi:text-box-outline',[toggle('show_details'),toggle('details_open')])];
  }
  private changed(e:CustomEvent<{value:Record<string,unknown>}>){
    e.stopPropagation();if(!this.config)return;
    this.config=cleanHomeConfig(tidy({...this.config,...e.detail.value},this.config as unknown as Record<string,unknown>,HOME_DEFAULTS) as unknown as HomeConfig);
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));
  }
  protected render(){
    if(!this.config||!this.hass)return nothing;
    const c=this.config;
    const data={...HOME_DEFAULTS,hold_action:c.hold_action??(c.hold_path?'page':'popup'),...c};
    return html`<p class="note">Toutes les pièces de Niak Confort. Elles se règlent dans <a href="/niak/confort" @click=${follow}>Niak Confort</a>.</p>
      <ha-form .hass=${this.hass} .data=${data} .schema=${this.schema()} .computeLabel=${labelFor(c.format)} .computeHelper=${helperFor} @value-changed=${this.changed}></ha-form>`;
  }
}
if(!customElements.get('niak-comfort-home-card-editor'))customElements.define('niak-comfort-home-card-editor',ComfortHomeEditor);
