import {html,nothing,type TemplateResult} from 'lit';
import type {Config,View,Level} from '../types';
import {numeric,number,heatingLabels,coverageText,windFrom,needs as needLabels,constraintLabels} from '../view';
import {icon} from '../ui/icons';

/** The level, said in two or three words: the colour is never the only signal. */
export const pills:Record<Level,string>={calm:'Tout va bien',benefit:'À saisir',action:'Geste conseillé',urgent:'Attention',neutral:'À vérifier'};
const hour=(iso:string)=>{const h=new Date(iso).getHours();return h===0?'minuit':h===12?'midi':h+' h';};
const b=(text:string)=>html`<b>${text}</b>`;
const deg=(v:number|null)=>v===null?'—':number(v)+' °C';

export interface Advice {title:string;line:TemplateResult|string;disk:string;cap?:string}
/** The banner: the gesture in a few words, then why in one line. The full explanation stays behind « i ». */
export function advice(v:View):Advice {
  const a=v.assessment,o=v.observations,ti=numeric(o.indoor_temperature);
  const opened=Object.entries(o).some(([k,r])=>k.startsWith('window:')&&r.quality==='valid'&&r.value===true);
  const gap=a.temperature_delta===null?null:Math.abs(a.temperature_delta);
  const first=(a.open_first??[]).map(id=>v.names?.[id]??id)[0];
  const slot=a.slot;
  const duration=a.features?.ventilation?.duration_minutes;
  const minutes=duration?`${duration.min} à ${duration.max} minutes`:'quelques minutes';
  const constraint=a.constraints.find(c=>c!=='heating_running'&&c!=='frost')??a.constraints[0];
  switch(a.reason){
    case 'within_comfort': return {title:'Rien à faire',line:html`${deg(ti)}, ${b('dans votre plage')}`,disk:opened?'open':'check',cap:opened?'Fenêtre ouverte':undefined};
    case 'rain_open_windows': return {title:'Fermez, il pleut',line:html`La pluie ${b('entre par les ouvrants exposés')}`,disk:'rain'};
    case 'gust_open_windows': return {title:'Fermez, vent fort',line:html`Les rafales ${b('dépassent votre seuil')}`,disk:'shut'};
    case 'rain_soon': return {title:'Refermez avant la pluie',line:html`Pluie ${b(a.rain_soon_minutes!=null&&a.rain_soon_minutes<60?`dans ${a.rain_soon_minutes} min`:'dans l’heure')}`,disk:'rain'};
    case 'opening_blocked': {
      const why=constraint?constraintLabels[constraint]??constraint:'Contrainte extérieure';
      return {title:a.action==='fermer'?'Refermez':'Gardez fermé',line:html`${b(why)}${a.needs.length?' : le besoin attendra':''}`,disk:a.action==='fermer'?'shut':'window'};
    }
    case 'short_air_change': return {title:a.action==='ok'?'Aération en cours':'Aérez 5 minutes',line:html`Air à renouveler, ${b(a.constraints.includes('frost')?'il gèle dehors':'le chauffage tourne')}`,disk:'open',cap:a.action==='ok'?undefined:'Puis refermez'};
    case 'air_needed': return {title:a.action==='ok'?'Aération en cours':`Aérez ${minutes}`,line:airWhy(v),disk:'open',cap:a.action==='ok'?undefined:first};
    case 'cooling_possible': return {title:a.action==='ok'?'Aération en cours':'Ouvrez pour rafraîchir',line:html`Il fait ${b(`${number(gap)} °C de moins`)} dehors`,disk:'open',cap:a.action==='ok'?undefined:first};
    case 'precool_possible': return {title:a.action==='ok'?'Laissez ouvert cette nuit':'Ouvrez pour la nuit',line:html`Demain sera chaud : ${b('stockez le frais')}`,disk:'moon',cap:first};
    case 'precool_later':
    case 'cooling_unavailable':
      return slot&&slot.kind==='open'?{title:`Ouvrez vers ${hour(slot.time)}`,line:html`Dehors descendra à ${b(number(slot.temperature)+' °C')}`,disk:'moon',cap:slot.wind_bearing!=null?windFrom(slot.wind_bearing):undefined}
        :{title:'Gardez fermé',line:html`Dehors ${b('n’est pas plus frais')} pour l’instant`,disk:'clock'};
    case 'drying_possible': return {title:a.action==='ok'?'Aération en cours':'Aérez pour assécher',line:html`L’air du dehors ${b('est plus sec')}`,disk:'open',cap:a.action==='ok'?undefined:first};
    case 'drying_unavailable': return {title:'Humidité à surveiller',line:html`Dehors ${b('n’est pas plus sec')}`,disk:'clock'};
    case 'exchange_harmful': return {title:'Refermez',line:html`Dehors ${b(a.temperature_delta!==null&&a.temperature_delta>0?'réchauffe la pièce':'refroidit la pièce')}`,disk:'shut'};
    case 'rehumidification_risk': return {title:'Refermez',line:html`L’air du dehors ${b('est plus humide')}`,disk:'shut'};
    case 'heat_needed': return {title:a.action==='fermer'?'Refermez':'Gardez fermé',line:html`Pièce fraîche : ${b(deg(ti))}`,disk:a.action==='fermer'?'shut':'window'};
    case 'sun_entering': return {title:'Fermez côté soleil',line:html`Le soleil ${b('chauffe la pièce')}`,disk:'shut'};
    case 'shutter_protection': return {title:'Adaptez les volets',line:html`Le soleil ${b('tape sur une façade')}`,disk:'window'};
    case 'optional_air_change': return {title:'Aérez si possible',line:html`CO₂ ${b(number(numeric(o.co2))+' ppm')}`,disk:'open'};
    case 'verify_exterior': {
      const missing=[...new Set((a.unverified?.length?a.unverified:a.missing).map(k=>k==='rain'?'Pluie':k==='pollution'?'Air extérieur':'Extérieur'))];
      const gesture=a.needs.includes('air')?`Aérez ${minutes}`:a.needs.includes('cool')?'Ouvrez pour rafraîchir':a.needs.includes('dry')?'Aérez pour assécher':'Vérifiez dehors';
      return {title:gesture,line:html`${missing.join(' et ')} non suivi${missing.length>1?'s':''} : ${b('regardez dehors avant')}`,disk:'ask',cap:'Si le temps le permet'};
    }
    case 'incomplete_data': {
      const failed=a.missing.filter(k=>!!o[k]);
      return {title:failed.length?'Mesure à vérifier':'Bilan partiel',line:failed.length?html`${b(coverageText(v).replace(/^Mesures à vérifier : /,''))} ne répond pas`:html`Les mesures connues sont ${b('dans votre plage')}`,disk:'ask'};
    }
  }
  return {title:pills[a.level],line:'',disk:a.action==='ouvrir'?'open':a.action==='fermer'?'shut':'window'};
}
function airWhy(v:View):TemplateResult {
  const o=v.observations,air=v.assessment.features?.air,parts:string[]=[];
  if(air?.co2_status==='high')parts.push(`CO₂ ${number(numeric(o.co2))} ppm`);
  if(air?.pm25_status==='high')parts.push('particules élevées');
  if(air?.voc_status==='high')parts.push('COV élevés');
  return html`${b(parts.join(', ')||'Air à renouveler')}`;
}

export interface ScaleInput {band?:[number,number]|null;day?:{min:number;max:number}|null;now?:number|null;out?:number|null;
  rooms?:{name:string;short:string;value:number;level:Level}[];unit?:string}
/** The charter's scale (as Niak Weather's « Ressenti »): a thin track, your range, a ring with its value; labels never overlap. */
export function scale(s:ScaleInput):TemplateResult {
  const values=[s.band?.[0],s.band?.[1],s.day?.min,s.day?.max,s.now,s.out,...(s.rooms??[]).map(r=>r.value)].filter((x):x is number=>typeof x==='number'&&Number.isFinite(x));
  if(!values.length)return html``;
  let lo=Math.floor(Math.min(...values)-1.5),hi=Math.ceil(Math.max(...values)+1.5);
  if(hi-lo<8){const pad=(8-(hi-lo))/2;lo=Math.floor(lo-pad);hi=Math.ceil(hi+pad);}
  const pos=(x:number)=>(Math.min(hi,Math.max(lo,x))-lo)/(hi-lo)*100,pct=(x:number)=>pos(x).toFixed(2)+'%';
  const fmt=(x:number)=>number(Math.round(x*10)/10),unit=s.unit??'°C';
  const labels:{x:number;text:TemplateResult|string;len:number;row:'up'|'down';strong:boolean}[]=[];
  if(s.band)labels.push({x:pos(s.band[0]),text:fmt(s.band[0]),len:4,row:'down',strong:false},{x:pos(s.band[1]),text:fmt(s.band[1]),len:4,row:'down',strong:false});
  if(s.out!=null)labels.push({x:pos(s.out),text:'dehors '+fmt(s.out),len:11,row:'down',strong:true});
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
  const said=[s.now!=null?`Maintenant ${fmt(s.now)} ${unit}`:'',s.band?`plage ${fmt(s.band[0])} à ${fmt(s.band[1])} ${unit}`:'',s.out!=null?`dehors ${fmt(s.out)} ${unit}`:''].filter(Boolean).join(', ');
  return html`<div class="nc-scale" role="img" aria-label=${said}>
    <div class="nc-track"></div>
    ${s.band?html`<div class="nc-band" style=${`left:${pct(s.band[0])};width:${(pos(s.band[1])-pos(s.band[0])).toFixed(2)}%`}></div>`:nothing}
    ${s.day?html`<div class="nc-day" style=${`left:${pct(s.day.min)};width:${(pos(s.day.max)-pos(s.day.min)).toFixed(2)}%`}></div>`:nothing}
    ${s.out!=null?html`<span class="nc-mk out" style=${'left:'+pct(s.out)}></span>`:nothing}
    ${(s.rooms??[]).map(r=>html`<span class="nc-mk room" data-level=${r.level} style=${'left:'+pct(r.value)} title=${r.name+' '+fmt(r.value)+' '+unit}></span>`)}
    ${s.now!=null?html`<span class="nc-ring" style=${'left:'+pct(s.now)}></span><span class="nw-pill nc-now" style=${'left:'+pct(s.now)}>${fmt(s.now)} ${unit}</span>`:nothing}
    ${placed}
  </div>
  <div class="nw-legend nc-legend">${s.band?html`<span><i class="k-band"></i>votre plage</span>`:nothing}${s.day?html`<span><i class="k-day"></i>min–max 24 h</span>`:nothing}${s.rooms?html`<span><i class="k-room"></i>pièces</span>`:nothing}${s.out!=null?html`<span><i class="k-out"></i>dehors</span>`:nothing}</div>`;
}

export interface Tile {ic:string;label:string;value:string;unit?:string;note:string;level:Level;out:boolean}
/** One compact frame per measure; it takes the level's outline when the measure leaves your range. */
export function tiles(v:View,config:Config):Tile[] {
  const o=v.observations,a=v.assessment,mods=new Set(config.modules??[]),list:Tile[]=[],air=a.features?.air;
  if(mods.has('humidity')&&o.indoor_humidity){const h=numeric(o.indoor_humidity),wet=a.needs.includes('dry');
    list.push({ic:'drop',label:'Humidité',value:number(h),unit:'%',note:h===null?'indisponible':wet?'trop humide':'dans votre plage',level:wet?'action':'calm',out:wet});}
  if(mods.has('air')&&o.co2){const c=numeric(o.co2),high=air?.co2_status==='high';
    list.push({ic:'air',label:'CO₂',value:number(c),unit:'ppm',note:c===null?'indisponible':high?'à renouveler':'dans votre plage',level:high?(a.level==='urgent'?'urgent':'action'):'calm',out:high});}
  if(mods.has('air'))for(const [key,ic,label,status] of [['pm25','pm','Particules',air?.pm25_status],['voc','flask','COV',air?.voc_status]] as const){
    if(!o[key])continue;const x=numeric(o[key]),high=status==='high';
    list.push({ic,label,value:number(x),unit:o[key].unit??'',note:x===null?'indisponible':high?'élevés':status==='uninterpreted'?'sans seuil':'dans votre plage',level:high?'action':status==='ok'?'calm':'neutral',out:high});}
  if(mods.has('windows')){const contacts=Object.entries(o).filter(([k])=>k.startsWith('window:')).map(([,r])=>r);
    if(contacts.length){const open=contacts.filter(r=>r.quality==='valid'&&r.value===true).length,flagged=(a.openings??[]).some(x=>x.flags.length>0&&x.open===true);
      list.push({ic:open?'open':'window',label:'Fenêtres',value:`${open}/${contacts.length}`,note:flagged?'à refermer':open?(open>1?`${open} ouvertes`:'1 ouverte'):'toutes fermées',level:flagged?'action':'neutral',out:flagged});}}
  if(mods.has('shutters')){const s=a.sun,solar=numeric(o.solar),entering=(a.openings??[]).some(x=>x.flags.includes('sun_entering'));
    if(s||solar!==null){const night=!!s&&s.elevation<=0,value=night?'Nuit':solar===null?'—':solar<150?'Faible':solar<500?'Moyen':'Fort';
      list.push({ic:night?'moon':'sun',label:'Soleil',value,note:entering?'entre dans la pièce':night?'pas d’apport':solar===null?'non mesuré':`${number(solar)} W/m²`,level:entering?'action':'neutral',out:entering});}}
  if(mods.has('air')&&o.purifier){const on=o.purifier.quality==='valid'?o.purifier.value===true:null;
    list.push({ic:'fan',label:'Purificateur',value:on===null?'—':on?'En marche':'Arrêté',note:on&&numeric(o.purifier_speed)!==null?`${number(numeric(o.purifier_speed))} %`:'filtre les particules',level:'neutral',out:false});}
  if(mods.has('coordination')&&o.heating){const label=heatingLabels[a.heating_action]??'Inconnu',running=a.heating_action==='heating';
    list.push({ic:'heat',label:'Chauffage',value:running?'Chauffe':label,note:running?'chauffe la pièce':'observé, jamais commandé',level:'neutral',out:false});}
  return list;
}
export const tile=(t:Tile)=>html`<div class=${'nc-tile'+(t.out?' out':'')} data-level=${t.level}><div class="nc-tile-h"><span class="nc-ic">${icon(t.ic)}</span><span class="nw-label">${t.label}</span></div><b>${t.value}${t.unit?html`<small>${t.unit}</small>`:nothing}</b><em>${t.note}</em></div>`;

const row=(t:string,x:string)=>html`<li><b>${t}</b><span> · ${x}</span></li>`;
/** One short line per fact: the long explanations of 0.9 become « title · fact ». */
export function details(v:View,config:Config):TemplateResult[] {
  const a=v.assessment,f=a.features,mods=new Set(config.modules??[]),out:TemplateResult[]=[];
  const season=f?.season;
  if(season)out.push(row('Votre plage aujourd’hui',`${number(season.minimum)} à ${number(season.maximum)} °C${!season.heated?' · pièce non chauffée':''}${season.known?(season.weight===0?' · hiver':season.weight===1?' · été':' · entre-saisons'):' · saison non calculée'}`));
  if(a.action==='ouvrir'&&a.open_first?.length)out.push(row('Ouvrez d’abord',a.open_first.map(id=>v.names?.[id]??id).join(' et ')));
  if(a.slot)out.push(row(a.slot.kind==='open'?'Ouverture possible':'Fermeture conseillée',`${hour(a.slot.time)} · ${number(a.slot.temperature)} °C${a.slot.wind_bearing!=null?' · '+windFrom(a.slot.wind_bearing):''}`));
  if(a.unverified?.length&&a.action!=='fermer')out.push(row('Non suivi',a.unverified.map(k=>k==='rain'?'pluie':'air extérieur').join(' et ')+' : vérifiez avant d’ouvrir'));
  const vent=f?.ventilation;
  if(mods.has('windows')&&vent){if(vent.opened_minutes!=null)out.push(row('Ouvert depuis',`${number(vent.opened_minutes)} min`));if(vent.duration_minutes)out.push(row('Durée indicative',`${vent.duration_minutes.min} à ${vent.duration_minutes.max} min`));}
  if(mods.has('shutters'))for(const s of f?.shutters??[]){if(s.mode==='none')continue;
    out.push(row(v.names?.[s.entity_id]??'Volet',[s.manual_override?'dérogation manuelle':s.advice==='close'?'à fermer':s.advice==='open'?'à ouvrir':'rien à faire',s.position!=null?`ouvert à ${number(s.position)} %`:''].filter(Boolean).join(' · ')));}
  if(mods.has('air')&&f?.presence&&f.presence.state!=='not_configured')out.push(row('Présence',{occupied:'quelqu’un est là',empty:'pièce vide',unknown:'inconnue'}[f.presence.state]??''));
  if(mods.has('humidity')&&f?.humidity&&f.humidity.condensation_risk!==null)out.push(row('Buée',f.humidity.condensation_risk?'risque estimé':'aucun risque estimé'));
  const tr=f?.trends;
  if(mods.has('temperature')&&tr&&(tr.indoor!=null||tr.outdoor!=null))out.push(row('Tendance',[tr.indoor!=null?`dedans ${tr.indoor>0?'+':''}${number(tr.indoor)} °C/h`:'',tr.outdoor!=null?`dehors ${tr.outdoor>0?'+':''}${number(tr.outdoor)} °C/h`:''].filter(Boolean).join(', ')));
  out.push(row('Sources',coverageText(v)));
  return out;
}

export interface CardState {why:boolean;tilesOpen:boolean;detailsOpen:boolean;toggle:(k:'why'|'tilesOpen'|'detailsOpen')=>void;uid:string;configure?:()=>void}
/** The « i » panel: needs, constraints and how complete the picture is, one line each. */
export function whyLines(v:View):TemplateResult {
  const a=v.assessment;
  return html`<p><b>Besoins</b> · ${a.needs.length?a.needs.map(n=>needLabels[n]??n).join(', '):'aucun parmi les mesures connues'}</p><p><b>Contraintes</b> · ${a.constraints.length?a.constraints.map(c=>constraintLabels[c]??c).join(', '):'aucune confirmée'}</p><p><b>Bilan</b> · ${coverageText(v)}</p>`;
}
/** Hero shared by the room and home cards: name, « i », level pill, the gesture, the disk, then the scale. */
export function hero(o:{name:string;level:Level;advice:Advice;scaleLabel:string;scale:TemplateResult;st:CardState;why:TemplateResult;compact?:boolean}):TemplateResult {
  const ad=o.advice;
  return html`<div class="nc-hero">
    <div class="nc-top"><h2>${o.name}</h2><button class="nw-info" aria-label="Pourquoi ce conseil ?" aria-expanded=${o.st.why} aria-controls=${o.st.uid+'-why'} @click=${()=>o.st.toggle('why')}>${icon('info')}</button><span class="nw-chip nc-level">${pills[o.level]}</span></div>
    <div class="nc-grid"><div class="nc-copy"><div class="nw-label">Conseil</div><p class="nc-advice">${ad.title}</p>${ad.line?html`<p class="nc-line">${ad.line}</p>`:nothing}</div>
      <div class="nc-diskwrap" aria-hidden="true"><div class="nc-disk">${icon(ad.disk)}</div>${ad.cap?html`<div class="nc-cap">${ad.cap}</div>`:nothing}</div></div>
    <div class="nc-why" id=${o.st.uid+'-why'} ?hidden=${!o.st.why}>${o.why}</div>
    ${o.compact?nothing:html`<div class="nc-sec"><div class="nw-label">${o.scaleLabel}</div>${o.scale}</div>`}
  </div>`;
}
/** A folding section with the charter's round chevron; out-of-range tiles stay visible when folded. */
export function fold(o:{label:string;summary:TemplateResult|string;open:boolean;onToggle:()=>void;id:string;body:TemplateResult;keep?:TemplateResult[]}):TemplateResult {
  return html`<div class=${'nc-fold'+(o.open?' open':'')}><button class="nw-fold-head" aria-expanded=${o.open} aria-controls=${o.id} @click=${o.onToggle}><span class="nw-label">${o.label}</span><span class="nw-sum">${o.summary}</span><span class="nw-chevron">${icon('chevron')}</span></button>
    <div id=${o.id}>${o.open?o.body:o.keep?.length?html`<div class="nc-tiles">${o.keep}</div>`:nothing}</div></div>`;
}
export const tileSummary=(n:number,k:number,unit:string)=>n?html`${n} ${unit}${n>1?'s':''}${k?html` · <b>${k} hors de votre plage</b>`:' · toutes dans votre plage'}`:html`Aucune ${unit}`;
/** The room card; the mini format keeps only the banner. */
export function roomCard(v:View,config:Config,st:CardState,mini=false):TemplateResult {
  const a=v.assessment,f=a.features,ti=numeric(v.observations.indoor_temperature),te=numeric(v.observations.outdoor_temperature);
  const list=tiles(v,config),outside=list.filter(t=>t.out);
  const band:[number,number]|null=f?.season?[f.season.minimum,f.season.maximum]:null;
  const sc=(config.modules??[]).includes('temperature')?scale({band,day:f?.day_range??null,now:ti,out:te}):html``;
  return html`<ha-card class="nc-c" data-level=${a.level}>
    ${hero({name:config.title||v.title,level:a.level,advice:advice(v),scaleLabel:'Température',scale:sc,st,why:whyLines(v),compact:mini})}
    ${mini?nothing:html`<div class="nc-body">
      ${list.length?fold({label:'Mesures',summary:tileSummary(list.length,outside.length,'mesure'),open:st.tilesOpen,onToggle:()=>st.toggle('tilesOpen'),id:st.uid+'-tiles',body:html`<div class="nc-tiles">${list.map(tile)}</div>`,keep:outside.map(tile)}):nothing}
      ${fold({label:'Détails',summary:'',open:st.detailsOpen,onToggle:()=>st.toggle('detailsOpen'),id:st.uid+'-details',body:html`<ul class="nc-list">${details(v,config)}</ul>${st.configure?html`<button class="nw-badge nc-configure" @click=${st.configure}>${icon('settings')}Configurer cette pièce</button>`:nothing}`})}
    </div>`}
  </ha-card>`;
}
