import {html,nothing,LitElement,type TemplateResult} from 'lit';
import {property,state} from 'lit/decorators.js';
import {SCALE_MARKS,CHIPS,TILE_BLOCKS,type Config,type View,type Level,type Format,type BannerBlock,type Chip} from '../types';
import {numeric,number,heatingLabels,coverageText,windFrom,sourceLabel,needs as needLabels,constraintLabels,shortWhy} from '../view';
import {icon} from '../ui/icons';

/** The level, said in two or three words: the colour is never the only signal. */
// Versatile Thermostat's presets and the reasons it stops by itself, in the person's words.
const presetWord=(p:string|null)=>!p?'mode réduit':p.includes('frost')?'hors-gel':p.includes('away')?'absence':p.includes('eco')?'éco':p;
const offWords:Record<string,string>={window:'fenêtre ouverte',auto_start_stop:'arrêt automatique',sleep:'veille',safety:'sécurité',central_mode:'mode central',inhibition:'délestage'};

export const pills:Record<Level,string>={calm:'Tout va bien',benefit:'À saisir',action:'Geste conseillé',urgent:'Attention',neutral:'À vérifier'};
const hour=(iso:string)=>{const h=new Date(iso).getHours();return h===0?'minuit':h===12?'midi':h+' h';};
/** « 15 h 20 », to the five minutes: when to shut before a coming rain. */
const rainClock=(d:Date)=>{const m=Math.floor(d.getMinutes()/5)*5;return d.getHours()+' h'+(m?' '+String(m).padStart(2,'0'):'');};
const b=(text:string)=>html`<b>${text}</b>`;
const deg=(v:number|null)=>v===null?'—':number(v)+' °C';

export interface Advice {title:string;line:TemplateResult|string;disk:string;cap?:string;
  /** Learned on this room by its twin: the basis, said under the gesture (« d'après 31 aérations »). */ learned?:string;
  /** A state that is not advice (sensors loading or silent) brings its own words and colour. */ pill?:string;level?:Level}
/** Reasons that only say « keep closed »: the engine lowers them to calm when nothing is open and no reflex is at stake. */
const QUIET=['drying_unavailable','drying_slow','opening_blocked','cooling_unavailable','precool_later'];
/** The banner: the gesture in a few words, then why in one line. The full explanation stays behind « i ». */
/** The room cannot be read: its temperature or three sensors silent. The banner then says so, and nothing that
 * supposes an advice (a result, an airing) is said under it. One or two late secondary sensors leave the advice. */
const unreadable=(v:View)=>{const failed=v.assessment.missing.filter(k=>!!v.observations[k]&&k!=='pollution');return failed.includes('indoor_temperature')||failed.length>=3;};
/** A pill names what is out; « votre plage » is kept for the temperature's range. */
const NEED_PILLS:Record<string,string>={dry:'Trop humide',heat:'Trop frais',cool:'Trop chaud',air:'Air à renouveler'};
/** …and its disk shows the measure's own pictogram: the tick is kept for « nothing to report ». */
const NEED_DISKS:Record<string,string>={dry:'drop',heat:'temp',cool:'temp',air:'air'};
const SEASON_NAMES:Record<string,string>={spring:'printemps',summer:'été',autumn:'automne',winter:'hiver'};
export function humidityLabel(v:View):string|null {
  if(numeric(v.observations.indoor_humidity)===null)return null;
  const humidity=v.assessment.features?.humidity;
  if(!humidity?.status)return v.assessment.needs.includes('dry')?'Trop humide':null;
  if(humidity.status==='unknown')return null;
  if(humidity.status==='normal')return 'Dans votre plage';
  const wet=humidity.status==='high';
  return humidity.degree===1?(wet?'Légèrement humide':'Légèrement sec'):humidity.degree===3?(wet?'Très humide':'Très sec'):(wet?'Air humide':'Air sec');
}
export function advice(v:View):Advice {
  const out=withLearning(v,gesture(v));
  const humidity=v.assessment.features?.humidity,label=humidityLabel(v);
  if(label&&humidity?.status&&v.assessment.reason!=='shared_volume'&&['calm','neutral'].includes(v.assessment.level)&&!unreadable(v)
      &&v.assessment.action!=='fermer'&&!v.assessment.needs.some(need=>need!=='dry'&&need!=='precool')){
    if(humidity.mould)return {...out,pill:'Murs à surveiller',disk:'drop',level:'neutral'};
    if(humidity.status==='normal'&&out.pill==='Trop humide')return {...out,pill:undefined,disk:'check',level:v.assessment.level};
    if(humidity.status==='low'||humidity.status==='high')return {...out,pill:label,disk:'drop',level:humidity.degree===1?'calm':'neutral'};
  }
  // To close, say which window: in a shared air it may be in the other room.
  if(v.assessment.action==='fermer'&&!out.cap){
    const open=(v.assessment.openings??[]).filter(o=>o.open).map(o=>v.names?.[o.entity_id]??o.entity_id);
    if(open.length)return {...out,cap:open.length>2?`${open.length} ouvertures`:open.join(' et ')};
  }
  return out;
}
function gesture(v:View):Advice {
  // One verdict per shared air: the room shows the leading room's advice, with that room's measures.
  const vol=v.assessment.features?.volume;
  if(v.assessment.reason==='shared_volume'&&vol?.assessment){
    const lead=advice({...v,observations:vol.observations??v.observations,assessment:{...v.assessment,...vol.assessment,features:{...v.assessment.features,...vol.assessment.features,volume:undefined}} as View['assessment']});
    // « Même air » is said in « À savoir », under the banner.
    return lead;
  }
  const a=v.assessment,o=v.observations,ti=numeric(o.indoor_temperature);
  const opened=Object.entries(o).some(([k,r])=>k.startsWith('window:')&&r.quality==='valid'&&r.value===true);
  const first=(a.open_first??[]).map(id=>v.names?.[id]??id)[0];
  const slot=a.slot;
  const duration=a.features?.ventilation?.duration_minutes;
  // The banner compares instead of asserting: the reader sees the two values the advice is based on.
  const te=numeric(o.outdoor_temperature),hi=numeric(o.indoor_humidity),incoming=a.features?.humidity?.incoming_relative??null;
  const temps=html`${deg(ti)} dedans, ${b(deg(te)+' dehors')}`;
  // Humidity in plain words: where the outdoor air would bring the room once warmed inside.
  // Once learned, the room's own past airings say where the humidity would really go.
  const drying=a.features?.drying??null;
  const water=(()=>{
    // The room's own measure, as on its tile; the drop is the one learned for its air.
    if(drying){const now=Math.round(hi??drying.now),after=Math.round((hi??drying.now)-drying.gain),outside=numeric(o.outdoor_humidity);
      return outside!==null&&Math.round(outside)>=now
        ?html`Dehors ${Math.round(outside)} %, mais l’air froid contient peu d’eau : ${b('environ '+after+' %')} après l’aération`
        :html`${now} % d’humidité, ${b('environ '+after+' %')} après l’aération`;}
    if(incoming==null||hi===null)return html`L’air du dehors est ${b('plus sec')}`;
    const target=Math.round(incoming),now=Math.round(hi),outside=numeric(o.outdoor_humidity);
    // The trap: a cold outdoor air at 79 % holds little water. Say it, or the advice looks wrong.
    if(target<now&&outside!==null&&Math.round(outside)>=now)
      return html`Dehors ${Math.round(outside)} %, mais l’air froid contient peu d’eau : réchauffé chez vous, il ferait ${b(target+' %')}`;
    return target<now?html`${now} % d’humidité, l’air du dehors la ferait ${b('descendre à '+target+' %')}`
      :target>now?html`${now} % d’humidité, l’air du dehors la ferait ${b('monter à '+target+' %')}`
      :html`${now} % d’humidité, l’air du dehors ${b('ne la changerait pas')}`;
  })();
  // How long, under the disk: the duration first, then where to open.
  const span=duration?`${duration.min} à ${duration.max} min`:undefined;
  // The airing time is part of the gesture: in the title, before opening and while the window is open.
  const opened_for=a.features?.ventilation?.opened_minutes??null;
  const airing=(verb:string,fallback:string,line:TemplateResult|string):Advice=>{
    if(a.action==='ok'){
      if(duration&&opened_for!=null){const left=Math.round(duration.max-opened_for);
        return left>0?{title:`Encore ${left} min d’aération`,line,disk:'open',cap:`ouvert depuis ${Math.round(opened_for)} min`}
          :{title:'Vous pouvez refermer',line,disk:'shut',cap:`ouvert depuis ${Math.round(opened_for)} min`};}
      return {title:'Aération en cours',line,disk:'open',cap:span?`${span} au total`:undefined};
    }
    // A later rain bounds the airing: the window is shut five minutes before it.
    const rain=a.features?.rain_ahead,shut=rain&&rain.minutes<=(duration?.max??15)+15?rainClock(new Date(new Date(v.computed_at).getTime()+(rain.minutes-5)*60000)):null;
    return {title:span?`${verb} ${span}`:fallback,line,disk:'open',cap:shut?`Refermez avant ${shut}`:first};
  };
  const constraint=a.constraints.find(c=>c!=='heating_running'&&c!=='frost')??a.constraints[0];
  // A silent sensor is not advice: the banner says what Niak cannot see, the tiles show which ones.
  const failed=a.missing.filter(k=>!!o[k]&&k!=='pollution'),count=failed.length;
  const blind=unreadable(v);
  if(blind&&v.starting)return {title:'Mesures en chargement',line:html`Home Assistant ${b('vient de démarrer')}`,disk:'clock',pill:'Démarrage',level:'neutral'};
  if(blind){const one=count===1;
    return {title:'Mesures absentes',line:html`${b(`${count} capteur${one?'':'s'} ne répond${one?'':'ent'} pas`)} · détail dans Mesures`,disk:'mute',pill:'Capteurs muets',level:'neutral'};}
  // « Do not open » to someone who was not opening brings nothing: the banner stays calm, the measure on its tile.
  // The banner only ever carries a gesture; what is merely worth knowing goes to « À savoir » below.
  const quiet=(QUIET.includes(a.reason)&&(a.level==='calm'||a.level==='neutral'))||['humid_outdoor','open_neutral','drying_unavailable'].includes(a.reason)
    ||(a.reason==='drying_slow'&&a.features?.air?.ventilation?.on!==false)||(a.reason==='heat_needed'&&a.action!=='fermer'&&a.level!=='action');
  if(quiet&&a.action!=='fermer'){
    // Already open, « opening would bring nothing » reads as a contradiction: open or shut makes no difference.
    // A measure out of range with nothing to do about it: not « Tout va bien », only nothing better to do.
    // Opening is held back (rain, gusts, outdoor air): not that it would bring nothing; « À savoir » says why.
    // A warm room in winter: opening would cool it, but too fast; the season, not the physics, says no.
    const winterWarm=a.features?.season?.group==='winter'&&a.needs.includes('cool');
    return {title:'Rien à faire',line:opened?html`Ouverte ou fermée, ${b('cela ne change rien')}`:a.reason==='opening_blocked'?html`Aérer ${b('n’est pas possible')} pour l’instant`
      :winterWarm?html`Ouvrir la ${b('refroidirait trop vite')} en hiver`:html`Ouvrir ${b('n’apporterait rien')} pour l’instant`,disk:opened?'open':'check',cap:opened?'Fenêtre ouverte':undefined,
      // The pill names what is out, never « plage »: that word is the temperature's range alone.
      ...(a.needs.length?{pill:a.needs[0]==='heat'&&a.features?.warmth?.slight?'Un peu frais':NEED_PILLS[a.needs[0]]??'À surveiller',level:'neutral' as Level,...(opened?{}:{disk:NEED_DISKS[a.needs[0]]??'info'})}:{})};}
  switch(a.reason){
    case 'within_comfort': return {title:'Rien à faire',line:html`${deg(ti)}, ${b('dans votre plage')}`,disk:opened?'open':'check',cap:opened?'Fenêtre ouverte':undefined};
    case 'rain_open_windows': return {title:'Fermez, il pleut',line:html`La pluie ${b('entre par les ouvrants exposés')}`,disk:'rain'};
    case 'gust_open_windows': return {title:'Fermez, vent fort',line:html`Les rafales ${b('dépassent votre seuil')}`,disk:'shut'};
    case 'alarm_open': return {title:'Refermez',line:html`L’alarme est armée ${b(a.features?.household?.alarm?.state==='armed_night'?'pour la nuit':'en absence')}`,disk:'shut'};
    case 'rain_soon': return {title:'Refermez avant la pluie',line:html`Pluie ${b(rainWhen(a))}`,disk:'rain'};
    case 'opening_blocked': {
      const why=constraint==='rain_soon'?`Pluie ${rainWhen(a)}`:constraint?constraintLabels[constraint]??constraint:'Contrainte extérieure';
      return {title:a.action==='fermer'?'Refermez':'Gardez fermé',line:html`${b(why)}${a.needs.length?' : le besoin attendra':''}`,disk:a.action==='fermer'?'shut':'window'};
    }
    case 'short_air_change': return {title:a.action==='ok'?'Aération en cours':'Aérez 5 minutes',line:html`${a.needs.includes('air')?'Air à renouveler':'Humidité à évacuer'}, ${b(shortWhy(a.constraints))}`,disk:'open',cap:a.action==='ok'?undefined:'Puis refermez'};
    case 'air_needed': return airing('Aérez','Renouvelez l’air',airWhy(v));
    case 'cooling_possible': return airing('Ouvrez','Ouvrez pour rafraîchir',temps);
    case 'precool_possible': return {title:a.action==='ok'?'Laissez ouvert cette nuit':'Ouvrez pour la nuit',line:html`Demain sera chaud : ${b('stockez le frais')}`,disk:'moon',cap:first};
    case 'precool_later':
    case 'cooling_unavailable':
      return slot&&slot.kind==='open'?{title:`Ouvrez vers ${hour(slot.time)}`,line:html`Il fera ${b(number(slot.temperature)+' °C')} dehors`,disk:'moon',cap:slot.wind_bearing!=null?windFrom(slot.wind_bearing):undefined}
        :{title:'Gardez fermé',line:html`Il ne fait ${b('pas plus frais dehors')} pour l’instant`,disk:'clock'};
    case 'shared_volume': {
      // Rooms open onto each other share one air: this one follows the room whose reason weighs more.
      const vol=a.features?.volume,lead=vol?.lead??'La pièce voisine',why=vol?SHARED[vol.reason]??'le demande':'le demande';
      const line=html`${b(lead)} ${why}`;
      return a.action==='fermer'?{title:'Refermez',line,disk:'shut',cap:'Même air'}
        :a.action==='ok'?{title:'Laissez ouvert',line,disk:'open',cap:'Même air'}
        :{title:'Aérez',line,disk:'open',cap:first??'Même air'};
    }
    case 'drying_possible': {const out=airing('Aérez','Aérez pour assécher',water);
      // « Environ 66 % après l’aération » from this room's own airings: its flask, even before « Conseil optimisé ».
      return (drying?.openings??0)>=5&&!out.learned?{...out,learned:`d’après ${drying!.openings} aérations`}:out;}
    case 'drying_later': {const later=drying?.later;
      // The figure comes from this room's own airings once five are learned: the pill says it with its flask.
      return later?{title:`Aérez vers ${hour(later.time)}`,line:html`L’air sera plus sec : ${b('environ '+Math.round(later.after)+' %')} après ${later.minutes} min`,disk:'clock',...((drying?.openings??0)>=5?{learned:`d’après ${drying!.openings} aérations`}:{})}
        :{title:'Aérez plus tard',line:water,disk:'clock'};}
    case 'drying_slow': {
      const vmc=a.features?.air?.ventilation;
      const line=drying?slowWindow(drying):water;
      return {title:'Lancez la VMC',line,disk:'vmc',cap:'Aérer assèche peu ici'};
    }
    case 'ventilation_possible': return {title:'Lancez la VMC',line:html`${b(number(hi)+' %')} d’humidité, la fenêtre la baisse à peine`,disk:'vmc',cap:'Elle assèchera mieux'};
    case 'exchange_harmful': return {title:'Refermez',line:html`L’air du dehors ${b(a.temperature_delta!==null&&a.temperature_delta>0?'réchauffe la pièce':'refroidit la pièce')}`,disk:'shut'};
    case 'rehumidification_risk': return {title:'Refermez',line:incoming!=null?water:html`L’air du dehors ${b('est plus humide')}`,disk:'shut'};
    // A cold room asks for a gesture only when someone is home and the heating is off.
    case 'heat_needed': return a.action==='fermer'?{title:'Refermez',line:html`Pièce fraîche : ${b(deg(ti))}`,disk:'shut'}
      :{title:'Rallumez le chauffage',line:html`${b(deg(ti))}, sous votre plage`,disk:'heat',cap:'Le chauffage est coupé'};
    case 'sun_entering': return {title:'Fermez côté soleil',line:html`Le soleil ${b('chauffe la pièce')}`,disk:'shut'};
    case 'shutter_protection': return {title:'Adaptez les volets',line:html`Le soleil ${b('tape sur une façade')}`,disk:'window'};
    case 'optional_air_change': return {title:'Aérez si possible',line:html`CO₂ ${b(number(numeric(o.co2))+' ppm')}`,disk:'open'};
    case 'verify_exterior': {
      const gesture=a.needs.includes('air')?'Renouvelez l’air':a.needs.includes('cool')?'Ouvrez pour rafraîchir':a.needs.includes('dry')?'Aérez pour assécher':'Vérifiez dehors';
      return {title:gesture,line:html`${outsideGaps(v)} : ${b('regardez dehors avant')}`,disk:'ask',cap:'Si le temps le permet'};
    }
    case 'incomplete_data': {
      // One or two secondary sensors silent, nothing else to say: a calm banner, the silent tile shows it.
      return failed.length?{title:'Rien à faire',line:html`${b(coverageText(v).replace(/^Mesures à vérifier : /,''))} ne répond pas`,disk:'check',pill:failed.length>1?'Capteurs muets':'Un capteur muet',level:'neutral'}
        :{title:'Bilan partiel',line:html`${b('Rien à signaler')} dans les mesures connues`,disk:'check'};
    }
  }
  // Any other combination still names a gesture, from the action, never the level's word.
  return a.action==='fermer'?{title:'Refermez',line:'',disk:'shut'}:a.action==='ouvrir'?{title:'Aérez',line:'',disk:'open'}:{title:'Rien à faire',line:'',disk:'check'};
}
/** A window that renews little air: what it would really gain, never « 85 → 85 % ». */
const slowWindow=(d:{gain:number}):TemplateResult=>{const g=Math.round(d.gain);
  return g<1?html`Aérer ${b('ne la baisserait presque pas')}`:html`Aérer ne la baisserait ${b(`que de ${g} point${g>1?'s':''}`)}`;};
/** A gesture the twin has learned in this room: the predicted result replaces the general explanation. */
function withLearning(v:View,out:Advice):Advice {
  const l=v.assessment.features?.learned;
  // « Refermez », learned: what the open window takes from the room in half an hour.
  if(l?.closing&&v.assessment.action==='fermer')
    return {...out,line:html`Ouverte, ${b(number(l.now)+' → '+number(l.after)+' °C')} en ${l.minutes} min`,learned:'appris dans cette pièce',pill:'Conseil optimisé'};
  if(!l||!['ouvrir','ok'].includes(v.assessment.action))return out;
  const unit=l.measure==='temperature'?' °C':l.measure==='co2'?' ppm':l.measure==='voc'?'':' %',fmt=(x:number)=>l.measure==='temperature'?number(x):number(Math.round(x));
  const label=l.measure==='co2'?'CO₂ ':l.measure==='voc'?'COV ':'';
  // The learned duration replaces the general span: the title and the promise say the same minutes.
  const title=v.assessment.action==='ouvrir'&&/^(Aérez|Ouvrez) /.test(out.title)?`${out.title.split(' ')[0]} ${l.minutes} min`:out.title;
  return {...out,title,line:html`${label}${b(fmt(l.now)+' → '+fmt(l.after)+unit)} en ${l.minutes} min`,learned:`d’après ${l.openings} aérations`,pill:'Conseil optimisé'};
}
/** Where the twin stands, when the advice is only estimated: said in « À savoir », never in the banner. */
function learning(v:View):Fact|null {
  const t=v.twin,gestureNow=['action','urgent','benefit'].includes(v.assessment.level);
  // Only a gesture that announces a result (open, keep open) can have it estimated: « Refermez » promises none.
  if(!t||!gestureNow||v.assessment.features?.learned||!['ouvrir','ok'].includes(v.assessment.action)||unreadable(v))return null;
  // What the gesture is about, and what that measure still lacks: its result is then estimated.
  const g=t.progress,a=v.assessment,ready=g?.ready;
  if(g&&ready){
    const kind=a.reason==='drying_possible'||a.reason==='ventilation_possible'?'humidity':['air_needed','short_air_change','optional_air_change'].includes(a.reason)?'air'
      :['cooling_possible','precool_possible'].includes(a.reason)?'temperature':null;
    if(!kind)return null;
    const n=g.seen.airings,p=t.precision,week=t.status==='ready'&&t.days>=7;
    const why=!week?`${Math.max(1,Math.floor(t.days))} jour${Math.floor(t.days)>1?'s':''} de mesures sur 7`
      :kind==='humidity'?(n<5?`humidité : ${n} aération${n>1?'s':''} sur 5`:!p||p.humidity>3?'humidité : prévisions pas encore assez justes':null)
      :kind==='temperature'?((g.seen.open??6)<6?'température : fenêtre pas assez ouverte ce mois-ci':!p||p.temperature>0.5?'température : prévisions pas encore assez justes':null)
      :'air : pas encore vu fenêtre ouverte';
    return why?{ic:'clock',title:'Apprentissage',text:`${why}, résultat estimé`}:null;}
  // A room is learned after a week of measures at least, then only if its twin replays the last day well.
  if(t.status!=='ready'||t.days<7)return {ic:'clock',title:'Apprentissage',text:`en cours : ${Math.max(1,Math.floor(t.days))} jour${Math.floor(t.days)>1?'s':''} sur 7`};
  if(!t.precision)return {ic:'clock',title:'Apprentissage',text:'vérification en attente : il manque une journée de mesures complète'};
  if(t.precision.temperature>0.5||t.precision.humidity>3)return {ic:'clock',title:'Apprentissage',text:'en cours : prévisions pas encore assez justes, conseil estimé'};
  return null;
}
/** « À savoir »: what is worth knowing about the room, under the advice. Never a gesture, one idea per line. */
export interface Fact {ic:string;title:string;text:TemplateResult|string}
export function facts(v:View):Fact[] {
  const a=v.assessment,o=v.observations,f=a.features,ti=numeric(o.indoor_temperature),out:Fact[]=[];
  // A room that cannot be read has no advice to explain: the banner sends to « Mesures ».
  if(unreadable(v))return out;
  const hum=f?.humidity,w=f?.warmth,air=f?.air,vol=f?.volume;
  if(hum?.status==='low')out.push({ic:'drop',title:'Air sec',text:hum.reachable!=null&&hum.measured!=null
    ?hum.reachable<hum.measured?'aérer assécherait davantage la pièce':hum.reachable>hum.measured?'l’air extérieur pourrait augmenter l’humidité ; le conseil tient aussi compte de la température':'aérer ne changerait pas l’humidité'
    :'effet de l’aération inconnu sans mesure extérieure'});
  if(hum?.trend==='improving'&&hum.degree)out.push({ic:'drop',title:'Humidité',text:'revient vers votre plage'});
  else if(hum?.lasting&&hum.degree)out.push({ic:'clock',title:'Humidité',text:hum.status==='low'?'sous votre plage depuis plusieurs heures':'au-dessus de votre plage depuis plusieurs heures'});
  if(a.reason==='shared_volume'&&vol)out.push({ic:'home',title:'Même air',text:`conseil commun avec : ${vol.lead}`});
  if(a.reason==='open_neutral')out.push({ic:'open',title:'Fenêtre ouverte',text:a.needs.includes('dry')?'elle ne fait presque pas baisser l’humidité, vous pouvez refermer':'sans effet sur le confort, vous pouvez refermer'});
  // Opening held back: what holds it, in words.
  // Only under « Rien à faire »: a « Gardez fermé » banner already names it. An open sheltered window may stay open.
  if(a.reason==='opening_blocked'&&a.action!=='fermer'&&['calm','neutral'].includes(a.level)){const c=a.constraints[0],open=Object.entries(o).some(([k,r])=>k.startsWith('window:')&&r.quality==='valid'&&r.value===true);
    out.push({ic:'shut',title:open?'Autres fenêtres':'Fenêtres',text:`à garder fermées : ${c==='rain_soon'?'pluie imminente':c?(constraintLabels[c]??c).toLowerCase():'contrainte extérieure'}`});}
  // « Refermez » in a damp room: why the airing is not kept for the humidity.
  const gain=f?.drying?.gain;
  if(a.reason==='exchange_harmful'&&a.needs.includes('dry'))
    out.push({ic:'drop',title:'Humidité',text:gain!=null&&gain<4?`l’aération ne la baisserait que ${gain<1.5?'d’un point à peine':`de ${Math.round(gain)} points`}`:'l’aération ne la ferait pas assez baisser'});
  if(a.reason==='heat_needed'&&a.action!=='fermer'&&a.level!=='action')
    out.push({ic:'temp',title:'Pièce fraîche',text:w?.outdoor_warms?'l’air du dehors, plus chaud, la réchauffe : vous pouvez laisser ouvert'
      :w?.occupied===false?(f?.people?.away?.length?`${f.people.away.join(' et ')} ${f.people.away.length>1?'absents':'absent'} : pas besoin de chauffer`:'maison vide : pas besoin de chauffer')
      :w?.thermostat?.lowered?`thermostat en ${presetWord(w.thermostat.preset)}${w.thermostat.target!=null?` : ${deg(w.thermostat.target)} visés`:''}`
      :w?.thermostat?.off_reason&&w.thermostat.off_reason!=='manual'?`chauffage arrêté par le thermostat (${offWords[w.thermostat.off_reason]??'automatique'}), il repartira seul`
      :w?.heating==='on'?'le chauffage s’en charge':w?.warming?`${deg(ti)}, elle se réchauffe d’elle-même`
      :w?.heating==='off'?`${deg(ti)}, un peu sous votre plage · chauffage coupé`:`${deg(ti)}, sous votre plage`});
  // Tonight, simulated on the room's twin (after NADIR): the hours to open and what it leaves for tomorrow's peak.
  const plan=f?.night,warm=a.needs.includes('cool')||a.needs.includes('precool')||['cooling_possible','precool_possible','precool_later','cooling_unavailable'].includes(a.reason);
  if(plan?.worth&&warm&&plan.windows.length){const w0=plan.windows[0];
    out.push({ic:'clock',title:'Cette nuit',text:`ouvrez de ${hour(w0.start)} à ${hour(w0.end)} · ${number(plan.gain)} °C de mieux demain au plus chaud${plan.humid?' · air humide':''}`});}
  // Who the room is for, and the alarm (engine/people.py).
  const hh=f?.household,ppl=f?.people;
  if(hh?.away_open)out.push({ic:'window',title:'Fenêtre ouverte',text:ppl?.away?.length?`${ppl.away.join(' et ')} ${ppl.away.length>1?'sont absents':'est absent'}`:'personne à la maison'});
  if(hh?.empty_room)out.push({ic:'open',title:'Pièce vide',text:'le bon moment pour aérer longuement'});
  if(hh?.sleeping&&a.action==='ouvrir'&&!['air_needed','short_air_change'].includes(a.reason))out.push({ic:'clock',title:'Nuit',text:'si vous dormez, aérez plutôt au réveil'});
  // A window no contact of the room watches, seen open by the thermostat (its temperature drop).
  if(f?.thermostat?.window)out.push({ic:'window',title:'Fenêtre ouverte',text:`vue par ${f.thermostat.name}`});
  // Words for everyone: the risk and where it comes from, never a percentage against a wall.
  // The cause is not guessed: after days of rain, walls and fabrics give back water without a shower or a meal.
  if(hum?.mould)out.push({ic:'drop',title:'Humidité élevée',text:'risque de moisissure'});
  // The mould line already says it comes from the weather: one line, not two.
  // Asked to open for the air, « airing would not lower the humidity » would read as a contradiction.
  if(hum?.source==='outside'&&!hum.mould)out.push({ic:'drop',title:'Air humide dehors',text:['ouvrir','ok'].includes(a.action)&&['action','urgent','benefit'].includes(a.level)?'l’humidité restera la même':'aérer ne ferait pas baisser l’humidité'});
  else if(a.reason==='drying_unavailable')out.push({ic:'open',title:'Aération',text:'n’aiderait pas, l’air du dehors n’est pas plus sec'});
  else if(a.reason==='drying_slow')out.push({ic:'open',title:'Aération',text:'ferait à peine baisser l’humidité'});
  if(hum?.local)out.push({ic:'drop',title:'Vapeur',text:'plus humide ici qu’à côté : cuisson ou douche'});
  if(air?.purifier?.on===true)out.push({ic:'fan',title:'Purificateur',text:'en marche, il filtre l’air'});
  if(air?.ventilation?.on===true)out.push({ic:'vmc',title:'VMC',text:a.needs.includes('dry')?'en marche, elle aide à assécher':'en marche'});
  // The season's rules, said where they change the advice.
  const winter=f?.season?.group==='winter';
  if(winter&&a.needs.includes('cool')&&!['ouvrir','ok'].includes(a.action)&&o.heating)
    out.push({ic:'temp',title:'Pièce chaude',text:'baissez le chauffage plutôt que d’ouvrir'});
  if(winter&&a.reason==='drying_possible'&&a.action==='ouvrir')
    out.push({ic:'open',title:'Aération d’hiver',text:'courte et franche, à refaire dans la journée : les murs restent chauds'});
  // What the sun does for the room now. Asked to open, « keep the window shut » would contradict the gesture.
  const opening=['ouvrir','ok'].includes(a.action)&&['action','urgent','benefit'].includes(a.level);
  for(const x of f?.benefits??[]){
    if(x.kind==='sun_warms')out.push({ic:'sun',title:'Soleil',text:x.keep_shut&&!opening?'il réchauffe la pièce : volets et rideaux ouverts, fenêtre fermée':'il réchauffe la pièce : volets et rideaux ouverts'});
    if(x.kind==='sun_heats')out.push({ic:'sun',title:'Soleil',text:'il chauffe la pièce : baissez le volet ou le store'});}
  // A confirmed habit names the cause of the humidity, only while it is going on.
  if(v.habit&&(a.needs.includes('dry')||hum?.mould))out.unshift({ic:'drop',title:'Humidité',text:v.habit});
  // A damp room with no gesture for it always says why the humidity stays.
  const said=out.some(x=>/umidit|Aération|Vapeur|VMC|Même air/.test(x.title+x.text));
  // « Gardez fermé … le besoin attendra » already says it.
  const waiting=a.reason==='opening_blocked'&&!['calm','neutral'].includes(a.level);
  if(a.needs.includes('dry')&&!said&&!waiting&&!['drying_possible','drying_later','ventilation_possible','short_air_change'].includes(a.reason))
    out.push({ic:'drop',title:'Humidité',text:a.reason==='heat_needed'||a.needs.includes('heat')?'aérer refroidirait une pièce déjà fraîche'
      :a.reason==='opening_blocked'?'elle attendra que l’on puisse aérer'
      // Asked to open for the air: the same words as the gesture, not a denial of it.
      :['ouvrir','ok'].includes(a.action)&&['action','urgent','benefit'].includes(a.level)?'l’aération la baissera peu'
      :gain!=null&&gain<4?`l’aération ne la baisserait que ${gain<1.5?'d’un point à peine':`de ${Math.round(gain)} points`}`:'l’aération ne la ferait pas assez baisser'});
  // The last airing followed: what it gave, against what was predicted.
  const last=v.feedback?.last;
  if(last){const f=(x:number)=>last.measure==='temperature'?number(x):number(Math.round(x)),u=last.measure==='temperature'?' °C':last.measure==='co2'?' ppm':last.measure==='voc'?'':' %';
    const what=last.measure==='humidity'?'humidité ':last.measure==='temperature'?'température ':last.measure==='co2'?'CO₂ ':'COV ';
    out.push({ic:'open',title:'Dernière aération',text:`${what}${f(last.before)} → ${f(last.after)}${u}${last.predicted!=null?` (prévu ${f(last.predicted)}${u})`:''}`});}
  const l=learning(v);if(l)out.push(l);
  return out.slice(0,4);
}
/** The « À savoir » box, under the advice; nothing when there is nothing to know. */
export function factBox(v:View,partners:View[]=[]):TemplateResult|typeof nothing {
  // One card for one air: « Même air » goes without saying, and a line said by two rooms is said once.
  // The card's room cannot be read: its banner sends to « Mesures », the other rooms' lines would explain no advice.
  if(unreadable(v))return nothing;
  const seen=new Set<string>(),list=[v,...partners].flatMap(r=>facts(r)).filter(f=>(!partners.length||f.title!=='Même air')&&!seen.has(f.title)&&!!seen.add(f.title)).slice(0,4);
  return list.length?html`<div class="nc-facts"><div class="nw-label">À savoir</div><ul>${list.map(f=>html`<li>${icon(f.ic)}<span><b>${f.title}</b> · ${f.text}</span></li>`)}</ul></div>`:nothing;
}
/** Why the room that leads a shared air asks for its gesture, after its name. */
const SHARED:Record<string,string>={air_needed:'a besoin d’air',short_air_change:'a besoin d’air',cooling_possible:'se rafraîchit',
  drying_possible:'s’assèche',precool_possible:'stocke le frais',rain_soon:'attend la pluie',rain_open_windows:'prend la pluie',
  gust_open_windows:'prend le vent',alarm_open:'est ouverte, alarme armée',opening_blocked:'doit rester fermé',exchange_harmful:'se dérègle',rehumidification_risk:'reprend l’humidité',
  heat_needed:'est trop fraîche',sun_entering:'prend le soleil'};
/** When the rain starts: to the minute from the radar, only « within the hour » from the hourly forecast. */
function rainWhen(a:View['assessment']):string {
  const m=a.rain_soon_minutes,precise=a.features?.rain_ahead?.precise;
  if(m==null||!precise)return 'annoncée dans l’heure';
  return m<=2?'imminente':`dans ${m} min`;
}
/** Outdoor sources the advice could not check: never configured (« non suivi ») or configured but silent (« indisponible »). */
const OUTSIDE:Record<string,[string,boolean]>={rain:['pluie',true],pollution:['air extérieur',false],outdoor_temperature:['température dehors',true],outdoor_humidity:['humidité dehors',true],wind_gust:['rafales',true]};
export function outsideGaps(v:View):string {
  const a=v.assessment,pick=(keys:string[])=>keys.filter(k=>k in OUTSIDE).map(k=>OUTSIDE[k]);
  const absent=pick(a.unverified??[]),silent=pick(a.missing.filter(k=>!!v.observations[k]));
  // French agreement: feminine only when every name is feminine; « rafales » is already plural.
  const part=(names:[string,boolean][],word:(fem:boolean,plural:boolean)=>string)=>names.length?`${names.map(n=>n[0]).join(' et ')} ${word(names.every(n=>n[1]),names.length>1||names.some(n=>n[0].endsWith('s')))}`:'';
  const text=[part(silent,(f,pl)=>'indisponible'+(pl?'s':'')),part(absent,(f,pl)=>'non suivi'+(f?'e':'')+(pl?'s':''))].filter(Boolean).join(', ');
  return text?text[0].toUpperCase()+text.slice(1):'Extérieur à vérifier';
}
function airWhy(v:View):TemplateResult {
  const o=v.observations,air=v.assessment.features?.air,parts:string[]=[];
  if(air?.co2_status==='high')parts.push(`CO₂ ${number(numeric(o.co2))} ppm`);
  if(air?.pm25_status==='high')parts.push('particules élevées');
  if(air?.voc_status==='high')parts.push('COV élevés');
  return html`${b(parts.join(', ')||'Air à renouveler')}`;
}

export interface Slide extends Advice {level:Level;pill:string}
/** Every advice of the moment, the main one first: what to do, then the remedies already at work and what Niak cannot check. */
export function slides(v:View,blocks:readonly BannerBlock[]=['remedies','later']):Slide[] {
  const a=v.assessment,main=advice(v),out:Slide[]=[{...main,level:main.level??a.level,pill:main.pill??pills[a.level]}];
  // Remedies at work (purifier, ventilation) are information: they are in « À savoir », not in the banner.
  // What Niak cannot check is information, not advice: it stays in « Détails ».
  const later=a.features?.drying?.later;
  if(blocks.includes('later')&&later&&a.reason==='drying_possible')out.push({level:'benefit',pill:'Plus tard',title:`Encore mieux vers ${hour(later.time)}`,line:html`L’air sera plus sec : ${b('environ '+Math.round(later.after)+' %')}`,disk:'clock'});
  if(blocks.includes('later')&&a.slot&&a.slot.kind==='open'&&!['cooling_unavailable','precool_later'].includes(a.reason))out.push({level:'benefit',pill:'Plus tard',title:`Ouvrez vers ${hour(a.slot.time)}`,line:html`Il fera ${b(number(a.slot.temperature)+' °C')} dehors`,disk:'moon'});
  return out;
}

export interface ScaleInput {band?:[number,number]|null;day?:{min:number;max:number}|null;now?:number|null;out?:number|null;
  rooms?:{name:string;short:string;value:number;level:Level;entity?:string}[];unit?:string;nowEntity?:string;outEntity?:string}
/** The charter's scale (as Niak Weather's « Ressenti »): a thin track, your range, a ring with its value; labels never overlap. */
export function scale(s:ScaleInput):TemplateResult {
  const values=[s.band?.[0],s.band?.[1],s.day?.min,s.day?.max,s.now,s.out,...(s.rooms??[]).map(r=>r.value)].filter((x):x is number=>typeof x==='number'&&Number.isFinite(x));
  if(!values.length)return html``;
  let lo=Math.floor(Math.min(...values)-1.5),hi=Math.ceil(Math.max(...values)+1.5);
  if(hi-lo<8){const pad=(8-(hi-lo))/2;lo=Math.floor(lo-pad);hi=Math.ceil(hi+pad);}
  const pos=(x:number)=>(Math.min(hi,Math.max(lo,x))-lo)/(hi-lo)*100,pct=(x:number)=>pos(x).toFixed(2)+'%';
  const fmt=(x:number)=>number(Math.round(x*10)/10),unit=s.unit??'°C';
  const labels:{x:number;text:TemplateResult|string;len:number;row:'up'|'down';strong:boolean}[]=[];
  if(s.band)labels.push({x:pos(s.band[0]),text:fmt(s.band[0])+' '+unit,len:7,row:'down',strong:false},{x:pos(s.band[1]),text:fmt(s.band[1])+' '+unit,len:7,row:'down',strong:false});
  if(s.out!=null)labels.push({x:pos(s.out),text:'dehors '+fmt(s.out)+' '+unit,len:14,row:'down',strong:true});
  if(s.rooms){
    // Rooms a few tenths apart share one label (« S·C »): every room stays named.
    const sorted=[...s.rooms].sort((x,y)=>x.value-y.value),groups:typeof sorted[]=[];
    for(const r of sorted){const g=groups[groups.length-1];if(g&&pos(r.value)-pos(g[g.length-1].value)<4.5)g.push(r);else groups.push([r]);}
    groups.forEach((g,i)=>{const t=g.map(r=>r.short).join('·');labels.push({x:g.reduce((sum,r)=>sum+pos(r.value),0)/g.length,text:html`<b>${t}</b>`,len:t.length,row:i%2?'down':'up',strong:true});});
  }
  const taken:[number,number,string][]=s.now!=null?[[pos(s.now)-10,pos(s.now)+10,'up']]:[];
  const placed=labels.sort((x,y)=>Number(y.strong)-Number(x.strong)).flatMap(l=>{
    const half=l.len*6.6/320*100/2+1.5,free=(row:string)=>taken.every(([a,z,r])=>r!==row||l.x+half<a||l.x-half>z);
    const row=free(l.row)?l.row:l.strong&&free(l.row==='up'?'down':'up')?(l.row==='up'?'down':'up'):null;
    if(!row)return [];taken.push([l.x-half,l.x+half,row]);
    const style=l.x<8?'left:0;transform:none':l.x>92?'right:0;left:auto;transform:none':`left:${l.x.toFixed(2)}%`;
    return [html`<span class=${'nc-lb'+(row==='up'?' up':'')} style=${style}>${l.text}</span>`];
  });
  // The bubble stays inside the frame when the value sits near an end of the scale.
  const bubble=(x:number)=>x<12?'left:0;transform:none':x>88?'right:0;left:auto;transform:none':'left:'+x.toFixed(2)+'%';
  // Temperature only: the track says too cool (blue) and too warm (orange) around the range; the last 24 hours are a
  // thin whisker over it, so the range always shows through.
  const zones=unit==='°C';
  const said=[s.now!=null?`Maintenant ${fmt(s.now)} ${unit}`:'',s.band?`plage ${fmt(s.band[0])} à ${fmt(s.band[1])} ${unit}`:'',s.out!=null?`dehors ${fmt(s.out)} ${unit}`:''].filter(Boolean).join(', ');
  return html`<div class="nc-scale" role="img" aria-label=${said}>
    <div class="nc-track"></div>
    ${s.band&&zones?html`<div class="nc-zone cold" style=${`left:0;width:${pct(s.band[0])}`}></div><div class="nc-zone warm" style=${`left:${pct(s.band[1])};right:0`}></div>`:nothing}
    ${s.band?html`<div class=${'nc-band'+(zones?' zoned':'')} style=${`left:${pct(s.band[0])};width:${(pos(s.band[1])-pos(s.band[0])).toFixed(2)}%`}></div>`:nothing}
    ${s.day?html`<div class="nc-day" style=${`left:${pct(s.day.min)};width:${(pos(s.day.max)-pos(s.day.min)).toFixed(2)}%`}></div>`:nothing}
    ${s.out!=null?(s.outEntity?html`<button type="button" class="nc-mk out nc-hit" style=${'left:'+pct(s.out)} title="Détails : dehors" aria-label="Détails de la température dehors" @click=${(e:Event)=>moreInfo(e,s.outEntity!)}></button>`:html`<span class="nc-mk out" style=${'left:'+pct(s.out)}></span>`):nothing}
    ${(s.rooms??[]).map(r=>r.entity?html`<button type="button" class="nc-mk room nc-hit" data-level=${r.level} style=${'left:'+pct(r.value)} title=${r.name+' '+fmt(r.value)+' '+unit} aria-label=${'Détails : '+r.name} @click=${(e:Event)=>moreInfo(e,r.entity!)}></button>`:html`<span class="nc-mk room" data-level=${r.level} style=${'left:'+pct(r.value)} title=${r.name+' '+fmt(r.value)+' '+unit}></span>`)}
    ${s.now!=null?html`<span class="nc-ring" style=${'left:'+pct(s.now)}></span>${s.nowEntity?html`<button type="button" class="nw-pill nc-now nc-hit" style=${bubble(pos(s.now))} title="Détails de la température" @click=${(e:Event)=>moreInfo(e,s.nowEntity!)}>${fmt(s.now)} ${unit}</button>`:html`<span class="nw-pill nc-now" style=${bubble(pos(s.now))}>${fmt(s.now)} ${unit}</span>`}`:nothing}
    ${placed}
  </div>
  <div class="nw-legend nc-legend">${s.band&&zones?html`<span><i class="k-zone cold"></i>trop frais</span>`:nothing}${s.band?html`<span><i class=${'k-band'+(zones?' zoned':'')}></i>votre plage</span>`:nothing}${s.band&&zones?html`<span><i class="k-zone warm"></i>trop chaud</span>`:nothing}${s.day?html`<span><i class="k-day"></i>min–max 24 h</span>`:nothing}${s.rooms?html`<span><i class="k-room"></i>pièces</span>`:nothing}${s.out!=null?html`<span><i class="k-out"></i>dehors</span>`:nothing}</div>`;
}

/** `watch` (soft yellow): the measure leaves your range, without a gesture asked; orange stays for gestures. */
/** A partner room's temperature, as a tile: the scale above shows only the chosen room. */
function roomTemperature(p:View):Tile[] {
  const t=numeric(p.observations.indoor_temperature),n=p.assessment.needs,out=n.includes('cool')||n.includes('heat');
  return t===null?[]:[{ic:'temp',label:'Température',value:number(t),unit:'°C',note:n.includes('cool')?'trop chaud':n.includes('heat')?(p.assessment.features?.warmth?.slight?'un peu frais':'trop frais'):'dans votre plage',level:out?'watch':'calm',out,entity:p.observations.indoor_temperature?.source??undefined}];
}
export interface Tile {ic:string;label:string;value:string;unit?:string;note:string;level:Level|'watch';out:boolean;entity?:string;
  /** A device at work (purifier, ventilation): framed like a measure, never counted out of your range. */
  remedy?:boolean}
/** Opens Home Assistant's own details window (history, attributes) for an entity, as any dashboard card does. */
export const moreInfo=(e:Event,entityId:string)=>{e.stopPropagation();(e.currentTarget as HTMLElement).dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId},bubbles:true,composed:true}));};
/** The entity behind each tile: the one a tap opens. */
function tileEntity(v:View,label:string):string|undefined {
  const o=v.observations,src=(k:string)=>o[k]?.source??undefined;
  if(label==='Fenêtres'){const contacts=Object.entries(o).filter(([k])=>k.startsWith('window:'));const open=contacts.find(([,r])=>r.value===true);return (open??contacts[0])?.[1].source??undefined;}
  return ({'Humidité':src('indoor_humidity'),'CO₂':src('co2'),'Particules':src('pm25'),'COV':src('voc'),'Soleil':src('solar'),'Purificateur':src('purifier'),
    'Ventilation':o.ventilation_boost?.value===true?src('ventilation_boost'):src('ventilation')??src('ventilation_boost'),'Chauffage':src('heating')} as Record<string,string|undefined>)[label];
}
/** One compact frame per measure; it takes the level's outline when the measure leaves your range. */
/** Thermostat modes in plain French (presets first, then the plain heating mode). */
const modeLabels:Record<string,string>={frost:'hors gel',eco:'éco',comfort:'confort',boost:'boost',away:'absence',sleep:'nuit',home:'présence',activity:'activité',off:'éteint',heat:'chauffage',auto:'programmé',heat_cool:'automatique'};
/** Why a measure has no value: silent for too long is not the same as gone. */
const gone=(r?:{quality:string})=>r?.quality==='stale'?'pas de nouvelle mesure':'indisponible';
/** « 13 h 50 », in the person's own clock. */
const clock=(x?:string|null)=>{const d=x?new Date(x):null;return d&&!isNaN(+d)?d.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}).replace(':',' h '):null;};
/** The source behind a tile, to know whether it is read from the room sharing this air. */
const tileKeys:Record<string,string>={'CO₂':'co2',Particules:'pm25',COV:'voc',Purificateur:'purifier',Ventilation:'ventilation',Chauffage:'heating'};
/** A room's tiles without those it reads from another room: on a card shared by both, each measure shows once. */
const ownTiles=(v:View,list:Tile[])=>list.filter(t=>!v.inherited?.[tileKeys[t.label]??'']);
export function tiles(v:View,config:Config):Tile[] {
  const o=v.observations,a=v.assessment,mods=new Set(config.modules??[]),list:Tile[]=[],air=a.features?.air;
  if(mods.has('humidity')&&o.indoor_humidity){const h=numeric(o.indoor_humidity),hum=a.features?.humidity,wet=a.needs.includes('dry'),outside=hum?.source==='outside',out=h!==null&&(hum?.degree!==undefined?hum.degree>=2:wet);
    list.push({ic:'drop',label:'Humidité',value:number(h),unit:'%',note:h===null?gone(o.indoor_humidity):(humidityLabel(v)?.toLowerCase()??(outside?'humide dehors aussi':'normale')),level:out?'watch':'calm',out});}
  if(mods.has('air')&&o.co2){const c=numeric(o.co2),high=air?.co2_status==='high';
    list.push({ic:'air',label:'CO₂',value:number(c),unit:'ppm',note:c===null?gone(o.co2):high?'à renouveler':'normal',level:high?(a.level==='urgent'?'urgent':'watch'):'calm',out:high});}
  if(mods.has('air'))for(const [key,ic,label,status] of [['pm25','pm','Particules',air?.pm25_status],['voc','flask','COV',air?.voc_status]] as const){
    if(!o[key])continue;const x=numeric(o[key]),high=status==='high',treated=key==='pm25'&&high&&air?.pm25_treated===true;
    list.push({ic,label,value:number(x),unit:o[key].unit??'',note:x===null?gone(o[key]):treated?'filtrées':high?'élevés':status==='uninterpreted'?'sans seuil':key==='pm25'?'normales':'normaux',level:treated?'calm':high?'watch':status==='ok'?'calm':'neutral',out:high});}
  if(mods.has('windows')){const contacts=Object.entries(o).filter(([k])=>k.startsWith('window:')).map(([,r])=>r);
    if(contacts.length){const open=contacts.filter(r=>r.quality==='valid'&&r.value===true).length,flagged=(a.openings??[]).some(x=>x.flags.length>0&&x.open===true);
      list.push({ic:open?'open':'window',label:'Fenêtres',value:`${open}/${contacts.length}`,note:flagged?'à refermer':open?(open>1?`${open} ouvertes`:'1 ouverte'):'toutes fermées',level:flagged?'action':'neutral',out:flagged});}}
  if(mods.has('shutters')){const s=a.sun,solar=numeric(o.solar),entering=(a.openings??[]).some(x=>x.flags.includes('sun_entering'));
    if(s||solar!==null){const night=!!s&&s.elevation<=0,value=night?'Nuit':solar===null?'—':solar<150?'Faible':solar<500?'Moyen':'Fort';
      list.push({ic:night?'moon':'sun',label:'Soleil',value,note:entering?'entre dans la pièce':night?'pas d’apport':solar===null?'non mesuré':`${number(solar)} W/m²${o.solar?.detail==='shaded_estimate'?' · estimé, station à l’ombre':''}`,level:entering?'action':'neutral',out:entering});}}
  // A connected cover: where it stands, and who moves it (Adaptive Cover Pro, the person, or nobody yet).
  if(mods.has('shutters'))for(const s of a.features?.shutters??[]){if(s.mode!=='connected')continue;
    const p=s.position,shut=p===0||(p==null&&s.state==='closed'),open=p===100||(p==null&&s.state==='open'),act=s.manual_override!==true&&!!s.advice;
    const auto=!!s.driver&&(s.driving??s.automatic===true)&&s.manual_override!==true;
    const until=clock(s.override_end),soon=s.soon?clock(s.sun_start):null;
    const note=s.manual_override===true?(until?`à la main jusqu’à ${until}`:'repris à la main'):act?(s.advice==='close'?(soon?`à fermer avant ${soon}`:'à fermer'):'à ouvrir'):auto?(s.sun_front?'automatique · soleil devant':'automatique'):s.driver&&(s.off||s.automatic===false)?({disabled:'ACP désactivé',tracking:'suivi du soleil coupé'} as Record<string,string>)[s.off??'']??'automatisme coupé':s.state==null&&p==null?'indisponible':'rien à faire';
    list.push({ic:shut?'shut':'window',label:'Volet',value:shut?'Fermé':open?'Ouvert':p!=null?number(p):'—',unit:!shut&&!open&&p!=null?'%':undefined,note,level:act?'action':auto?'calm':'neutral',out:act,entity:s.cover??undefined});}
  if(mods.has('air')&&o.purifier){const on=o.purifier.quality==='valid'?o.purifier.value===true:null,speed=numeric(o.purifier_speed);
    // Running, it is a remedy at work: framed in green, like the measure it treats.
    list.push({ic:'fan',label:'Purificateur',value:on===null?'—':on?'En marche':'Arrêté',note:on?(speed!==null?`filtre à ${number(speed)} %`:'filtre l’air'):on===false?'à l’arrêt':'indisponible',level:on?'calm':'neutral',out:on===true,remedy:true});}
  const vent=air?.ventilation;
  if(mods.has('air')&&vent){const on=vent.on,fast=vent.boost===true;
    list.push({ic:'vmc',label:'Ventilation',value:on===null?'—':fast?'Rapide':on?'En marche':'Arrêtée',note:on?(fast?'grande vitesse':'renouvelle l’air'):on===false?'à l’arrêt':'indisponible',level:on?'calm':'neutral',out:on===true,remedy:true});}
  if(mods.has('coordination')&&o.heating){const label=heatingLabels[a.heating_action]??'Inconnu',running=a.heating_action==='heating';
    const raw=o.heating_mode?.quality==='valid'&&typeof o.heating_mode.value==='string'?o.heating_mode.value:null,mode=raw?modeLabels[raw]??raw:null;
    list.push({ic:'heat',label:'Chauffage',value:running?'Chauffe':label,note:mode?`mode ${mode}`:running?'chauffe la pièce':'observé, jamais commandé',level:'neutral',out:false});}
  for(const t of list)t.entity??=tileEntity(v,t.label);
  // A measure read from the room sharing this air says where it is measured.
  for(const t of list){const from=v.inherited?.[tileKeys[t.label]??''];if(from)t.note=`${t.note} · ${from}`;}
  // Right after a start, a silent sensor is still on its way, not broken.
  return v.starting?list.map(t=>t.note==='indisponible'||t.note==='pas de nouvelle mesure'?{...t,note:'en attente'}:t):list;
}
// Only a sensor that stopped answering is drawn muted, not a measure that was never configured (« non mesuré »).
// Out of range with a gesture to make: the orange frame; without one, a discreet mark (« soft »).
const tileClass=(t:Tile,soft=false)=>'nc-tile'+(t.out?(soft?' out soft':' out'):'')+(['indisponible','pas de nouvelle mesure','en attente'].includes(t.note)?' mute':'');
export const tile=(t:Tile,soft=false)=>t.entity?html`<button type="button" class=${tileClass(t,soft)} data-level=${t.level} title=${'Détails : '+t.label} @click=${(e:Event)=>moreInfo(e,t.entity!)}>${tileBody(t)}</button>`:html`<div class=${tileClass(t,soft)} data-level=${t.level}>${tileBody(t)}</div>`;
const tileBody=(t:Tile)=>html`<div class="nc-tile-h"><span class="nc-ic">${icon(t.ic)}</span><span class="nw-label">${t.label}</span></div><b>${t.value}${t.unit&&t.value!=='—'?html`<small>${t.unit}</small>`:nothing}</b><em>${t.note}</em>`;

const row=(t:string,x:string)=>html`<li><b>${t}</b><span> · ${x}</span></li>`;
/** One short line per fact: the long explanations of 0.9 become « title · fact ». */
export function details(v:View,config:Config):TemplateResult[] {
  const a=v.assessment,f=a.features,mods=new Set(config.modules??[]),out:TemplateResult[]=[];
  const season=f?.season;
  if(season)out.push(row('Votre plage de confort',`${number(season.minimum)} à ${number(season.maximum)} °C${!season.heated?' · pièce non chauffée':''}${season.name?' · '+(SEASON_NAMES[season.name]??season.name):season.known?(season.weight===0?' · hiver':season.weight===1?' · été':' · entre-saisons'):' · saison non calculée'}`));
  if(a.action==='ouvrir'&&a.open_first?.length)out.push(row('Ouvrez d’abord',a.open_first.map(id=>v.names?.[id]??id).join(' et ')));
  // Only a complete slot is said: an hour and a temperature, never « NaN h ».
  const slotOk=!!a.slot&&typeof a.slot.temperature==='number'&&!Number.isNaN(new Date(a.slot.time).getTime());
  if(slotOk)out.push(row(a.slot!.kind==='open'?'Ouverture possible':'Fermeture conseillée',`${hour(a.slot!.time)} · ${number(a.slot!.temperature)} °C${a.slot!.wind_bearing!=null?' · '+windFrom(a.slot!.wind_bearing):''}`));
  const silent=a.missing.filter(k=>!!v.observations[k]);
  if(silent.length)out.push(row('Ne répond pas',silent.map(k=>sourceLabel(v,k)).join(', ')));
  if(a.unverified?.length&&a.action!=='fermer')out.push(row('Sans capteur',a.unverified.map(k=>k==='rain'?'pluie':'qualité de l’air dehors').join(', ')));
  const vent=f?.ventilation;
  if(mods.has('windows')&&vent){if(vent.opened_minutes!=null)out.push(row('Ouvert depuis',`${number(vent.opened_minutes)} min`));}
  if(mods.has('shutters'))for(const s of f?.shutters??[]){if(s.mode==='none'||(!s.advice&&!s.manual_override&&s.position==null))continue;
    const from=clock(s.sun_start),to=clock(s.sun_end);
    // In plain words: who sets it, where it stands, when the sun comes. Adaptive Cover Pro's own wording is left out.
    out.push(row(v.names?.[s.entity_id]??'Volet',[s.manual_override?'réglé à la main':s.advice==='close'?'à fermer':s.advice==='open'?'à ouvrir':s.driver&&(s.driving??s.automatic===true)?'piloté par Adaptive Cover Pro':'rien à faire',s.driver&&s.detection===false?'reprise à la main non détectée':'',s.driver&&s.climate===false?'mode climat coupé':'',
      s.position!=null?`ouvert à ${number(s.position)} %`:'',s.driver&&s.target!=null&&s.target!==s.position?`visé ${number(s.target)} %`:'',from&&to?`soleil de ${from} à ${to}`:''].filter(Boolean).join(' · ')));}
  if(f?.people&&(f.people.home.length||f.people.away.length))out.push(row('Personnes',[f.people.home.length?`${f.people.home.join(', ')} à la maison`:'',f.people.away.length?`${f.people.away.join(', ')} ${f.people.away.length>1?'absents':'absent'}`:''].filter(Boolean).join(' · ')));
  if(f?.household?.alarm)out.push(row('Alarme',`${f.household.alarm.name} · ${({disarmed:'désarmée',armed_away:'absence',armed_home:'à la maison',armed_night:'nuit',armed_vacation:'vacances'} as Record<string,string>)[f.household.alarm.state]??f.household.alarm.state}`));
  if(mods.has('air')&&f?.presence&&f.presence.state!=='not_configured')out.push(row('Présence',{occupied:'quelqu’un est là',empty:'pièce vide',leaving:`personne depuis ${f.presence.minutes??0} min (vide après ${f.presence.delay??5} min)`,unknown:'inconnue'}[f.presence.state]??''));
  // Where the drying promise comes from: this room's own airings, or an ordinary room until one is seen.
  if(mods.has('humidity')&&f?.drying)out.push(row('Séchage',f.drying.openings?`appris sur ${f.drying.openings} aération${f.drying.openings>1?'s':''}`:'estimé, aucune aération observée'));
  if(mods.has('humidity')&&f?.humidity&&f.humidity.condensation_risk!==null)out.push(row('Buée',f.humidity.condensation_risk?'risque estimé':'aucun risque estimé'));
  const tr=f?.trends;
  if(mods.has('temperature')&&tr&&(tr.indoor!=null||tr.outdoor!=null))out.push(row('Tendance',[tr.indoor!=null?`dedans ${tr.indoor>0?'+':''}${number(tr.indoor)} °C/h`:'',tr.outdoor!=null?`dehors ${tr.outdoor>0?'+':''}${number(tr.outdoor)} °C/h`:''].filter(Boolean).join(', ')));
  if(!silent.length)out.push(row('Sources',coverageText(v)));
  return out;
}

export interface CardState {why:boolean;tilesOpen:boolean;detailsOpen:boolean;toggle:(k:'why'|'tilesOpen'|'detailsOpen')=>void;uid:string;configure?:()=>void}
/** The « i » panel: needs, constraints and how complete the picture is, one line each. */
export function whyLines(v:View):TemplateResult {
  const a=v.assessment;
  return html`<p><b>Besoins</b> · ${a.needs.length?a.needs.map(n=>needLabels[n]??n).join(', '):'aucun parmi les mesures connues'}</p><p><b>Contraintes</b> · ${a.constraints.length?a.constraints.map(c=>constraintLabels[c]??c).join(', '):'aucune confirmée'}</p><p><b>Bilan</b> · ${coverageText(v)}</p>`;
}
/** Hero shared by the room and home cards: name, « i », level pill, the gesture, the disk, then the scale. */
export function hero(o:{name:string;level:Level;slides:Slide[];scaleLabel:string;scale:TemplateResult;st:CardState;why:TemplateResult;compact?:boolean;still?:boolean;small?:boolean;after?:TemplateResult|typeof nothing}):TemplateResult {
  const many=o.slides.length>1;
  return html`<div class=${'nc-hero'+(o.small?' nc-compact':'')}>
    <div class="nc-top"><h2>${o.name}</h2><button class="nw-info" aria-label="Pourquoi ce conseil ?" aria-expanded=${o.st.why} aria-controls=${o.st.uid+'-why'} @click=${()=>o.st.toggle('why')}>${icon('info')}</button><span class="nw-chip nc-level">${many?`${o.slides.length} conseils`:o.slides[0]?.learned?html`<span class="nc-learned">${icon('flask')}${o.slides[0].pill}</span>`:o.slides[0]?.pill??pills[o.level]}</span></div>
    <niak-advice-ticker .slides=${o.slides} .still=${!!o.still}></niak-advice-ticker>
    <div class="nc-why" id=${o.st.uid+'-why'} ?hidden=${!o.st.why}>${o.why}</div>
    ${o.compact?nothing:html`<div class="nc-sec nw-glass"><div class="nw-label">${o.scaleLabel}</div>${o.scale}</div>`}
    ${o.after??nothing}
  </div>`;
}
/** A folding section with the charter's round chevron; out-of-range tiles stay visible when folded. */
export function fold(o:{label:string;summary:TemplateResult|string;open:boolean;onToggle:()=>void;id:string;body:TemplateResult;keep?:TemplateResult[]}):TemplateResult {
  return html`<div class=${'nc-fold'+(o.open?' open':'')}><button class="nw-fold-head" aria-expanded=${o.open} aria-controls=${o.id} @click=${o.onToggle}><span class="nw-label">${o.label}</span><span class="nw-sum">${o.summary}</span><span class="nw-chevron">${icon('chevron')}</span></button>
    <div id=${o.id}>${o.open?o.body:o.keep?.length?html`<div class="nc-tiles">${o.keep}</div>`:nothing}</div></div>`;
}
/** « 4 mesures · 1 à surveiller · 2 muettes »: a silent measure is never counted as fine. */
export const tileSummary=(n:number,k:number,unit:string,mute=0,waiting=false)=>n?html`${n} ${unit}${n>1?'s':''}${k?html` · <b>${k} à surveiller</b>`:''}${mute?(waiting?` · ${mute} en attente`:` · ${mute} muette${mute>1?'s':''}`):''}${!k&&!mute?' · rien à signaler':''}`:html`Aucune ${unit}`;
/** The few values a tile or a mini line shows, out of range in amber. */
function chipValues(v:View,which:readonly Chip[]):{ic:string;text:string;out:boolean;entity?:string}[]{
  const o=v.observations,a=v.assessment,out=[];
  for(const c of which){
    if(c==='temperature'){const t=numeric(o.indoor_temperature);if(t!==null)out.push({ic:'temp',text:number(t)+' °C',out:a.needs.includes('cool')||a.needs.includes('heat'),entity:o.indoor_temperature?.source??undefined});}
    if(c==='humidity'){const h=numeric(o.indoor_humidity),degree=a.features?.humidity?.degree;if(h!==null)out.push({ic:'drop',text:number(h)+' %',out:degree!==undefined?degree>=2:a.needs.includes('dry'),entity:o.indoor_humidity?.source??undefined});}
    if(c==='co2'){const x=numeric(o.co2);if(x!==null)out.push({ic:'air',text:number(x)+' ppm',out:a.features?.air?.co2_status==='high',entity:o.co2?.source??undefined});}
  }
  return out;
}
const chipRow=(list:ReturnType<typeof chipValues>)=>list.length?html`<div class="nc-chips">${list.map(c=>c.entity
  ?html`<button type="button" class=${'nc-chip nc-hit'+(c.out?' out':'')} title="Détails" @click=${(e:Event)=>moreInfo(e,c.entity!)}>${icon(c.ic)}${c.text}</button>`
  :html`<span class=${'nc-chip'+(c.out?' out':'')}>${icon(c.ic)}${c.text}</span>`)}</div>`:nothing;
/** Is something asked of the person? The alert format shows only then. */
export const asking=(v:View)=>['action','urgent'].includes(slides(v)[0]?.level??v.assessment.level);
/** The room card in each format; null when the alert format has nothing to say. */
export function roomCard(v:View,config:Config,st:CardState,format:Format='full',partners:View[]=[]):TemplateResult|null {
  const a=v.assessment,f=a.features,ti=numeric(v.observations.indoor_temperature),te=numeric(v.observations.outdoor_temperature);
  // Rooms sharing one air are one card: the other rooms' own measures, without the windows and the sun they share.
  const shared=new Set(['Fenêtres','Soleil']),others=partners.map(p=>({title:p.title,list:[...roomTemperature(p),...ownTiles(p,tiles(p,config)).filter(t=>!shared.has(t.label)&&t.label!=='Température')]}));
  // On a card shared by several rooms, the scale shows the first room's temperature: its own tile says so too.
  const own=partners.length?[...roomTemperature(v),...ownTiles(v,tiles(v,config))]:tiles(v,config),list=[...own,...others.flatMap(o=>o.list)],outside=list.filter(t=>t.out&&!t.remedy),muted=list.filter(t=>tileClass(t).includes(' mute'));
  const marks=config.scale_marks??(config.show_scale===false?[]:SCALE_MARKS);
  const band:[number,number]|null=f?.season&&marks.includes('band')?[f.season.minimum,f.season.maximum]:null;
  const sc=(config.modules??[]).includes('temperature')&&marks.length&&ti!==null
    ?scale({band,day:marks.includes('day')?f?.day_range??null:null,now:ti,out:marks.includes('out')?te:null,nowEntity:v.observations.indoor_temperature?.source??undefined,outEntity:v.observations.outdoor_temperature?.source??undefined}):null;
  const all=slides(v,config.banner_blocks),top=all[0]?.level??a.level,name=config.title||(partners.length?v.volume_name:null)||v.title;
  const still=config.animations===false||config.rotate===false;
  // A measure out of range is framed in orange only when the room asks for a gesture.
  const soft=!['action','urgent'].includes(top);
  const summary=tileSummary(list.length,outside.length,'mesure',muted.length,!!v.starting);
  // Folded, a card shared by several rooms names each room on the measures it keeps: « Salon », « Cuisine », not twice « Température ».
  const named=(t:Tile,room:string)=>others.length?{...t,label:t.label==='Température'?room:`${t.label} · ${room}`}:t;
  const watched=[...own.map(t=>named(t,v.title)),...others.flatMap(o=>o.list.map(t=>named(t,o.title)))].filter(t=>(t.out&&!t.remedy)||tileClass(t).includes(' mute'));
  const grid=others.length?html`<div class="nw-label nc-room-label">${v.title}</div><div class="nc-tiles">${own.map(t=>tile(t,soft))}</div>${others.map(o=>o.list.length?html`<div class="nw-label nc-room-label">${o.title}</div><div class="nc-tiles">${o.list.map(t=>tile(t,soft))}</div>`:nothing)}`
    :html`<div class="nc-tiles">${list.map(t=>tile(t,soft))}</div>`;
  const box=factBox(v,partners);
  const detailList=html`<ul class="nc-list">${details(v,config)}</ul>${st.configure?html`<button class="nw-badge nc-configure" @click=${st.configure}>${icon('settings')}Configurer cette pièce</button>`:nothing}`;
  const scaleBox=sc?html`<div class="nc-sec nw-glass"><div class="nw-label">Température</div>${sc}</div>`:nothing;
  if(format==='mini'){
    const values=chipValues(v,config.mini_values??['temperature']),temp=values.find(c=>c.ic==='temp');
    return html`<ha-card class="nc-c nc-line-card" data-level=${top}><div class="nc-disk" data-disk=${all[0]?.disk}>${icon(all[0]?.disk??'check')}</div>
      <div class="nc-line-text"><span>${name}</span><b>${all[0]?.title}</b></div>${chipRow(values.filter(c=>c!==temp))}${temp?html`<span class="nc-line-value">${temp.text.replace(' °C','')}<small> °C</small></span>`:nothing}</ha-card>`;
  }
  if(format==='measures')
    return html`<ha-card class="nc-c nc-measures-card" data-level="neutral"><div class="nc-mhead"><h2>${name}</h2><span class="nw-sum">${summary}</span></div><div class="nc-mbody">${config.scale_marks?.length?scaleBox:nothing}${grid}</div></ha-card>`;
  if(format==='alert'){
    if(!asking(v))return null;
    return html`<ha-card class="nc-c" data-level=${top}>${hero({name,level:top,slides:all,scaleLabel:'',scale:html``,st,why:whyLines(v),compact:true,small:true,still})}</ha-card>`;
  }
  if(format==='tile'||format==='intermediate'){
    const blocks=config.tile_blocks??TILE_BLOCKS;
    const body=blocks.map(b=>b==='scale'?scaleBox:b==='measures'?(list.length?grid:nothing):html`<div class="nc-tile-details"><div class="nw-label">Détails</div>${detailList}</div>`);
    const chips=st.tilesOpen?nothing:chipRow([...chipValues(v,config.tile_chips??CHIPS),...partners.flatMap(p=>chipValues(p,['temperature']).map(c=>({...c,text:p.title+' '+c.text})))]);
    return html`<ha-card class="nc-c" data-level=${top} ?data-starting=${!!v.starting}>
      ${hero({name,level:top,slides:all,scaleLabel:'',scale:html``,st,why:whyLines(v),compact:true,small:true,still,after:chips})}
      ${box}
      ${blocks.length?html`<div class="nc-body nc-tile-body">${fold({label:'Mesures et détails',summary:list.length?summary:'',open:st.tilesOpen,onToggle:()=>st.toggle('tilesOpen'),id:st.uid+'-tile',body:html`<div class="nc-tile-blocks">${body}</div>`})}</div>`:nothing}
    </ha-card>`;
  }
  const measures=list.length&&config.show_measures!==false;
  const body=measures||config.show_details!==false;
  return html`<ha-card class="nc-c" data-level=${top} ?data-starting=${!!v.starting}>
    ${hero({name,level:top,slides:all,scaleLabel:'Température',scale:sc??html``,st,why:whyLines(v),compact:!sc,still})}
    ${box}
    ${!body?nothing:html`<div class="nc-body">
      ${measures?fold({label:'Mesures',summary,open:st.tilesOpen,onToggle:()=>st.toggle('tilesOpen'),id:st.uid+'-tiles',body:grid,keep:watched.map(t=>tile(t,soft))}):nothing}
      ${config.show_details===false?nothing:fold({label:'Détails',summary:'',open:st.detailsOpen,onToggle:()=>st.toggle('detailsOpen'),id:st.uid+'-details',body:detailList})}
    </div>`}
  </ha-card>`;
}

/** The advices, one at a time every 4.5 s (as Niak Weather's ticker). Every slide sits in the same place,
    so the card keeps the height of the longest one. Pauses on hover or focus; a tap shows the next one. */
export class NiakAdviceTicker extends LitElement {
  @property({attribute:false}) slides:Slide[]=[];
  @property({type:Boolean}) still=false;
  @state() private index=0;
  @state() private paused=false;
  private timer?:ReturnType<typeof setTimeout>;
  createRenderRoot(){return this;}
  connectedCallback(){super.connectedCallback();this.schedule();}
  disconnectedCallback(){super.disconnectedCallback();clearTimeout(this.timer);this.timer=undefined;}
  /** The advice that just left: it fades upward, whichever way the list turns. */
  private previous=-1;
  protected willUpdate(changed:Map<string,unknown>){if(changed.has('index'))this.previous=(changed.get('index') as number|undefined)??-1;if(changed.has('slides')&&this.index>=this.slides.length)this.index=0;}
  // The view is refreshed whenever a sensor moves (every few seconds for CO₂): a new list of slides
  // must not restart the countdown, or the first advice would never leave. Only a new slide, a pause
  // or a missing countdown starts one.
  protected updated(changed:Map<string,unknown>){
    if(changed.has('index')||changed.has('paused')||changed.has('still')||!this.timer)this.schedule();
  }
  private get calm(){return this.still||matchMedia('(prefers-reduced-motion: reduce)').matches;}
  private schedule(){
    clearTimeout(this.timer);this.timer=undefined;
    if(this.slides.length>1&&!this.paused&&!this.calm)this.timer=setTimeout(()=>{this.timer=undefined;this.index=(this.index+1)%this.slides.length;},4500);
  }
  private go(i:number){this.index=(i+this.slides.length)%this.slides.length;}
  private hold(on:boolean){this.paused=on;}
  protected render(){
    const list=this.slides,many=list.length>1,i=Math.min(this.index,list.length-1);
    if(!list.length)return nothing;
    return html`<div class="nc-grid" @mouseenter=${()=>this.hold(true)} @mouseleave=${()=>this.hold(false)} @focusin=${()=>this.hold(true)} @focusout=${()=>this.hold(false)}
        @click=${(e:Event)=>{if(many&&!(e.target as HTMLElement).closest('.nc-bars'))this.go(i+1);}} style=${many?'cursor:pointer':''}>
      <div class="nc-copy">
        <div class="nc-tk-head"><span class="nw-label">${many?'Conseils':list[0]?.pill&&list[0].level==='neutral'?'État':['action','urgent'].includes(list[0]?.level)?'Action à faire':'Conseil'}</span>${many?html`<span class="nc-tk-count">${i+1} sur ${list.length}</span>
          <span class="nc-bars">${list.map((s,k)=>html`<button type="button" aria-label=${`Conseil ${k+1} : ${s.title}`} aria-current=${k===i?'true':'false'} data-level=${s.level} class=${k<i?'done':k===i?(this.paused||this.calm?'done':'on'):''} @click=${()=>this.go(k)}><i></i></button>`)}</span>`:nothing}</div>
        <div class="nc-stack" aria-live=${this.paused?'polite':'off'}>${list.map((s,k)=>html`<div class=${'nc-slide'+(k===i?' on':k===this.previous?' out':'')} aria-hidden=${k===i?'false':'true'}>
          ${many?html`<span class="nw-chip nc-slide-pill" data-level=${s.level}>${s.learned?html`<span class="nc-learned">${icon('flask')}${s.pill}</span>`:s.pill}</span>`:nothing}<p class="nc-advice">${s.title}</p>${s.line?html`<p class="nc-line">${s.line}</p>`:nothing}</div>`)}</div>
      </div>
      <div class="nc-diskwrap nc-stack" aria-hidden="true">${list.map((s,k)=>html`<div class=${'nc-slide nc-diskslide'+(k===i?' on':k===this.previous?' out':'')} data-level=${s.level} ?data-learned=${!!s.learned}><div class="nc-disk" data-disk=${s.disk}>${icon(s.disk)}</div>${s.cap?html`<div class="nc-cap">${s.cap}</div>`:nothing}</div>`)}</div>
    </div>`;
  }
}
if(!customElements.get('niak-advice-ticker'))customElements.define('niak-advice-ticker',NiakAdviceTicker);

/** What a room needs, as measured: « 68 % trop humide », « 282 COV élevés ». The home card shows it under
    the room, since the advice itself is already in its banner. A device at work is not a need. */
export function needs(v:View,includeSlight=true):string[] {
  const o=v.observations,a=v.assessment,air=a.features?.air,out:string[]=[],val=(k:string)=>numeric(o[k]);
  const h=val('indoor_humidity'),c=val('co2'),pm=val('pm25'),voc=val('voc');
  // The temperature is the tile's own figure, just above: the words alone.
  if(a.needs.includes('cool'))out.push('trop chaud');
  if(a.needs.includes('heat'))out.push(a.features?.warmth?.slight?'un peu frais':'trop frais');
  const humidity=humidityLabel(v),degree=a.features?.humidity?.degree;
  if(humidity&&(degree!==undefined?degree>=(includeSlight?1:2):a.needs.includes('dry')))out.push(h!==null?`${number(h)} % ${humidity.toLowerCase()}`:humidity.toLowerCase());
  if(air?.co2_status==='high')out.push(c!==null?`${number(c)} ppm de CO₂`:'CO₂ élevé');
  if(air?.pm25_status==='high'&&air?.pm25_treated!==true)out.push(pm!==null?`${number(pm)} particules élevées`:'particules élevées');
  if(air?.voc_status==='high')out.push(voc!==null?`${number(voc)} COV élevés`:'COV élevés');
  if((a.openings??[]).some(x=>x.flags.length>0&&x.open===true))out.push('fenêtre à refermer');
  return out;
}

/** Short texts one at a time, every 3 s, in the same place; still when animations are off. */
export class NiakNoteTicker extends LitElement {
  @property({attribute:false}) notes:string[]=[];
  @property({type:Boolean}) still=false;
  @state() private index=0;
  private timer?:ReturnType<typeof setInterval>;
  createRenderRoot(){return this;}
  connectedCallback(){super.connectedCallback();this.timer=setInterval(()=>{
    if(this.notes.length>1&&!this.still&&!matchMedia('(prefers-reduced-motion: reduce)').matches)this.index=(this.index+1)%this.notes.length;},3000);}
  disconnectedCallback(){super.disconnectedCallback();clearInterval(this.timer);this.timer=undefined;}
  protected render(){
    const list=this.notes,i=this.index%Math.max(1,list.length);
    return html`<span class="nc-notes" title=${list.join(' · ')}>${list.map((n,k)=>html`<span class=${k===i?'on':''} aria-hidden=${k===i?'false':'true'}>${n}</span>`)}</span>`;
  }
}
if(!customElements.get('niak-note-ticker'))customElements.define('niak-note-ticker',NiakNoteTicker);
