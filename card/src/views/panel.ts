import {html,nothing} from 'lit';
import type {Config,View,Module} from '../types';
import {numeric,number,summary,needs,levelLabels,heatingLabels,sourceLabels,constraintLabels,exposureLabels,kindLabels,coverageText,readingStatus} from '../view';
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
    ${Object.entries(v.observations).map(([k,r])=>html`<dt>${sourceLabels[k]??(k.startsWith('window:')?'Contact d’ouvrant':k)} · ${readingStatus(r)}</dt><dd>${r.source??'Source non configurée'}${r.received_at?` · reçu le ${new Date(r.received_at).toLocaleString('fr-FR')}`:''}${r.quality!=='valid'?' · exclu des mesures actuelles':''}</dd>`)}
    ${Object.keys(sourceLabels).filter(k=>!v.observations[k]).map(k=>html`<dt>${sourceLabels[k]??k}</dt><dd>Non configuré</dd>`)}
  </dl><p class="truth">La publication d’un conseil ne rajeunit pas ses sources. Les heures indiquent la réception par Home Assistant, pas forcément l’instant physique de mesure.</p></section>`;
}
export function hero(v:View,config:Config,c:Controls) {
  const [title,text]=summary(v),w=contactState(v),a=v.assessment;
  return html`<div class="hero"><div class="hero-head"><h2>${config.title||`Confort · ${v.title}`}</h2><span class="source-chip">${icon('home')}${v.title}</span></div>
    <div class="hero-text"><span class="status">${icon(a.action==='ouvrir'?'open':a.action==='ok'?'check':a.action==='unknown'?'info':'alert')}${levelLabels[a.level]}</span><h3>${title}</h3><p>${text}</p>${(a.action==='ouvrir'||a.action==='ok')&&a.unverified?.length?html`<p class="unverified">${icon('info')}${a.unverified.map(k=>k==='rain'?'Pluie':'Qualité de l’air dehors').join(' et ')} non suivie${a.unverified.length>1?'s':''} : vérifiez avant d’ouvrir.</p>`:nothing}
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
  if(mods.has('air')&&o.co2){const co2=numeric(o.co2),air=a.needs.includes('air');
    out.push(metric('air','CO₂',number(co2),'ppm',air?'Air à renouveler':co2===null?(o.co2?readingStatus(o.co2):'Non suivi'):'Air correct',air?(a.level==='urgent'?'alert':'need'):co2===null?'off':'ok','calm'));}
  if(mods.has('windows')){const w=contactState(v),flagged=(a.openings??[]).some(x=>x.flags.length);
    out.push(metric(w.opened?'open':'window','Ouvrants',w.total?`${w.opened}/${w.total}`:'—','',w.total?(w.opened?`${w.opened} ouvert${w.opened>1?'s':''}`:'Tout fermé'):'Non suivis',flagged?'alert':w.total?'ok':'off','accent'));}
  if(mods.has('shutters')){const s=a.sun,list=a.openings??[],sunny=list.filter(x=>x.sun_wm2!==null&&x.sun_wm2>=50),top=Math.max(0,...sunny.map(x=>x.sun_wm2??0));
    const night=!s||s.elevation<=0;
    out.push(metric(night?'moon':'sun','Soleil',night?'Nuit':sunny.length?String(top):'—',night||!sunny.length?'':'W/m²',night?'Pas d’apport':!list.some(x=>x.exposure)?'Exposition à renseigner':sunny.length?`${sunny.length} ouvrant${sunny.length>1?'s':''} au soleil`:'Pas de soleil direct',list.some(x=>x.flags.includes('sun_entering'))?'need':night||!sunny.length?'off':'ok','heat'));}
  if(mods.has('coordination')&&o.heating){out.push(metric('heat','Chauffage',o.heating?heatingLabels[a.heating_action]??'Inconnu':'—','',o.heating?'Observé, jamais commandé':'Non suivi',a.heating_action==='heating'?'need':o.heating?'ok':'off','heat'));}
  return out.length?html`<div class="metrics">${out}</div>`:html`<p class="empty-rubrics">Rubriques masquées. Le conseil reste disponible.</p>`;
}
const flagShort:Record<string,string>={rain_exposed:'pluie',gust:'rafales',sun_entering:'soleil'};
/** Openings as small chips: open ones stand out, a flag says why it matters now. */
export function openingChips(v:View) {
  const list=v.assessment.openings??[];
  if(!list.length) return nothing;
  return html`<div class="opening-chips" aria-label="Ouvrants">${list.map(x=>html`<span class="opening-chip" ?data-open=${x.open===true} ?data-flag=${x.flags.length>0} title=${[kindLabels[x.kind],x.exposure?'exposé '+exposureLabels[x.exposure]:'',x.sheltered?'abrité':''].filter(Boolean).join(' · ')}>${icon(x.open?'open':'window')}${v.names?.[x.entity_id]??x.entity_id}${x.exposure?html`<em>${x.exposure}</em>`:nothing}${x.flags.length?html`<b>${x.flags.map(f=>flagShort[f]??f).join(' · ')}</b>`:nothing}</span>`)}</div>`;
}
export function details(v:View,config:Config,c:Controls,full:boolean) {
  return html`${why(v,c)}${metrics(v,config)}${full&&(config.modules??[]).includes('windows')?openingChips(v):nothing}`;
}
export function quality(v:View,c:Controls,configure?:()=>void) {
  return html`<div class="quality-foot">${icon('source')}<span>${coverageText(v)}</span><button @click=${c.toggleSources} aria-expanded=${c.sources} aria-controls=${'sources-'+c.uid}>Sources</button>${configure?html`<button class="configure" @click=${configure} aria-label="Configurer cette pièce" title="Configurer cette pièce">${icon('settings')}</button>`:nothing}</div>${sources(v,c)}`;
}
