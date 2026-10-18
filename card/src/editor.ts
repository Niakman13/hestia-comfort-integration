import {LitElement,html,css,type PropertyValues} from 'lit';
import {property,state} from 'lit/decorators.js';
import {cleanConfig,cleanHomeConfig,MODULES,moduleLabels,type Config,type HomeConfig,type Module,type HomeAssistant,type Entry} from './types';
import {icon} from './ui/icons';

export class ComfortEditor extends LitElement {
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:Config;
  @state() private entries:Entry[]=[];
  @state() private error='';
  private connection?:HomeAssistant['connection'];
  private generation=0;
  static styles=css`
    :host {display:block;color:var(--primary-text-color);font:14px/1.5 var(--paper-font-body1_-_font-family,Roboto,system-ui,sans-serif)}
    * {box-sizing:border-box}h3 {font-size:16px;margin:24px 0 12px}p {font-size:13px;color:var(--secondary-text-color)}.hint {margin:-6px 0 10px 28px;font-size:12px}
    label {display:flex;flex-direction:column;gap:6px;margin:12px 0}input,select,button {font:inherit;color:inherit;border:1px solid var(--divider-color,#bdc5d1);border-radius:8px;background:var(--card-background-color,#fff);padding:10px;max-width:100%;min-height:40px}
    .check {flex-direction:row;align-items:center;gap:10px}.check input {width:18px;height:18px;min-height:18px;margin:0;accent-color:var(--primary-color)}
    .row {display:flex;gap:10px;align-items:center}.row label {flex:1}.row button {display:flex;align-items:center;justify-content:center;min-width:40px;padding:8px}.icon {width:18px;height:18px}
    :focus-visible {outline:2px solid var(--primary-color);outline-offset:3px}button {cursor:pointer}button:disabled {opacity:.4;cursor:default}
  `;
  setConfig(config:Config){this.config=cleanConfig(config);}
  protected updated(changed:PropertyValues){if(changed.has('hass')&&this.hass?.connection!==this.connection){this.connection=this.hass?.connection;void this.load();}}
  disconnectedCallback(){super.disconnectedCallback();this.generation++;this.connection=undefined;}
  connectedCallback(){super.connectedCallback();if(this.hass)void this.load();}
  private async load(){
    if(!this.hass)return;const generation=++this.generation;this.error='';this.entries=[];
    try{const entries=await this.hass.callWS<Entry[]>({type:'niak_comfort/entries'});if(generation===this.generation){this.entries=entries;if(!entries.length)this.error='Aucune pièce Niak Comfort chargée. Ajoutez une pièce dans l’intégration.';}}
    catch{if(generation===this.generation)this.error='La liste des pièces est indisponible. Vérifiez que l’intégration Niak Comfort est installée et chargée.';}
  }
  private change(patch:Partial<Config>){
    this.config=cleanConfig({...this.config!,...patch});
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));
  }
  private module(id:Module,enabled:boolean){const current=this.config?.modules??[];this.change({modules:enabled?[...current,id]:current.filter(m=>m!==id)});}
  private move(id:Module){const order=[...(this.config?.modules??[])],i=order.indexOf(id);if(i>0){[order[i-1],order[i]]=[order[i],order[i-1]];this.change({modules:order});}}
  private check(key:keyof Config,label:string,fallback:boolean,hint?:string,disabled=false){
    const c=this.config!,value=(c[key] as boolean|undefined)??fallback;
    return html`<label class="check"><input type="checkbox" .checked=${value} ?disabled=${disabled} @change=${(e:Event)=>this.change({[key]:(e.target as HTMLInputElement).checked} as Partial<Config>)}>${label}</label>${hint?html`<p class="hint">${hint}</p>`:null}`;
  }
  protected render(){
    const c=this.config;if(!c)return html``;
    const order=[...c.modules??[],...MODULES.filter(m=>!c.modules?.includes(m))],full=c.format==='full'||c.format==='intermediate',mini=c.format==='mini';
    return html`<h3>La carte</h3>
      <label>Pièce<select .value=${c.entry_id??''} @change=${(e:Event)=>this.change({entry_id:(e.target as HTMLSelectElement).value||undefined})}><option value="" ?selected=${!c.entry_id}>Automatique · une seule pièce configurée</option>
        ${c.entry_id&&!this.entries.some(e=>e.entry_id===c.entry_id)?html`<option value=${c.entry_id} selected>Pièce sélectionnée · à vérifier</option>`:null}
        ${this.entries.map(e=>html`<option value=${e.entry_id} ?selected=${e.entry_id===c.entry_id}>${e.title}</option>`)}</select></label>
      ${this.error?html`<p role="status">${this.error}</p><button @click=${()=>this.load()}>Recharger les pièces</button>`:null}
      <label>Titre facultatif<input type="text" maxlength="100" .value=${c.title??''} @input=${(e:Event)=>this.change({title:(e.target as HTMLInputElement).value})}></label>
      <label>Format<select .value=${full?'full':c.format??'tile'} @change=${(e:Event)=>this.change({format:(e.target as HTMLSelectElement).value as Config['format']})}>
        <option value="full">Complète : bandeau, échelle, mesures et détails</option><option value="tile">Tuile : mesures repliées au départ</option><option value="mini">Mini : le bandeau seul, un appui ouvre la complète</option></select></label>
      <h3>Contenu</h3>
      ${this.check('rotate','Faire défiler les conseils',true,'Quand il y a plusieurs conseils, ils défilent toutes les 4,5 s. Décoché, ils changent seulement d’un appui.')}
      ${this.check('show_scale','Échelle de température',true,'Votre plage, la température actuelle, le minimum et le maximum des dernières 24 h et dehors.',mini)}
      ${this.check('show_measures','Section Mesures',true,undefined,mini)}
      ${this.check('measures_open','Mesures dépliées au départ',full,'Repliées, les mesures hors de votre plage restent visibles.',mini||c.show_measures===false)}
      ${this.check('show_details','Section Détails',true,undefined,mini)}
      ${this.check('details_open','Détails dépliés au départ',false,undefined,mini||c.show_details===false)}
      <h3>Rubriques des mesures</h3><p class="hint">Masquer une rubrique change l’affichage, pas le calcul du conseil.</p>
      ${order.filter(id=>id!=='temperature').map(id=>html`<div class="row"><label class="check"><input type="checkbox" .checked=${!!c.modules?.includes(id)} @change=${(e:Event)=>this.module(id,(e.target as HTMLInputElement).checked)}>${moduleLabels[id]}</label><button aria-label=${'Monter '+moduleLabels[id]} ?disabled=${!c.modules?.includes(id)||c.modules.indexOf(id)===0} @click=${()=>this.move(id)}>${icon('up')}</button></div>`)}
      <h3>Visuel et performance</h3><label>Thème<select .value=${c.theme??'auto'} @change=${(e:Event)=>this.change({theme:(e.target as HTMLSelectElement).value as Config['theme']})}><option value="auto">Suivre Home Assistant</option><option value="light">Clair</option><option value="dark">Sombre</option></select></label>
      ${this.check('animations','Animations',true,'Coupées, les conseils ne défilent plus seuls et rien ne bouge.')}
      ${this.check('glass_effect','Effet de verre',true,'Le décocher allège l’affichage sur les appareils lents. La réduction des animations de votre appareil est toujours respectée.')}
      <p class="hint">Les capteurs et préférences se règlent dans Niak Confort, accessible depuis la barre latérale de Home Assistant.</p>`;
  }
}
if(!customElements.get('niak-comfort-card-editor'))customElements.define('niak-comfort-card-editor',ComfortEditor);

/** The home card's settings, laid out like the room card's: the card, its content, then visuals and performance. */
export class ComfortHomeEditor extends LitElement {
  @property({attribute:false}) hass?:HomeAssistant;
  @state() private config?:HomeConfig;
  static styles=ComfortEditor.styles;
  setConfig(config:HomeConfig){this.config=cleanHomeConfig(config);}
  private change(patch:Partial<HomeConfig>){
    this.config=cleanHomeConfig({...this.config!,...patch});
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));
  }
  private check(key:keyof HomeConfig,label:string,fallback:boolean,hint?:string,disabled=false){
    const value=(this.config![key] as boolean|undefined)??fallback;
    return html`<label class="check"><input type="checkbox" .checked=${value} ?disabled=${disabled} @change=${(e:Event)=>this.change({[key]:(e.target as HTMLInputElement).checked} as Partial<HomeConfig>)}>${label}</label>${hint?html`<p class="hint">${hint}</p>`:null}`;
  }
  protected render(){
    const c=this.config;if(!c)return html``;
    return html`<h3>La carte</h3>
      <label>Titre facultatif<input type="text" maxlength="100" placeholder="Mon logement" .value=${c.title??''} @input=${(e:Event)=>this.change({title:(e.target as HTMLInputElement).value||undefined})}></label>
      <h3>Contenu</h3>
      ${this.check('rotate','Faire défiler les conseils',true,'Quand plusieurs pièces demandent quelque chose, leurs conseils défilent toutes les 4,5 s. Décoché, ils changent seulement d’un appui.')}
      ${this.check('show_scale','Échelle des pièces',true,'Votre plage, la température de chaque pièce et dehors.')}
      ${this.check('show_rooms','Section Pièces',true)}
      ${this.check('rooms_open','Pièces dépliées au départ',false,'Repliées, les pièces qui demandent un geste restent visibles.',c.show_rooms===false)}
      ${this.check('show_details','Section Détails',true)}
      ${this.check('details_open','Détails dépliés au départ',false,undefined,c.show_details===false)}
      <h3>Visuel et performance</h3><label>Thème<select .value=${c.theme??'auto'} @change=${(e:Event)=>this.change({theme:(e.target as HTMLSelectElement).value as HomeConfig['theme']})}><option value="auto">Suivre Home Assistant</option><option value="light">Clair</option><option value="dark">Sombre</option></select></label>
      ${this.check('animations','Animations',true,'Coupées, les conseils ne défilent plus seuls et rien ne bouge.')}
      ${this.check('glass_effect','Effet de verre',true,'Le décocher allège l’affichage sur les appareils lents. La réduction des animations de votre appareil est toujours respectée.')}
      <p class="hint">Les pièces et préférences se règlent dans Niak Confort, accessible depuis la barre latérale de Home Assistant.</p>`;
  }
}
if(!customElements.get('niak-comfort-home-card-editor'))customElements.define('niak-comfort-home-card-editor',ComfortHomeEditor);
