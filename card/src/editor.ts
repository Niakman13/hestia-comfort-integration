import {LitElement,html,css,type PropertyValues} from 'lit';
import {property,state} from 'lit/decorators.js';
import {cleanConfig,MODULES,moduleLabels,type Config,type Module,type HomeAssistant,type Entry} from './types';
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
    * {box-sizing:border-box}h3 {font-size:16px;margin:24px 0 12px}p {font-size:13px;color:var(--secondary-text-color)}
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
  protected render(){
    const c=this.config;if(!c)return html``;
    const order=[...c.modules??[],...MODULES.filter(m=>!c.modules?.includes(m))];
    return html`<h3>La carte</h3>
      <label>Pièce<select .value=${c.entry_id??''} @change=${(e:Event)=>this.change({entry_id:(e.target as HTMLSelectElement).value||undefined})}><option value="" ?selected=${!c.entry_id}>Automatique · une seule pièce configurée</option>
        ${c.entry_id&&!this.entries.some(e=>e.entry_id===c.entry_id)?html`<option value=${c.entry_id} selected>Pièce sélectionnée · à vérifier</option>`:null}
        ${this.entries.map(e=>html`<option value=${e.entry_id} ?selected=${e.entry_id===c.entry_id}>${e.title}</option>`)}</select></label>
      ${this.error?html`<p role="status">${this.error}</p><button @click=${()=>this.load()}>Recharger les pièces</button>`:null}
      <label>Titre facultatif<input type="text" maxlength="100" .value=${c.title??''} @input=${(e:Event)=>this.change({title:(e.target as HTMLInputElement).value})}></label>
      <label>Format<select .value=${c.format??'tile'} @change=${(e:Event)=>this.change({format:(e.target as HTMLSelectElement).value as Config['format']})}><option value="mini">Mini</option><option value="tile">Tuile</option><option value="intermediate">Dépliée</option><option value="full">Complète</option></select></label>
      <h3>Rubriques et ordre</h3><p>Masquer une rubrique change l’affichage, pas le calcul du conseil.</p>
      ${order.map(id=>html`<div class="row"><label class="check"><input type="checkbox" .checked=${!!c.modules?.includes(id)} @change=${(e:Event)=>this.module(id,(e.target as HTMLInputElement).checked)}>${moduleLabels[id]}</label><button aria-label=${'Monter '+moduleLabels[id]} ?disabled=${!c.modules?.includes(id)||c.modules.indexOf(id)===0} @click=${()=>this.move(id)}>${icon('up')}</button></div>`)}
      <h3>Affichage et performance</h3><label>Thème<select .value=${c.theme??'auto'} @change=${(e:Event)=>this.change({theme:(e.target as HTMLSelectElement).value as Config['theme']})}><option value="auto">Suivre Home Assistant</option><option value="light">Clair</option><option value="dark">Sombre</option></select></label>
      <label class="check"><input type="checkbox" .checked=${c.animations!==false} @change=${(e:Event)=>this.change({animations:(e.target as HTMLInputElement).checked})}>Animations</label>
      <label class="check"><input type="checkbox" .checked=${c.glass_effect!==false} @change=${(e:Event)=>this.change({glass_effect:(e.target as HTMLInputElement).checked})}>Effet de verre</label><p>Désactiver ces effets allège l’affichage. La réduction des animations de votre appareil est toujours respectée.</p>
      <p>Les capteurs et préférences se règlent dans Niak Confort, accessible depuis la barre latérale de Home Assistant.</p>`;
  }
}
if(!customElements.get('niak-comfort-card-editor'))customElements.define('niak-comfort-card-editor',ComfortEditor);
