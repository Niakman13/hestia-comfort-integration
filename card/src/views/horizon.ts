import {html,nothing,svg,type TemplateResult} from 'lit';
import type {Horizon,HorizonMode,HorizonSubject} from '../types';
import {number} from '../view';
import {t,th,fr} from '../i18n';
const B=(text:string)=>html`<b>${text}</b>`;

/** « Prochaines heures »: the room without the gesture (grey, dashed) and with it (in colour), the band of the gesture
 *  and, under the curve, a strip saying when. Drawn from engine/horizon.py; a trend, not a decimal. */
const W=300,H=66,COLORS:Record<string,string>={cool:'var(--nc-h-cool)',air:'var(--nc-h-air)',sun:'var(--nc-h-sun)',dry:'var(--nc-h-dry)',trend:'var(--nc-h-trend)'};
/** An hour, with « demain » when it is not today: the graph runs into tomorrow. */
const clockText=(h:number,m:number)=>h===0&&!m?t('minuit'):h===12&&!m?t('midi'):m?t('{h} h {m}',{h,m:String(m).padStart(2,'0')}):t('{n} h',{n:h});
const hour=(iso:string|null|undefined)=>{if(!iso)return '';const d=new Date(iso),time=clockText(d.getHours(),d.getMinutes());
  return d.toDateString()===new Date().toDateString()?time:t('demain {time}',{time});};
const soon=(iso:string)=>Math.abs(new Date(iso).getTime()-Date.now())<20*60e3;
const deg=(v:number|null|undefined,unit:string)=>v==null?'—':`${number(v)}${unit==='%'?' %':' °C'}`;

/** What the gesture is, in the header of the graph. */
export function horizonHead(h:Horizon):string{
  const r=h.result;
  switch(h.kind){
    case 'cool':return t('ouvrez de {from} à {to}',{from:hour(r.open_from as string),to:hour(r.open_until as string)});
    case 'air':case 'dry':return soon(r.at as string)?t('aérez {n} min maintenant',{n:r.minutes as number}):t('aérez {n} min vers {time}',{n:r.minutes as number,time:hour(r.at as string)});
    // The sun far ahead (at night, tomorrow's) is only announced: it spares no heating now.
    case 'sun':{const from=h.bands[0]?.[0];if(from&&new Date(from).getTime()-Date.now()>3*3600e3)return t('soleil {time}',{time:hour(from)});
      return r.cold?t('le soleil réchauffe : inutile de chauffer'):t('le soleil va réchauffer la pièce');}
    case 'trend':return t('sans rien faire');
  }
  return '';
}
/** What it changes, under the graph. */
export function horizonResult(h:Horizon):TemplateResult{
  const r=h.result;
  switch(h.kind){
    case 'cool':return th('demain {time} : {aired} au lieu de {shut}',{time:hour(r.peak_time as string),aired:B(deg(r.aired as number,'°C')),shut:deg(r.shut as number,'°C')});
    case 'air':return html`${B(`−${number(r.drop as number)} °C`)}${r.back?t(', revenu vers {time}',{time:hour(r.back as string)}):t(' · pas revenu dans les 24 h')}`;
    // The night after only when it says something more than the top.
    // With and without the sun: what it brings; an older engine drew the forecast alone.
    case 'sun':return r.gain!=null?th('{gain} grâce au soleil vers {time} · au plus haut {top}',{gain:B(`+${number(r.gain as number)} °C`),time:hour(r.gain_time as string),top:B(deg(r.top as number,'°C'))})
      :html`${th('au plus haut {top} vers {time}',{top:B(deg(r.top as number,'°C')),time:hour(r.top_time as string)})}${r.night!=null&&(r.top as number)-(r.night as number)>=0.3?html` · ${th('{value} vers {time}',{value:B(deg(r.night as number,'°C')),time:hour(r.night_time as string)})}`:nothing}`;
    case 'dry':return th('{with} au lieu de {without} vers {time}',{with:B(deg(r.with as number,'%')),without:deg(r.without as number,'%'),time:hour(r.time as string)});
    case 'trend':return th('au plus haut {top} vers {time} · au plus bas {low} vers {lowTime}',{top:B(deg(r.top as number,'°C')),time:hour(r.top_time as string),low:B(deg(r.low as number,'°C')),lowTime:hour(r.low_time as string)});
  }
  return html``;
}
const bandLabel:Record<string,string>={cool:fr('ouvrir'),air:fr('aérer'),sun:fr('soleil sur les fenêtres'),dry:fr('aérer')};
const baseLabel:Record<string,string>={cool:fr('fermé'),air:fr('sans aérer'),sun:fr('sans soleil'),dry:fr('sans aérer'),trend:fr('prévue')};
const gestureLabel:Record<string,string>={cool:fr('aéré'),air:fr('en aérant'),sun:fr('avec le soleil'),dry:fr('en aérant')};

export function horizonChart(h:Horizon,plage:[number,number]|null):TemplateResult{
  const n=h.base.length,t0=new Date(h.start).getTime(),stepMs=h.step_minutes*60e3,t1=t0+(n-1)*stepMs;
  const X=(t:number)=>((t-t0)/(t1-t0))*W,values=[...h.base,...(h.gesture??[])];
  // A few tenths must not look like a cliff: at least 3 °C (12 %) from top to bottom, around the curves.
  const span=Math.max(h.unit==='%'?12:3,Math.max(...values)-Math.min(...values)+(h.unit==='%'?4:0.8)),mid=(Math.max(...values)+Math.min(...values))/2;
  const lo=mid-span/2,hi=mid+span/2,Y=(v:number)=>H-(Math.max(lo,Math.min(hi,v))-lo)/(hi-lo)*H;
  // A smooth line through the half hours (Catmull-Rom as Bézier curves).
  const path=(s:number[])=>{const p=s.map((v,i)=>[X(t0+i*stepMs),Y(v)]);let d=`M${p[0][0].toFixed(1)} ${p[0][1].toFixed(1)}`;
    for(let i=0;i<p.length-1;i++){const a=p[Math.max(0,i-1)],b=p[i],c=p[i+1],e=p[Math.min(p.length-1,i+2)];
      d+=` C${(b[0]+(c[0]-a[0])/6).toFixed(1)} ${(b[1]+(c[1]-a[1])/6).toFixed(1)} ${(c[0]-(e[0]-b[0])/6).toFixed(1)} ${(c[1]-(e[1]-b[1])/6).toFixed(1)} ${c[0].toFixed(1)} ${c[1].toFixed(1)}`;}
    return d;};
  const color=COLORS[h.kind]??'var(--nc-h-air)',line=h.gesture??h.base;
  const band=([a,b]:string[])=>{const xa=Math.max(0,X(new Date(a).getTime())),xb=Math.min(W,Math.max(X(new Date(b).getTime()),xa+5));return [xa,xb];};
  // The drawing starts now: said under its first point, so that it is not read as the past hours.
  const ticks:TemplateResult[]=[svg`<text x="0" y=${H+30} text-anchor="start" class="nc-h-tick nc-h-start">${t('maintenant')}</text>`];
  for(let i=0;i<n;i++){const d=new Date(t0+i*stepMs);if(d.getMinutes()===0&&d.getHours()%6===0&&X(d.getTime())>=70){const x=X(d.getTime());
    ticks.push(svg`<text x=${x} y=${H+30} text-anchor=${x<12?'start':x>W-12?'end':'middle'} class="nc-h-tick">${clockText(d.getHours(),0)}</text>`);}}
  // The comfort range as two thin lines, only where they fall inside the drawing.
  const edges=plage?plage.filter(v=>v>lo&&v<hi):[];
  const fmt=(v:number)=>number(Math.round(v*10)/10)+(h.unit==='%'?' %':'°');
  const last=line[line.length-1];
  return html`<svg class="nc-h-svg" viewBox="-2 -6 ${W+30} ${H+42}" role="img" aria-label=${`${horizonHead(h)}`}>
    <defs><linearGradient id="nc-h-fill" x1="0" x2="0" y1="0" y2="1" style=${'color:'+color}><stop offset="0" stop-color="currentColor" stop-opacity=".16"/><stop offset="1" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs>
    ${edges.map(v=>svg`<line x1="0" x2=${W} y1=${Y(v)} y2=${Y(v)} class="nc-h-edge"/><text x=${W+4} y=${Y(v)+3} class="nc-h-tick">${fmt(v)}</text>`)}
    ${h.gesture?svg`<path d=${path(h.base)} class="nc-h-base"/>`:svg`<path d=${path(h.base)+` L${W} ${H} L0 ${H} Z`} style=${'color:'+color} fill="url(#nc-h-fill)"/>`}
    <path d=${path(line)} class="nc-h-line" style=${'stroke:'+color}/>
    <circle cx="0" cy=${Y(line[0])} r="3" class="nc-h-dot" style=${'stroke:'+color}/>
    <text x="4" y=${Y(line[0])-6} class="nc-h-value">${fmt(line[0])}</text>
    <text x=${W+4} y=${Y(last)+3} class="nc-h-value">${fmt(last)}</text>
    ${h.bands.length||h.extra.length?svg`<rect x="0" y=${H+6} width=${W} height="10" rx="5" class="nc-h-strip"/>`:nothing}
    ${h.extra.map(e=>{const [a,b]=band(e);return svg`<rect x=${a} y=${H+6} width=${b-a} height="10" rx="5" class="nc-h-keep"/>`;})}
    ${h.bands.map(e=>{const [a,b]=band(e);return svg`<rect x=${a} y=${H+6} width=${b-a} height="10" rx="5" style=${'fill:'+color}/>`;})}
    ${ticks}
  </svg>`;
}
export function horizonLegend(h:Horizon):TemplateResult{
  const color=COLORS[h.kind]??'var(--nc-h-air)';
  // Without a gesture there is one curve, the forecast, drawn in colour.
  return html`<div class="nw-legend nc-legend nc-h-legend">${h.gesture?html`<span><i class="k-h-base"></i>${t(baseLabel[h.kind])}</span><span><i class="k-h-line" style=${'border-color:'+color}></i>${t(gestureLabel[h.kind])}</span>`:html`<span><i class="k-h-line" style=${'border-color:'+color}></i>${t(baseLabel[h.kind])}</span>`}${h.bands.length?html`<span><i class="k-h-band" style=${'background:'+color}></i>${t(bandLabel[h.kind])}</span>`:nothing}${h.extra.length?html`<span><i class="k-h-band keep"></i>fermé, soleil</span>`:nothing}</div>`;
}
/** The last subjects shown by each card, kept while the graph folds away. */
const lastShown=new Map<string,Horizon[]>();
/** The subjects to draw: those the gesture needs (« needed »), or else the forecast when the card keeps its graph
 *  (« always »): the sun's when it warms the room, otherwise the trend.
 *  A subject from an older engine, without `needed`, counts as needed. */
export function horizonShown(list:Horizon[],mode:HorizonMode='needed',subjects?:HorizonSubject[]):Horizon[]{
  const allowed=list.filter(h=>!subjects||subjects.includes(h.subject));
  const needed=allowed.filter(h=>h.kind!=='trend'&&h.needed!==false);
  if(needed.length||mode==='needed')return needed;
  const forecast=allowed.find(h=>h.kind==='sun')??allowed.find(h=>h.kind==='trend');
  return forecast?[forecast]:[];
}
/** The graph for the banner: one subject, or two behind small tabs (the banner's first). It opens and folds in height,
 *  so that the card grows or shrinks smoothly instead of jumping; folding, it keeps the last drawing until it is gone. */
export function horizonBox(list:Horizon[],o:{plage:(s:HorizonSubject)=>[number,number]|null;second:boolean;onTab:()=>void;subjects?:HorizonSubject[];mode?:HorizonMode;uid:string}):TemplateResult|typeof nothing{
  const now=horizonShown(list,o.mode,o.subjects),open=now.length>0;
  if(open)lastShown.set(o.uid,now);
  const shown=open?now:lastShown.get(o.uid);
  if(!shown)return nothing;
  const h=shown[o.second&&shown.length>1?1:0],label=(s:HorizonSubject)=>s==='humidity'?t('Humidité'):t('Température');
  return html`<div class="nc-h-fold ${open?'open':''}" aria-hidden=${open?'false':'true'} ?inert=${!open}><div class="nc-h-inner"><div class="nc-sec nw-glass nc-horizon">
    <div class="nc-h-head"><span class="nw-label">${t('Prochaines heures')}</span>${shown.length>1?html`<span class="nc-h-tabs" role="tablist">${shown.map((x,i)=>html`<button role="tab" aria-selected=${x===h} class=${x===h?'on':''} @click=${()=>{if((i===1)!==o.second)o.onTab();}}>${label(x.subject)}</button>`)}</span>`:nothing}<b class="nc-h-gesture" style=${'color:'+(COLORS[h.kind]??'inherit')}>${horizonHead(h)}</b></div>
    ${horizonChart(h,o.plage(h.subject))}
    <p class="nc-h-result">${horizonResult(h)}</p>
    ${horizonLegend(h)}
  </div></div></div>`;
}
