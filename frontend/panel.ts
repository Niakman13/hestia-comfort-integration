import {LitElement,html,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {customElement,property,state} from 'lit/decorators.js';
import {live} from 'lit/directives/live.js';
import styles from './styles.css';
import {labels,indoor,outdoor,multiple,exposures,kinds,measurement,newRoom,coverage,exteriorSummary,livingArea,defaultOpening,warningText,warningId,type Area,type Candidate,type Discovery,type Snapshot,type Hass,type Room,type RoomConfig,type Spec} from './model';
const stages=['Mesures','Ouvrants','Air','Chauffage','Préférences','Récapitulatif'];
const help:Record<string,string>={indoor_temperature:'La mesure de l’air de cette pièce. Seule information obligatoire. La température d’un appareil ou du sol d’une plante peut être différente.',indoor_humidity:'Permet de repérer un air trop humide et de savoir si aérer l’assèche vraiment.',co2:'Permet de savoir quand renouveler l’air. Ce capteur ne mesure pas tous les polluants.',windows:'Les contacts des fenêtres et portes qui donnent sur l’extérieur. Pas les portes de meubles ou d’appareils.',heating:'Permet de savoir si le chauffage tourne vraiment, pour ne pas conseiller d’ouvrir à ce moment-là. Niak ne commande rien.',outdoor_temperature:'Permet de savoir si ouvrir rafraîchit ou réchauffe, et s’il gèle.',outdoor_humidity:'Avec les températures, permet de comparer l’eau contenue dans l’air dedans et dehors.',rain:'Une intensité en mm/h dit s’il pleut maintenant. Un cumul de la journée ne le dit pas.',wind_gust:'Au-delà de vos réglages (45 km/h par défaut), Niak conseille de ne rien laisser ouvert.',solar:'Un capteur d’ensoleillement en W/m² permet de calculer le soleil reçu par chaque façade.',pollution:'L’indice ATMO du jour (intégration Atmo France) sert de précaution régionale. Ce n’est pas une mesure à vos fenêtres.'};
let pickerLoad:Promise<string|null>|undefined;
// Home Assistant loads its entity picker lazily; a card editor makes it available to this page.
function loadPicker():Promise<string|null>{
 pickerLoad??=(async()=>{
  const tag=()=>customElements.get('ha-selector')?'ha-selector':customElements.get('ha-entity-picker')?'ha-entity-picker':null;
  if(tag())return tag();
  try{const helpers=await (window as unknown as {loadCardHelpers?:()=>Promise<{createCardElement:(c:object)=>Promise<HTMLElement>}>}).loadCardHelpers?.();
   if(helpers)for(const config of [{type:'tile',entity:'sun.sun'},{type:'entities',entities:['sun.sun']}]){const card=await helpers.createCardElement(config);await (card.constructor as unknown as {getConfigElement?:()=>Promise<unknown>}).getConfigElement?.();if(tag())break;}}
  catch{/* the simple search list remains available */}
  for(let i=0;i<30&&!tag();i++)await new Promise(r=>setTimeout(r,100));
  return tag();
 })();
 return pickerLoad;
}
@customElement('niak-comfort-setup')
export class ComfortSetup extends LitElement {
 static styles=unsafeCSS(styles);
 @property({attribute:false}) hass?:Hass;
 @property({attribute:false}) route?:{path:string};
 @property({type:Boolean}) narrow=false;
 @state() private snapshot?:Snapshot;
 @state() private discovery?:Discovery;
 @state() private draft?:RoomConfig;
 @state() private exteriorDraft?:Record<string,Spec>;
 @state() private entryId?:string;
 @state() private stage=0;
 @state() private busy=false;
 @state() private error='';
 @state() private saved='';
 @state() private search:Record<string,string>={};
 @state() private acknowledged:string[]=[];
 @state() private confirmed=false;
 @state() private overview?:{area_id:string;name:string;suggestions:Record<string,string|string[]>;temperatures:number}[];
 @state() private picked:string[]=[];
 @state() private proposed:string[]=[];
 @state() private advanced=false;
 @state() private confirmDiscard=false;
 @state() private freeName='';
 @state() private preview?:string;
 @state() private previewEdited=false;
 @state() private pickerTag:string|null=null;
 private generation=0;
 private connection?:unknown;
 private routeHandled='';
 private revision='';
 private previewCard?:{id:string;el:HTMLElement&{hass?:unknown;setConfig?:(c:object)=>void}};
 private beforeUnload=(e:BeforeUnloadEvent)=>{if(this.draft||this.exteriorDraft){e.preventDefault();e.returnValue='';}};
 connectedCallback(){super.connectedCallback();window.addEventListener('beforeunload',this.beforeUnload);void loadPicker().then(tag=>this.pickerTag=tag);}
 disconnectedCallback(){super.disconnectedCallback();this.generation++;window.removeEventListener('beforeunload',this.beforeUnload);}
 protected updated(changed:PropertyValues){
  this.setAttribute('data-theme',this.hass?.themes?.darkMode===false?'light':'dark');
  if(changed.has('hass')&&this.hass?.connection!==this.connection){this.connection=this.hass?.connection;void this.load();}
  if(changed.has('hass')&&this.previewCard)this.previewCard.el.hass=this.hass;
  if(changed.has('route')&&this.snapshot&&!this.draft&&!this.exteriorDraft)void this.followRoute();
  // An error appears next to what the person was doing, never only at the top of a long page.
  if(changed.has('error')&&this.error)this.renderRoot.querySelector('.error')?.scrollIntoView({block:'center',behavior:'smooth'});
 }
 private async load(){
  if(!this.hass)return;const generation=++this.generation;this.busy=true;this.error='';
  try{const value=await this.hass.callWS<Snapshot>({type:'niak_comfort/configuration'});if(generation===this.generation){this.snapshot=value;await this.followRoute();if(!value.rooms.length)await this.loadOverview();}}
  catch(e){if(generation===this.generation)this.error=this.message(e);}
  finally{if(generation===this.generation)this.busy=false;}
 }
 private message(e:unknown){return typeof e==='object'&&e&&'message' in e?String(e.message):'La connexion est indisponible. Réessayez sans quitter votre brouillon.';}
 private async followRoute(){const path=this.route?.path??'';if(this.routeHandled===path)return;this.routeHandled=path;const id=path.split('/').filter(Boolean)[0];const room=this.snapshot?.rooms.find(r=>r.entry_id===id);if(room)await this.editRoom(room);}
 private async loadOverview(){
  try{const o=await this.hass!.callWS<{areas:NonNullable<ComfortSetup['overview']>}>({type:'niak_comfort/overview'});const living=livingArea(o.areas.map(a=>({...a,outdoor:false})),new Set());this.overview=living?[...o.areas.filter(a=>a.area_id===living.area_id),...o.areas.filter(a=>a.area_id!==living.area_id)]:o.areas;this.picked=o.areas.filter(a=>typeof a.suggestions.indoor_temperature==='string').map(a=>a.area_id);}
  catch{this.overview=[];}
 }
 private detected(s:Record<string,string|string[]>){const parts=[s.indoor_temperature&&'température',s.indoor_humidity&&'humidité',s.co2&&'CO₂',s.heating&&'chauffage'].filter(Boolean) as string[];const n=Array.isArray(s.windows)?s.windows.length:0;if(n)parts.push(n+' ouvrant'+(n>1?'s':''));return parts.join(', ');}
 // Creates every checked room at once with Niak's unambiguous proposals; each room keeps its assistant.
 private async createAll(){
  const areas=(this.overview??[]).filter(a=>this.picked.includes(a.area_id));if(!areas.length){this.error='Cochez au moins une pièce.';return;}
  this.busy=true;this.error='';let created=0;
  try{for(const a of areas){const snapshot:Snapshot=await this.hass!.callWS<Snapshot>({type:'niak_comfort/save_config',config:newRoom({area_id:a.area_id,name:a.name},'',{version:1,revision:'',candidates:{},suggestions:a.suggestions}),revision:this.snapshot!.revision,acknowledged:[]});this.snapshot=snapshot;created++;}
   this.saved=`${created} pièce${created>1?'s':''} créée${created>1?'s':''}. Ouvrez chacune pour renseigner l’exposition des ouvrants et compléter si besoin.`;this.overview=undefined;}
  catch(e){this.error=(created?`${created} pièce${created>1?'s':''} créée${created>1?'s':''}, puis : `:'')+this.message(e);}
  finally{this.busy=false;}
 }
 private menu(){this.dispatchEvent(new CustomEvent('hass-toggle-menu',{bubbles:true,composed:true}));}
 private areaName(id:string|null){return id?this.snapshot?.areas.find(a=>a.area_id===id)?.name??id:'';}
 private async discover(area_id?:string|null,entry_id?:string){
  return await this.hass!.callWS<Discovery>({type:'niak_comfort/discover',...(area_id?{area_id}:{}),...(entry_id?{entry_id}:{})});
 }
 private begin(){this.busy=true;this.error='';this.saved='';this.preview=undefined;this.search={};this.confirmed=false;}
 private async start(area:{area_id:string;name:string}|null,name=''){
  if(!area&&!name.trim()){this.error='Donnez un nom à la pièce libre, par exemple « Étage » ou « Suite parentale ».';return;}
  this.begin();
  try{const d=await this.discover(area?.area_id);this.discovery=d;this.revision=d.revision;this.entryId=undefined;this.draft=newRoom(area,name.trim(),d);this.proposed=[...Object.values(this.draft.sources),...this.draft.windows];this.stage=0;this.acknowledged=[];this.freeName='';}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async editRoom(room:Room){
  this.begin();
  try{const d=await this.discover(room.config.area_id,room.entry_id);this.discovery=d;this.revision=d.revision;this.entryId=room.entry_id;
   const config=structuredClone(room.config);config.area_id??=null;config.openings??={};for(const id of config.windows)config.openings[id]??={...defaultOpening(),sheltered:config.rain_exposed===false};
   this.draft=config;this.proposed=[];this.stage=0;this.acknowledged=[...(config.acknowledged??[])];}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async editExterior(){
  this.begin();
  try{const d=await this.discover();this.discovery=d;this.revision=d.revision;this.exteriorDraft=structuredClone(this.snapshot!.home.sources);this.acknowledged=[...(this.snapshot!.home.acknowledged??[])];this.proposed=[];}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async changeArea(area_id:string){
  if(!this.draft)return;this.busy=true;this.error='';
  try{const d=await this.discover(area_id||null,this.entryId);this.discovery=d;this.revision=d.revision;this.draft={...this.draft,area_id:area_id||null};}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async refreshCandidates(){
  this.busy=true;this.error='';
  try{const d=await this.discover(this.draft?.area_id,this.entryId);if(d.revision!==this.revision){this.error='La configuration a changé ailleurs. Votre brouillon est conservé ; revenez à Mon logement et rechargez avant d’enregistrer.';return;}this.discovery=d;this.saved='La liste des capteurs a été actualisée. Vos choix restent inchangés.';}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private cancel(){if(this.draft||this.exteriorDraft){this.confirmDiscard=true;return;}this.discard();}
 private discard(){this.confirmDiscard=false;this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;this.error='';this.acknowledged=[];this.proposed=[];}
 private selected(key:string):string[]{if(this.exteriorDraft)return this.exteriorDraft[key]?[this.exteriorDraft[key].entity_id]:[];if(!this.draft)return [];return key==='windows'?this.draft.windows:this.draft.sources[key]?[this.draft.sources[key]]:[];}
 private choose(key:string,c:Candidate){
  const previous=this.selected(key);
  if(this.exteriorDraft){this.exteriorDraft={...this.exteriorDraft,[key]:{entity_id:c.entity_id,adapter:c.adapter,...(c.adapter==='atmo_daily'?{block_from:4}:{})}};}
  else if(this.draft){if(key==='windows'){this.draft={...this.draft,windows:[...new Set([...this.draft.windows,c.entity_id])],openings:{...this.draft.openings,[c.entity_id]:this.draft.openings[c.entity_id]??defaultOpening()}};}else this.draft={...this.draft,sources:{...this.draft.sources,[key]:c.entity_id}};}
  if(!multiple.has(key))this.acknowledged=this.acknowledged.filter(id=>!previous.some(p=>id===warningId(key,p)));
  this.proposed=this.proposed.filter(id=>id!==c.entity_id);this.search={...this.search,[key]:''};this.error='';
 }
 private pick(key:string,id:unknown){if(typeof id!=='string'||!id)return;const c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(c)this.choose(key,c);}
 private clear(key:string,id?:string){
  if(this.exteriorDraft){const next={...this.exteriorDraft};delete next[key];this.exteriorDraft=next;}
  else if(this.draft){if(key==='windows'){const openings={...this.draft.openings};delete openings[id!];this.draft={...this.draft,windows:this.draft.windows.filter(e=>e!==id),openings};}else{const next={...this.draft.sources};delete next[key];this.draft={...this.draft,sources:next};}}
  this.acknowledged=this.acknowledged.filter(v=>v!==warningId(key,id??this.selected(key)[0]??''));
 }
 private ack(id:string,on:boolean){this.acknowledged=on?[...new Set([...this.acknowledged,id])]:this.acknowledged.filter(v=>v!==id);}
 private setOpening(id:string,change:Partial<RoomConfig['openings'][string]>){const d=this.draft!;this.draft={...d,openings:{...d.openings,[id]:{...(d.openings[id]??defaultOpening()),...change}}};}
 private warnings(c:Candidate,_key?:string,_selected?:boolean){return html`${c.warnings.filter(w=>!(w==='derived'&&c.warnings.includes('alias'))).map(w=>html`<p class="warning hint">${warningText[w]??'Source à vérifier.'}</p>`)}${c.provenance.length>1?html`<p class="provenance">Origine de la mesure : ${c.provenance.map((p,i)=>html`${i?' → ':nothing}${p.name}${p.area_id?` (${this.areaName(p.area_id)})`:nothing}`)}</p>`:nothing}`;}
 // Sensors chosen with a warning that the person has not confirmed yet: one confirmation covers them all.
 private pending(){const keys=this.exteriorDraft?[...outdoor]:[...indoor,'co2','heating','windows'];const out:{id:string;name:string}[]=[];
  for(const key of keys)for(const id of this.selected(key)){const c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(c?.warnings.length&&!this.acknowledged.includes(warningId(key,id)))out.push({id:warningId(key,id),name:c.name});}
  return out;}
 private confirmBlock(){const list=this.pending();if(!list.length)return nothing;
  return html`<div class="notice confirm"><p>${list.length===1?'Un capteur est à vérifier':list.length+' capteurs sont à vérifier'} (autre pièce, porte d’appareil ou mesure recopiée) : ${list.map(x=>x.name).join(', ')}. Les explications sont aux étapes précédentes.</p><label class="check"><input type="checkbox" .checked=${this.confirmed} @change=${(e:Event)=>{this.confirmed=(e.target as HTMLInputElement).checked;if(this.confirmed)this.error='';}}>J’ai vérifié, je confirme mes choix.</label></div>`;}
 private where(c:Candidate){return c.area_id?this.areaName(c.area_id):'Sans pièce';}
 private candidateRow(c:Candidate,key:string){return html`<div class="candidate"><div><strong>${c.name}</strong><p>${measurement(c)} · ${this.where(c)}${c.reference?' · référence de la pièce':nothing}</p>${this.warnings(c,key,false)}</div><button @click=${()=>this.choose(key,c)}>Utiliser</button></div>`;}
 private replace(key:string,old:string,id:unknown){
  if(id===''||id===undefined||id===null){this.clear(key,old);return;}  // the picker's cross removes the sensor
  if(typeof id!=='string'||id===old)return;
  const c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(!c)return;
  if(key==='windows'&&this.draft){
   // The replacement keeps the exposure, type and shelter already described for this opening.
   const d=this.draft,openings={...d.openings,[id]:d.openings[old]??defaultOpening()};delete openings[old];
   this.draft={...d,windows:d.windows.map(w=>w===old?id:w),openings};
   this.acknowledged=this.acknowledged.filter(a=>a!==warningId(key,old));this.proposed=this.proposed.filter(p=>p!==old);
  }else this.choose(key,c);
 }
 private selector(key:string,ids:string[],value:string,label:string,changed:(id:unknown)=>void){
  if(this.pickerTag==='ha-selector')return html`<ha-selector .hass=${this.hass} .selector=${{entity:{include_entities:ids}}} .value=${live(value)} .required=${false} .label=${label} @value-changed=${(e:CustomEvent)=>changed(e.detail?.value)}></ha-selector>`;
  return html`<ha-entity-picker .hass=${this.hass} .includeEntities=${ids} .value=${live(value)} .required=${false} .label=${label} @value-changed=${(e:CustomEvent)=>changed(e.detail?.value)}></ha-entity-picker>`;
 }
 private picker(key:string,all:Candidate[],selected:string[]){
  const free=all.filter(c=>!selected.includes(c.entity_id));
  if(!free.length)return html`<p class="hint">Aucun autre capteur compatible dans Home Assistant.</p>`;
  const label=multiple.has(key)&&selected.length?'Ajouter un autre ouvrant':'Choisir un autre capteur';
  if(this.pickerTag)return html`<div class="picker">${this.selector(key,free.map(c=>c.entity_id),'',label,id=>this.pick(key,id))}</div>`;
  const text=(this.search[key]??'').toLowerCase();
  return html`<div class="picker"><label>${label}<input type="search" placeholder="Tapez un nom, une pièce…" .value=${this.search[key]??''} @input=${(e:Event)=>this.search={...this.search,[key]:(e.target as HTMLInputElement).value}}></label>${text?html`<div class="search-results">${free.filter(c=>(c.name+' '+c.entity_id+' '+this.where(c)).toLowerCase().includes(text)).slice(0,8).map(c=>this.candidateRow(c,key))}</div>`:nothing}</div>`;
 }
 private chosen(key:string,id:string,all:Candidate[],selected:string[]){
  const c=all.find(x=>x.entity_id===id);
  // Each chosen sensor is itself a picker: choosing another one replaces it in place.
  const ids=[id,...all.filter(x=>!selected.includes(x.entity_id)).map(x=>x.entity_id)];
  return html`<div class="choice">${this.pickerTag?html`<div class="chosen">${this.selector(key,ids,id,labels[key]===labels.windows?'Ouvrant':labels[key],v=>this.replace(key,id,v))}</div>`:html`<strong>${c?.name??id}</strong>`}
   <span>${c?measurement(c)+' · '+this.where(c):'Capteur introuvable ou incompatible · choisissez-en un autre'}</span>${this.proposed.includes(id)?html`<span>Proposé par Niak · gardez-le, changez-le ou retirez-le</span>`:nothing}${c?.reference?html`<span>Référence de cette pièce dans Home Assistant</span>`:nothing}${c?this.warnings(c,key,true):nothing}${key==='windows'?this.openingDetails(id):nothing}<button class="link" @click=${()=>this.clear(key,id)}>Retirer</button></div>`;
 }
 private openingDetails(id:string){const m=this.draft!.openings[id]??defaultOpening();return html`<div class="opening">
  <label>Exposition<select @change=${(e:Event)=>this.setOpening(id,{exposure:(e.target as HTMLSelectElement).value||null})}><option value="" ?selected=${!m.exposure}>Je ne sais pas</option>${exposures.map(([v,l])=>html`<option value=${v} ?selected=${m.exposure===v}>${l}</option>`)}</select></label>
  <label>Type<select @change=${(e:Event)=>this.setOpening(id,{kind:(e.target as HTMLSelectElement).value})}>${kinds.map(([v,l])=>html`<option value=${v} ?selected=${m.kind===v}>${l}</option>`)}</select></label>
  <label class="check"><input type="checkbox" .checked=${m.sheltered} @change=${(e:Event)=>this.setOpening(id,{sheltered:(e.target as HTMLInputElement).checked})}>Abrité par une avancée de toit ou un balcon</label></div>`;}
 private field(key:string){
  const all=this.discovery?.candidates[key]??[],selected=this.selected(key),room=this.draft;
  const proposals=(this.exteriorDraft?all.filter(c=>c.outside):all.filter(c=>c.local)).filter(c=>!selected.includes(c.entity_id));
  const canAdd=multiple.has(key)||!selected.length;
  const where=this.exteriorDraft?'dans vos pièces extérieures':room?.area_id?'dans la pièce '+this.areaName(room.area_id):'';
  return html`<section class="field" aria-label=${labels[key]}><div class="field-top"><h3>${labels[key]}</h3><span>${key==='indoor_temperature'?'Obligatoire':'Facultatif'}</span></div><p class="hint">${help[key]}</p>
   ${key==='windows'&&selected.length?html`<p class="hint">L’exposition est le côté vers lequel regarde l’ouvrant. Elle permet de savoir quand le soleil y entre.</p>`:nothing}
   ${selected.map(id=>this.chosen(key,id,all,selected))}
   ${canAdd&&proposals.length?html`<p class="hint strong">${proposals.length===1?'Trouvé '+where:'Trouvés '+where+' : choisissez '+(multiple.has(key)?'ceux qui conviennent':'celui qui convient')}</p><div class="candidates">${proposals.slice(0,5).map(c=>this.candidateRow(c,key))}</div>`:nothing}
   ${canAdd&&!proposals.length&&!selected.length?html`<p class="notice">${where?'Rien trouvé '+where+'.':'Pièce libre : choisissez le capteur ci-dessous.'}${where?' Vous pouvez en choisir un ailleurs ci-dessous.':''}</p>`:nothing}
   ${canAdd?this.picker(key,all,selected):nothing}
   ${key!=='indoor_temperature'&&!selected.length?html`<button class="link" @click=${()=>{this.clear(key);this.saved=labels[key]+' : laissé vide pour l’instant.';}}>Continuer sans</button>`:nothing}
   ${this.exteriorDraft?.[key]?.adapter==='atmo_daily'?html`<label>Prudence à partir du niveau<select @change=${(e:Event)=>{this.exteriorDraft={...this.exteriorDraft!,[key]:{...this.exteriorDraft![key],block_from:Number((e.target as HTMLSelectElement).value)}};}}>${['Moyen','Dégradé','Mauvais','Très mauvais','Extrêmement mauvais'].map((label,i)=>html`<option value=${i+2} ?selected=${(this.exteriorDraft![key].block_from??4)===i+2}>${label}</option>`)}</select></label><p class="hint">C’est votre préférence de prudence, pas une consigne sanitaire.</p>`:nothing}
  </section>`;
 }
 private go(stage:number){this.stage=stage;this.error='';this.saved='';this.updateComplete.then(()=>this.renderRoot.querySelector<HTMLElement>('h1')?.focus());}
 private next(){
  if(this.stage===0&&!this.draft?.sources.indoor_temperature){this.error='Choisissez la température de la pièce pour continuer. C’est la seule mesure obligatoire.';return;}
  if(this.stage===4){const s=this.draft!.settings;if(!this.draft!.name.trim()){this.error='Donnez un nom à la pièce.';return;}if(!Number.isFinite(s.minimum)||!Number.isFinite(s.maximum)||s.minimum>=s.maximum){this.error='La température minimum doit être inférieure au maximum.';return;}}
  this.go(this.stage+1);
 }
 private async save(){
  const config=this.exteriorDraft?{sources:this.exteriorDraft}:this.draft;if(!config)return;
  this.busy=true;this.error='';
  try{const validated=await this.hass!.callWS<{warnings:{key:string;entity_id:string}[]}>({type:'niak_comfort/validate_config',config,home:!!this.exteriorDraft});const missing=validated.warnings.map(w=>warningId(w.key,w.entity_id)).filter(id=>!this.acknowledged.includes(id));
   if(missing.length&&!this.confirmed){this.error='Cochez « J’ai vérifié, je confirme mes choix » juste au-dessus pour enregistrer.';return;}
   this.acknowledged=[...new Set([...this.acknowledged,...missing])];
   const before=new Set(this.snapshot?.rooms.map(r=>r.entry_id));const wasRoom=!this.exteriorDraft;const edited=this.entryId;
   this.snapshot=await this.hass!.callWS<Snapshot>({type:'niak_comfort/save_config',config,home:!!this.exteriorDraft,revision:this.revision,...(this.entryId?{entry_id:this.entryId}:{}),acknowledged:this.acknowledged});
   this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;
   if(wasRoom){this.preview=edited??this.snapshot.rooms.find(r=>!before.has(r.entry_id))?.entry_id;this.previewEdited=!!edited;}
   this.saved=wasRoom?'':'L’extérieur est enregistré. Toutes vos pièces l’utilisent.';}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private number(key:string,label:string,initial:number,step=1){const d=this.draft!;return html`<label>${label}<input type="number" step=${step} .value=${String(d.settings[key]??initial)} @input=${(e:Event)=>this.draft={...d,settings:{...d.settings,[key]:Number((e.target as HTMLInputElement).value)}}}></label>`;}
 private preferences(){const d=this.draft!,used=new Set(this.snapshot!.rooms.filter(r=>r.entry_id!==this.entryId).map(r=>r.config.area_id));
  return html`<section class="field"><h2>La pièce</h2><label>Nom<input type="text" maxlength="100" .value=${d.name} @input=${(e:Event)=>this.draft={...d,name:(e.target as HTMLInputElement).value}}></label>
   <label>Pièce Home Assistant<select @change=${(e:Event)=>this.changeArea((e.target as HTMLSelectElement).value)}><option value="" ?selected=${!d.area_id}>Aucune (pièce libre)</option>${this.snapshot!.areas.filter(a=>!a.outdoor&&(!used.has(a.area_id)||a.area_id===d.area_id)).map(a=>html`<option value=${a.area_id} ?selected=${a.area_id===d.area_id}>${a.name}</option>`)}</select></label>
   <p class="hint">Rattacher la pièce permet à Niak de proposer ses capteurs. Vous pouvez toujours en choisir ailleurs.</p></section>
   <section class="field"><h2>Votre plage de confort</h2><p>Les températures dans lesquelles vous vous sentez bien.</p>${this.number('minimum','Température minimum (°C)',20,0.5)}${this.number('maximum','Température maximum (°C)',24,0.5)}
   <button class="link" aria-expanded=${this.advanced} @click=${()=>this.advanced=!this.advanced}>${this.advanced?'Masquer':'Afficher'} les réglages avancés</button>
   ${this.advanced?html`<p class="hint">Ces seuils reprennent votre ancien template. Ce ne sont pas des références sanitaires.</p>${this.number('humidity_high','Humidité haute (%)',62)}${this.number('co2_potential','CO₂ : aérer ferait du bien (ppm)',1000)}${this.number('co2_action','CO₂ : aérer (ppm)',1200)}${this.number('co2_urgent','CO₂ : attention (ppm)',1600)}${this.number('gust_max','Rafales : ne rien laisser ouvert au-delà de (km/h)',45)}${this.number('frost','Gel : pas d’ouverture prolongée en dessous de (°C)',1,0.5)}${this.number('sun_facade','Soleil fort sur une façade (W/m²)',250,10)}${this.number('max_age_seconds','Ancienneté maximum des mesures (secondes)',1800)}`:nothing}</section>`;}
 private summary(){const d=this.draft!,home=this.snapshot!.home;const name=(key:string,id?:string)=>id?this.discovery?.candidates[key]?.find(v=>v.entity_id===id)?.name??id:'';
  const metas=d.windows.map(id=>d.openings[id]??defaultOpening());const counts=new Map<string,number>();for(const m of metas)if(m.exposure)counts.set(m.exposure,(counts.get(m.exposure)??0)+1);
  const expo=[...counts].map(([e,n])=>n+' '+exposures.find(x=>x[0]===e)![1].toLowerCase()).join(', ');const unknown=metas.filter(m=>!m.exposure).length,sheltered=metas.filter(m=>m.sheltered).length;
  const measures=[name('indoor_temperature',d.sources.indoor_temperature),name('indoor_humidity',d.sources.indoor_humidity)].filter(Boolean).join(' · ');
  return html`<dl class="summary compact"><dt>Pièce</dt><dd>${d.name} · ${d.area_id?'rattachée à « '+this.areaName(d.area_id)+' »':'pièce libre'}</dd>
   <dt>Mesures</dt><dd>${measures||'—'}</dd><dt>Air</dt><dd>${name('co2',d.sources.co2)||'Pas de CO₂'}</dd><dt>Chauffage</dt><dd>${name('heating',d.sources.heating)||'Non suivi'}</dd>
   <dt>Ouvrants</dt><dd>${d.windows.length?html`${d.windows.length} ${d.windows.length>1?'ouvrants':'ouvrant'}${sheltered?' · '+sheltered+' abrité'+(sheltered>1?'s':''):''}${expo?' · '+expo:''}${unknown?' · '+unknown+' sans exposition':''}<details><summary>Voir la liste</summary>${d.windows.map(id=>html`<div>${name('windows',id)}</div>`)}</details>`:'Aucun'}</dd>
   <dt>Extérieur</dt><dd>${home.configured?exteriorSummary(home.sources):'À configurer depuis Mon logement'}</dd><dt>Confort</dt><dd>${d.settings.minimum}–${d.settings.maximum} °C</dd></dl>
   ${this.confirmBlock()}`;}
 private errorBlock(){return this.error?html`<p class="notice error" role="alert">${this.error}</p>`:nothing;}
 private wizard(){const d=this.draft!;return html`<div class="actions"><button class="link" @click=${()=>this.cancel()}>← Mon logement</button></div><h1 tabindex="-1">${this.entryId?'Modifier':'Configurer'} ${d.name||'la pièce'}</h1><p class="step-count">${d.area_id?'Pièce Home Assistant : '+this.areaName(d.area_id):'Pièce libre'} · étape ${this.stage+1} sur ${stages.length}</p>
  <nav class="steps" aria-label="Étapes">${stages.map((label,i)=>html`<button aria-current=${i===this.stage?'step':'false'} @click=${()=>this.go(i)}>${label}</button>`)}</nav>
  ${this.stage===0?indoor.map(key=>this.field(key)):this.stage===1?this.field('windows'):this.stage===2?this.field('co2'):this.stage===3?this.field('heating'):this.stage===4?this.preferences():this.summary()}
  ${this.stage<4?html`<button class="link" @click=${()=>this.refreshCandidates()}>Rechercher à nouveau les capteurs</button>`:nothing}
  ${this.errorBlock()}
  <div class="bottom"><button @click=${()=>this.stage?this.go(this.stage-1):this.cancel()}>Retour</button><div>${this.stage>0&&this.stage<5?html`<button @click=${()=>this.go(this.stage+1)}>Passer</button>`:nothing}<button class="primary" ?disabled=${this.busy} @click=${()=>this.stage===5?this.save():this.next()}>${this.stage===5?'Enregistrer':'Continuer'}</button></div></div>`;}
 private exterior(){return html`<div class="actions"><button class="link" @click=${()=>this.cancel()}>← Mon logement</button></div><h1 tabindex="-1">L’extérieur du logement</h1><p>Choisissez une fois les mesures du dehors. Toutes vos pièces les utilisent.</p>
  ${outdoor.map(key=>this.field(key))}${this.confirmBlock()}${this.errorBlock()}<div class="bottom"><button @click=${()=>this.cancel()}>Annuler</button><button class="primary" ?disabled=${this.busy} @click=${()=>this.save()}>Enregistrer l’extérieur</button></div>`;}
 private card(id:string){
  if(!customElements.get('niak-comfort-card'))return html`<p class="notice">L’aperçu de la carte apparaîtra après un rechargement de la page.</p>`;
  if(this.previewCard?.id!==id){const el=document.createElement('niak-comfort-card') as HTMLElement&{hass?:unknown;setConfig?:(c:object)=>void};el.setConfig?.({type:'custom:niak-comfort-card',entry_id:id,format:'full'});el.hass=this.hass;this.previewCard={id,el};}
  return this.previewCard!.el;
 }
 private previewScreen(){const s=this.snapshot!,room=s.rooms.find(r=>r.entry_id===this.preview);if(!room)return this.home();
  return html`<h1 tabindex="-1">${this.previewEdited?room.title+' : modifications enregistrées':room.title+' est prêt'}</h1><p>Voici sa carte confort, telle qu’elle apparaîtra sur votre tableau de bord. Les conseils se mettent à jour en quelques secondes.</p><div class="preview">${this.card(room.entry_id)}</div>
   <h2>Ajouter la carte à un tableau de bord</h2><ol class="howto"><li>Ouvrez votre tableau de bord, puis le crayon <strong>Modifier</strong>.</li><li><strong>Ajouter une carte</strong>, puis cherchez <strong>Niak Confort</strong>. Pour toutes les pièces d’un coup : <strong>Niak Confort · logement</strong>.</li><li>Choisissez la pièce <strong>${room.title}</strong> et enregistrez.</li></ol>
   ${!s.home.configured?html`<p class="notice">Pour comparer avec le dehors (fraîcheur, pluie, vent, soleil), configurez maintenant l’extérieur du logement.</p>`:nothing}
   <div class="actions">${!s.home.configured?html`<button class="primary" @click=${()=>this.editExterior()}>Configurer l’extérieur</button>`:nothing}<button class=${s.home.configured?'primary':''} @click=${()=>{this.preview=undefined;}}>Retour à Mon logement</button></div>`;}
 private foundRooms(){const list=this.overview!;const n=this.picked.length;
  return html`<section class="start"><h2>Vos pièces trouvées</h2><p>Niak a cherché dans vos pièces Home Assistant. Décochez celles à ne pas suivre : vous pourrez tout retoucher ensuite, pièce par pièce.</p>
   <div class="found">${list.map(a=>{const ok=typeof a.suggestions.indoor_temperature==='string';return html`<div class="found-row"><label class="check"><input type="checkbox" ?disabled=${!ok} .checked=${this.picked.includes(a.area_id)} @change=${(e:Event)=>{const on=(e.target as HTMLInputElement).checked;this.picked=on?[...this.picked,a.area_id]:this.picked.filter(x=>x!==a.area_id);}}><span><strong>${a.name}</strong><span class="hint">${ok?this.detected(a.suggestions):a.temperatures>1?'Plusieurs températures : à choisir':'Aucune température trouvée'}</span></span></label>${ok?nothing:html`<button @click=${()=>this.start(a)}>Configurer</button>`}</div>`;})}</div>
   ${this.errorBlock()}<button class="primary" ?disabled=${this.busy||!n} @click=${()=>this.createAll()}>${n?`Créer ${n>1?'les '+n+' pièces':'la pièce'}`:'Cochez une pièce'}</button></section>`;}
 private home(){const s=this.snapshot!;const used=new Set(s.rooms.map(r=>r.config.area_id).filter((a):a is string=>!!a));const living=livingArea(s.areas,used);const areas=s.areas.filter(a=>!a.outdoor&&!used.has(a.area_id)&&(s.rooms.length||a!==living));
  return html`<h1>Mon logement</h1><p class="muted">Vos pièces et les mesures qui aident Niak à expliquer leur confort. Aucun équipement n’est commandé.</p>
  ${!s.rooms.length&&this.overview?.some(a=>typeof a.suggestions.indoor_temperature==='string')?this.foundRooms():!s.rooms.length?html`<section class="start"><h2>Commençons par le Salon</h2>${living?html`<p>Niak a trouvé la pièce « ${living.name} » dans Home Assistant. Il vous proposera ses capteurs ; vous gardez, retirez ou complétez.</p><button class="primary" @click=${()=>this.start(living)}>Configurer le Salon</button>`:html`<p>Aucune pièce « Salon » dans Home Assistant : Niak crée une pièce libre et vous choisissez ses capteurs.</p><button class="primary" @click=${()=>this.start(null,'Salon')}>Créer le Salon</button>`}</section>`:html`<h2>Vos pièces</h2>${s.rooms.map(room=>html`<section class="room"><div><h3>${room.title}</h3><p class="hint">${coverage(room.config)}${room.config.area_id?'':' · pièce libre'}</p>${!room.loaded?html`<p class="warning hint">Le calcul de cette pièce n’est pas chargé. Vérifiez ses capteurs et les journaux de l’intégration.</p>`:nothing}</div><button @click=${()=>this.editRoom(room)}>Modifier</button></section>`)}`}
  <section class="field"><h3>${s.rooms.length?'Ajouter une pièce':this.overview?'Une pièce sans pièce Home Assistant ?':'Ou commencer par une autre pièce'}</h3>${areas.length&&!(this.overview&&!s.rooms.length)?html`<p class="hint">Vos pièces Home Assistant : Niak proposera leurs capteurs.</p><div class="area-buttons">${areas.map(a=>html`<button @click=${()=>this.start(a)}>${a.name}</button>`)}</div>`:nothing}
   <form class="free" @submit=${(e:Event)=>{e.preventDefault();void this.start(null,this.freeName);}}><label>Pièce libre, sans pièce Home Assistant<input type="text" maxlength="100" placeholder="Par exemple : Étage" .value=${this.freeName} @input=${(e:Event)=>this.freeName=(e.target as HTMLInputElement).value}></label><button type="submit">Créer</button></form></section>
  ${s.rooms.length?html`<section class="field"><h2>Les cartes</h2><p>Dans un tableau de bord : <strong>Ajouter une carte</strong>, puis <strong>Niak Confort</strong> pour une pièce, ou <strong>Niak Confort · logement</strong> pour la synthèse de toutes les pièces.</p></section>`:nothing}<section class="field"><h2>L’extérieur du logement</h2><p>Température, humidité, pluie, vent, soleil et qualité de l’air dehors : vous les choisissez une fois, toutes vos pièces les utilisent.</p><p class="hint">${s.home.configured?exteriorSummary(s.home.sources):'Pas encore configuré'}</p><button @click=${()=>this.editExterior()}>${s.home.configured?'Modifier l’extérieur':'Configurer l’extérieur'}</button></section>`;}
 protected render(){if(this.hass?.user?.is_admin===false)return html`<main><h1>Niak Confort</h1><p>La configuration du logement est réservée aux administrateurs Home Assistant.</p></main>`;
  const editing=!!(this.draft||this.exteriorDraft);
  return html`<header><button aria-label="Ouvrir le menu Home Assistant" @click=${()=>this.menu()}><span class="menu-icon"></span></button><strong>Niak Confort</strong></header><main>${this.confirmDiscard?html`<section class="notice" role="alertdialog" aria-label="Abandonner le brouillon"><h2>Quitter sans enregistrer ?</h2><p>Vos choix de cette page seront perdus.</p><div class="actions"><button @click=${()=>this.confirmDiscard=false}>Continuer la configuration</button><button @click=${()=>this.discard()}>Quitter sans enregistrer</button></div></section>`:nothing}
   ${!editing?html`${this.errorBlock()}${this.error&&!this.snapshot?html`<button @click=${()=>this.load()}>Réessayer</button>`:nothing}`:nothing}${this.saved?html`<p class="notice success" role="status">${this.saved}</p>`:nothing}${this.busy&&!this.snapshot?html`<p class="loading" role="status">Chargement de votre logement…</p>`:nothing}
   ${this.snapshot?(this.exteriorDraft?this.exterior():this.draft?this.wizard():this.preview?this.previewScreen():this.home()):nothing}${this.busy&&this.snapshot?html`<p class="busy" role="status">Un instant…</p>`:nothing}</main>`;
 }
}
