import {html,nothing} from 'lit';
import type {Config,View,Module} from '../types';
import {windFrom,numeric,number,summary,needs,levelLabels,heatingLabels,sourceLabels,constraintLabels,exposureLabels,kindLabels,coverageText,readingStatus,sourceLabel,evolutionLines,co2Metric,solarMetric} from '../view';
import {icon} from '../ui/icons';
export interface Controls {why:boolean;sources:boolean;toggleWhy:()=>void;toggleSources:()=>void;uid:string}
export const moduleLabels:Record<Module,string>={windows:'Fenêtres',air:'Qualité de l’air',temperature:'Température',humidity:'Humidité',shutters:'Soleil et volets',coordination:'Lien chauffage'};
function contactState(v:View) {
  const contacts=Object.entries(v.observations).filter(([k])=>k.startsWith('window:')).map(([,r])=>r);
  const opened=contacts.filter(r=>r.quality==='valid'&&r.value===true).length;
  const known=contacts.filter(r=>r.quality==='valid'&&typeof r.value==='boolean').length;
  return {opened,known,total:contacts.length,label:!contacts.length?'Ouverture non mesurée':known<contacts.length?`${opened} ouverte${opened>1?'s':''} · contacts incomplets`:opened?`${opened} ouverte${opened>1?'s':''}`:'Fenêtres fermées'};
}
export function why(v:View,c:Controls) {
  return html`<section class="explanation" id=${'why-'+c.uid} ?hidden=${!c.why}><h3>Pourquoi ce conseil ?</h3>
    <div class="reason-row"><strong>Les besoins</strong><p>${v.assessment.needs.length?v.assessment.needs.map(n=>needs[n]??n).join(' · '):'Aucun besoin prioritaire parmi les mesures connues. Les polluants non mesurés restent inconnus.'}</p></div>
    <div class="reason-row"><strong>Les contraintes</strong><p>${v.assessment.constraints.map(n=>constraintLabels[n]??n).join(' · ')||'Aucune contrainte confirmée ; cela ne certifie pas les sources absentes.'}</p></div>
    <div class="reason-row"><strong>Le bilan</strong><p>${coverageText(v)}. Les besoins confirmés restent visibles ; les informations non mesurées restent inconnues.</p></div>
  </section>`;
}
export function sources(v:View,c:Controls) {
  return html`<section class="sources" id=${'sources-'+c.uid} ?hidden=${!c.sources}><h3>Les données derrière le conseil</h3><dl>
    ${Object.entries(v.observations).map(([k,r])=>html`<dt>${sourceLabel(v,k)} · ${readingStatus(r)}</dt><dd>${r.source??'Source non configurée'}${r.received_at?` · reçu le ${new Date(r.received_at).toLocaleString('fr-FR')}`:''}${r.quality!=='valid'?' · exclu des mesures actuelles':''}</dd>`)}
    ${Object.keys(sourceLabels).filter(k=>!v.observations[k]).map(k=>html`<dt>${sourceLabels[k]??k}</dt><dd>Non configuré</dd>`)}
  </dl><p class="truth">La publication d’un conseil ne rajeunit pas ses sources. Les heures indiquent la réception par Home Assistant, pas forcément l’instant physique de mesure.</p></section>`;
}
export function hero(v:View,config:Config,c:Controls) {
  const [title,text]=summary(v),w=contactState(v),a=v.assessment;
  return html`<div class="hero"><div class="hero-head"><h2>${config.title||`Confort · ${v.title}`}</h2><span class="source-chip">${icon('home')}${v.title}</span></div>
    <div class="hero-text"><span class="status">${icon(a.action==='ouvrir'?'open':a.action==='ok'?'check':a.action==='unknown'?'info':'alert')}${levelLabels[a.level]}</span><h3>${title}</h3><p>${text}</p>${a.action==='ouvrir'&&a.open_first?.length?html`<p class="open-first">${icon('open')}Ouvrez ${a.open_first.map(id=>{const o=(a.openings??[]).find(x=>x.entity_id===id);return (v.names?.[id]??id)+(o?.wind_side==='windward'?' (au vent)':o?.wind_side==='leeward'?' (sous le vent)':'');}).join(' et ')}.</p>`:nothing}${(a.action==='ouvrir'||a.action==='ok')&&a.unverified?.length?html`<p class="unverified">${icon('info')}${a.unverified.map(k=>k==='rain'?'Pluie':'Qualité de l’air dehors').join(' et ')} non suivie${a.unverified.length>1?'s':''} : vérifiez avant d’ouvrir.</p>`:nothing}
    </div><div class="window-scene" aria-hidden="true"><div class="window-disk">${icon(a.action==='ouvrir'||w.opened?'open':'window')}</div>${w.opened?html`<div class="air-stream"><i></i><i></i><i></i></div>`:nothing}<span>${w.label}</span></div>
      <div class="hero-actions wide"><button @click=${c.toggleWhy} aria-expanded=${c.why} aria-controls=${'why-'+c.uid}>${icon('info')}Pourquoi ?</button><button @click=${c.toggleSources} aria-expanded=${c.sources} aria-controls=${'sources-'+c.uid}>${icon('source')}Les sources</button></div>
  </div>`;
}
type MetricState='need'|'alert'|'ok'|'off';
function metric(ic:string,label:string,value:string,unit:string,note:string,state:MetricState,tone:string) {
  return html`<div class="metric" data-state=${state} style=${'--tone:var(--'+tone+')'}><span class="metric-head">${icon(ic)}${label}</span><strong>${value}${unit?html`<small>${unit}</small>`:nothing}</strong><span class="metric-note">${note}</span></div>`;
}
/** One bubble per measure: an icon, a value and a short note. Explanations stay behind « Pourquoi ? ». */
export function metrics(v:View,config:Config) {
  const o=v.observations,a=v.assessment,mods=new Set(config.modules??[]),out=[];
  if(mods.has('temperature')){const t=numeric(o.indoor_temperature),hot=a.needs.includes('cool'),cold=a.needs.includes('heat');
    out.push(metric('temp','Température',number(t),'°C',hot?'Trop chaud':cold?'Trop frais':t===null?readingStatus(o.indoor_temperature):'Dans vos repères',hot||cold?'need':t===null?'off':'ok','heat'));}
  if(mods.has('temperature')){const te=numeric(o.outdoor_temperature),d=a.temperature_delta;
    out.push(metric('cloud','Dehors',number(te),'°C',te===null?(o.outdoor_temperature?readingStatus(o.outdoor_temperature):'Non configuré'):d===null?'—':`${d>0?'+':''}${number(d)} °C vs dedans`,te===null?'off':'ok','cold'));}
  if(mods.has('humidity')&&o.indoor_humidity){const h=numeric(o.indoor_humidity),wet=a.needs.includes('dry');
    out.push(metric('drop','Humidité',number(h),'%',wet?'Trop humide':a.indoor_absolute_humidity!==null?number(a.indoor_absolute_humidity)+' g/m³':o.indoor_humidity?readingStatus(o.indoor_humidity):'Non suivie',wet?'need':h===null?'off':'ok','cold'));}
  if(mods.has('air')&&o.co2){const co2=numeric(o.co2),verdict=co2Metric(v);
    out.push(metric('air','CO₂',number(co2),'ppm',verdict.note,verdict.state,'calm'));}
  if(mods.has('air'))for(const [key,label,status] of [['pm25','PM2.5',a.features?.air?.pm25_status],['voc','COV',a.features?.air?.voc_status]] as const){if(!o[key])continue;const value=numeric(o[key]),high=status==='high';out.push(metric('air',label,number(value),o[key].unit??'',high?'Au-dessus de votre seuil':status==='uninterpreted'?'Seuil non renseigné':value===null?readingStatus(o[key]):status==='ok'?'Dans vos repères':'Interprétation indisponible',high?'need':value===null||status!=='ok'?'off':'ok','calm'));}
  if(mods.has('windows')){const w=contactState(v),flagged=(a.openings??[]).some(x=>x.flags.length);
    out.push(metric(w.opened?'open':'window','Ouvrants',w.total?`${w.opened}/${w.total}`:'—','',w.total?(w.opened?`${w.opened} ouvert${w.opened>1?'s':''}`:'Tout fermé'):'Non suivis',flagged?'alert':w.total?'ok':'off','accent'));}
  if(mods.has('shutters')){const s=solarMetric(v);out.push(metric(s.ic,'Soleil',s.value,s.unit,s.note,s.state,'heat'));}
  if(mods.has('coordination')&&o.heating){out.push(metric('heat','Chauffage',o.heating?heatingLabels[a.heating_action]??'Inconnu':'—','',o.heating?'Observé, jamais commandé':'Non suivi',a.heating_action==='heating'?'need':o.heating?'ok':'off','heat'));}
  return out.length?html`<div class="metrics">${out}</div>`:html`<p class="empty-rubrics">Rubriques masquées. Le conseil reste disponible.</p>`;
}
const flagShort:Record<string,string>={rain_exposed:'pluie',gust:'rafales',sun_entering:'soleil'};
const sideShort:Record<string,string>={windward:'au vent',leeward:'sous le vent'};
const hour=(iso:string)=>{const d=new Date(iso),h=d.getHours();return h===0?'minuit':h===12?'midi':h+' h';};
/** The next hours from Niak Weather, as chips: when to open or close, rain coming, how the air goes through. */
export function nextHours(v:View) {
  const a=v.assessment,chips=[];
  if(a.slot)chips.push(html`<span class="chip strong">${icon(a.slot.kind==='open'?'open':'window')}${a.slot.kind==='open'?'Ouverture possible':'Fermeture conseillée'} à ${hour(a.slot.time)} · ${number(a.slot.temperature)} °C${a.slot.wind_bearing!=null?' · '+windFrom(a.slot.wind_bearing):''}</span>`);
  if(a.rain_soon_minutes!=null)chips.push(html`<span class="chip warn">${icon('rain')}Pluie dans ${a.rain_soon_minutes<60?a.rain_soon_minutes+' min':'1 h'}</span>`);
  if(a.crossing==='wind')chips.push(html`<span class="chip">${icon('air')}L’air traverse avec le vent</span>`);
  else if(a.crossing==='one_side')chips.push(html`<span class="chip">${icon('air')}Ouvert d’un seul côté</span>`);
  if(a.wind_bearing!=null&&!a.slot)chips.push(html`<span class="chip">${icon('arrow')}${windFrom(a.wind_bearing).replace(/^./,c=>c.toUpperCase())}</span>`);
  return chips.length?html`<div class="next-hours" aria-label="Prochaines heures">${chips}</div>`:nothing;
}
/** Openings as small chips: open ones stand out, a flag says why it matters now. */
export function openingChips(v:View) {
  const list=v.assessment.openings??[];
  if(!list.length) return nothing;
  return html`<div class="opening-chips" aria-label="Ouvrants">${list.map(x=>html`<span class="opening-chip" ?data-open=${x.open===true} ?data-flag=${x.flags.length>0} title=${[kindLabels[x.kind],x.exposure?'exposé '+exposureLabels[x.exposure]:'',x.sheltered?'abrité':''].filter(Boolean).join(' · ')}>${icon(x.open?'open':'window')}${v.names?.[x.entity_id]??x.entity_id}${x.exposure?html`<em>${x.exposure}${x.wind_side&&sideShort[x.wind_side]?' · '+sideShort[x.wind_side]:''}</em>`:nothing}${x.flags.length?html`<b>${x.flags.map(f=>flagShort[f]??f).join(' · ')}</b>`:nothing}</span>`)}</div>`;
}
export function details(v:View,config:Config,c:Controls,full:boolean) {
  return html`${why(v,c)}${metrics(v,config)}${nextHours(v)}${evolutionLines(v,config.modules??[]).length?html`<section class="explanation" aria-label="Suivi détaillé">${evolutionLines(v,config.modules??[]).map(l=>html`<div class="reason-row"><strong>${l.title}</strong><p>${l.text}</p></div>`)}</section>`:nothing}${full&&(config.modules??[]).includes('windows')?openingChips(v):nothing}`;
}
export function quality(v:View,c:Controls,configure?:()=>void) {
  return html`<div class="quality-foot">${icon('source')}<span>${coverageText(v)}</span><button @click=${c.toggleSources} aria-expanded=${c.sources} aria-controls=${'sources-'+c.uid}>Sources</button>${configure?html`<button class="configure" @click=${configure} aria-label="Configurer cette pièce" title="Configurer cette pièce">${icon('settings')}</button>`:nothing}</div>${sources(v,c)}`;
}
