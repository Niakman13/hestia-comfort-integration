import {LitElement,html,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {customElement,property,state} from 'lit/decorators.js';
import {live} from 'lit/directives/live.js';
import styles from './styles.css';
import {frame,hubStyles,modernStyles,hubIcon,helpTip,defaultValue} from './socle/ui';
import {labels,indoor,outdoor,multiple,exposures,kinds,measurement,newRoom,coverage,exteriorSummary,livingArea,defaultOpening,warningText,warningId,stages,intros,outdoorGroups,changedAdvanced,advancedDefaults,airSource,airChoices,exteriorChoices,airReferenceDefaults,vocPreset,thresholdSources,type Choice,type Area,type Candidate,type Discovery,type Health,type HealthLine,type Target,type Snapshot,type Hass,type Room,type RoomConfig,type Spec,type Twins,type Twin} from './model';
const roomSections=[{stage:0,path:'temperature',label:'Température',title:'Température et humidité',icon:'temperature'},{stage:1,path:'ouvertures',label:'Ouvertures',title:'Fenêtres et portes',icon:'openings'},{stage:2,path:'air',label:'Air intérieur',title:'Qualité de l’air',icon:'air'},{stage:6,path:'presence',label:'Présence',title:'Présence',icon:'presence'},{stage:3,path:'chauffage',label:'Chauffage',title:'Chauffage',icon:'heating'},{stage:4,path:'piece',label:'La pièce',title:'La pièce et ses réglages',icon:'room'}];
const roomOrder=[0,1,2,6,3,4,5];
const help:Record<string,string>={indoor_temperature:'La mesure de l’air de cette pièce. Seule information obligatoire. La température d’un appareil ou du sol d’une plante peut être différente.',indoor_humidity:'Permet de repérer un air trop humide et de savoir si aérer l’assèche vraiment.',illuminance:'La lumière mesurée en lux aide à interpréter le soleil. Elle ne mesure pas la position d’un volet.',pm25:'Mesure les particules fines. Le seuil d’action est votre réglage de confort.',voc:'Les repères ci-dessous dépendent du capteur et de son unité ; un indice n’est pas une concentration.',purifier:'Observe son fonctionnement sans le commander. Un purificateur filtre les particules ; il ne retire pas le CO₂.',ventilation:'Une VMC ou une ventilation renouvelle l’air et aide à assécher. Niak observe si elle tourne, sans la commander ni présumer son débit.',ventilation_boost:'Seulement si votre VMC a deux vitesses : choisissez ici sa position rapide (Turbo). La VMC compte comme en marche si l’une des deux tourne.',presence:'Plusieurs capteurs peuvent suivre la pièce. L’absence adapte les conseils sans couper le suivi ni les alertes.',co2:'Permet de savoir quand renouveler l’air. Ce capteur ne mesure pas tous les polluants.',windows:'Les contacts des fenêtres et portes qui donnent sur l’extérieur. Pas les portes de meubles ou d’appareils.',heating:'Permet de savoir si le chauffage tourne vraiment, pour ne pas conseiller d’ouvrir à ce moment-là. Niak ne commande rien.',outdoor_temperature:'Permet de savoir si ouvrir rafraîchit ou réchauffe, et s’il gèle.',outdoor_humidity:'Avec les températures, permet de comparer l’eau contenue dans l’air dedans et dehors.',rain:'Une intensité en mm/h dit s’il pleut maintenant. Un cumul de la journée ne le dit pas.',wind_gust:'Au-delà de vos réglages (45 km/h par défaut), Niak conseille de ne rien laisser ouvert.',wind_bearing:'D’où vient le vent, en degrés. Avec l’exposition des ouvrants, Niak sait lesquels sont au vent, fait traverser l’air et repère la pluie poussée sous un avant-toit.',solar:'Un capteur d’ensoleillement en W/m² permet de calculer le soleil reçu par chaque façade.',pollution:'L’indice ATMO du jour (intégration Atmo France) sert de précaution régionale. Ce n’est pas une mesure à vos fenêtres.'};
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
 static styles=[unsafeCSS(styles),hubStyles,modernStyles];
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
 @state() private health?:Health;
 @state() private healthLoading=true;
 @state() private twins?:Twins;
 @state() private healthError='';
 private healthGeneration=0;
 // The tab opens on the home's technical state; « Modifier » leads to the rooms.
 @state() private page:'health'|'rooms'='rooms';
 @state() private overview?:{area_id:string;name:string;suggestions:Record<string,string|string[]>;temperatures:number}[];
 @state() private picked:string[]=[];
 @state() private weatherEntry:string|null=null;
 @state() private proposed:string[]=[];
 @state() private confirmDiscard=false;
 @state() private confirmRemove=false;
 @state() private freeName='';
 @state() private preview?:string;
 @state() private previewEdited=false;
 @state() private pickerTag:string|null=null;
 private generation=0;
 private connection?:unknown;
 private routeHandled:string|undefined;
 private workspaceGeneration=0;
 private workspaceKey='';
 private drafts=new Map<string,{draft?:RoomConfig;exteriorDraft?:Record<string,Spec>;discovery?:Discovery;entryId?:string;stage:number;revision:string;acknowledged:string[];proposed:string[];search:Record<string,string>;weatherEntry:string|null}>();
 private revision='';
 private previewCard?:{id:string;el:HTMLElement&{hass?:unknown;setConfig?:(c:object)=>void}};
 private beforeUnload=(e:BeforeUnloadEvent)=>{if(this.draft||this.exteriorDraft||this.drafts.size){e.preventDefault();e.returnValue='';}};
 connectedCallback(){super.connectedCallback();if(this.hass&&!this.snapshot){this.connection=this.hass.connection;void this.load();}else if(this.healthLoading&&this.snapshot)void this.loadHealth();window.addEventListener('beforeunload',this.beforeUnload);void loadPicker().then(tag=>this.pickerTag=tag);}
 disconnectedCallback(){super.disconnectedCallback();this.workspaceGeneration++;if(this.busy)this.routeHandled=undefined;this.generation++;this.healthGeneration++;window.removeEventListener('beforeunload',this.beforeUnload);}
 protected updated(changed:PropertyValues){
  this.setAttribute('data-theme',this.hass?.themes?.darkMode===false?'light':'dark');
  if(changed.has('hass')&&this.hass&&(this.hass.connection!==this.connection||!this.snapshot&&!this.busy&&!this.error)){this.connection=this.hass?.connection;void this.load();}
  if(changed.has('hass')&&this.previewCard)this.previewCard.el.hass=this.hass;
  if(changed.has('route')&&this.snapshot)void this.followRoute();
  // Fresh state after every change of the home (a room saved, the exterior changed…).
  if(changed.has('snapshot')&&this.snapshot)void this.loadHealth();
  // An error appears next to what the person was doing, never only at the top of a long page.
  if(changed.has('error')&&this.error)this.renderRoot.querySelector('.error')?.scrollIntoView({block:'center',behavior:'smooth'});
 }
 private async load(){
  if(!this.hass)return;const generation=++this.generation;this.busy=true;this.error='';
  try{const value=await this.hass.callWS<Snapshot>({type:'niak_comfort/configuration'});if(generation===this.generation){this.snapshot=value;await this.followRoute();if(!value.rooms.length)await this.loadOverview();}}
  catch(e){if(generation===this.generation)this.error=this.message(e);}
  finally{if(generation===this.generation)this.busy=false;}
 }
 private async loadHealth(){
  const generation=++this.healthGeneration;this.healthLoading=true;this.healthError='';
  // What the twins learned is a bonus: the health page never waits for it nor fails with it.
  void this.hass!.callWS<Twins>({type:'niak_comfort/twins'}).then(t=>{if(generation===this.healthGeneration)this.twins=t;},()=>{});
  try{const value=await this.hass!.callWS<Health>({type:'niak_comfort/health'});if(generation===this.healthGeneration)this.health=value;}
  catch(e){if(generation===this.healthGeneration)this.healthError=this.message(e);}
  finally{if(generation===this.healthGeneration)this.healthLoading=false;}
 }
 private healthScreen(){
  if(this.health)return html`${this.healthError?html`<p class="notice error" role="alert">Le bilan n’a pas pu être actualisé. <button @click=${()=>void this.loadHealth()}>Réessayer</button></p>`:nothing}${this.healthPage()}`;
  return html`<h1>Mon logement</h1>${this.healthError?html`<p class="notice error" role="alert">Le bilan du logement n’a pas pu être chargé. ${this.healthError}</p>
   <div class="actions"><button @click=${()=>void this.loadHealth()}>Réessayer</button><button @click=${()=>this.page='rooms'}>Ouvrir les réglages</button></div>`
   :html`<p class="loading" role="status">Chargement du bilan de votre logement…</p>`}`;
 }
 private async goTo(t:Target){
  if(t.kind==='exterior')return this.editExterior();
  if(t.kind==='area')return this.start({area_id:t.area_id,name:this.areaName(t.area_id)});
  const room=this.snapshot?.rooms.find(r=>r.entry_id===t.entry_id);if(room)return this.editRoom(room);
 }
 private hline(l:HealthLine){
  return html`<li class=${l.level}><span class="hl-dot"></span><div><strong>${l.text}</strong>${l.why?html`<span class="hl-why">${l.why}</span>`:nothing}</div>
   ${l.target?html`<button class="link hl-go" ?disabled=${this.busy} @click=${()=>void this.goTo(l.target!)}>${l.target.label}</button>`:nothing}</li>`;
 }
 private healthPage(details=false){const h=this.health!;
  return html`<div class="hl-head"><div><h1>Mon logement</h1>
    <p class="hl-state ${h.level==='ok'?'ok':'bad'}"><span class="hl-dot"></span>${h.summary}<span class="muted"> · ${h.rooms_summary}${h.tips_summary?` · ${h.tips_summary}`:''}</span></p></div>
   </div>
  <p class="hl-legend"><span class="ok"><span class="hl-dot"></span>fonctionne</span><span class="bad"><span class="hl-dot"></span>à régler</span><span class="tip"><span class="hl-dot"></span>à améliorer</span><span class="none"><span class="hl-dot"></span>non utilisé</span></p>
  <div class="hl-grid">
   ${!details&&h.todo.length?html`${frame('À régler',html`<ul class="hl-lines">${h.todo.map(l=>this.hline(l))}</ul>`,{className:'wide todo'})}`:nothing}
   ${!details&&h.tips.length?html`${frame('À améliorer',html`<ul class="hl-lines">${h.tips.map(l=>this.hline(l))}</ul>`,{className:'wide'})}`:nothing}
   ${frame('Sources',html`<ul class="hl-lines">${h.sources.map(s=>html`<li class=${s.level}><span class="hl-dot"></span><div><strong>${s.label}</strong><span class="hl-why">${s.text}</span></div></li>`)}</ul>`,{className:'nk-plain'})}
   ${this.twins?.rooms.length?frame('Ce que Niak a appris',html`<p class="hint">Chaque pièce a son jumeau : quelques chiffres appris sur ses propres mesures. Il observe seulement, il ne change aucun conseil. Pour juger s’il voit juste, il rejoue les dernières 24 heures avec la vraie météo et vos fenêtres, sans regarder la pièce.</p>
    <div class="tw-grid">${this.twins.rooms.map(r=>this.twinCard(r.title,r.twin))}</div>`,{className:'wide',collapsible:true,open:false}):nothing}
   ${frame('Versions et liens',html`<ul class="hl-lines">${h.versions.map(l=>this.hline(l))}</ul>`,{collapsible:true,open:false})}
   ${frame('Capteurs par pièce',html`<div class="hl-table" tabindex="0" role="region" aria-label="Capteurs par pièce, tableau défilant"><table><thead><tr><th scope="col">Pièce</th>${h.columns.map(c=>html`<th scope="col">${c}</th>`)}</tr></thead>
    <tbody>${h.rooms.map(r=>html`<tr><th scope="row"><button class="link" @click=${()=>void this.goTo({kind:'room',entry_id:r.entry_id,label:r.title})}>${r.title}</button></th>
     ${r.cells.map(c=>html`<td class=${c.level}><span class="hl-dot"></span>${c.text}</td>`)}</tr>`)}</tbody></table></div>`,{className:'wide',collapsible:true})}
  </div>`;}
 private twinCard(title:string,t:Twin){
  const n=(v:number,d=1)=>v.toLocaleString('fr-FR',{maximumFractionDigits:d,minimumFractionDigits:0});
  if(t.status!=='ready'||!t.room)return html`<div class="tw-card"><h3>${title}</h3><p class="muted">En apprentissage : ${n(t.days)} jour${t.days>=2?'s':''} sur 3.</p></div>`;
  const r=t.room,p=t.precision,lines:string[]=[];
  lines.push(`Inertie : suit le dehors en ${n(r.inertia_hours,0)} h environ`);
  if(r.sun_degrees!=null&&r.sun_degrees>=0.3)lines.push(`Soleil fort : +${n(r.sun_degrees)} °C`);
  if(r.heating_degrees!=null&&r.heating_degrees>=0.3)lines.push(`Chauffage : +${n(r.heating_degrees)} °C`);
  if(r.household_degrees>=0.3)lines.push(`Vie de la maison : +${n(r.household_degrees)} °C`);
  if(r.window_half_minutes!=null)lines.push(`Fenêtre ouverte : l’écart avec le dehors divisé par 2 en ${r.window_half_minutes<120?n(r.window_half_minutes,0)+' min':n(r.window_half_minutes/60)+' h'}`);
  if(r.air_changes_per_hour>0)lines.push(`Fenêtres fermées : air renouvelé en ${n(1/r.air_changes_per_hour,0)} h environ`);
  if(r.water_per_hour>=0.1)lines.push(`Humidité produite : ${n(r.water_per_hour)} g/m³ par heure`);
  return html`<div class="tw-card"><h3>${title}</h3><ul>${lines.map(l=>html`<li>${l}</li>`)}</ul>
   ${p?html`<p class="tw-score">Précision sur 24 h : <strong>±${n(p.temperature)} °C</strong> et <strong>±${n(p.humidity,0)} %</strong> d’humidité</p>${this.twinCurve(p.curve)}`:nothing}
   <p class="hint">Appris sur ${n(t.days)} jours${t.open_samples?`, dont ${n(t.open_samples/2,0)} h fenêtre ouverte`:''}.</p></div>`;
 }
 /** Measured (solid) and replayed (dashed) temperature over the last 24 hours. */
 private twinCurve(curve:{temperature:number;measured_temperature:number}[]){
  if(curve.length<2)return nothing;
  const all=curve.flatMap(c=>[c.temperature,c.measured_temperature]),lo=Math.min(...all)-0.2,hi=Math.max(...all)+0.2,w=240,h=48;
  const line=(k:'temperature'|'measured_temperature')=>curve.map((c,i)=>`${(i/(curve.length-1)*w).toFixed(1)},${(h-(c[k]-lo)/(hi-lo)*h).toFixed(1)}`).join(' ');
  return html`<svg class="tw-curve" viewBox="0 0 240 48" preserveAspectRatio="none" role="img" aria-label="Température mesurée et rejouée sur 24 heures"><polyline points=${line('measured_temperature')} class="measured"/><polyline points=${line('temperature')} class="replayed"/></svg>
   <p class="tw-legend"><span class="measured">mesurée</span><span class="replayed">rejouée par le jumeau</span></p>`;
 }
 private message(e:unknown){return typeof e==='object'&&e&&'message' in e?String(e.message):'La connexion est indisponible. Réessayez sans quitter votre brouillon.';}
 private path(path:string){if(!this.isConnected)return;const full='/'+path.replace(/^\//,'');this.routeHandled=full==='/'?'':full;history.pushState(null,'','/niak/confort'+(path?'/'+path:''));window.dispatchEvent(new CustomEvent('location-changed'));}
 private remember(){if(this.workspaceKey&&(this.draft||this.exteriorDraft))this.drafts.set(this.workspaceKey,{draft:this.draft,exteriorDraft:this.exteriorDraft,discovery:this.discovery,entryId:this.entryId,stage:this.stage,revision:this.revision,acknowledged:this.acknowledged,proposed:this.proposed,search:this.search,weatherEntry:this.weatherEntry});}
 private async followRoute(){
  const path=this.route?.path??'';if(this.routeHandled===path)return;this.routeHandled=path;const generation=++this.workspaceGeneration;this.remember();
  const [id,section]=path.split('/').filter(Boolean);const key=id??'';
  this.workspaceKey=key;this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;this.preview=undefined;this.error='';this.saved='';this.confirmDiscard=false;this.confirmRemove=false;this.page='rooms';
  const cached=this.drafts.get(key);
  if(cached){Object.assign(this,cached);this.stage=roomSections.find(x=>x.path===section)?.stage??(section==='recapitulatif'?5:cached.stage);return;}
  if(id==='apercu'&&this.snapshot?.rooms.some(r=>r.entry_id===section)){this.preview=section;this.previewEdited=true;return;}
  if(id==='reglages'){await this.editExterior(false);return;}
  const room=this.snapshot?.rooms.find(r=>r.entry_id===id);if(room){await this.editRoom(room,false);if(generation===this.workspaceGeneration)this.stage=roomSections.find(x=>x.path===section)?.stage??(section==='recapitulatif'?5:0);}else if(id){this.error='Cette pièce n’est plus disponible. Choisissez une pièce ci-dessous.';}
 }
 private async loadOverview(){
  try{const o=await this.hass!.callWS<{areas:NonNullable<ComfortSetup['overview']>}>({type:'niak_comfort/overview'});const living=livingArea(o.areas.map(a=>({...a,outdoor:false})),new Set());this.overview=living?[...o.areas.filter(a=>a.area_id===living.area_id),...o.areas.filter(a=>a.area_id!==living.area_id)]:o.areas;this.picked=o.areas.filter(a=>typeof a.suggestions.indoor_temperature==='string').map(a=>a.area_id);}
  catch{this.overview=[];}
 }
 private detected(s:Record<string,string|string[]>){const parts=[s.indoor_temperature&&'température',s.indoor_humidity&&'humidité',s.co2&&'CO₂',s.heating&&'chauffage'].filter(Boolean) as string[];const n=Array.isArray(s.windows)?s.windows.length:0;if(n)parts.push(n+' ouvrant'+(n>1?'s':''));return parts.join(', ');}
 // Creates every checked room at once with Niak's unambiguous proposals; each room keeps its assistant.
 private async createAll(){
  const areas=(this.overview??[]).filter(a=>this.picked.includes(a.area_id));if(!areas.length){this.error='Cochez au moins une pièce.';return;}
  this.busy=true;this.error='';let created=0;
  try{for(const a of areas){const discovery=await this.discover(a.area_id);const snapshot:Snapshot=await this.hass!.callWS<Snapshot>({type:'niak_comfort/save_config',config:newRoom({area_id:a.area_id,name:a.name},'',discovery),revision:this.snapshot!.revision,acknowledged:[]});this.snapshot=snapshot;created++;}
   this.saved=`${created} pièce${created>1?'s':''} créée${created>1?'s':''}. Ouvrez chacune pour renseigner l’exposition des ouvrants et compléter si besoin.`;this.overview=undefined;}
  catch(e){this.error=(created?`${created} pièce${created>1?'s':''} créée${created>1?'s':''}, puis : `:'')+this.message(e);}
  finally{this.busy=false;}
 }
 private menu(){this.dispatchEvent(new CustomEvent('hass-toggle-menu',{bubbles:true,composed:true}));}
 private areaName(id:string|null){return id?this.snapshot?.areas.find(a=>a.area_id===id)?.name??id:'';}
 private async discover(area_id?:string|null,entry_id?:string){
  return await this.hass!.callWS<Discovery>({type:'niak_comfort/discover',...(area_id?{area_id}:{}),...(entry_id?{entry_id}:{})});
 }
 private begin(){this.confirmRemove=false;this.busy=true;this.error='';this.saved='';this.preview=undefined;this.search={};this.confirmed=false;}
 private async start(area:{area_id:string;name:string}|null,name=''){
  if(!area&&!name.trim()){this.error='Donnez un nom à la pièce libre, par exemple « Étage » ou « Suite parentale ».';return;}
  const workspace=this.workspaceGeneration;this.begin();
  try{const d=await this.discover(area?.area_id);if(workspace!==this.workspaceGeneration)return;this.discovery=d;this.revision=d.revision;this.entryId=undefined;this.draft=newRoom(area,name.trim(),d);this.proposed=[...Object.values(this.draft.sources),...this.draft.windows];this.stage=0;this.acknowledged=[];this.freeName='';this.workspaceKey='nouvelle';this.path('nouvelle/temperature');}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async editRoom(room:Room,route=true){
  const cached=this.drafts.get(room.entry_id);if(route&&cached){Object.assign(this,cached);this.workspaceKey=room.entry_id;this.path(room.entry_id+'/'+(roomSections.find(x=>x.stage===this.stage)?.path??'recapitulatif'));return;}
  const generation=this.workspaceGeneration;this.begin();
  try{const d=await this.discover(room.config.area_id,room.entry_id);if(generation!==this.workspaceGeneration)return;this.discovery=d;this.revision=d.revision;this.entryId=room.entry_id;
   const config=structuredClone(room.config);config.area_id??=null;config.openings??={};for(const id of config.windows)config.openings[id]??={...defaultOpening(),sheltered:config.rain_exposed===false};
   this.draft=config;this.proposed=[];this.stage=0;this.acknowledged=[...(config.acknowledged??[])];this.workspaceKey=room.entry_id;if(route)this.path(room.entry_id+'/temperature');}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async editExterior(route=true){
  const cached=this.drafts.get('reglages');if(route&&cached){Object.assign(this,cached);this.workspaceKey='reglages';this.path('reglages');return;}
  const generation=this.workspaceGeneration;this.begin();
  try{const d=await this.discover();if(generation!==this.workspaceGeneration)return;this.discovery=d;this.revision=d.revision;this.exteriorDraft=structuredClone(this.snapshot!.home.sources);this.weatherEntry=this.snapshot!.home.weather??null;this.acknowledged=[...(this.snapshot!.home.acknowledged??[])];this.proposed=[];this.workspaceKey='reglages';if(route)this.path('reglages');}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 // Takes Niak Weather's station and signals as the exterior: one setting place for the whole home.
 private async useWeather(entry_id:string){
  this.busy=true;this.error='';
  try{const p=await this.hass!.callWS<{entry_id:string;title:string;sources:Record<string,Spec>}>({type:'niak_comfort/weather_proposal',entry_id});
   this.exteriorDraft={...(this.exteriorDraft??{}),...p.sources};this.weatherEntry=p.entry_id;this.saved=`Station de Niak Weather (${p.title}) reprise : vérifiez puis enregistrez.`;}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private ownSensors(){this.weatherEntry=null;this.saved='';}
 // The exterior: its source by integration first, then the place of Niak Weather.
 private exteriorSource(){const s=this.snapshot!,nw=s.niak_weather,from=this.weatherEntry?'weather':'own';
  return frame('D’où viennent les mesures du dehors ?',html`<span id="l-from" class="sr-only">Source des mesures du dehors</span>
   ${this.choiceList('from','l-from',exteriorChoices(s),from,v=>v==='weather'?void this.useWeather(nw!.places[0].entry_id):this.ownSensors())}
   ${from==='weather'?this.zone('Lieu Niak Weather',(nw?.places??[]).map(p=>({value:p.entry_id,label:p.title})),this.weatherEntry!,id=>void this.useWeather(id),
    'Niak Confort lit aussi ses alertes (orage, vigilance, pluie qui arrive) et ses prévisions pour les créneaux d’ouverture.'):nothing}`);}
 // The outdoor air quality: the integration first, then its zone or place, then the person's caution.
 private airBlock(){const all=this.discovery?.candidates.pollution??[],spec=this.exteriorDraft!.pollution,current=airSource(spec);
  const pickSource=(v:string)=>{if(v===current)return;if(v==='none'){this.clear('pollution');return;}
   const first=all.find(c=>c.adapter===(v==='atmo'?'atmo_daily':'niak_index'));if(first)this.choose('pollution',first);};
  const zones=spec&&current!=='other'?all.filter(c=>c.adapter===spec.adapter):[],c=all.find(x=>x.entity_id===spec?.entity_id);
  return frame(labels.pollution,html`<span id="l-air" class="sr-only">${labels.pollution}</span><p class="hint">Une précaution régionale du jour, pas une mesure à vos fenêtres.</p>
   ${this.choiceList('air','l-air',airChoices(this.snapshot!,all,current),current,pickSource)}
   ${spec&&current!=='other'?this.zone(current==='atmo'?'Zone Atmo France':'Lieu Niak Weather',zones.map(z=>({value:z.entity_id,label:z.name+' · '+measurement(z)})),spec.entity_id,id=>this.pick('pollution',id)):nothing}
   ${current==='other'?html`<p class="hint">${c?.name??spec!.entity_id}</p>`:nothing}${c?this.warnings(c):nothing}
   ${spec?.adapter==='atmo_daily'?html`<label>Prudence à partir du niveau<select @change=${(e:Event)=>{this.exteriorDraft={...this.exteriorDraft!,pollution:{...spec,block_from:Number((e.target as HTMLSelectElement).value)}};}}>${['Moyen','Dégradé','Mauvais','Très mauvais','Extrêmement mauvais'].map((label,i)=>html`<option value=${i+2} ?selected=${(spec.block_from??4)===i+2}>${label}</option>`)}</select></label><p class="hint">C’est votre préférence de prudence, pas une consigne sanitaire.</p>`:nothing}`);}
 // ---- Pieces shared by every step (charte des onglets de réglage) ----
 // What the step is for, in a frame that folds and stays folded.
 private intro(key:string){if(key==='6')return html`<div class="nk-step-help">${helpTip('Présence',help.presence,'À quoi sert cette étape ?')}</div>`;return html`<div class="nk-step-help">${helpTip('Comprendre cette étape',html`<ul>${intros[key].map(line=>html`<li>${line}</li>`)}</ul>`,'À quoi sert cette étape ?')}</div>`;}

 private choiceList(name:string,label:string,choices:Choice[],value:string,pick:(v:string)=>void){
  return html`<div class="sources" role="radiogroup" aria-labelledby=${label}>${choices.map(c=>html`<label class="source ${c.value===value?'on':''} ${c.available?'':'off'}">
   <input type="radio" name=${name} .checked=${c.value===value} ?disabled=${!c.available||this.busy} @change=${()=>pick(c.value)}>
   <span><strong>${c.label}</strong><span>${c.hint}</span>${c.available?nothing:html`<span>${c.missing}${c.url?html` · <a href=${c.url} target="_blank" rel="noreferrer">installer ${c.label}</a>`:nothing}</span>`}</span></label>`)}</div>`;}
 // The zone, place or device of the chosen source, shown even when there is only one.
 private zone(label:string,options:{value:string;label:string}[],value:string,pick:(v:string)=>void,hint=''){
  const known=options.some(o=>o.value===value);
  return html`<label class="zone">${label}<select ?disabled=${this.busy} @change=${(e:Event)=>pick((e.target as HTMLSelectElement).value)}>
   ${known?nothing:html`<option value="" selected disabled>Introuvable · choisissez-en un autre</option>`}
   ${options.map(o=>html`<option value=${o.value} ?selected=${o.value===value}>${o.label}</option>`)}</select></label>${hint?html`<p class="hint">${hint}</p>`:nothing}`;}
 // A part that folds, in a frame of its own: title, « x sur y », and what is left to check.
 private group(title:string,keys:string[]){
  const on=keys.filter(k=>this.selected(k).length).length;
  return frame(title,html`${keys.map(k=>this.field(k))}`,{count:`${on} sur ${keys.length}`});
 }

 private async changeArea(area_id:string){
  if(!this.draft)return;this.busy=true;this.error='';
  try{const d=await this.discover(area_id||null,this.entryId);this.discovery=d;this.revision=d.revision;this.draft={...this.draft,area_id:area_id||null,floor_id:null};}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async refreshCandidates(){
  this.busy=true;this.error='';
  try{const d=await this.discover(this.draft?.area_id,this.entryId);if(d.revision!==this.revision){this.error='La configuration a changé ailleurs. Votre brouillon est conservé ; revenez à Mon logement et rechargez avant d’enregistrer.';return;}this.discovery=d;this.saved='La liste des capteurs a été actualisée. Vos choix restent inchangés.';}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 // Deleting a room leaves the person's devices untouched; an area room is proposed again on the home page.
 private async removeRoom(){const id=this.entryId,d=this.draft;if(!id||!d)return;this.busy=true;this.error='';
  try{const snapshot=await this.hass!.callWS<Snapshot>({type:'niak_comfort/remove_room',entry_id:id,revision:this.revision});this.snapshot=snapshot;this.discard();this.confirmRemove=false;
   this.saved=`« ${d.name} » est supprimée. Vos capteurs n’ont pas été touchés.${d.area_id?' La pièce vous est de nouveau proposée ci-dessous.':''}`;if(!snapshot.rooms.length)await this.loadOverview();}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private removeBlock(){const d=this.draft!;if(!this.entryId)return nothing;
  return this.confirmRemove?html`<section class="notice remove" role="alertdialog" aria-label="Supprimer la pièce"><h2>Supprimer « ${d.name} » ?</h2><p>Niak arrête de suivre cette pièce et sa carte n’affichera plus rien. Vos appareils et capteurs Home Assistant ne sont pas touchés.</p><p class="hint">${d.area_id?'La pièce Home Assistant vous sera de nouveau proposée dans Mon logement.':'Vous pourrez la recréer comme pièce libre.'}</p><div class="actions"><button @click=${()=>this.confirmRemove=false}>Garder la pièce</button><button class="danger" ?disabled=${this.busy} @click=${()=>this.removeRoom()}>Supprimer la pièce</button></div></section>`
   :html`<div class="remove"><button class="link danger-link" @click=${()=>this.confirmRemove=true}>Supprimer cette pièce</button></div>`;}
 private cancel(){if(this.draft||this.exteriorDraft){this.confirmDiscard=true;return;}this.discard();}
 private discard(){this.drafts.delete(this.workspaceKey);this.workspaceKey='';this.path('');this.confirmDiscard=false;this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;this.error='';this.acknowledged=[];this.proposed=[];}
 private selected(key:string):string[]{if(this.exteriorDraft)return this.exteriorDraft[key]?[this.exteriorDraft[key].entity_id]:[];if(!this.draft)return [];return key==='presence'?(this.draft.presence??[]):key==='windows'?this.draft.windows:this.draft.sources[key]?[this.draft.sources[key]]:[];}
 private choose(key:string,c:Candidate){
  const previous=this.selected(key);
  if(this.exteriorDraft){this.exteriorDraft={...this.exteriorDraft,[key]:{entity_id:c.entity_id,adapter:c.adapter,...(c.adapter==='atmo_daily'?{block_from:this.exteriorDraft[key]?.block_from??4}:{})}};}
  else if(this.draft){if(key==='presence'){this.draft={...this.draft,presence:[...new Set([...(this.draft.presence??[]),c.entity_id])]};}else if(key==='windows'){this.draft={...this.draft,windows:[...new Set([...this.draft.windows,c.entity_id])],openings:{...this.draft.openings,[c.entity_id]:this.draft.openings[c.entity_id]??defaultOpening()}};}else {const evolution={...this.draft.evolution};if(key==='voc'&&this.draft.sources.voc!==c.entity_id){const preset=vocPreset(c);if(preset)evolution.voc_threshold=preset;else delete evolution.voc_threshold;}this.draft={...this.draft,evolution,sources:{...this.draft.sources,[key]:c.entity_id}};}}
  if(!multiple.has(key))this.acknowledged=this.acknowledged.filter(id=>!previous.some(p=>id===warningId(key,p)));
  this.proposed=this.proposed.filter(id=>id!==c.entity_id);this.search={...this.search,[key]:''};this.error='';
 }
 private pick(key:string,id:unknown){if(typeof id!=='string'||!id)return;const c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(c)this.choose(key,c);}
 private clear(key:string,id?:string){
  const removed=id??this.selected(key)[0]??'';
  if(this.exteriorDraft){const next={...this.exteriorDraft};delete next[key];this.exteriorDraft=next;}
  else if(this.draft){if(key==='presence'){this.draft={...this.draft,presence:(this.draft.presence??[]).filter(e=>e!==id)};}else if(key==='windows'){const openings={...this.draft.openings};delete openings[id!];this.draft={...this.draft,windows:this.draft.windows.filter(e=>e!==id),openings};}else{const next={...this.draft.sources};delete next[key];const evolution={...this.draft.evolution};if(key==='voc')delete evolution.voc_threshold;this.draft={...this.draft,evolution,sources:next};}}
  this.acknowledged=this.acknowledged.filter(v=>v!==warningId(key,removed));
 }
 private ack(id:string,on:boolean){this.acknowledged=on?[...new Set([...this.acknowledged,id])]:this.acknowledged.filter(v=>v!==id);}
 private setOpening(id:string,change:Partial<RoomConfig['openings'][string]>){const d=this.draft!;this.draft={...d,openings:{...d.openings,[id]:{...(d.openings[id]??defaultOpening()),...change}}};}
 private warnings(c:Candidate,_key?:string,_selected?:boolean){return html`${c.warnings.filter(w=>!(w==='derived'&&c.warnings.includes('alias'))).map(w=>html`<p class="warning hint">${warningText[w]??'Source à vérifier.'}</p>`)}${c.provenance.length>1?html`<p class="provenance">Origine de la mesure : ${c.provenance.map((p,i)=>html`${i?' → ':nothing}${p.name}${p.area_id?` (${this.areaName(p.area_id)})`:nothing}`)}</p>`:nothing}`;}
 // Sensors chosen with a warning that the person has not confirmed yet: one confirmation covers them all.
 private pending(){const keys=this.exteriorDraft?[...outdoor]:[...indoor,'illuminance','co2','pm25','voc','purifier','ventilation','ventilation_boost','presence','heating','windows'];const out:{id:string;name:string}[]=[];
  for(const key of keys)for(const id of this.selected(key)){const c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(c?.warnings.length&&!this.acknowledged.includes(warningId(key,id)))out.push({id:warningId(key,id),name:c.name});}
  if(this.draft)for(const m of Object.values(this.draft.openings))for(const [field,key] of [['cover_entity','covers'],['auto_entity','shutter_auto'],['override_entity','shutter_override']] as const){const id=m[field],c=this.discovery?.candidates[key]?.find(x=>x.entity_id===id);if(c?.warnings.length&&!this.acknowledged.includes(warningId(key,c.entity_id)))out.push({id:warningId(key,c.entity_id),name:c.name});}
  return out;}
 private confirmBlock(){const list=this.pending();if(!list.length)return nothing;
  return html`<div class="notice confirm"><p>${list.length===1?'Un capteur est à vérifier':list.length+' capteurs sont à vérifier'} (autre pièce, porte d’appareil ou mesure recopiée) : ${list.map(x=>x.name).join(', ')}.${this.exteriorDraft?' Les explications sont plus haut.':' Les explications sont aux étapes précédentes.'}</p><label class="check"><input type="checkbox" .checked=${this.confirmed} @change=${(e:Event)=>{this.confirmed=(e.target as HTMLInputElement).checked;if(this.confirmed)this.error='';}}>J’ai vérifié, je confirme mes choix.</label></div>`;}
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
  }else if(key==='presence'&&this.draft){this.draft={...this.draft,presence:[...new Set((this.draft.presence??[]).map(e=>e===old?id:e))]};this.acknowledged=this.acknowledged.filter(a=>a!==warningId(key,old));}else this.choose(key,c);
 }
 private selector(key:string,ids:string[],value:string,label:string,changed:(id:unknown)=>void){
  if(this.pickerTag==='ha-selector')return html`<ha-selector .hass=${this.hass} .selector=${{entity:{include_entities:ids}}} .value=${live(value)} .required=${false} .label=${label} @value-changed=${(e:CustomEvent)=>changed(e.detail?.value)}></ha-selector>`;
  return html`<ha-entity-picker .hass=${this.hass} .includeEntities=${ids} .value=${live(value)} .required=${false} .label=${label} @value-changed=${(e:CustomEvent)=>changed(e.detail?.value)}></ha-entity-picker>`;
 }
 private picker(key:string,all:Candidate[],selected:string[]){
  const free=all.filter(c=>!selected.includes(c.entity_id));
  if(!free.length)return html`<p class="hint">Aucun autre capteur compatible dans Home Assistant.</p>`;
  const label=multiple.has(key)&&selected.length?(key==='presence'?'Ajouter un autre capteur de présence':'Ajouter un autre ouvrant'):'Choisir un autre capteur';
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
 private openingSource(id:string,key:'cover_entity'|'auto_entity'|'override_entity',kind:string,label:string){const m=this.draft!.openings[id]??defaultOpening(),all=this.discovery?.candidates[kind]??[],value=m[key]??'';
  const change=(next:unknown)=>{if(typeof next==='string'){this.acknowledged=this.acknowledged.filter(a=>a!==warningId(kind,value));this.confirmed=false;this.setOpening(id,{[key]:next||undefined});}};
  return html`<label>${this.pickerTag?nothing:label}${this.pickerTag?this.selector(kind,[...new Set([...(value?[value]:[]),...all.map(c=>c.entity_id)])],value,label,change):html`<select @change=${(e:Event)=>change((e.target as HTMLSelectElement).value)}><option value="" ?selected=${!value}>Non renseigné</option>${value&&!all.some(c=>c.entity_id===value)?html`<option selected value=${value}>${value} · introuvable</option>`:nothing}${all.map(c=>html`<option value=${c.entity_id} ?selected=${value===c.entity_id}>${c.name} · ${measurement(c)}</option>`)}</select>`}</label>${all.find(c=>c.entity_id===value)?this.warnings(all.find(c=>c.entity_id===value)!):nothing}`;
 }
 private evolutionNumber(key:'glazing_factor'|'presence_delay_minutes',label:string,initial:number,min:number,max:number,step:number){const d=this.draft!;return html`<label>${label}<input type="number" min=${min} max=${max} step=${step} .value=${String(d.evolution?.[key]??initial)} @input=${(e:Event)=>this.draft={...d,evolution:{...d.evolution,[key]:Number((e.target as HTMLInputElement).value)}}}></label>`;}
 private airPresence(){return html`${['co2','pm25','voc','purifier','ventilation'].map(key=>this.field(key))}${this.draft?.sources.ventilation?this.field('ventilation_boost'):nothing}`;}
 private sensorSettings(key:string){const d=this.draft!;if(!d)return nothing;const selected=!!this.selected(key).length;if(!selected&&!['pm25','voc'].includes(key))return nothing;
 const voc=this.discovery?.candidates.voc?.find(c=>c.entity_id===d.sources.voc),unit=voc?(voc.unit??''):(d.evolution?.voc_threshold?.unit??''),preset=vocPreset(voc),availableVoc=this.discovery?.candidates.voc?.find(c=>vocPreset(c)),availablePreset=vocPreset(availableVoc);
 if(key==='co2')return html`<div class="sensor-settings"><h4>Repères d’interprétation</h4>

  ${this.number('co2_potential','CO₂ : aérer ferait du bien (ppm)',1000)}${this.number('co2_action','CO₂ : aérer (ppm)',1200)}${this.number('co2_urgent','CO₂ : attention (ppm)',1600)}
  ${defaultValue('800 / 1 000 / 1 500 ppm',()=>this.draft={...d,settings:{...d.settings,co2_potential:airReferenceDefaults.co2_potential,co2_action:airReferenceDefaults.co2_action,co2_urgent:airReferenceDefaults.co2_urgent}},html`<p class="hint">Pourquoi : le HCSP retient 800 ppm comme objectif de renouvellement d’air et 1 500 ppm comme valeur d’action rapide dans les établissements recevant du public. Niak s’en inspire pour le logement et ajoute un palier intermédiaire à 1 000 ppm. Ces valeurs décrivent le confinement, pas la toxicité ni l’ensemble des polluants. Les anciens repères Niak étaient 1 000 / 1 200 / 1 600 ppm. <a href=${thresholdSources.co2} target="_blank" rel="noopener noreferrer">Source : HCSP, avis du 21 janvier 2022</a>.</p>`,{applied:['co2_potential','co2_action','co2_urgent'].every(k=>d.settings[k]===airReferenceDefaults[k as keyof typeof airReferenceDefaults])})}</div>`;
 if(key==='pm25')return html`<div class="sensor-settings"><h4>Repère d’interprétation</h4>
  ${selected?this.number('pm25_action','PM2.5 : seuil de signalement (µg/m³)',25):nothing}
  ${defaultValue('15 µg/m³',()=>this.draft={...d,settings:{...d.settings,pm25_action:airReferenceDefaults.pm25_action}},html`<p class="hint">Pourquoi 15 : l’OMS recommande 15 µg/m³ en moyenne sur 24 heures (et 5 sur un an). Niak utilise ici 15 comme repère de vigilance sur la mesure reçue ; il ne calcule pas une exposition sur 24 heures. Un pic n’est donc pas un dépassement de la moyenne OMS, et une mesure basse ne garantit pas l’absence de risque. Le seuil Niak précédent était 25. <a href=${thresholdSources.pm25} target="_blank" rel="noopener noreferrer">Source : OMS, lignes directrices 2021</a>.</p>`,{applied:d.settings.pm25_action===15,disabled:!selected,note:!selected?'Choisissez le capteur pour activer le suivi.':undefined})}</div>`;
 if(key==='voc')return html`<div class="sensor-settings"><h4>Repère d’interprétation</h4>
  ${d.sources.voc?html`<p class="hint">Capteur choisi : ${voc?.name??d.sources.voc}. Unité : ${unit||'indice sans unité'}. Le seuil reste attaché à cette unité ; changer de capteur ou d’unité impose de le vérifier.</p>
  <label>Seuil COV (${unit||'indice'})<input type="number" min="0" step="any" .value=${d.evolution?.voc_threshold?.unit===unit?String(d.evolution.voc_threshold.value):''} @input=${(e:Event)=>{const value=(e.target as HTMLInputElement).value,evolution={...d.evolution};if(value)evolution.voc_threshold={value:Number(value),unit};else delete evolution.voc_threshold;this.draft={...d,evolution};}}></label>
  ${preset?html`${defaultValue('Indice 150',()=>this.draft={...d,evolution:{...d.evolution,voc_threshold:{...preset}}},html`<p class="hint">Pourquoi 150 : pour la VINDSTYRKA IKEA identifiée, Niak reprend l’exemple d’action de Sensirion. L’indice 100 correspond au niveau habituel appris par le capteur ; un indice plus haut signale davantage de COV par rapport à cet historique. Ce n’est ni une concentration, ni une limite sanitaire. L’adaptation du capteur peut ramener une pollution persistante vers 100. <a href=${thresholdSources.voc} target="_blank" rel="noopener noreferrer">Source : Sensirion, fonctionnement du VOC Index</a>.</p>`,{applied:d.evolution?.voc_threshold?.value===preset.value&&d.evolution?.voc_threshold?.unit===preset.unit})}`:html`<p class="hint">Aucune valeur par défaut pour ce capteur : son unité seule ne suffit pas à justifier un seuil commun. Utilisez un repère documenté par son fabricant dans cette unité ; Niak ne convertit pas les indices en ppb ou en µg/m³. À défaut de seuil, la mesure reste visible sans verdict COV.</p><p class="hint">L’UBA rappelle que le total des COV ne permet pas à lui seul d’évaluer le risque sanitaire. Un seuil d’une substance ou un repère TVOC ne s’applique pas automatiquement à tous les capteurs grand public. <a href=${thresholdSources.tvoc} target="_blank" rel="noopener noreferrer">Source : agence allemande de l’environnement, AIR</a>.</p>`}
  <p class="hint">Vous pouvez laisser le seuil vide pour suivre la mesure sans l’interpréter.</p>`:html`<p class="hint">Choisissez votre capteur COV pour activer le suivi.</p>${availablePreset?defaultValue('Indice '+availablePreset.value,()=>{},html`<p class="hint">Pourquoi 150 : pour la VINDSTYRKA IKEA identifiée, Niak reprend l’exemple d’action de Sensirion. L’indice 100 correspond au niveau habituel appris par le capteur ; un indice plus haut signale davantage de COV par rapport à cet historique. Ce n’est ni une concentration, ni une limite sanitaire. L’adaptation du capteur peut ramener une pollution persistante vers 100. <a href=${thresholdSources.voc} target="_blank" rel="noopener noreferrer">Source : Sensirion, fonctionnement du VOC Index</a>.</p>`,{applied:false,disabled:true,note:'Pour le capteur reconnu : '+availableVoc!.name}):html`<p class="hint">Valeur par défaut : selon le modèle et l’unité du capteur.</p>`}`}</div>`;
 if(key==='indoor_humidity')return html`<div class="sensor-settings"><h4>Repère d’humidité</h4>${this.number('humidity_high','Humidité haute (%)',62)}${defaultValue('60 %',()=>this.draft={...d,settings:{...d.settings,humidity_high:airReferenceDefaults.humidity_high}},html`<p class="hint">L’ADEME conseille 40 à 60 % d’humidité. Niak propose donc 60 % pour signaler un air humide ; le choix d’aérer dépend aussi de l’humidité extérieure. L’ancien repère Niak était 62 %. <a href=${thresholdSources.humidity} target="_blank" rel="noopener noreferrer">Source : ADEME, Respirer un air sain chez soi</a>.</p>`,{applied:d.settings.humidity_high===60})}</div>`;
 if(key==='presence')return html`<div class="sensor-settings">${this.evolutionNumber('presence_delay_minutes','Délai avant de considérer la pièce vide (minutes)',5,0,120,1)}${helpTip('Comprendre le délai de présence',html`<p>5 minutes est un choix pratique Niak pour éviter les changements trop rapides. Le délai commence après une absence réellement signalée ; le silence d’un détecteur de mouvement ne suffit pas. Une pièce vide conserve son suivi et ses alertes.</p>`,'Comprendre ce réglage')}</div>`;
 if(key==='indoor_temperature')return html`<div class="sensor-settings"><h4>Votre plage de confort</h4>${this.number('minimum','Température minimum (°C)',20,0.5)}${this.number('maximum','Température maximum en hiver (°C)',24,0.5)}${this.number('summer_maximum','Température maximum en été (°C)',26,0.5)}${defaultValue('20–24 °C l’hiver, 26 °C l’été',()=>this.draft={...d,settings:{...d.settings,minimum:20,maximum:24,summer_maximum:26}},html`<p class="hint">Le maximum monte progressivement de la valeur d’hiver à celle d’été quand la température extérieure moyenne des 7 derniers jours passe de 12 à 20 °C. Ces valeurs sont un choix de confort personnel, à adapter à cette pièce. Ce n’est pas une limite sanitaire.</p>`,{applied:d.settings.minimum===20&&d.settings.maximum===24&&(d.settings.summer_maximum??26)===26})}
  <label class="check"><input type="checkbox" .checked=${d.heated===false} @change=${(e:Event)=>this.draft={...d,heated:!(e.target as HTMLInputElement).checked}}>Pièce non chauffée : ne jamais conseiller de la réchauffer</label></div>`;
 return nothing;
 }
 /** Who moves the cover. Adaptive Cover Pro is recognised by itself and each signal it gives is shown;
     any other automation is told by hand. Full width, below the cover's own fields. */
 private coverDriver(id:string,cover?:string|null){
  const m=this.draft!.openings[id]??defaultOpening(),driver=cover?this.discovery?.drivers?.[cover]:undefined;
  const fields=html`${this.openingSource(id,'auto_entity','shutter_auto','Interrupteur qui active le pilotage automatique')}${this.openingSource(id,'override_entity','shutter_override','Capteur « repris à la main »')}`;
  if(!driver)return html`<div class="wide"><h4>Qui pilote ce volet ?</h4><p class="hint">Si une automatisation ouvre et ferme ce volet, indiquez l’interrupteur qui l’active et, s’il existe, le capteur qui signale que vous avez repris la main. Niak ne commande rien : il évite seulement de vous conseiller ce que l’automatisme fait déjà.</p>${fields}</div>`;
  const sig=driver.signals,row=(label:string,s:{name:string;on:boolean}|null|undefined,on:string,off:string)=>s?html`<li><b>${label}</b> · ${s.on?on:off}<span class="hint"> (${s.name})</span></li>`:nothing;
  const names:Record<string,string>={N:'Nord',NE:'Nord-Est',E:'Est',SE:'Sud-Est',S:'Sud',SO:'Sud-Ouest',O:'Ouest',NO:'Nord-Ouest'};
  return html`<div class="wide driver"><h4>Piloté par ${driver.name}</h4>
   <p class="hint">Niak lit ces signaux tout seul, rien à renseigner :</p>
   <ul>${row('Intégration',sig?.enabled,'activée','désactivée : elle ne pilote rien')}${row('Pilotage automatique',sig?.auto,'activé','coupé')}${row('Suivi du soleil',sig?.tracking,'activé','coupé')}${row('Mode climat',sig?.climate,'activé','coupé : il ne ferme pas contre la chaleur')}${row('Détection de la reprise à la main',sig?.detection,'activée','coupée : Niak ne saura pas si vous avez bougé le volet')}${row('Repris à la main',sig?.override,'oui','non')}${row('Soleil devant la fenêtre',sig?.sun,'oui','non')}
    ${driver.azimuth!=null?html`<li><b>Orientation de la fenêtre</b> · ${Math.round(driver.azimuth)}°${driver.exposure?` (${names[driver.exposure]})`:''}${driver.exposure&&m.exposure!==driver.exposure?html` <button class="link" @click=${()=>this.setOpening(id,{exposure:driver.exposure})}>Utiliser pour l’exposition</button>`:nothing}</li>`:nothing}</ul>
   <p class="hint">Ainsi, quand ${driver.name} pilote le volet, Niak ne vous demande pas de le faire ; s’il est coupé, Niak vous prévient avant que le soleil n’arrive sur la fenêtre. Niak ne commande rien.</p>
   ${m.auto_entity||m.override_entity?html`<h4>Signaux choisis à la main</h4><p class="hint">Ils remplacent ceux de ${driver.name}. Retirez-les pour revenir à la détection.</p>${fields}`:nothing}</div>`;
 }
 private openingDetails(id:string){const m=this.draft!.openings[id]??defaultOpening(),known=m.shutter==='connected'&&m.cover_entity?this.discovery?.drivers?.[m.cover_entity]:undefined;return html`<div class="opening">
  <label>Exposition<select @change=${(e:Event)=>this.setOpening(id,{exposure:(e.target as HTMLSelectElement).value||null})}><option value="" ?selected=${!m.exposure}>Je ne sais pas</option>${exposures.map(([v,l])=>html`<option value=${v} ?selected=${m.exposure===v}>${l}</option>`)}</select></label>
  <label>Type<select @change=${(e:Event)=>this.setOpening(id,{kind:(e.target as HTMLSelectElement).value})}>${kinds.map(([v,l])=>html`<option value=${v} ?selected=${m.kind===v}>${l}</option>`)}</select></label>
  <label class="check"><input type="checkbox" .checked=${m.sheltered} @change=${(e:Event)=>this.setOpening(id,{sheltered:(e.target as HTMLInputElement).checked})}>Abrité par une avancée de toit ou un balcon</label>
  <label>Volet<select @change=${(e:Event)=>{const shutter=(e.target as HTMLSelectElement).value as 'none'|'manual'|'connected';this.setOpening(id,{shutter,cover_entity:undefined,auto_entity:undefined,override_entity:undefined});}}>${[['none','Sans volet'],['manual','Volet manuel (bois, battant…)'],['connected','Volet connecté']].map(([v,l])=>html`<option value=${v} ?selected=${(m.shutter??'none')===v}>${l}</option>`)}</select></label>
  ${m.shutter==='manual'?html`<p class="hint">Position non mesurée. Les conseils resteront conditionnels : si votre volet est ouvert, vous pouvez le fermer.</p>`:nothing}
  ${m.shutter==='connected'?this.openingSource(id,'cover_entity','covers','Volet de cet ouvrant'):nothing}
  ${m.shutter==='connected'?this.coverDriver(id,m.cover_entity):nothing}
  <details class="group"><summary>Dimensions et avancée de toit (pour l’ombre)</summary><p class="hint">En mètres. L’ombre et la capacité d’aération seront estimées ; laissez vide ce que vous ne connaissez pas.</p>${known?.width!=null||known?.height!=null?html`<p class="hint"><b>Repris de ${known.name} :</b> ${[known.width!=null?`largeur ${String(known.width).replace('.',',')} m`:'',known.height!=null?`hauteur ${String(known.height).replace('.',',')} m`:''].filter(Boolean).join(', ')}. Une valeur saisie ici le remplace.</p>`:nothing}${([['width','Largeur de l’ouvrant'],['height','Hauteur de l’ouvrant'],['overhang_depth','Profondeur de l’avancée'],['overhang_gap','Écart entre avancée et haut de l’ouvrant']] as const).map(([key,label])=>html`<label>${label} (m)<input type="number" min="0" step="0.01" placeholder=${key==='width'&&known?.width!=null?String(known.width):key==='height'&&known?.height!=null?String(known.height):''} .value=${m[key]===undefined?'':String(m[key])} @input=${(e:Event)=>{const value=(e.target as HTMLInputElement).value;this.setOpening(id,{[key]:value===''?undefined:Number(value)});}}></label>`)}</details></div>`;}
 private field(key:string){
  const all=this.discovery?.candidates[key]??[],selected=this.selected(key),room=this.draft;
  const proposals=(this.exteriorDraft?all.filter(c=>c.outside):all.filter(c=>c.local)).filter(c=>!selected.includes(c.entity_id));
  const canAdd=multiple.has(key)||!selected.length;
  const where=this.exteriorDraft?'dans vos pièces extérieures':room?.area_id?'dans la pièce '+this.areaName(room.area_id):'';
  return frame(labels[key],html`
   ${key==='windows'&&selected.length?html`${helpTip('Comprendre l’exposition',html`<p>L’exposition est le côté vers lequel regarde l’ouvrant. Elle permet de savoir quand le soleil y entre.</p>`,'Comprendre ce réglage')}`:nothing}
   ${selected.map(id=>this.chosen(key,id,all,selected))}
   ${canAdd&&proposals.length?html`<p class="hint strong">${proposals.length===1?'Trouvé '+where:'Trouvés '+where+' : choisissez '+(multiple.has(key)?'ceux qui conviennent':'celui qui convient')}</p><div class="candidates">${proposals.slice(0,5).map(c=>this.candidateRow(c,key))}</div>`:nothing}
   ${canAdd&&!proposals.length&&!selected.length?html`<p class="notice">${where?'Rien trouvé '+where+'.':'Pièce libre : choisissez le capteur ci-dessous.'}${where?' Vous pouvez en choisir un ailleurs ci-dessous.':''}</p>`:nothing}
   ${canAdd?this.picker(key,all,selected):nothing}
   ${this.draft?this.sensorSettings(key):nothing}
   ${key!=='indoor_temperature'&&!selected.length?html`<button class="link" @click=${()=>{this.clear(key);this.saved=labels[key]+' : laissé vide pour l’instant.';}}>Continuer sans</button>`:nothing}
  `,{count:key==='indoor_temperature'?'Obligatoire':selected.length?'Choisi':'Facultatif',help:help[key],className:this.exteriorDraft?'nk-setting-section nk-plain':'nk-field-section nk-plain'});
 }
 private go(stage:number){this.stage=stage;if(this.workspaceKey)this.path(this.workspaceKey+'/'+(roomSections.find(x=>x.stage===stage)?.path??'recapitulatif'));this.error='';this.saved='';this.updateComplete.then(()=>{this.renderRoot.querySelector<HTMLElement>('h1')?.focus();});}
 private next(){
  if(this.stage===0&&!this.draft?.sources.indoor_temperature){this.error='Choisissez la température de la pièce pour continuer. C’est la seule mesure obligatoire.';return;}
  if(this.stage===4){const s=this.draft!.settings;if(!this.draft!.name.trim()){this.error='Donnez un nom à la pièce.';return;}if(!Number.isFinite(s.minimum)||!Number.isFinite(s.maximum)||s.minimum>=s.maximum){this.error='La température minimum doit être inférieure au maximum.';return;}if(Number.isFinite(s.summer_maximum)&&s.summer_maximum<s.maximum){this.error='Le maximum d’été ne peut pas être inférieur à celui d’hiver.';return;}}
  this.go(roomOrder[roomOrder.indexOf(this.stage)+1]??5);
 }
 private async save(){
  const config=this.exteriorDraft?{sources:this.exteriorDraft,weather:this.weatherEntry}:this.draft;if(!config)return;
  const workspace=this.workspaceGeneration,entryId=this.entryId,isHome=!!this.exteriorDraft,revision=this.revision;this.busy=true;this.error='';
  try{const validated=await this.hass!.callWS<{warnings:{key:string;entity_id:string}[]}>({type:'niak_comfort/validate_config',config,home:isHome});if(workspace!==this.workspaceGeneration)return;const missing=validated.warnings.map(w=>warningId(w.key,w.entity_id)).filter(id=>!this.acknowledged.includes(id));
   if(missing.length&&!this.confirmed){this.error='Cochez « J’ai vérifié, je confirme mes choix » juste au-dessus pour enregistrer.';return;}
   this.acknowledged=[...new Set([...this.acknowledged,...missing])];
   const before=new Set(this.snapshot?.rooms.map(r=>r.entry_id));const wasRoom=!isHome;const edited=entryId;
   this.snapshot=await this.hass!.callWS<Snapshot>({type:'niak_comfort/save_config',config,home:isHome,revision,...(entryId?{entry_id:entryId}:{}),acknowledged:this.acknowledged});
   if(workspace!==this.workspaceGeneration)return;
   this.drafts.delete(this.workspaceKey);this.workspaceKey='';this.path('');this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;
   if(wasRoom){this.preview=edited??this.snapshot.rooms.find(r=>!before.has(r.entry_id))?.entry_id;this.previewEdited=!!edited;if(this.preview)this.path('apercu/'+this.preview);}
   this.saved=wasRoom?'':'L’extérieur est enregistré. Toutes vos pièces l’utilisent.';}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private number(key:string,label:string,initial:number,step=1){const d=this.draft!;return html`<label>${label}<input type="number" step=${step} .value=${String(d.settings[key]??initial)} @input=${(e:Event)=>this.draft={...d,settings:{...d.settings,[key]:Number((e.target as HTMLInputElement).value)}}}></label>`;}
 private floorName(){const d=this.draft!;const id=d.area_id?this.snapshot?.areas.find(a=>a.area_id===d.area_id)?.floor_id:d.floor_id;return this.snapshot?.floors?.find(f=>f.floor_id===id)?.name??'Non renseigné';}
 private preferences(){const d=this.draft!,used=new Set(this.snapshot!.rooms.filter(r=>r.entry_id!==this.entryId).map(r=>r.config.area_id));
  return html`${frame('La pièce',html`<label>Nom<input type="text" maxlength="100" .value=${d.name} @input=${(e:Event)=>this.draft={...d,name:(e.target as HTMLInputElement).value}}></label>
   <label>Pièce Home Assistant<select @change=${(e:Event)=>this.changeArea((e.target as HTMLSelectElement).value)}><option value="" ?selected=${!d.area_id}>Aucune (pièce libre)</option>${this.snapshot!.areas.filter(a=>!a.outdoor&&(!used.has(a.area_id)||a.area_id===d.area_id)).map(a=>html`<option value=${a.area_id} ?selected=${a.area_id===d.area_id}>${a.name}</option>`)}</select></label>
   ${d.area_id?html`<p>Étage : <strong>${this.floorName()}</strong></p><p class="hint">Repris de Home Assistant. Pour le modifier, changez l’étage de cette pièce dans Home Assistant.</p>`:html`<label>Étage (facultatif)<select @change=${(e:Event)=>this.draft={...d,floor_id:(e.target as HTMLSelectElement).value||null}}><option value="" ?selected=${!this.snapshot?.floors?.some(f=>f.floor_id===d.floor_id)}>Non renseigné</option>${(this.snapshot?.floors??[]).map(f=>html`<option value=${f.floor_id} ?selected=${d.floor_id===f.floor_id}>${f.name}</option>`)}</select></label>`}
   <p class="hint">Le suivi fonctionne aussi de plain-pied, sans étage à configurer.</p>
   <p class="hint">Rattacher la pièce permet à Niak de proposer ses capteurs. Vous pouvez toujours en choisir ailleurs.</p>`,{className:'nk-field-section nk-plain'})}
   ${this.sharedAir()}
   ${frame('Réglages avancés',html`
    <p class="hint">Choix de fonctionnement Niak, modifiables selon votre logement ; ces valeurs ne sont pas des normes sanitaires.</p>${this.number('gust_max','Rafales : ne rien laisser ouvert au-delà de (km/h)',45)}${this.number('frost','Gel : pas d’ouverture prolongée en dessous de (°C)',1,0.5)}${this.number('sun_facade','Soleil fort sur une façade (W/m²)',250,10)}${this.evolutionNumber('glazing_factor','Facteur estimé du vitrage (0 à 1)',0.7,0,1,0.05)}${this.number('illuminance_low','Luminosité basse (lux)',100)}${this.number('max_age_seconds','Ancienneté maximum des mesures (secondes)',10800)}<p class="hint">45 km/h de rafales et 1 °C : précautions Niak pour les ouvrants, à adapter à leur exposition. 250 W/m² : repère Niak de soleil fort sur la façade, estimé. 100 lux : repère de faible luminosité, sans déduction de position de volet. Facteur vitrage 0,7 : hypothèse de calcul de buée entre température extérieure (0) et intérieure (1), sans mesure du vitrage. 10 800 secondes : après 3 heures sans nouvelle mesure de l’appareil, une donnée numérique devient trop ancienne. Beaucoup de capteurs n’envoient une valeur que lorsqu’elle change ; une valeur stable reste donc valable. Cette expiration ne s’applique pas aux états de contacts.</p>`,{collapsible:true,open:false,count:changedAdvanced(d.settings)?`${changedAdvanced(d.settings)} sur ${Object.keys(advancedDefaults).length} modifiés`:'Par défaut'})}`;}
 /** Rooms with no wall or door between them share one air: their windows are common, their advice never opposite. */
 private sharedAir(){const d=this.draft!,others=this.snapshot!.rooms.filter(r=>r.entry_id!==this.entryId);if(!others.length)return nothing;
  const mine=d.open_to??[],theirs=(r:{config:RoomConfig})=>!!this.entryId&&(r.config.open_to??[]).includes(this.entryId);
  return frame('Même air',html`<p class="hint">Cochez les pièces ouvertes sur celle-ci, sans mur ni porte entre elles (un salon ouvert sur sa cuisine). Leurs fenêtres comptent pour les deux, et Niak ne donne jamais deux gestes contraires dans le même air.</p>
   ${others.map(r=>html`<label class="check"><input type="checkbox" .checked=${mine.includes(r.entry_id)||theirs(r)} ?disabled=${theirs(r)}
    @change=${(e:Event)=>{const on=(e.target as HTMLInputElement).checked;this.draft={...d,open_to:on?[...mine,r.entry_id]:mine.filter(x=>x!==r.entry_id)};}}>${r.title}${theirs(r)?' (déclaré depuis cette pièce)':''}</label>`)}`,{className:'nk-field-section nk-plain'});}
 private summary(){const d=this.draft!,home=this.snapshot!.home;const name=(key:string,id?:string)=>id?this.discovery?.candidates[key]?.find(v=>v.entity_id===id)?.name??id:'';
  const metas=d.windows.map(id=>d.openings[id]??defaultOpening());const counts=new Map<string,number>();for(const m of metas)if(m.exposure)counts.set(m.exposure,(counts.get(m.exposure)??0)+1);
  const expo=[...counts].map(([e,n])=>n+' '+exposures.find(x=>x[0]===e)![1].toLowerCase()).join(', ');const unknown=metas.filter(m=>!m.exposure).length,sheltered=metas.filter(m=>m.sheltered).length;
  const measures=[name('indoor_temperature',d.sources.indoor_temperature),name('indoor_humidity',d.sources.indoor_humidity)].filter(Boolean).join(' · ');
  return html`${frame('Récapitulatif',html`<dl class="summary compact"><dt>${stages[0]}</dt><dd>${measures||'—'}</dd>
   <dt>${stages[1]}</dt><dd>${d.windows.length?html`${d.windows.length} ${d.windows.length>1?'ouvrants':'ouvrant'}${sheltered?' · '+sheltered+' abrité'+(sheltered>1?'s':''):''}${expo?' · '+expo:''}${unknown?' · '+unknown+' sans exposition':''}<details><summary>Voir la liste</summary>${d.windows.map(id=>html`<div>${name('windows',id)}</div>`)}</details>`:'Aucun'}</dd>
   <dt>${stages[2]}</dt><dd>${['co2','pm25','voc','purifier','ventilation','ventilation_boost'].map(k=>name(k,d.sources[k])).filter(Boolean).join(' · ')||'Air non mesuré'}${d.presence?.length?' · '+d.presence.length+' capteur(s) de présence':''}</dd><dt>${stages[3]}</dt><dd>${name('heating',d.sources.heating)||'Non suivi'}</dd>
   <dt>${stages[4]}</dt><dd>${d.name} · ${d.area_id?'rattachée à « '+this.areaName(d.area_id)+' »':'pièce libre'} · étage : ${this.floorName()} · ${d.settings.minimum}–${d.settings.maximum} °C${(d.settings.summer_maximum??26)>d.settings.maximum?' (été '+(d.settings.summer_maximum??26)+' °C)':''}${d.heated===false?' · non chauffée':''}</dd>
   <dt>Extérieur</dt><dd>${home.configured?exteriorSummary(home.sources):'À configurer depuis Mon logement'}</dd></dl>`)}
   ${this.confirmBlock()}`;}
 private errorBlock(){return this.error?html`<p class="notice error" role="alert">${this.error}</p>`:nothing;}
 private wizard(){const d=this.draft!,section=roomSections.find(x=>x.stage===this.stage);return html`<div class="workspace-head"><button class="link" @click=${()=>this.cancel()}>← Vue d’ensemble Confort</button><h1 tabindex="-1">Configurer ${d.name||'la pièce'}</h1><p class="step-count">${d.area_id?'Pièce Home Assistant : '+this.areaName(d.area_id):'Pièce libre'} · Les réglages de cette pièce</p></div>
  <nav class="room-menu" aria-label="Réglages de la pièce">${[roomSections.slice(0,3),roomSections.slice(3)].map(row=>html`<div class="room-menu-row">${row.map(x=>html`<button aria-label=${x.title} title=${x.title} aria-current=${x.stage===this.stage?'page':nothing} @click=${()=>this.go(x.stage)}>${hubIcon(x.icon)}<span>${x.label}</span></button>`)}</div>`)}</nav>
  <div class="room-content-head"><h2>${section?.title??'Récapitulatif'}</h2></div>${this.intro(String(this.stage))}
  ${this.stage===0?[...indoor,'illuminance'].map(key=>this.field(key)):this.stage===1?this.field('windows'):this.stage===2?this.airPresence():this.stage===6?this.field('presence'):this.stage===3?this.field('heating'):this.stage===4?this.preferences():this.summary()}
  ${this.stage!==4&&this.stage!==5?html`<button class="link" ?disabled=${this.busy} @click=${()=>this.refreshCandidates()}>Rechercher à nouveau les capteurs</button>`:nothing}${this.errorBlock()}
  <div class="bottom"><button ?disabled=${this.busy} @click=${()=>this.stage?this.go(roomOrder[roomOrder.indexOf(this.stage)-1]??0):this.cancel()}>Retour</button><div>${this.stage!==5?html`<button ?disabled=${this.busy} @click=${()=>this.go(5)}>Récapitulatif</button>`:nothing}<button class="primary" ?disabled=${this.busy} @click=${()=>this.stage===5?this.save():this.next()}>${this.stage===5?'Enregistrer':'Continuer'}</button></div></div>${this.removeBlock()}`;}
 private exterior(){return html`<div class="actions"><button class="link" @click=${()=>this.cancel()}>← Mon logement</button></div><h1 tabindex="-1">Réglages généraux</h1><p class="muted">L’extérieur du logement, partagé par toutes vos pièces.</p>${this.intro('exterior')}${this.exteriorSource()}
  ${outdoorGroups.map(([title,keys])=>this.group(title,keys))}${this.airBlock()}${this.confirmBlock()}${this.errorBlock()}<div class="bottom"><button @click=${()=>this.cancel()}>Annuler</button><button class="primary" ?disabled=${this.busy} @click=${()=>this.save()}>Enregistrer l’extérieur</button></div>`;}
 private card(id:string){
  if(!customElements.get('niak-comfort-card'))return html`<p class="notice">L’aperçu de la carte apparaîtra après un rechargement de la page.</p>`;
  if(this.previewCard?.id!==id){const el=document.createElement('niak-comfort-card') as HTMLElement&{hass?:unknown;setConfig?:(c:object)=>void};el.setConfig?.({type:'custom:niak-comfort-card',entry_id:id,format:'full'});el.hass=this.hass;this.previewCard={id,el};}
  return this.previewCard!.el;
 }
 private previewScreen(){const s=this.snapshot!,room=s.rooms.find(r=>r.entry_id===this.preview);if(!room)return this.home();
  return html`<h1 tabindex="-1">${this.previewEdited?room.title+' : modifications enregistrées':room.title+' est prêt'}</h1><p>Voici sa carte confort, telle qu’elle apparaîtra sur votre tableau de bord. Les conseils se mettent à jour en quelques secondes.</p><div class="preview">${this.card(room.entry_id)}</div>
   <h2>Ajouter la carte à un tableau de bord</h2><ol class="howto"><li>Ouvrez votre tableau de bord, puis le crayon <strong>Modifier</strong>.</li><li><strong>Ajouter une carte</strong>, puis cherchez <strong>Niak Confort</strong>. Pour toutes les pièces d’un coup : <strong>Niak Confort · logement</strong>.</li><li>Choisissez la pièce <strong>${room.title}</strong> et enregistrez.</li></ol>
   ${!s.home.configured?html`<p class="notice">Pour comparer avec le dehors (fraîcheur, pluie, vent, soleil), configurez maintenant l’extérieur du logement.</p>`:nothing}
   <div class="actions">${!s.home.configured?html`<button class="primary" @click=${()=>this.editExterior()}>Configurer l’extérieur</button>`:nothing}<button class=${s.home.configured?'primary':''} @click=${()=>{this.preview=undefined;this.path('');}}>Retour à Mon logement</button></div>`;}
 private foundRooms(){const list=this.overview!;const n=this.picked.length;
  return html`<section class="start"><h2>Vos pièces trouvées</h2><p>Niak a cherché dans vos pièces Home Assistant. Décochez celles à ne pas suivre : vous pourrez tout retoucher ensuite, pièce par pièce.</p>
   <div class="found">${list.map(a=>{const ok=typeof a.suggestions.indoor_temperature==='string';return html`<div class="found-row"><label class="check"><input type="checkbox" ?disabled=${!ok} .checked=${this.picked.includes(a.area_id)} @change=${(e:Event)=>{const on=(e.target as HTMLInputElement).checked;this.picked=on?[...this.picked,a.area_id]:this.picked.filter(x=>x!==a.area_id);}}><span><strong>${a.name}</strong><span class="hint">${ok?this.detected(a.suggestions):a.temperatures>1?'Plusieurs températures : à choisir':'Aucune température trouvée'}</span></span></label>${ok?nothing:html`<button @click=${()=>this.start(a)}>Configurer</button>`}</div>`;})}</div>
   ${this.errorBlock()}<button class="primary" ?disabled=${this.busy||!n} @click=${()=>this.createAll()}>${n?`Créer ${n>1?'les '+n+' pièces':'la pièce'}`:'Cochez une pièce'}</button></section>`;}
 private home(){const s=this.snapshot!;const used=new Set(s.rooms.map(r=>r.config.area_id).filter((a):a is string=>!!a));const living=livingArea(s.areas,used);const areas=s.areas.filter(a=>!a.outdoor&&!used.has(a.area_id)&&(s.rooms.length||a!==living));
  return html`
  <h1>Pièces du logement</h1><p class="muted">Vos pièces et les mesures qui aident Niak à expliquer leur confort. Aucun équipement n’est commandé.</p>
  ${!s.rooms.length&&this.overview?.some(a=>typeof a.suggestions.indoor_temperature==='string')?this.foundRooms():!s.rooms.length?html`<section class="start"><h2>Commençons par le Salon</h2>${living?html`<p>Niak a trouvé la pièce « ${living.name} » dans Home Assistant. Il vous proposera ses capteurs ; vous gardez, retirez ou complétez.</p><button class="primary" @click=${()=>this.start(living)}>Configurer le Salon</button>`:html`<p>Aucune pièce « Salon » dans Home Assistant : Niak crée une pièce libre et vous choisissez ses capteurs.</p><button class="primary" @click=${()=>this.start(null,'Salon')}>Créer le Salon</button>`}</section>`:html`<div class="room-list">${s.rooms.map(room=>html`<section class="room"><div><h3>${room.title}</h3><p class="hint">${coverage(room.config)}${room.config.area_id?'':' · pièce libre'}</p>${!room.loaded?html`<p class="warning hint">Le calcul de cette pièce n’est pas chargé. Vérifiez ses capteurs et les journaux de l’intégration.</p>`:nothing}</div><button ?disabled=${this.busy} @click=${()=>this.editRoom(room)}>Configurer</button></section>`)}</div>`}
  ${frame(s.rooms.length?'Ajouter une pièce':this.overview?'Une pièce sans pièce Home Assistant ?':'Ou commencer par une autre pièce',html`${areas.length&&!(this.overview&&!s.rooms.length)?html`<p class="hint">Vos pièces Home Assistant : Niak proposera leurs capteurs.</p><div class="area-buttons">${areas.map(a=>html`<button @click=${()=>this.start(a)}>${a.name}</button>`)}</div>`:nothing}
   <form class="free" @submit=${(e:Event)=>{e.preventDefault();void this.start(null,this.freeName);}}><label>Pièce libre, sans pièce Home Assistant<input type="text" maxlength="100" placeholder="Par exemple : Étage" .value=${this.freeName} @input=${(e:Event)=>this.freeName=(e.target as HTMLInputElement).value}></label><button type="submit">Créer</button></form>`)}
  ${s.rooms.length?html`${frame('Les cartes',html`<p>Dans un tableau de bord : <strong>Ajouter une carte</strong>, puis <strong>Niak Confort</strong> pour une pièce, ou <strong>Niak Confort · logement</strong> pour la synthèse de toutes les pièces.</p>`)}`:nothing}${this.health?html`${this.health.todo.length?frame('À régler',html`<ul class="hl-lines">${this.health.todo.map(l=>this.hline(l))}</ul>`,{className:'todo'}):nothing}${this.health.tips.length?frame('À améliorer',html`<ul class="hl-lines">${this.health.tips.map(l=>this.hline(l))}</ul>`):nothing}<details class="health-details"><summary>Sources, conseils et état du logement</summary>${this.healthPage(true)}</details>`:this.healthError?html`<p class="notice" role="alert">Le bilan technique n’a pas pu être chargé. <button @click=${()=>void this.loadHealth()}>Réessayer</button></p>`:html`<p class="muted" role="status">Actualisation du bilan…</p>`}`;}
 protected render(){if(this.hass?.user?.is_admin===false)return html`<main><h1>Niak Confort</h1><p>La configuration du logement est réservée aux administrateurs Home Assistant.</p></main>`;
  const editing=!!(this.draft||this.exteriorDraft);
  // Inside the shared « Niak » panel, its header and tabs replace this one.
  const header=this.hasAttribute('embedded')?nothing:html`<header><button aria-label="Ouvrir le menu Home Assistant" @click=${()=>this.menu()}><span class="menu-icon"></span></button><strong>Niak Confort</strong></header>`;
  return html`${header}<main>${this.confirmDiscard?html`<section class="notice" role="alertdialog" aria-label="Abandonner le brouillon"><h2>Quitter sans enregistrer ?</h2><p>Vos choix de cette page seront perdus.</p><div class="actions"><button @click=${()=>this.confirmDiscard=false}>Continuer la configuration</button><button @click=${()=>this.discard()}>Quitter sans enregistrer</button></div></section>`:nothing}
   ${!editing?html`${this.errorBlock()}${this.error&&!this.snapshot?html`<button @click=${()=>this.load()}>Réessayer</button>`:nothing}`:nothing}${this.saved?html`<p class="notice success" role="status">${this.saved}</p>`:nothing}${this.busy&&!this.snapshot?html`<p class="loading" role="status">Chargement de votre logement…</p>`:nothing}
   ${this.snapshot?(this.exteriorDraft?this.exterior():this.draft?this.wizard():this.preview?this.previewScreen():this.page==='health'&&this.snapshot.rooms.length?this.healthScreen():this.home()):nothing}${this.busy&&this.snapshot?html`<p class="busy" role="status">Un instant…</p>`:nothing}</main>`;
 }
}
