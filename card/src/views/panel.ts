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
export function exchange(v:View) {
  const o=v.observations,a=v.assessment;
  return html`<div class="exchange" aria-label="Comparaison dedans et dehors">
    <div><div class="measure-name">Dedans</div><div class="measure-value">${number(numeric(o.indoor_temperature))}<small>°C</small></div><div class="measure-detail">${number(numeric(o.indoor_humidity))} % · ${number(a.indoor_absolute_humidity)} g/m³</div></div>
    <div class="exchange-line">${icon('arrow')}${a.temperature_delta===null?'Écart inconnu':`${a.temperature_delta>0?'+':''}${number(a.temperature_delta)} °C`}<span>dehors − dedans</span></div>
    <div class="outside"><div class="measure-name">Dehors</div><div class="measure-value">${number(numeric(o.outdoor_temperature))}<small>°C</small></div><div class="measure-detail">${number(numeric(o.outdoor_humidity))} % · ${number(a.outdoor_absolute_humidity)} g/m³</div></div>
  </div>`;
}
const flagText:Record<string,string>={rain_exposed:'pluie : à fermer',gust:'rafales : à fermer',sun_entering:'le soleil entre par là'};
function openingList(v:View) {
  const list=v.assessment.openings??[];
  if(!list.length) return nothing;
  return html`<ul class="openings">${list.map(o=>html`<li data-flag=${o.flags[0]??''}><strong>${v.names?.[o.entity_id]??o.entity_id}</strong>
    <span>${o.open===null?'état inconnu':o.open?'ouvert':'fermé'} · ${kindLabels[o.kind]??'Ouvrant'}${o.exposure?` · exposé ${exposureLabels[o.exposure]??o.exposure}`:' · exposition non renseignée'}${o.sheltered?' · abrité':''}${o.sun_wm2!==null&&o.sun_wm2>=50?` · soleil ${o.sun_wm2} W/m²`:''}</span>
    ${o.flags.length?html`<em>${o.flags.map(f=>flagText[f]??f).join(' · ')}</em>`:nothing}</li>`)}</ul>`;
}
function sunText(v:View) {
  const s=v.assessment.sun,list=v.assessment.openings??[];
  if(!s) return 'Position du soleil indisponible.';
  if(s.elevation<=0) return 'Il fait nuit : aucun apport solaire.';
  const sunny=list.filter(o=>o.sun_wm2!==null&&o.sun_wm2>=50);
  if(!list.some(o=>o.exposure)) return 'Renseignez l’exposition des ouvrants dans Niak Confort pour savoir lesquels reçoivent le soleil.';
  if(!list.some(o=>o.sun_wm2!==null)) return 'Ajoutez un capteur d’ensoleillement à l’extérieur du logement pour mesurer le soleil sur chaque façade.';
  return sunny.length?'Au soleil : '+sunny.map(o=>`${v.names?.[o.entity_id]??o.entity_id} (${o.sun_wm2} W/m²)`).join(' · '):'Aucun ouvrant suivi ne reçoit de soleil direct maintenant.';
}
export function moduleRow(id:Module,v:View) {
  const o=v.observations,a=v.assessment,w=contactState(v);
  const info={windows:'window',air:'air',temperature:'temp',humidity:'drop',shutters:'sun',coordination:'heat'};
  let label='',body;
  if(id==='windows'){
    label=w.total?`${w.opened} ouverte${w.opened>1?'s':''} / ${w.total}`:'Non mesuré';
    body=html`<p>${w.label}. ${w.total?'Le constat repose sur les contacts de cette pièce.':'Sans contact, aucune fermeture ni geste effectué n’est présumé.'}</p>${openingList(v)}`;
  }else if(id==='air'){
    label=numeric(o.co2)===null?`CO₂ · ${readingStatus(o.co2).toLowerCase()}`:'CO₂ mesuré';
    body=html`<div class="air-values"><span><strong>${number(numeric(o.co2))}</strong>ppm de CO₂</span><span><strong>${number(numeric(o.indoor_humidity))}</strong>% d’humidité</span></div><p>${a.needs.includes('air')?'Le besoin de renouvellement d’air reste présent, même si une contrainte empêche l’ouverture.':'Aucun besoin de renouvellement par CO₂ n’est établi avec les mesures disponibles.'}</p><p>Particules et COV : pas de diagnostic dans cette version.</p>`;
  }else if(id==='temperature'){
    label=`${number(numeric(o.indoor_temperature))} °C`;
    body=html`<p>${a.needs.includes('cool')?'La pièce appelle de la fraîcheur.':a.needs.includes('heat')?'La pièce appelle de la chaleur.':'Aucun besoin thermique prioritaire parmi les mesures connues.'}</p><p>Évaluation locale à cette pièce. Les repères se règlent dans l’intégration.</p>`;
  }else if(id==='humidity'){
    label=`${number(numeric(o.indoor_humidity))} % dedans`;
    body=html`<p>${a.indoor_absolute_humidity===null||a.outdoor_absolute_humidity===null?'La comparaison de l’eau contenue dans l’air nécessite les températures et humidités dedans/dehors.':`${number(a.indoor_absolute_humidity)} g/m³ dedans · ${number(a.outdoor_absolute_humidity)} g/m³ dehors.`}</p><p>${a.opportunities.includes('dry')?'L’air extérieur contient suffisamment moins d’eau pour offrir un potentiel d’assèchement.':'Un bénéfice d’assèchement par l’extérieur n’est pas confirmé.'}</p>`;
  }else if(id==='shutters'){
    const sunny=(v.assessment.openings??[]).filter(o=>o.sun_wm2!==null&&o.sun_wm2>=50).length;
    label=v.assessment.sun&&v.assessment.sun.elevation>0?(sunny?`${sunny} ouvrant${sunny>1?'s':''} au soleil`:'Soleil suivi'):'Nuit';
    body=html`<p>${sunText(v)}</p><p>Volets et luminosité : à venir dans une prochaine version.</p>`;
  }else{
    label=o.heating?heatingLabels[a.heating_action]??'Action inconnue':'Non relié';
    body=html`<p>${o.heating?`Action observée : ${heatingLabels[a.heating_action]??'inconnue'}.`:'Aucun équipement de chauffage sélectionné.'}</p><p>Aucune pause demandée ni confirmée. Le futur pilote recevra les besoins de cette pièce ; il conservera ses protections et la responsabilité des commandes.</p>`;
  }
  return html`<section class="module" data-module=${id}><div class="module-head">${icon(info[id])}<h3>${moduleLabels[id]}</h3><span class="chip">${label}</span></div>${body}</section>`;
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
    <div class="hero-text"><span class="status">${icon(a.action==='ouvrir'?'open':a.action==='ok'?'check':a.action==='unknown'?'info':'alert')}${levelLabels[a.level]}</span><h3>${title}</h3><p>${text}</p>
      <div class="hero-actions"><button @click=${c.toggleWhy} aria-expanded=${c.why} aria-controls=${'why-'+c.uid}>${icon('info')}Pourquoi ?</button><button @click=${c.toggleSources} aria-expanded=${c.sources} aria-controls=${'sources-'+c.uid}>${icon('source')}Les sources</button></div>
    </div><div class="window-scene" aria-hidden="true"><div class="window-disk">${icon(a.action==='ouvrir'||w.opened?'open':'window')}</div>${w.opened?html`<div class="air-stream"><i></i><i></i><i></i></div>`:nothing}<span>${w.label}</span></div>
  </div>`;
}
export function details(v:View,config:Config,c:Controls,full:boolean) {
  const modules=full?config.modules??[]:(config.modules??[]).filter(id=>['windows','air','coordination'].includes(id));
  return html`${why(v,c)}${exchange(v)}<section class="events"><div class="section-head"><h3>Événements</h3><span>Anticipation indisponible</span></div><p class="event-text">Les prévisions ne sont pas encore raccordées. Le conseil actuel repose sur les observations connues.</p></section>
    ${modules.length?modules.map(id=>moduleRow(id,v)):html`<p class="empty-rubrics">Rubriques masquées. Les observations et le conseil restent disponibles.</p>`}`;
}
export function quality(v:View,c:Controls) {
  return html`<div class="quality-foot">${icon('source')}<span>${coverageText(v)}</span><button @click=${c.toggleSources} aria-expanded=${c.sources} aria-controls=${'sources-'+c.uid}>Sources</button></div>${sources(v,c)}`;
}
