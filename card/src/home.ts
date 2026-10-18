import {html,LitElement,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {property,state} from 'lit/decorators.js';
import style from './ui/charter.css';
import charte from './ui/niak-charte.css';
import roomStyle from './ui/room.css';
import {html as h2} from 'lit';
import {isView,number,numeric} from './view';
import {advice,scale,fold,hero,tileSummary,pills,moreInfo,type CardState,type Advice,type Slide} from './views/room';
import {cleanHomeConfig,type Connection,type HomeAssistant,type HomeConfig,type Unsubscribe,type View,type Level} from './types';

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

/** The home card: a synthesis of every room. It never replaces the room cards' advice. */
export class NiakComfortHomeCard extends LitElement {
  static styles=[unsafeCSS(style),unsafeCSS(charte),unsafeCSS(roomStyle)];
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:HomeConfig;
  @state() private rooms:View[]=[];
  @state() private home?:Home;
  @state() private problem?:string;
  @state() private folds:Record<string,boolean>={};
  private uid=`nch-${Math.random().toString(36).slice(2,8)}`;
  private connection?:Connection;
  private unsubscribe?:Unsubscribe;
  private retry?:ReturnType<typeof setTimeout>;
  private generation=0;
  setConfig(input:HomeConfig){this.config=cleanHomeConfig(input);}
  static getConfigElement(){return document.createElement('niak-comfort-home-card-editor');}
  static getStubConfig():HomeConfig{return {type:'custom:niak-comfort-home-card'};}
  getCardSize(){return 4+this.rooms.length;}
  connectedCallback(){super.connectedCallback();this.connect();}
  disconnectedCallback(){super.disconnectedCallback();this.stop();}
  protected updated(changed:PropertyValues){
    if(changed.has('hass'))this.connect();
    const theme=this.config?.theme==='auto'||!this.config?.theme?(this.hass?.themes?.darkMode===false?'light':'dark'):this.config.theme;
    this.setAttribute('theme',theme);this.toggleAttribute('still',this.config?.animations===false);this.toggleAttribute('flat',this.config?.glass_effect===false);
    if(this.config?.theme==='light'||this.config?.theme==='dark')this.setAttribute('forced',this.config.theme);else this.removeAttribute('forced');
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
  private state():CardState{
    const o=this.folds,c=this.config,start:Record<string,boolean>={tilesOpen:c?.rooms_open??false,detailsOpen:c?.details_open??false},get=(k:string)=>o[k]??start[k]??false;
    return {why:get('why'),tilesOpen:get('tilesOpen'),detailsOpen:get('detailsOpen'),uid:this.uid,toggle:k=>{const cur=this.folds;this.folds={...cur,[k]:!(cur[k]??start[k]??false)};}};
  }
  /** Short names for the scale: « Chambre AL » → AL, « Salle de bain » → SB, « Salon » → S; never twice the same. */
  private shorts(rooms:View[]):Map<string,string>{
    const out=new Map<string,string>(),used=new Set<string>();
    for(const r of rooms){const words=r.title.trim().split(/\s+/).filter(w=>!/^(de|du|des|la|le|les|d’|d')$/i.test(w));
      let s=words.length>1&&words[words.length-1].length<=3?words[words.length-1].toUpperCase():words.length>1?words.map(w=>w[0]).join('').toUpperCase():r.title.slice(0,1).toUpperCase();
      if(used.has(s))s=r.title.slice(0,2);used.add(s);out.set(r.entry_id,s);}
    return out;
  }
  private roomTile(r:View){
    const t=numeric(r.observations.indoor_temperature),a=r.assessment,lvl=a.level as Level,unheated=a.features?.season?.heated===false;
    const note=t===null?'mesure indisponible':['action','urgent'].includes(lvl)?advice(r).title.toLowerCase():a.needs.includes('cool')?'trop chaud':a.needs.includes('heat')?'trop frais':unheated?'non chauffée':'dans votre plage';
    const out=['action','urgent'].includes(lvl);
    return h2`<button class=${'nc-tile'+(out?' out':'')} data-level=${unheated&&!out?'neutral':lvl} @click=${(e:Event)=>{const id=r.observations.indoor_temperature?.source;if(id)moreInfo(e,id);else this.open(r);}} title=${'Détails : '+r.title}><div class="nc-tile-h"><span class="nw-label">${r.title}</span></div><b>${number(t)}<small>°C</small></b><em>${note}</em></button>`;
  }
  private details(h:Home){
    const row=(t:string,x:string)=>h2`<li><b>${t}</b><span> · ${x}</span></li>`,out=[];
    if(h.start_with)out.push(row('Commencez par',h.start_with+(h.start_floor?` (${h.start_floor.name})`:'')));
    if(h.floor_contrast){const c=h.floor_contrast;out.push(row(c.warmer,`${number(c.difference)} °C de plus que ${c.cooler}${c.partial?' · mesures incomplètes':''}`));}
    if(h.hottest&&h.coolest)out.push(row('Écart entre pièces',`${number(h.spread)} °C (${h.hottest.title} la plus chaude, ${h.coolest.title} la plus fraîche)`));
    if(h.ventilation){const v=h.ventilation;out.push(row(v.kind==='cross'?'Air traversant':'Effet cheminée',`${v.openings.map(o=>`${o.title} — ${o.name}`).join(' + ')}${v.engaged?' · déjà ouverts':''}`));}
    if(h.open_rooms.length)out.push(row('Ouvert',h.open_rooms.map(r=>`${r.title} (${r.open.length})`).join(', ')));
    for(const s of h.sun_entering)out.push(row('Soleil qui entre',s.title));
    if(h.partial)out.push(row('Bilan','sur les mesures disponibles'));
    return out;
  }
  /** One slide per room that asks for something, the most urgent first, then what the home can do as a whole. */
  private slides(h:Home,calmAdvice:Advice):Slide[]{
    const rank:Record<string,number>={urgent:0,action:1,benefit:2};
    const asking=this.rooms.filter(r=>r.assessment.level in rank).sort((a,b)=>rank[a.assessment.level]-rank[b.assessment.level]);
    const out:Slide[]=asking.map(r=>{const ad=advice(r),cool=r.assessment.needs.includes('cool')&&h.start_with===r.title;
      return {...ad,level:r.assessment.level as Level,pill:r.title,line:cool&&h.start_floor?h2`${ad.line} · <b>${h.start_floor.name}</b> d’abord`:ad.line};});
    if(h.ventilation&&!h.ventilation.engaged)out.push({level:'benefit',pill:'Logement',title:h.ventilation.kind==='cross'?'Faites traverser l’air':'Ouvrez en bas et en haut',
      line:h2`${h.ventilation.openings.map(o=>o.name).join(' + ')}`,disk:'open'});
    return out.length?out:[{...calmAdvice,level:h.level as Level,pill:pills[h.level as Level]}];
  }
  protected render(){
    if(!this.config)return nothing;
    const h=this.home;
    if(!h){const text=this.problem==='not_configured'?['Aucune pièce','Ouvrez Niak Confort dans la barre latérale pour configurer vos pièces.']:this.problem?['Connexion indisponible','La carte réessaie automatiquement.']:['Chargement du logement','En attente des pièces.'];
      return html`<ha-card class="nc-card problem" data-level="neutral" role="status"><h2>${text[0]}</h2><p>${text[1]}</p></ha-card>`;}
    const focus=this.rooms.find(r=>r.entry_id===h.focus);
    const calmAdvice={title:h.partial?'Bilan partiel':'Rien à faire',line:h2`Toutes les pièces sont <b>${h.partial?'suivies avec les mesures disponibles':'dans votre plage'}</b>`,disk:h.open_rooms.length?'open':'check',cap:h.open_rooms.length?undefined:'Tout est fermé'};
    const homeSlides=this.slides(h,calmAdvice);
    const shorts=this.shorts(this.rooms),season=(focus??this.rooms[0])?.assessment.features?.season;
    const rooms=this.rooms.flatMap(r=>{const t=numeric(r.observations.indoor_temperature);return t===null?[]:[{name:r.title,entity:r.observations.indoor_temperature?.source??undefined,short:shorts.get(r.entry_id)!,value:t,level:(r.assessment.features?.season?.heated===false&&!['action','urgent'].includes(r.assessment.level)?'neutral':r.assessment.level) as Level}];});
    const st=this.state(),floors=h.floors?.length?h.floors:[{floor_id:null,name:'Mon logement',level:null,room_ids:this.rooms.map(r=>r.entry_id),mean:null,measured:0,total:0,hottest:null}];
    const all=this.rooms.map(r=>this.roomTile(r)),outside=this.rooms.filter(r=>['action','urgent'].includes(r.assessment.level));
    const body=h2`<div class="nc-tiles">${floors.map(f=>h2`${floors.length>1?h2`<div class="nc-floor"><span class="nw-label">${f.name}</span><b>${number(f.mean)} °C</b></div>`:nothing}${this.rooms.filter(r=>f.room_ids.includes(r.entry_id)).map(r=>this.roomTile(r))}`)}</div>`;
    const c=this.config;
    return html`<ha-card class="nc-c" data-level=${h.level}>
      ${hero({name:c.title||'Mon logement',level:h.level as Level,slides:homeSlides,compact:c.show_scale===false,still:c.animations===false||c.rotate===false,scaleLabel:'Les pièces',scale:scale({band:season?[season.minimum,season.maximum]:null,out:h.outdoor_temperature,rooms,outEntity:this.rooms[0]?.observations.outdoor_temperature?.source??undefined}),st,why:h2`<p><b>Pièce suivie de près</b> · ${focus?focus.title:'aucune'}</p><p><b>Bilan</b> · ${h.partial?'mesures incomplètes dans au moins une pièce':'toutes les pièces répondent'}</p>`})}
      <div class="nc-body" ?hidden=${c.show_rooms===false&&c.show_details===false}>
        ${c.show_rooms===false?nothing:fold({label:'Pièces',summary:tileSummary(all.length,outside.length,'pièce'),open:st.tilesOpen,onToggle:()=>st.toggle('tilesOpen'),id:this.uid+'-rooms',body,keep:outside.map(r=>this.roomTile(r))})}
        ${c.show_details===false?nothing:fold({label:'Détails',summary:'',open:st.detailsOpen,onToggle:()=>st.toggle('detailsOpen'),id:this.uid+'-details',body:h2`<ul class="nc-list">${this.details(h)}</ul>`})}
      </div>
    </ha-card>`;
  }
}
if(!customElements.get('niak-comfort-home-card'))customElements.define('niak-comfort-home-card',NiakComfortHomeCard);
declare global {interface Window {customCards?:Array<Record<string,unknown>>}}
window.customCards??=[];
if(!window.customCards.some(c=>c.type==='niak-comfort-home-card'))window.customCards.push({type:'niak-comfort-home-card',name:'Niak Confort · logement',description:'La synthèse de toutes vos pièces : celle qui demande le plus d’attention, la plus chaude, les ouvrants ouverts.'});
