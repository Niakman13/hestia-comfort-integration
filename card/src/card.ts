import {html, LitElement, unsafeCSS, nothing, type PropertyValues} from 'lit';
import {property,state} from 'lit/decorators.js';
import style from './ui/charter.css';
import charte from './ui/niak-charte.css';
import roomStyle from './ui/room.css';
import {cleanConfig,type Config,type View,type HomeAssistant} from './types';
import {icon} from './ui/icons';
import {roomCard,asking,type CardState} from './views/room';
import {LiveView} from './live';
import './editor';
import './home';

let instances=0;
const problems:Record<string,[string,string]>={
  choose_entry:['Choisissez une pièce','Plusieurs pièces Niak Comfort sont configurées. Choisissez celle de cette carte dans ses réglages.'],
  not_configured:['Ajoutez Niak Comfort','Ouvrez Niak Confort dans la barre latérale pour configurer votre première pièce après installation de l’intégration.'],
  not_found:['Pièce introuvable','Cette pièce a été supprimée ou n’est pas chargée. Choisissez une autre pièce dans les réglages de la carte.'],
  unknown_command:['Installez la version compatible de l’intégration','La carte nécessite l’intégration Niak Comfort avec la vue v1. Installez ou mettez à jour les deux fichiers ensemble, puis redémarrez Home Assistant.'],
  version:['Vue incompatible','La réponse reçue ne correspond pas à cette carte. Mettez à jour la carte et l’intégration ensemble.'],
  stale:['Le conseil n’est plus actuel','Le lien n’a pas fourni de résultat récent. Les anciennes mesures sont retirées jusqu’au retour des mises à jour.'],
  unavailable:['Calcul indisponible','Le moteur n’a pas de résultat utilisable. Vérifiez l’intégration et ses journaux.'],
  reload:['La pièce se recharge','Les réglages ont changé. Le conseil reviendra après reconnexion.'],
  connection:['Connexion indisponible','Le conseil est retiré. La carte réessaie automatiquement ; vérifiez la connexion et les journaux de l’intégration.'],
};
export class NiakComfortCard extends LitElement {
  static styles=[unsafeCSS(style),unsafeCSS(charte),unsafeCSS(roomStyle)];
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:Config;
  @state() private view?:View;
  @state() private problem?:string;
  @state() private open:Record<string,boolean>={};
  @state() private dialogOpen=false;
  /** Set by Home Assistant in the card editor's preview and while the dashboard is edited. */
  @property({type:Boolean}) preview=false;
  @property({type:Boolean}) editMode=false;
  private uid=`nc-${++instances}`;
  private openingControl?:HTMLElement;
  private live=new LiveView(v=>{this.view=v;this.problem=undefined;},code=>{this.problem=code;},()=>{this.view=undefined;this.closeFull();});
  setConfig(input:Config) {
    const next=cleanConfig(input),old=this.config;
    if(old?.entry_id!==next.entry_id){this.live.stop();this.view=undefined;this.problem=undefined;this.closeFull();this.open={};}
    this.config=next;
  }
  static getConfigElement(){return document.createElement('niak-comfort-card-editor');}
  static getStubConfig():Config{return {type:'custom:niak-comfort-card',format:'tile'};}
  getCardSize(){const f=this.config?.format;return f==='mini'?1:f==='alert'?2:f==='full'?10:f==='measures'?4:3;}
  getGridOptions(){return {columns:this.config?.format==='full'?'full':12,rows:'auto',min_columns:6};}
  connectedCallback(){super.connectedCallback();this.connect();}
  disconnectedCallback(){super.disconnectedCallback();this.live.stop();this.closeFull();}
  protected updated(changed:PropertyValues){
    if(changed.has('hass')||changed.has('config')) this.connect();
    const theme=this.config?.theme==='auto'||!this.config?.theme?(this.hass?.themes?.darkMode===false?'light':'dark'):this.config.theme;
    this.setAttribute('theme',theme);this.toggleAttribute('still',this.config?.animations===false);
    // An alert with nothing to say takes no room on the dashboard.
    this.toggleAttribute('empty',this.config?.format==='alert'&&!!this.view&&!asking(this.view)&&!this.preview&&!this.editMode);this.toggleAttribute('flat',this.config?.glass_effect===false);
    // The new cards follow the Home Assistant theme, like Niak Weather; a theme forced in the card's settings still wins.
    if(this.config?.theme==='light'||this.config?.theme==='dark')this.setAttribute('forced',this.config.theme);else this.removeAttribute('forced');
    const dialog=this.renderRoot.querySelector<HTMLDialogElement>('dialog');
    if(this.dialogOpen&&dialog&&!dialog.open) dialog.showModal();
  }
  private connect(){if(this.isConnected&&this.hass?.connection&&this.config)this.live.start(this.hass.connection,this.config.entry_id);}
  private state(modal:boolean):CardState{
    const prefix=modal?'dialog-':'',fmt=this.config?.format,open=this.open;
    // Measures stay folded in the tile, open in the full card; out-of-range ones always show.
    const get=(k:string,fallback:boolean)=>open[prefix+k]??fallback;
    // Opening at start follows the card's settings; the full card in its window always shows the measures.
    const measures=modal||(this.config?.measures_open??(fmt==='full'||fmt==='intermediate')),details=this.config?.details_open??false;
    const fallback=(k:string)=>k==='tilesOpen'?measures:k==='detailsOpen'?details:false;
    return {why:get('why',false),tilesOpen:get('tilesOpen',measures),detailsOpen:get('detailsOpen',details),uid:this.uid+(modal?'-dialog':'-main'),
      // Read the current state at click time: two quick clicks must not overwrite each other.
      toggle:k=>{const cur=this.open;this.open={...cur,[prefix+k]:!(cur[prefix+k]??fallback(k))};},
      configure:this.hass?.user?.is_admin?()=>this.configure():undefined};
  }
  private openFull(event?:Event){this.openingControl=event?.currentTarget instanceof HTMLElement?event.currentTarget:undefined;this.dialogOpen=true;}
  private closeFull(){
    this.renderRoot?.querySelector<HTMLDialogElement>('dialog')?.close();this.dialogOpen=false;
    this.openingControl?.focus();this.openingControl=undefined;
  }
  private configure(){
    const path="/niak/confort"+(this.view?.entry_id?"/"+encodeURIComponent(this.view.entry_id):"");
    // Navigate inside Home Assistant, without reloading the whole page.
    history.pushState(null,'',path);window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));
  }
  /** What a long press (a tap on mini and alert) does: the full card in a window by default, a page, or nothing. */
  private act=(e:Event)=>{
    const c=this.config!,action=c.hold_action??(c.hold_path?'page':'popup');
    if(action==='none')return;
    if(action==='page'&&c.hold_path){history.pushState(null,'',c.hold_path);window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));return;}
    this.openFull(e);
  };
  private pressTimer?:ReturnType<typeof setTimeout>;
  private held=false;
  private press=(e:PointerEvent)=>{if(e.button!==0)return;this.held=false;clearTimeout(this.pressTimer);
    this.pressTimer=setTimeout(()=>{this.held=true;this.act(e);},500);};
  private release=()=>{clearTimeout(this.pressTimer);};
  // After a long press, the click that follows must not also fold the tile or open a measure.
  private swallow={handleEvent:(e:Event)=>{if(this.held){e.stopPropagation();e.preventDefault();this.held=false;}},capture:true};
  private panel(full:boolean,modal=false){
    const format=full?'full':this.config!.format??'tile';
    const card=roomCard(this.view!,this.config!,this.state(modal),format);
    // The alert format has nothing to say: hidden on the dashboard, a short note in the card editor's preview.
    if(card===null)return this.preview||this.editMode?html`<ha-card class="nc-c nc-alert-note" data-level="calm"><p>Alerte · ${this.view!.title} : rien à signaler. La carte n’apparaît que lorsqu’un geste est conseillé.</p></ha-card>`:nothing;
    if(format==='full')return card;
    const tap=format==='mini'||format==='alert';
    const label=tap?'Ouvrir la carte complète':undefined;
    return html`<div class="nc-hold" role=${tap?'button':'group'} tabindex=${tap?0:-1} aria-label=${label??this.view!.title}
      @click=${tap?this.act:this.swallow} @pointerdown=${tap?undefined:this.press} @pointerup=${this.release} @pointerleave=${this.release} @pointercancel=${this.release} @contextmenu=${(e:Event)=>{if(this.held)e.preventDefault();}}
      @keydown=${(e:KeyboardEvent)=>{if(tap&&(e.key==='Enter'||e.key===' ')){e.preventDefault();this.act(e);}}}>${card}</div>`;
  }
  protected render(){
    if(!this.config)return nothing;
    if(!this.view){const [title,text]=this.problem?(problems[this.problem]??problems.connection):['Chargement du confort','En attente des observations de la pièce.'];
      return html`<ha-card class="nc-card problem" data-level="neutral" role="status"><h2>${title}</h2><p>${text}</p>${this.problem?html`<button @click=${()=>{this.live.stop();this.problem=undefined;this.connect();}}>Réessayer</button>${this.hass?.user?.is_admin?html`<button @click=${()=>this.configure()}>Ouvrir Niak Confort</button>`:nothing}`:nothing}</ha-card>`;}
    return html`${this.panel(this.config.format==='full')}
      <dialog aria-labelledby=${this.uid+'-dialog-title'} @cancel=${()=>{this.dialogOpen=false;}} @close=${()=>{this.dialogOpen=false;}}>
        <div class="dialog-top"><span id=${this.uid+'-dialog-title'}>${this.view.title}</span><button class="icon-button" aria-label="Fermer la carte complète" @click=${()=>this.closeFull()}>${icon('close')}</button></div><div>${this.dialogOpen?this.panel(true,true):nothing}</div>
      </dialog>`;
  }
}
// The integration bundles this card; an older copy declared as a resource must not break the page.
if(!customElements.get('niak-comfort-card'))customElements.define('niak-comfort-card',NiakComfortCard);
declare global {interface Window {customCards?:Array<Record<string,unknown>>}}
window.customCards??=[];
if(!window.customCards.some(c=>c.type==='niak-comfort-card'))window.customCards.push({type:'niak-comfort-card',name:'Niak Confort',description:'Niak Comfort : le confort par pièce, avec des conseils expliqués et des sources visibles.'});
