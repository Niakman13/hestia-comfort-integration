import {html,LitElement,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {property,state} from 'lit/decorators.js';
import style from './ui/charter.css';
import {isView,number,numeric,summary,levelLabels} from './view';
import {icon} from './ui/icons';
import type {Connection,HomeAssistant,Unsubscribe,View} from './types';

interface FloorRef {floor_id:string|null;name:string;level:number|null}
interface Floor extends FloorRef {room_ids:string[];mean:number|null;measured:number;total:number;hottest:{title:string;temperature:number}|null}
interface Ventilation {kind:'stack'|'cross'|'combined';engaged:boolean;wind_favorable:boolean;openings:{title:string;name:string;floor:FloorRef|null}[]}
interface Home {
  floors?:Floor[];floor_contrast?:{warmer:string;cooler:string;difference:number;partial:boolean}|null;
  ventilation?:Ventilation|null; start_floor?:FloorRef|null;
  level:string; focus:string|null; partial:boolean; outdoor_temperature:number|null; spread:number|null;
  hottest:{title:string;temperature:number}|null; coolest:{title:string;temperature:number}|null;
  open_rooms:{title:string;open:string[]}[]; crossing:'strong'|'partial'|'none'|null; start_with:string|null;
  sun_entering:{title:string;openings:string[]}[];
}
interface HomeConfig {type:'custom:niak-comfort-home-card';title?:string;theme?:'auto'|'light'|'dark'}

/** The home card: a synthesis of every room. It never replaces the room cards' advice. */
export class NiakComfortHomeCard extends LitElement {
  static styles=unsafeCSS(style);
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:HomeConfig;
  @state() private rooms:View[]=[];
  @state() private home?:Home;
  @state() private problem?:string;
  private connection?:Connection;
  private unsubscribe?:Unsubscribe;
  private retry?:ReturnType<typeof setTimeout>;
  private generation=0;
  setConfig(input:HomeConfig){if(!input||input.type!=='custom:niak-comfort-home-card')throw new Error('Type de carte invalide.');this.config={...input};}
  static getStubConfig():HomeConfig{return {type:'custom:niak-comfort-home-card'};}
  getCardSize(){return 4+this.rooms.length;}
  connectedCallback(){super.connectedCallback();this.connect();}
  disconnectedCallback(){super.disconnectedCallback();this.stop();}
  protected updated(changed:PropertyValues){
    if(changed.has('hass'))this.connect();
    const theme=this.config?.theme==='auto'||!this.config?.theme?(this.hass?.themes?.darkMode===false?'light':'dark'):this.config.theme;
    this.setAttribute('theme',theme);
  }
  private stop(){this.generation++;if(this.retry)clearTimeout(this.retry);this.retry=undefined;const remove=this.unsubscribe;this.unsubscribe=undefined;this.connection=undefined;if(remove)void Promise.resolve().then(()=>remove()).catch(()=>{});}
  private connect(){
    const connection=this.hass?.connection;if(!this.isConnected||!connection||!this.config||connection===this.connection)return;
    this.stop();this.connection=connection;const generation=this.generation;
    connection.subscribeMessage<{version:number;rooms?:unknown[];home?:Home;reload?:boolean}>(event=>{
      if(generation!==this.generation)return;
      if(event.reload){this.rooms=[];this.home=undefined;this.problem='reload';this.later();return;}
      if(event.version!==1||!event.home||!Array.isArray(event.rooms)){this.problem='version';return;}
      this.rooms=event.rooms.filter(isView);this.home=event.home;this.problem=undefined;
    },{type:'niak_comfort/home_subscribe'}).then(remove=>{if(generation!==this.generation)void remove();else this.unsubscribe=remove;})
      .catch((e:{code?:string})=>{if(generation===this.generation){this.problem=e?.code??'connection';this.later();}});
  }
  private later(){if(this.retry)return;this.retry=setTimeout(()=>{this.retry=undefined;this.connection=undefined;this.connect();},4000);}
  private open(view:View){history.pushState(null,'','/niak/confort/'+encodeURIComponent(view.entry_id));window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));}
  private facts(h:Home){
    const f=[];
    if(h.hottest&&h.coolest)f.push(html`<span class="chip">${icon('temp')}Plus chaude : ${h.hottest.title} ${number(h.hottest.temperature)} °C</span><span class="chip">${icon('cold')}Plus fraîche : ${h.coolest.title} ${number(h.coolest.temperature)} °C</span>`);
    if(h.start_with)f.push(html`<span class="chip strong">${icon('open')}Commencez par : ${h.start_with}${h.start_floor?` · ${h.start_floor.name}`:''}</span>`);
    if(h.open_rooms.length)f.push(html`<span class="chip">${icon('open')}Ouvert : ${h.open_rooms.map(r=>`${r.title} (${r.open.length})`).join(', ')}</span>`);
    if(h.crossing==='strong')f.push(html`<span class="chip">${icon('air')}Façades opposées ouvertes · passage de l’air à vérifier</span>`);
    else if(h.crossing==='partial')f.push(html`<span class="chip">${icon('air')}Deux façades ouvertes</span>`);
    for(const s of h.sun_entering)f.push(html`<span class="chip warn">${icon('sun')}Soleil qui entre : ${s.title}</span>`);
    if(h.floor_contrast){const c=h.floor_contrast;f.push(html`<span class="chip">${c.warmer} : ${number(c.difference)} °C de plus que ${c.cooler}${c.partial?' · mesures incomplètes':''}</span>`);}
    return f.length?html`<div class="home-facts">${f}</div>`:nothing;
  }
  private room(r:View){return html`<button class="home-room" data-level=${r.assessment.level} @click=${()=>this.open(r)} title="Configurer ${r.title}"><span class="dot"></span><strong>${r.title}</strong><span class="home-room-advice">${['action','urgent','benefit'].includes(r.assessment.level)?summary(r)[0]:numeric(r.observations.indoor_temperature)===null?'Mesure indisponible':''}</span><span class="home-room-temp">${number(numeric(r.observations.indoor_temperature))}<small> °C</small></span></button>`;}
  protected render(){
    if(!this.config)return nothing;
    const h=this.home;
    if(!h){const text=this.problem==='not_configured'?['Aucune pièce','Ouvrez Niak Confort dans la barre latérale pour configurer vos pièces.']:this.problem?['Connexion indisponible','La carte réessaie automatiquement.']:['Chargement du logement','En attente des pièces.'];
      return html`<ha-card class="nc-card problem" data-level="neutral" role="status"><h2>${text[0]}</h2><p>${text[1]}</p></ha-card>`;}
    const focus=this.rooms.find(r=>r.entry_id===h.focus),calm=!focus||focus.assessment.level==='calm';
    const [title,text]=focus&&!calm?summary(focus):[h.partial?'Bilan du logement incomplet':'Tout va bien dans le logement',h.partial?'Bilan sur les mesures disponibles.':'Toutes les pièces sont dans vos repères.'];
    const temps=this.rooms.map(r=>numeric(r.observations.indoor_temperature)).filter((t):t is number=>t!==null);
    return html`<ha-card class="nc-card home-card" data-level=${h.level}>
      <div class="hero home-hero"><div class="hero-head"><h2>${this.config.title||'Confort · Mon logement'}</h2><span class="source-chip">${icon('home')}${this.rooms.length} pièce${this.rooms.length>1?'s':''}</span></div>
        <div class="hero-text"><span class="status">${icon(calm?'check':'alert')}${levelLabels[h.level as keyof typeof levelLabels]??''}</span><h3>${focus&&!calm?html`${focus.title} · ${title}`:title}</h3><p>${text}</p></div></div>
      <div class="exchange" aria-label="Dedans et dehors"><div><div class="measure-name">Dedans</div><div class="measure-value range">${temps.length?number(Math.min(...temps)):'—'}${temps.length>1?html`<small>–</small>${number(Math.max(...temps))}`:nothing}<small>°C</small></div></div>
        <div class="exchange-line">${h.spread!==null?`${number(h.spread)} °C d’écart entre pièces`:'Écart entre pièces inconnu'}</div>
        <div class="outside"><div class="measure-name">Dehors</div><div class="measure-value">${number(h.outdoor_temperature)}<small>°C</small></div></div></div>
      ${h.floors?.length?html`${h.floors.map(f=>html`<section class="home-floor"><div class="home-floor-heading"><h3>${h.floors!.length===1?'Mon logement':f.name}</h3><strong>${number(f.mean)} °C <small>· moyenne</small></strong></div><p class="home-floor-coverage">${f.measured} pièce${f.measured>1?'s':''} mesurée${f.measured>1?'s':''} sur ${f.total}${f.hottest?` · Plus chaude : ${f.hottest.title} (${number(f.hottest.temperature)} °C)`:''}</p><div class="home-rooms">${this.rooms.filter(r=>f.room_ids.includes(r.entry_id)).map(r=>this.room(r))}</div></section>`)}`:html`<div class="home-rooms">${this.rooms.map(r=>this.room(r))}</div>`}
      ${h.ventilation?html`<div class="home-ventilation"><strong>${h.ventilation.engaged?'Ouvertures engagées':h.ventilation.kind==='cross'?'Aération traversante possible':'Effet cheminée possible'}</strong><p>${h.ventilation.openings.map(o=>`${o.title} — ${o.name}`).join(' + ')}.</p><p>${h.ventilation.engaged?'Ces ouvrants sont ouverts.':'Associez ces ouvertures si le passage intérieur est libre.'} ${h.ventilation.kind==='combined'?'Le vent peut aider le tirage entre les niveaux.':''}</p><details><summary>Pourquoi ce conseil ?</summary><p>L’air extérieur est plus frais et les conditions suivies de ces pièces permettent le rafraîchissement. ${h.ventilation.kind==='cross'?'Les ouvrants donnent sur des façades opposées.':'Les ouvertures se situent sur deux niveaux différents ; un tirage thermique est possible, même sans vent.'} Le passage intérieur doit rester libre. Le débit et la circulation réelle de l’air ne sont pas mesurés.</p></details></div>`:nothing}
      ${this.facts(h)}
    </ha-card>`;
  }
}
if(!customElements.get('niak-comfort-home-card'))customElements.define('niak-comfort-home-card',NiakComfortHomeCard);
declare global {interface Window {customCards?:Array<Record<string,unknown>>}}
window.customCards??=[];
if(!window.customCards.some(c=>c.type==='niak-comfort-home-card'))window.customCards.push({type:'niak-comfort-home-card',name:'Niak Confort · logement',description:'La synthèse de toutes vos pièces : celle qui demande le plus d’attention, la plus chaude, les ouvrants ouverts.'});
