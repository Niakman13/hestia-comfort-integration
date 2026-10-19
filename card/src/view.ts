import {ACTIONS, LEVELS, type View, type Reading} from './types';
const record = (x:unknown):x is Record<string,unknown> => !!x && typeof x==='object' && !Array.isArray(x);
const strings = (x:unknown):x is string[] => Array.isArray(x) && x.every(i=>typeof i==='string');
const finiteOrNull = (x:unknown) => x===null || typeof x==='number' && Number.isFinite(x);
export function isView(x:unknown):x is View {
  if(!record(x) || x.version!==1 || typeof x.entry_id!=='string' || typeof x.title!=='string'
    || !(x.area_id===null||typeof x.area_id==='string') || typeof x.computed_at!=='string' || !Number.isFinite(Date.parse(x.computed_at))
    || !record(x.assessment) || !record(x.observations)) return false;
  const a=x.assessment;
  if(!ACTIONS.includes(a.action as never)||!LEVELS.includes(a.level as never)||typeof a.reason!=='string'||typeof a.partial!=='boolean'
    || !['needs','constraints','opportunities','missing'].every(k=>strings(a[k]))
    || !['indoor_absolute_humidity','outdoor_absolute_humidity','temperature_delta'].every(k=>finiteOrNull(a[k]))
    || typeof a.heating_action!=='string'||typeof a.coordination!=='string') return false;
  return Object.values(x.observations).every(r=>record(r) && ['valid','unknown','stale','estimated'].includes(r.quality as string)
    && (r.value===null||typeof r.value==='boolean'||typeof r.value==='string'||typeof r.value==='number'&&Number.isFinite(r.value))
    && (r.source===null||typeof r.source==='string') && (r.received_at===null||typeof r.received_at==='string'&&Number.isFinite(Date.parse(r.received_at)))
    && (r.detail===null||typeof r.detail==='string') && (r.unit===null||typeof r.unit==='string')
    && !(r.quality==='unknown'&&r.value!==null));
}
export const numeric = (r:Reading|undefined):number|null => r?.quality==='valid'&&typeof r.value==='number'&&Number.isFinite(r.value)?r.value:null;
export const number = (v:number|null) => v===null?'—':new Intl.NumberFormat('fr-FR',{maximumFractionDigits:1}).format(v);
export const levelLabels = {calm:'Tout va bien',benefit:'Potentiel détecté',action:'Geste conseillé',urgent:'Attention nécessaire',neutral:'Information incomplète'};
export const needs:Record<string,string> = {air:'Renouveler l’air',cool:'Rafraîchir',heat:'Préserver la chaleur',dry:'Réduire l’humidité'};
export const heatingLabels:Record<string,string> = {heating:'Chauffe en cours',idle:'Au repos',off:'Arrêté',cooling:'Rafraîchit',unknown:'Action indisponible',not_configured:'Non configuré'};
export const sourceLabels:Record<string,string> = {indoor_temperature:'Température intérieure',outdoor_temperature:'Température extérieure',indoor_humidity:'Humidité intérieure',outdoor_humidity:'Humidité extérieure',co2:'CO₂',pm25:'Particules fines PM2.5',voc:'COV',illuminance:'Luminosité',purifier:'Purificateur observé',purifier_speed:'Vitesse du purificateur',rain:'Pluie sur les ouvrants',wind_gust:'Rafales',solar:'Ensoleillement',pollution:'Qualité de l’air dehors',wind_bearing:'Direction du vent',heating:'Chauffage observé'};
export const constraintLabels:Record<string,string> = {rain:'Pluie sur les ouvrants exposés',storm:'Orage',vigilance:'Vigilance météo orange ou rouge',gust:'Rafales trop fortes',pollution:'Air extérieur défavorable',frost:'Gel dehors',heating_running:'Chauffage en marche'};
export const exposureLabels:Record<string,string> = {N:'nord',NE:'nord-est',E:'est',SE:'sud-est',S:'sud',SO:'sud-ouest',O:'ouest',NO:'nord-ouest'};
const compass=['nord','nord-est','est','sud-est','sud','sud-ouest','ouest','nord-ouest'];
/** « vent d’ouest », « vent du nord » : where the wind comes from. */
export function windFrom(bearing:number|null|undefined):string {
  if(bearing==null||!Number.isFinite(bearing)) return '';
  const name=compass[Math.round(((bearing%360)+360)%360/45)%8];
  return 'vent '+(name==='est'||name==='ouest'?'d’'+name:name==='nord'||name==='sud'?'du '+name:'de '+name);
}
export const kindLabels:Record<string,string> = {window:'Fenêtre',french:'Porte-fenêtre',skylight:'Vasistas',door:'Porte'};
export const reasons:Record<string,[string,string]> = {
  within_comfort:['Vous êtes bien','Les mesures disponibles sont dans vos repères de confort. Cela ne renseigne pas les polluants non mesurés.'],
  rain_open_windows:['Fermez les ouvrants exposés','La pluie concerne cette pièce et au moins un contact indique une ouverture. Les autres besoins restent visibles.'],
  opening_blocked:['L’aération doit attendre','Une contrainte extérieure empêche une ouverture favorable. Un besoin intérieur éventuel reste à traiter.'],
  verify_exterior:['L’extérieur reste à vérifier','Le besoin intérieur est connu. Les conditions manquantes empêchent de confirmer le bénéfice ou les contraintes d’une ouverture.'],
  air_needed:['Aérez quelques minutes','Les mesures de qualité de l’air appellent un renouvellement d’air. Surveillez les mesures pour décider de la suite ; aucune durée ne garantit le résultat.'],
  rehumidification_risk:['Refermez pour éviter de réhumidifier','L’air extérieur contient davantage d’eau. Rester ouvert ne permet plus d’assécher la pièce ; les besoins de renouvellement d’air restent évalués séparément.'],
  shutter_protection:['Adaptez la protection solaire','Un geste sur les volets peut aider. Consultez le conseil par ouvrant ; une position non mesurée reste inconnue.'],
  cooling_possible:['Profitez de la fraîcheur','L’air extérieur est suffisamment plus frais pour aider cette pièce à retrouver votre plage de confort.'],
  drying_possible:['Un aérage peut assécher','L’air extérieur contient moins d’eau. Le gain annoncé tient compte de ce que les aérations passées ont vraiment donné dans cette pièce.'],
  drying_later:['Aérez plus tard','L’air du dehors sera nettement plus sec dans quelques heures : l’aération gagnera bien plus que maintenant.'],
  ventilation_possible:['Lancez la VMC','Aérer assèche peu cette pièce, mais l’air du dehors est plus sec : la VMC le fera entrer mieux qu’une fenêtre.'],
  drying_slow:['Aérer assèche peu ici','Les aérations passées de cette pièce ont peu fait baisser l’humidité : l’humidité y revient vite ou l’air s’y renouvelle mal.'],
  exchange_harmful:['Refermez les fenêtres','La comparaison dedans/dehors montre un échange thermique défavorable au confort de cette pièce.'],
  cooling_unavailable:['Attendez un air plus frais','La pièce a besoin de fraîcheur, mais ouvrir maintenant ne fournit pas un échange suffisamment favorable.'],
  heat_needed:['Préservez la chaleur','La température intérieure est sous votre repère. Le chauffage reste responsable de sa réponse thermique.'],
  drying_unavailable:['L’humidité reste à surveiller','Le besoin existe, mais un bénéfice d’assèchement par l’extérieur n’est pas confirmé.'],
  incomplete_data:['Les mesures restent à vérifier','Certaines informations sont manquantes ou périmées. Aucun chiffre de remplacement ne complète le bilan.'],
  optional_air_change:['Un renouvellement peut faire du bien','Une aération est une possibilité d’amélioration, sans besoin prioritaire détecté.'],
  gust_open_windows:['Fermez, le vent est trop fort','Les rafales dépassent votre seuil : rien ne doit rester ouvert.'],
  short_air_change:['Aérez quelques minutes','De l’air neuf en quelques minutes, pour très peu de confort perdu. Refermez ensuite.'],
  rain_soon:['Refermez avant la pluie','La pluie arrive bientôt sur les ouvrants exposés.'],
  precool_later:['Pas encore, demain sera chaud','Ouvrez dès que l’air dehors sera plus frais que dedans : la maison stockera ce frais pour demain.'],
  precool_possible:['Ouvrez pour la nuit','Il fera chaud demain : la maison stocke le frais de la nuit.'],
  sun_entering:['Fermez côté soleil','Une fenêtre ouverte reçoit le soleil alors que la pièce a déjà trop chaud : c’est par là que la chaleur entre.'],
};
const blockedText:Record<string,[string,string]> = {
  storm:['Gardez fermé, orage','Un orage est en cours ou prévu dans les 6 heures.'],
  vigilance:['Gardez fermé, vigilance météo','Météo-France a placé le département en vigilance orange ou rouge.'],
  gust:['Gardez fermé, le vent est fort','Les rafales dépassent votre seuil. L’aération attendra qu’elles retombent.'],
  frost:['Gardez fermé, il gèle dehors','Une ouverture prolongée refroidirait la pièce sans bénéfice.'],
  heating_running:['Gardez fermé, le chauffage tourne','Ouvrir maintenant ferait perdre la chaleur produite.'],
};
export function summary(v:View):[string,string] {
  const a=v.assessment;
  if(a.reason==='incomplete_data'&&numeric(v.observations.indoor_temperature)!==null&&!a.missing.some(k=>!!v.observations[k])) return ['Les mesures connues sont dans vos repères','Les conditions extérieures non configurées restent à vérifier avant d’ouvrir. Ce bilan porte sur les mesures disponibles.'];
  if(a.reason==='incomplete_data'){
    // Name what is missing: a person can fix « Qualité de l’air dehors », not « certaines informations ».
    const failed=a.missing.filter(k=>!!v.observations[k]).map(k=>sourceLabel(v,k));
    if(failed.length) return [failed.length>1?'Des mesures ne sont pas à jour':'Une mesure n’est pas à jour',`${failed.join(', ')} : ${failed.length>1?'ne répondent pas ou sont trop anciennes':'ne répond pas ou est trop ancienne'}. Niak attend son retour pour conseiller.`];
  }
  if(a.action==='ok'&&a.needs.includes('air')) return ['L’aération est en cours','Les mesures de qualité de l’air restent à surveiller : une ouverture observée ne signifie pas que le besoin d’air est résolu.'];
  if(a.reason==='opening_blocked'){
    const main=a.constraints.find(k=>k in blockedText);
    if(a.action==='fermer') return [main==='storm'?'Fermez, orage':main==='vigilance'?'Fermez, vigilance météo':main==='frost'?'Refermez, il gèle dehors':main==='heating_running'?'Refermez, le chauffage tourne':'Fermez les ouvrants concernés',main?blockedText[main][1]:reasons.opening_blocked[1]];
    if(main&&!a.constraints.some(k=>k==='rain'||k==='pollution')) return blockedText[main];
  }
  if(a.slot&&a.slot.kind==='open'&&(a.reason==='cooling_unavailable'||a.reason==='precool_later')){
    const h=new Date(a.slot.time).getHours(),at=h===0?'minuit':h===12?'midi':h+' h';
    return [a.reason==='precool_later'?'Pas encore, demain sera chaud':'Attendez un air plus frais',`Ouvrez vers ${at} : il fera ${number(a.slot.temperature)} °C dehors${a.slot.wind_bearing!=null?', '+windFrom(a.slot.wind_bearing):''}.`];
  }
  if(a.reason==='rain_soon'&&a.rain_soon_minutes!=null) return ['Refermez avant la pluie',`La pluie arrive dans ${a.rain_soon_minutes<60?a.rain_soon_minutes+' min':'une heure'} sur les ouvrants exposés.`];
  if(a.reason==='short_air_change'){
    const why=shortWhy(a.constraints);
    return [a.action==='ok'?'Aération en cours, pas trop longtemps':'Aérez quelques minutes',`Les mesures demandent de l’air neuf, mais ${why} : une aération courte suffit.`];
  }
  return reasons[a.reason]??['Conseil à vérifier','Cette raison n’est pas reconnue par la carte. Mettez à jour la carte et l’intégration ensemble.'];
}

// Why the airing stays short. A forecast storm or vigilance only shortens it when the station sees it dry and calm.
export function shortWhy(c:string[]):string{
  return c.includes('storm')?'un orage est prévu':c.includes('vigilance')?'une vigilance météo est en cours':c.includes('frost')?'il gèle dehors':'le chauffage tourne';
}

// A contact is named as the person knows it (« Fenêtre Ouest »), never as a generic « Contact de fenêtre ».
export function sourceLabel(v:View,k:string):string{
 const split=k.indexOf(':');if(split<0)return sourceLabels[k]??k;
 const kind=k.slice(0,split),name=v.names?.[k.slice(split+1)];
 const titles:Record<string,string>={window:'Contact d’ouvrant',presence:'Présence',cover:'Position du volet',cover_state:'État du volet',shutter_auto:'Automatisation du volet',shutter_override:'Dérogation du volet',
  shutter_sun:'Soleil devant le volet',shutter_target:'Position visée du volet',shutter_enabled:'Adaptive Cover Pro',shutter_tracking:'Suivi du soleil du volet',shutter_detection:'Détection de la reprise à la main',shutter_climate:'Mode climat du volet'};
 return name?(kind==='window'?name:`${titles[kind]??'Source'} · ${name}`):titles[kind]??'Source';
}
export function coverageText(v:View):string {
  const failed=v.assessment.missing.filter(k=>!!v.observations[k]);
  const absent=v.assessment.missing.filter(k=>!v.observations[k]);
  if(failed.length) return 'Mesures à vérifier : '+failed.map(k=>sourceLabel(v,k)).join(' · ');
  if(absent.length) return 'Bilan limité : '+absent.map(k=>sourceLabels[k]??k).join(' · ')+' non configuré';
  return 'Sources configurées disponibles';
}
export function readingStatus(r:Reading|undefined):string {
  if(!r) return 'Non configuré';
  if(r.quality==='stale') return 'Mesure trop ancienne';
  if(r.detail==='atmo_daily_forecast' && r.quality==='estimated') return 'Indice prévu du jour';
  if(r.detail==='user_declared' && r.quality==='valid') return 'Déclaré par vous';
  if(r.quality==='estimated') return 'Estimation';
  if(r.quality==='valid') return 'Disponible';
  return r.detail==='incompatible_unit'?'Unité incompatible':r.detail==='out_of_range'?'Valeur hors plage':r.detail==='unknown_action'?'Action non fournie par le chauffage':'Temporairement indisponible';
}

/** Additive engine explanations, shared by all formats and never inferred from missing readings. */
export function evolutionLines(v:View,modules:import('./types').Module[]):{title:string;text:string}[]{
 const f=v.assessment.features;if(!f)return [];const lines:{title:string;text:string}[]=[];
 if(modules.includes('shutters'))for(const s of f.shutters??[]){
  if(s.mode==='none'&&!s.message)continue;
  const position=s.position==null?(/position non mesurée/i.test(s.message)?'':'Position non mesurée'):`Ouverture du volet : ${number(s.position)} %`;
  const shade=s.shade_fraction==null?'':` · ombre estimée : ${number(s.shade_fraction*100)} %`;
  lines.push({title:v.names?.[s.entity_id]??'Volet',text:[s.message,position+shade,s.manual_override===true?'Dérogation manuelle active.':'',s.automatic===true?'Automatisation active.':''].filter(Boolean).join(' ')});
 }
 if(modules.includes('air')){
  if(f.presence)lines.push({title:'Présence',text:f.presence.message});
  if(f.air){const purifier=f.air.purifier;lines.push({title:'Qualité de l’air',text:[f.air.message,f.air.coverage,purifier?.on===true?'Purificateur en marche'+(purifier.speed!=null?' · '+number(purifier.speed)+' %':'')+'. Il ne retire pas le CO₂.':purifier?.on===false?'Purificateur arrêté.':''].filter(Boolean).join(' ')});}
 }
 if(modules.includes('windows')&&f.ventilation&&(f.ventilation.opened_minutes!=null||f.ventilation.duration_minutes!=null||Object.entries(v.observations).some(([k,r])=>k.startsWith('window:')&&r.quality==='valid'&&r.value===true))){const vent=f.ventilation;lines.push({title:'Aération',text:[vent.message,vent.opened_minutes!=null?'Ouvert depuis '+number(vent.opened_minutes)+' min.':'',vent.duration_minutes?`Durée indicative : ${number(vent.duration_minutes.min)}–${number(vent.duration_minutes.max)} min ; surveillez les mesures.`:''].filter(Boolean).join(' ')});}
 if(modules.includes('humidity')&&f.humidity){const h=f.humidity;lines.push({title:'Humidité et buée',text:[h.condensation_risk===true?'Risque de buée estimé.':h.condensation_risk===false?'Aucun risque de buée estimé avec les mesures actuelles.':'Risque de buée inconnu.',h.message,h.dew_point!=null?'Point de rosée : '+number(h.dew_point)+' °C.':'',h.incoming_relative!=null?'Humidité entrante estimée : '+number(h.incoming_relative)+' %.':'',h.glass_temperature!=null?'Vitrage estimé : '+number(h.glass_temperature)+' °C.':''].filter(Boolean).join(' ')});}
 if(modules.includes('temperature')&&f.trends){const t=f.trends;lines.push({title:'Évolution des températures',text:t.indoor==null&&t.outdoor==null?'Historique insuffisant pour estimer une tendance.':[t.message,t.indoor!=null?'Dedans : '+(t.indoor>0?'+':'')+number(t.indoor)+' °C/h.':'',t.outdoor!=null?'Dehors : '+(t.outdoor>0?'+':'')+number(t.outdoor)+' °C/h.':''].filter(Boolean).join(' ')});}
 return lines.filter(l=>l.text);
}

/** CO₂ is its own pollutant; a particulate need cannot set its metric to alert. */
export function co2Metric(v:View):{state:'need'|'alert'|'ok'|'off';note:string}{
 const value=numeric(v.observations.co2),status=v.assessment.features?.air?.co2_status;
 if(value===null)return {state:'off',note:readingStatus(v.observations.co2)};
 if(status==='high')return {state:v.assessment.level==='urgent'?'alert':'need',note:'CO₂ : air à renouveler'};
 if(status==='ok')return {state:'ok',note:'Dans vos repères CO₂'};
 return {state:'off',note:'Mesure disponible · seuil non transmis'};
}
export function solarMetric(v:View):{ic:string;value:string;unit:string;note:string;state:'need'|'ok'|'off'}{
 const s=v.assessment.sun,list=v.assessment.openings??[];
 if(!s)return {ic:'sun',value:'—',unit:'',note:'Position du soleil inconnue',state:'off'};
 if(s.elevation<=0)return {ic:'moon',value:'Nuit',unit:'',note:'Pas d’apport solaire',state:'off'};
 const sunny=list.filter(x=>x.sun_wm2!==null&&x.sun_wm2>=50),top=Math.max(0,...sunny.map(x=>x.sun_wm2??0));
 return {ic:'sun',value:sunny.length?String(top):'—',unit:sunny.length?'W/m²':'',note:!list.some(x=>x.exposure)?'Exposition à renseigner':sunny.length?`${sunny.length} ouvrant${sunny.length>1?'s':''} au soleil`:'Pas de soleil direct',state:list.some(x=>x.flags.includes('sun_entering'))?'need':sunny.length?'ok':'off'};
}
