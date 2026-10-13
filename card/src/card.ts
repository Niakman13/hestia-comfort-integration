import {html, LitElement, unsafeCSS, nothing, type PropertyValues} from 'lit';
import {property,state} from 'lit/decorators.js';
import style from './ui/charter.css';
import {cleanConfig,type Config,type View,type HomeAssistant} from './types';
import {number,numeric,summary,levelLabels} from './view';
import {icon} from './ui/icons';
import {details,hero,quality,type Controls} from './views/panel';
import {LiveView} from './live';
import './editor';

let instances=0;
const problems:Record<string,[string,string]>={
  choose_entry:['Choisissez une pièce','Plusieurs pièces Niak Comfort sont configurées. Choisissez celle de cette carte dans ses réglages.'],
  not_configured:['Ajoutez Niak Comfort','Ouvrez Niak Confort dans la barre latérale pour configurer votre première pièce après installation de l’intégration.'],
  not_found:['Pièce introuvable','Cette pièce n’est pas chargée. Vérifiez l’intégration ou choisissez une autre pièce dans les réglages de la carte.'],
  unknown_command:['Installez la version compatible de l’intégration','La carte nécessite l’intégration Niak Comfort avec la vue v1. Installez ou mettez à jour les deux fichiers ensemble, puis redémarrez Home Assistant.'],
  version:['Vue incompatible','La réponse reçue ne correspond pas à cette carte. Mettez à jour la carte et l’intégration ensemble.'],
  stale:['Le conseil n’est plus actuel','Le lien n’a pas fourni de résultat récent. Les anciennes mesures sont retirées jusqu’au retour des mises à jour.'],
  unavailable:['Calcul indisponible','Le moteur n’a pas de résultat utilisable. Vérifiez l’intégration et ses journaux.'],
  reload:['La pièce se recharge','Les réglages ont changé. Le conseil reviendra après reconnexion.'],
  connection:['Connexion indisponible','Le conseil est retiré. La carte réessaie automatiquement ; vérifiez la connexion et les journaux de l’intégration.'],
};
export class NiakComfortCard extends LitElement {
  static styles=unsafeCSS(style);
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:Config;
  @state() private view?:View;
  @state() private problem?:string;
  @state() private expanded=false;
  @state() private why=false;
  @state() private sources=false;
  @state() private dialogOpen=false;
  @state() private dialogWhy=false;
  @state() private dialogSources=false;
  private uid=`nc-${++instances}`;
  private press?:{timer:ReturnType<typeof setTimeout>;x:number;y:number};
  private held=false;
  private openingControl?:HTMLElement;
  private live=new LiveView(v=>{this.view=v;this.problem=undefined;},code=>{this.problem=code;},()=>{this.view=undefined;this.closeFull();});
  setConfig(input:Config) {
    const next=cleanConfig(input),old=this.config;
    if(!old||old.format!==next.format) this.expanded=next.format==='intermediate';
    if(old?.entry_id!==next.entry_id){this.live.stop();this.view=undefined;this.problem=undefined;this.closeFull();this.why=false;this.sources=false;}
    this.config=next;
  }
  static getConfigElement(){return document.createElement('niak-comfort-card-editor');}
  static getStubConfig():Config{return {type:'custom:niak-comfort-card',format:'tile'};}
  getCardSize(){return this.config?.format==='mini'?1:this.config?.format==='full'?10:this.expanded?7:2;}
  getGridOptions(){return {columns:this.config?.format==='full'?'full':12,rows:'auto',min_columns:6};}
  connectedCallback(){super.connectedCallback();this.connect();}
  disconnectedCallback(){super.disconnectedCallback();this.cancelPress();this.live.stop();this.closeFull();}
  protected updated(changed:PropertyValues){
    if(changed.has('hass')||changed.has('config')) this.connect();
    const theme=this.config?.theme==='auto'||!this.config?.theme?(this.hass?.themes?.darkMode===false?'light':'dark'):this.config.theme;
    this.setAttribute('theme',theme);this.toggleAttribute('still',this.config?.animations===false);this.toggleAttribute('flat',this.config?.glass_effect===false);
    const dialog=this.renderRoot.querySelector<HTMLDialogElement>('dialog');
    if(this.dialogOpen&&dialog&&!dialog.open) dialog.showModal();
  }
  private connect(){if(this.isConnected&&this.hass?.connection&&this.config)this.live.start(this.hass.connection,this.config.entry_id);}
  private controls(modal=false):Controls{return {why:modal?this.dialogWhy:this.why,sources:modal?this.dialogSources:this.sources,uid:this.uid+(modal?'-dialog':'-main'),
    toggleWhy:()=>{if(modal)this.dialogWhy=!this.dialogWhy;else this.why=!this.why;},toggleSources:()=>{if(modal)this.dialogSources=!this.dialogSources;else this.sources=!this.sources;}};}
  private openFull(event?:Event){this.cancelPress();this.openingControl=event?.currentTarget instanceof HTMLElement?event.currentTarget:undefined;this.dialogOpen=true;}
  private closeFull(){
    this.renderRoot?.querySelector<HTMLDialogElement>('dialog')?.close();this.dialogOpen=false;
    this.openingControl?.focus();this.openingControl=undefined;
  }
  private cancelPress(){if(this.press)clearTimeout(this.press.timer);this.press=undefined;}
  private down(e:PointerEvent){if(e.button!==0)return;this.held=false;this.cancelPress();const control=e.currentTarget as HTMLElement;this.press={x:e.clientX,y:e.clientY,timer:setTimeout(()=>{this.held=true;this.openFull();this.openingControl=control;},650)};}
  private move(e:PointerEvent){if(this.press&&Math.hypot(e.clientX-this.press.x,e.clientY-this.press.y)>10)this.cancelPress();}
  private tap(e:Event){this.cancelPress();if(this.held){this.held=false;return;}if(this.config?.format==='mini')this.openFull(e);else this.expanded=!this.expanded;}
  private key(e:KeyboardEvent){if(e.key==='Enter'&&e.shiftKey){e.preventDefault();this.openFull(e);}}
  private configure(){
    const path="/niak-confort"+(this.view?.entry_id?"/"+encodeURIComponent(this.view.entry_id):"");
    // Navigate inside Home Assistant, without reloading the whole page.
    history.pushState(null,'',path);window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));
  }
  private panel(full:boolean,modal=false){
    const v=this.view!,config=this.config!,c=this.controls(modal),[title,text]=summary(v),mini=!full&&config.format==='mini';
    return html`<ha-card class=${'nc-card '+(mini?'mini':'')} data-level=${v.assessment.level} data-action=${v.assessment.action}>
      ${full?hero(v,config,c):html`<button class="tile-head" aria-label=${title+': '+(mini?'ouvrir la carte complète':this.expanded?'replier le détail':'déplier le détail')} aria-expanded=${mini?nothing:this.expanded}
        @click=${this.tap} @keydown=${this.key} @pointerdown=${this.down} @pointermove=${this.move} @pointerup=${this.cancelPress} @pointercancel=${this.cancelPress} @pointerleave=${this.cancelPress} @contextmenu=${(e:Event)=>{e.preventDefault();this.cancelPress();}}>
        ${icon(v.assessment.action==='ouvrir'?'open':'window')}<span class="tile-copy"><span class="situation-label">${levelLabels[v.assessment.level]}</span><strong>${title}</strong><span>${config.title||v.title} · ${mini?(v.assessment.partial?'Bilan partiel':'Confort observé'):text}</span></span><span class="tile-now">${number(numeric(v.observations.indoor_temperature))}<small> °C</small></span>${icon('chevron','tile-chevron')}
      </button>`}
      ${mini?nothing:html`${full||this.expanded?html`${full?nothing:html`<div class="hero-actions" style="padding:0 16px 12px"><button @click=${c.toggleWhy} aria-expanded=${c.why} aria-controls=${'why-'+c.uid}>${icon('info')}Pourquoi ?</button></div>`}${details(v,config,c,full)}`:nothing}${quality(v,c)}
        ${full?nothing:html`<div class="tile-footer"><span>Appui long : vue complète</span><button @click=${this.openFull}>Ouvrir la complète</button></div>`}`}
      ${this.hass?.user?.is_admin?html`<div class="tile-footer"><button @click=${()=>this.configure()}>${icon("settings")}Configurer cette pièce</button></div>`:nothing}
    </ha-card>`;
  }
  protected render(){
    if(!this.config)return nothing;
    if(!this.view){const [title,text]=this.problem?(problems[this.problem]??problems.connection):['Chargement du confort','En attente des observations de la pièce.'];
      return html`<ha-card class="nc-card problem" data-level="neutral" role="status"><h2>${title}</h2><p>${text}</p>${this.problem?html`<button @click=${()=>{this.live.stop();this.problem=undefined;this.connect();}}>Réessayer</button>${this.hass?.user?.is_admin?html`<button @click=${()=>this.configure()}>Ouvrir Niak Confort</button>`:nothing}`:nothing}</ha-card>`;}
    return html`${this.panel(this.config.format==='full')}
      <dialog aria-labelledby=${this.uid+'-dialog-title'} @cancel=${()=>{this.dialogOpen=false;}} @close=${()=>{this.dialogOpen=false;}}>
        <div class="dialog-top"><span id=${this.uid+'-dialog-title'}>Confort · ${this.view.title}</span><button class="icon-button" aria-label="Fermer la carte complète" @click=${()=>this.closeFull()}>${icon('close')}</button></div><div>${this.dialogOpen?this.panel(true,true):nothing}</div>
      </dialog>`;
  }
}
// The integration bundles this card; an older copy declared as a resource must not break the page.
if(!customElements.get('niak-comfort-card'))customElements.define('niak-comfort-card',NiakComfortCard);
declare global {interface Window {customCards?:Array<Record<string,unknown>>}}
window.customCards??=[];
if(!window.customCards.some(c=>c.type==='niak-comfort-card'))window.customCards.push({type:'niak-comfort-card',name:'Niak Confort',description:'Niak Comfort : le confort par pièce, avec des conseils expliqués et des sources visibles.'});
