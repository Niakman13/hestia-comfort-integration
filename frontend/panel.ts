import {LitElement,html,unsafeCSS,nothing,type PropertyValues} from 'lit';
import {customElement,property,state} from 'lit/decorators.js';
import styles from './styles.css';
import {labels,indoor,outdoor,measurement,newRoom,coverage,warningText,warningId,type Candidate,type Discovery,type Snapshot,type Hass,type Room,type RoomConfig,type Spec} from './model';
const stages=['Intérieur','Extérieur','Fenêtres','Chauffage','Préférences','Récapitulatif'];
const help:Record<string,string>={indoor_temperature:'Choisissez une mesure de l’air de cette pièce. La température d’un appareil ou du sol d’une plante peut être différente.',indoor_humidity:'Aide à repérer un besoin de réduire l’humidité. Vous pouvez continuer sans cette mesure.',co2:'Aide à repérer un besoin de renouvellement d’air. Ce capteur ne mesure pas tous les polluants.',windows:'Choisissez seulement les fenêtres ou portes qui donnent sur l’extérieur. Les portes de meubles ou d’appareils ne conviennent pas.',heating:'Permet d’observer si le chauffage fonctionne réellement. Niak ne commande aucun équipement.',outdoor_temperature:'Permet de savoir si ouvrir peut rafraîchir ou refroidir la pièce.',outdoor_humidity:'Avec les températures et l’humidité intérieure, permet de comparer l’eau contenue dans l’air.',rain:'Une intensité en mm/h ou in/h indique la pluie actuelle. Un cumul de la journée ou une prévision ne dit pas s’il pleut maintenant.',pollution:'L’indice ATMO du jour apporte une précaution régionale. Il est distinct d’une mesure actuelle à vos fenêtres et des capteurs d’air intérieur.'};
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
 @state() private picker='';
 @state() private search='';
 @state() private showElsewhere=false;
 @state() private acknowledged:string[]=[];
 @state() private advanced=false;
 @state() private confirmDiscard=false;
 private generation=0;
 private connection?:unknown;
 private routeHandled='';
 private revision='';
 private beforeUnload=(e:BeforeUnloadEvent)=>{if(this.draft||this.exteriorDraft){e.preventDefault();e.returnValue='';}};
 connectedCallback(){super.connectedCallback();window.addEventListener('beforeunload',this.beforeUnload);}
 disconnectedCallback(){super.disconnectedCallback();this.generation++;window.removeEventListener('beforeunload',this.beforeUnload);}
 protected updated(changed:PropertyValues){
  this.setAttribute('data-theme',this.hass?.themes?.darkMode===false?'light':'dark');
  if(changed.has('hass')&&this.hass?.connection!==this.connection){this.connection=this.hass?.connection;void this.load();}
  if(changed.has('route')&&this.snapshot&&!this.draft&&!this.exteriorDraft)void this.followRoute();
 }
 private async load(){
  if(!this.hass)return;const generation=++this.generation;this.busy=true;this.error='';
  try{const value=await this.hass.callWS<Snapshot>({type:'niak_comfort/configuration'});if(generation===this.generation){this.snapshot=value;await this.followRoute();}}
  catch(e){if(generation===this.generation)this.error=this.message(e);}
  finally{if(generation===this.generation)this.busy=false;}
 }
 private message(e:unknown){return typeof e==='object'&&e&&'message' in e?String(e.message):'La connexion est indisponible. Réessayez sans quitter votre brouillon.';}
 private async followRoute(){const path=this.route?.path??'';if(this.routeHandled===path)return;this.routeHandled=path;const id=path.split('/').filter(Boolean)[0];const room=this.snapshot?.rooms.find(r=>r.entry_id===id);if(room)await this.editRoom(room);}
 private menu(){this.dispatchEvent(new CustomEvent('hass-toggle-menu',{bubbles:true,composed:true}));}
 private async discover(area_id?:string,entry_id?:string){
  return await this.hass!.callWS<Discovery>({type:'niak_comfort/discover',...(area_id?{area_id}:{}),...(entry_id?{entry_id}:{})});
 }
 private async start(area_id:string){
  const area=this.snapshot?.areas.find(a=>a.area_id===area_id);if(!area)return;
  this.busy=true;this.error='';this.saved='';
  try{const d=await this.discover(area_id);this.discovery=d;this.revision=d.revision;this.entryId=undefined;this.draft=newRoom(area,d,!!this.snapshot?.home.configured);this.stage=0;this.acknowledged=[];this.picker='';}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async editRoom(room:Room){
  this.busy=true;this.error='';this.saved='';
  try{const d=await this.discover(room.config.area_id,room.entry_id);this.discovery=d;this.revision=d.revision;this.entryId=room.entry_id;this.draft=structuredClone(room.config);this.draft.use_home??=false;this.draft.rain_exposed??=true;this.stage=0;this.acknowledged=[];this.picker='';}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async editExterior(){
  this.busy=true;this.error='';this.saved='';
  try{const d=await this.discover();this.discovery=d;this.revision=d.revision;this.exteriorDraft=structuredClone(this.snapshot!.home.sources);this.acknowledged=[];this.picker='';}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private async refreshCandidates(){
  this.busy=true;this.error='';
  try{const d=await this.discover(this.draft?.area_id,this.entryId);if(d.revision!==this.revision){this.error='La configuration a changé ailleurs. Votre brouillon est conservé ; revenez aux pièces et rechargez avant d’enregistrer.';return;}this.discovery=d;this.saved='La liste des capteurs a été actualisée. Vos choix restent inchangés.';}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private cancel(){if(this.draft||this.exteriorDraft){this.confirmDiscard=true;return;}this.discard();}
 private discard(){this.confirmDiscard=false;this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.entryId=undefined;this.picker='';this.error='';this.acknowledged=[];}
 private selected(key:string):string[]{if(this.exteriorDraft)return this.exteriorDraft[key]?[this.exteriorDraft[key].entity_id]:[];if(!this.draft)return [];return key==='windows'?this.draft.windows:this.draft.sources[key]?[this.draft.sources[key]]:[];}
 private choose(key:string,c:Candidate){
  if(this.exteriorDraft){this.exteriorDraft={...this.exteriorDraft,[key]:{entity_id:c.entity_id,adapter:c.adapter,...(c.adapter==='atmo_daily'?{block_from:4}:{})}};}
  else if(this.draft){if(key==='windows'){this.draft={...this.draft,windows:[...new Set([...this.draft.windows,c.entity_id])]};}else this.draft={...this.draft,sources:{...this.draft.sources,[key]:c.entity_id}};}
  this.acknowledged=this.acknowledged.filter(id=>!id.startsWith(key+':'));this.picker='';this.error='';
 }
 private clear(key:string,id?:string){
  if(this.exteriorDraft){const next={...this.exteriorDraft};delete next[key];this.exteriorDraft=next;}
  else if(this.draft){if(key==='windows')this.draft={...this.draft,windows:this.draft.windows.filter(e=>e!==id)};else{const next={...this.draft.sources};delete next[key];this.draft={...this.draft,sources:next};}}
  this.acknowledged=this.acknowledged.filter(v=>v!==warningId(key,id??''));
 }
 private ack(id:string,on:boolean){this.acknowledged=on?[...new Set([...this.acknowledged,id])]:this.acknowledged.filter(v=>v!==id);}
 private warnings(c:Candidate,key:string,selected:boolean){return html`${c.warnings.filter(w=>!(w==='derived'&&c.warnings.includes('alias'))).map(w=>html`<p class="warning hint">${warningText[w]??'Source à vérifier.'}</p>`)}${c.provenance.length>1?html`<p class="provenance">Origine de la mesure : ${c.provenance.map((p,i)=>html`${i?' → ':nothing}${p.name}${p.area_id?` (${this.snapshot?.areas.find(a=>a.area_id===p.area_id)?.name??p.area_id})`:nothing}`)}</p>`:nothing}${selected&&c.warnings.length?html`<label class="check"><input type="checkbox" .checked=${this.acknowledged.includes(warningId(key,c.entity_id))} @change=${(e:Event)=>this.ack(warningId(key,c.entity_id),(e.target as HTMLInputElement).checked)}>J’ai vérifié la provenance et le rôle de ce capteur ; je souhaite l’utiliser ici.</label>`:nothing}`;}
 private candidateRow(c:Candidate,key:string){return html`<div class="candidate"><div><strong>${c.name}</strong><p>${measurement(c)} · ${this.snapshot?.areas.find(a=>a.area_id===c.area_id)?.name??'Pièce non affectée'}${c.reference?' · référence Home Assistant':nothing}</p>${this.warnings(c,key,false)}</div><button @click=${()=>this.choose(key,c)}>Utiliser</button></div>`;}
 private field(key:string){
  const all=this.discovery?.candidates[key]??[],selected=this.selected(key);
  const local=all.filter(c=>c.local),visible=this.exteriorDraft?all:local;
  const available=visible.filter(c=>!selected.includes(c.entity_id));
  return html`<section class="field" aria-label=${labels[key]}><div class="field-top"><h3>${labels[key]}</h3><span>${key==='indoor_temperature'?'Nécessaire':'Facultatif'}</span></div><p class="hint">${help[key]}</p>
   ${selected.map(id=>{const c=all.find(x=>x.entity_id===id);return html`<div class="choice"><strong>${c?.name??id}</strong><span>${c?measurement(c):'Source indisponible ou incompatible · à remplacer'}</span>${!this.entryId&&!this.exteriorDraft?html`<span>Proposition Niak · à confirmer avant d’enregistrer</span>`:nothing}${c?.reference?html`<span>Référence définie pour cette pièce dans Home Assistant</span>`:nothing}${c?this.warnings(c,key,true):nothing}<button class="link" @click=${()=>this.clear(key,id)}>Retirer ce choix</button></div>`;})}
   ${!selected.length?html`<p class="notice">${available.length===0?'Aucun capteur compatible trouvé'+(this.exteriorDraft?' pour cette information.':' dans cette pièce.'):available.length===1?'Une proposition à vérifier.':'Plusieurs capteurs possibles : choisissez celui qui représente cette pièce.'}</p>`:nothing}
   ${available.length?html`<div class="candidates">${available.slice(0,6).map(c=>this.candidateRow(c,key))}${available.length>6?html`<p class="hint">${available.length-6} autres candidats : utilisez la recherche.</p>`:nothing}</div>`:nothing}
   <div class="actions"><button @click=${()=>{this.picker=this.picker===key?'':key;this.search='';this.showElsewhere=!!this.exteriorDraft;}}>${this.exteriorDraft?'Choisir une autre source':'Choisir dans cette pièce ou ailleurs'}</button>${key!=='indoor_temperature'&&key!=='windows'&&selected.length===0?html`<button class="link" @click=${()=>{this.clear(key);this.picker='';this.saved=labels[key]+' laissé non configuré dans ce brouillon.';}}>Continuer sans cette mesure</button>`:nothing}</div>
   ${this.picker===key?html`<div class="searched"><label>Rechercher un capteur<input type="search" .value=${this.search} @input=${(e:Event)=>this.search=(e.target as HTMLInputElement).value}></label>${!this.exteriorDraft?html`<label class="check"><input type="checkbox" .checked=${this.showElsewhere} @change=${(e:Event)=>this.showElsewhere=(e.target as HTMLInputElement).checked}>Afficher aussi les capteurs des autres pièces</label>`:nothing}<div class="search-results">${all.filter(c=>(this.exteriorDraft||this.showElsewhere||c.local)&&!selected.includes(c.entity_id)&&(c.name+' '+c.entity_id).toLowerCase().includes(this.search.toLowerCase())).map(c=>this.candidateRow(c,key))}</div><button @click=${()=>this.picker=''}>Fermer la recherche</button></div>`:nothing}
   ${this.exteriorDraft?.[key]?.adapter==='atmo_daily'?html`<label>Appliquer ma précaution à partir du niveau<select .value=${String(this.exteriorDraft[key].block_from??4)} @change=${(e:Event)=>{this.exteriorDraft={...this.exteriorDraft!,[key]:{...this.exteriorDraft![key],block_from:Number((e.target as HTMLSelectElement).value)}};}}>${['Moyen','Dégradé','Mauvais','Très mauvais','Extrêmement mauvais'].map((label,i)=>html`<option value=${i+2}>${label}</option>`)}</select></label><p class="hint">C’est votre préférence de prudence, pas une consigne sanitaire ni une mesure instantanée. Un indice favorable ne suffit pas à confirmer une ouverture.</p>`:nothing}
  </section>`;
 }
 private go(stage:number){this.stage=stage;this.picker='';this.error='';this.saved='';this.updateComplete.then(()=>this.renderRoot.querySelector<HTMLElement>('h1')?.focus());}
 private async next(){if(this.stage===0&&!this.draft?.sources.indoor_temperature){this.error='Choisissez la température intérieure, ou revenez aux pièces pour configurer celle-ci plus tard.';return;}if(this.stage===4){const minimum=this.draft?.settings.minimum,maximum=this.draft?.settings.maximum;if(!Number.isFinite(minimum)||!Number.isFinite(maximum)||minimum!>=maximum!){this.error='La température minimum doit être inférieure au maximum.';return;}}this.go(this.stage+1);}
 private async save(){
  const config=this.exteriorDraft?{sources:this.exteriorDraft}:this.draft;if(!config)return;
  this.busy=true;this.error='';
  try{const validated=await this.hass!.callWS<{warnings:{key:string;entity_id:string}[]}>({type:'niak_comfort/validate_config',config,home:!!this.exteriorDraft});const missing=validated.warnings.filter(w=>!this.acknowledged.includes(warningId(w.key,w.entity_id)));if(missing.length){this.error='Vérifiez et confirmez les capteurs signalés : '+missing.map(w=>labels[w.key]).join(', ');return;}
   this.snapshot=await this.hass!.callWS<Snapshot>({type:'niak_comfort/save_config',config,home:!!this.exteriorDraft,revision:this.revision,...(this.entryId?{entry_id:this.entryId}:{}),acknowledged:this.acknowledged});this.draft=undefined;this.exteriorDraft=undefined;this.discovery=undefined;this.saved='Configuration enregistrée. Les conseils utiliseront ces choix.';}
  catch(e){this.error=this.message(e);}finally{this.busy=false;}
 }
 private preferences(){const d=this.draft!;return html`<section class="field"><h2>Votre plage de confort</h2><p>Choisissez les températures dans lesquelles vous vous sentez bien.</p>${(['minimum','maximum'] as const).map(key=>html`<label>${key==='minimum'?'Température minimum':'Température maximum'} (°C)<input type="number" min="5" max="40" step="0.5" .value=${String(d.settings[key]??(key==='minimum'?20:24))} @input=${(e:Event)=>this.draft={...d,settings:{...d.settings,[key]:Number((e.target as HTMLInputElement).value)}}}></label>`)}<button class="link" aria-expanded=${this.advanced} @click=${()=>this.advanced=!this.advanced}>${this.advanced?'Masquer':'Afficher'} les réglages avancés</button>${this.advanced?html`<p class="hint">Ces réglages modifient les seuils et la sensibilité du calcul. Les valeurs initiales ne sont pas des références sanitaires.</p>${Object.entries({humidity_high:['Humidité haute (%)',62],co2_potential:['CO₂ : potentiel (ppm)',1000],co2_action:['CO₂ : conseil (ppm)',1200],co2_urgent:['CO₂ : attention (ppm)',1600],max_age_seconds:['Ancienneté maximum des mesures (secondes)',1800]}).map(([key,[label,initial]])=>html`<label>${label}<input type="number" .value=${String(d.settings[key]??initial)} @input=${(e:Event)=>this.draft={...d,settings:{...d.settings,[key]:Number((e.target as HTMLInputElement).value)}}}></label>`)}`:nothing}</section>`;}
 private summary(){const d=this.draft!;return html`<p>Vérifiez les sources et ce que Niak pourra analyser avant d’enregistrer.</p><dl class="summary">${[...indoor,'windows','heating'].map(key=>html`<dt>${labels[key]}</dt><dd>${this.selected(key).length?this.selected(key).map(id=>{const c=this.discovery?.candidates[key]?.find(v=>v.entity_id===id);return html`<div>${c?.name??id} · ${c?measurement(c):'Source à vérifier'}${c?this.warnings(c,key,true):nothing}</div>`;}):'Non configuré'}</dd>`)}<dt>Données extérieures</dt><dd>${d.use_home?'Données communes du logement':(outdoor.some(key=>d.sources[key])?'Sources propres à cette pièce, conservées':'Non configurées · à compléter depuis Mon logement')} · ${d.rain_exposed?'ouvrants exposés à la pluie':'ouvrants déclarés à l’abri de la pluie'}</dd><dt>Préférences</dt><dd>${d.settings.minimum}–${d.settings.maximum} °C</dd></dl><div class="notice"><p>Niak suivra la température de ${d.name}${d.sources.co2?' et le CO₂ choisi':''}. ${!d.windows.length?'Sans contacts, il ne saura pas si vos fenêtres sont ouvertes.':''}</p><p>Les conditions extérieures non mesurées resteront à vérifier avant d’ouvrir. Aucun équipement ne sera commandé.</p></div>`;}
 private wizard(){const d=this.draft!;return html`<div class="actions"><button class="link" @click=${()=>this.cancel()}>Revenir à Mon logement</button></div><h1 tabindex="-1">${this.entryId?'Modifier':'Configurer'} ${d.name}</h1><p class="step-count">Étape ${this.stage+1} sur ${stages.length} · ${stages[this.stage]}</p><button class="link" @click=${()=>this.refreshCandidates()}>Rechercher à nouveau les capteurs</button><nav class="steps" aria-label="Catégories de configuration">${stages.map((label,i)=>html`<button aria-current=${i===this.stage?'step':'false'} @click=${()=>this.go(i)}>${label}</button>`)}</nav>
  ${this.stage===0?html`${indoor.map(key=>this.field(key))}`:this.stage===1?html`<h2>Les conditions autour de votre logement</h2>${this.snapshot?.home.configured?html`<label class="check"><input type="checkbox" .checked=${!!d.use_home} @change=${(e:Event)=>this.draft={...d,use_home:(e.target as HTMLInputElement).checked}}>Utiliser les données extérieures communes du logement</label>`:html`<p class="notice">Les données communes ne sont pas encore configurées. Vous pouvez terminer cette pièce, puis ouvrir « Données extérieures » depuis Mon logement.</p>`}<p class="hint">${d.use_home?'Les changements des données communes s’appliqueront à cette pièce.':(outdoor.some(key=>d.sources[key])?'Les sources extérieures existantes de cette pièce sont conservées.':'Vous pourrez choisir les données extérieures depuis Mon logement après cette pièce.')}</p><label class="check"><input type="checkbox" .checked=${d.rain_exposed!==false} @change=${(e:Event)=>this.draft={...d,rain_exposed:(e.target as HTMLInputElement).checked}}>Mes fenêtres ou portes extérieures peuvent recevoir la pluie</label><p class="hint">Décochez seulement si tous les ouvrants suivis sont à l’abri de la pluie. Cette déclaration ne mesure ni le vent ni les projections.</p>`:this.stage===2?this.field('windows'):this.stage===3?this.field('heating'):this.stage===4?this.preferences():this.summary()}
  <div class="bottom"><button @click=${()=>this.stage?this.go(this.stage-1):this.cancel()}>Retour</button><div>${this.stage>0&&this.stage<5?html`<button @click=${()=>this.go(this.stage+1)}>Configurer plus tard</button>`:nothing}<button class="primary" ?disabled=${this.busy} @click=${()=>this.stage===5?this.save():this.next()}>${this.stage===5?'Enregistrer':'Continuer'}</button></div></div>`;}
 private home(){const s=this.snapshot!;const configured=new Set(s.rooms.map(r=>r.config.area_id)),areas=s.areas.filter(a=>!configured.has(a.area_id));return html`<h1>Mon logement</h1><p class="muted">Retrouvez vos pièces et les données qui aident Niak à expliquer leur confort. Aucun équipement n’est commandé.</p>
 ${!s.rooms.length?html`<section><h2>Commençons par le Salon</h2><p>Niak recherchera les mesures associées à votre pièce. Vous pourrez vérifier les propositions, les remplacer ou compléter plus tard.</p>${areas.find(a=>a.name.toLowerCase()==='salon')?html`<button class="primary" @click=${()=>this.start(areas.find(a=>a.name.toLowerCase()==='salon')!.area_id)}>Configurer le Salon</button>`:nothing}</section>`:nothing}
 <h2>Vos pièces</h2>${s.rooms.map(room=>html`<section class="room"><div><h3>${room.title}</h3><p class="hint">${coverage(room.config)}</p>${!room.loaded?html`<p class="warning hint">Le calcul de cette pièce n’est pas chargé. Vérifiez ses sources et les journaux de l’intégration.</p>`:nothing}</div><button @click=${()=>this.editRoom(room)}>Modifier ${room.title}</button></section>`)}
 ${areas.length?html`<section class="field"><h3>${s.rooms.length?'Ajouter une pièce':'Ou choisir une autre pièce'}</h3><p class="hint">Les pièces proviennent de Home Assistant. Les sources disponibles seront proposées avant votre confirmation.</p><div class="area-buttons">${areas.map(a=>html`<button @click=${()=>this.start(a.area_id)}>Ajouter ${a.name}</button>`)}</div></section>`:html`<p>Toutes vos pièces Home Assistant sont déjà configurées.</p>`}
 <section class="field"><h2>Les données extérieures du logement</h2><p>Choisissez une fois les températures, l’humidité, la pluie et la qualité de l’air. Chaque pièce pourra utiliser ces données communes.</p><p class="hint">${s.home.configured?Object.keys(s.home.sources).length+' information(s) configurée(s)':'À configurer · les choix actuels des pièces sont conservés'}</p><button @click=${()=>this.editExterior()}>${s.home.configured?'Modifier':'Configurer'} les données extérieures</button></section>`;}
 protected render(){if(this.hass?.user?.is_admin===false)return html`<main><h1>Niak Confort</h1><p>La configuration du logement est réservée aux administrateurs Home Assistant.</p></main>`;
  return html`<header><button aria-label="Ouvrir le menu Home Assistant" @click=${()=>this.menu()}><span class="menu-icon"></span></button><strong>Niak Confort</strong></header><main>${this.confirmDiscard?html`<section class="notice" role="alertdialog" aria-label="Abandonner le brouillon" aria-modal="false"><h2>Abandonner ce brouillon ?</h2><p>Aucun changement ne sera enregistré.</p><div class="actions"><button @click=${()=>this.confirmDiscard=false}>Continuer la configuration</button><button @click=${()=>this.discard()}>Abandonner le brouillon</button></div></section>`:nothing}${this.error?html`<p class="notice error" role="alert">${this.error}</p>${!this.draft&&!this.exteriorDraft?html`<button @click=${()=>this.load()}>Réessayer</button>`:nothing}`:nothing}${this.saved?html`<p class="notice success" role="status">${this.saved}</p>`:nothing}${this.busy?html`<p class="loading" role="status">${this.snapshot?'Vérification en cours…':'Chargement des pièces et de la configuration…'}</p>`:nothing}${!this.busy&&this.snapshot?(this.exteriorDraft?html`<button class="link" @click=${()=>this.cancel()}>Retour à Mon logement</button><h1>Les données extérieures</h1><p>Ces choix seront communs aux pièces qui utilisent les données du logement. Vos autres pièces garderont leurs sources actuelles.</p>${outdoor.map(key=>this.field(key))}<div class="bottom"><button @click=${()=>this.cancel()}>Annuler</button><button class="primary" @click=${()=>this.save()}>Enregistrer les données extérieures</button></div>`:this.draft?this.wizard():this.home()):nothing}</main>`;
 }
}
