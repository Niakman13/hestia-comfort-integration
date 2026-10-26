import {html,nothing,svg,type TemplateResult} from 'lit';
import type {Horizon,HorizonMode,HorizonSubject} from '../types';
import {number} from '../view';

/** « Prochaines heures »: the room without the gesture (grey, dashed) and with it (in colour), the band of the gesture
 *  and, under the curve, a strip saying when. Drawn from engine/horizon.py; a trend, not a decimal. */
const W=300,H=66,COLORS:Record<string,string>={cool:'var(--nc-h-cool)',air:'var(--nc-h-air)',sun:'var(--nc-h-sun)',dry:'var(--nc-h-dry)',trend:'var(--nc-h-trend)'};
/** An hour, with « demain » when it is not today: the graph runs into tomorrow. */
const hour=(iso:string|null|undefined)=>{if(!iso)return '';const d=new Date(iso),h=d.getHours(),m=d.getMinutes(),today=new Date();
  const day=d.toDateString()===today.toDateString()?'':'demain ';
  return day+(h===0&&!m?'minuit':h===12&&!m?'midi':h+' h'+(m?' '+String(m).padStart(2,'0'):''));};
const soon=(iso:string)=>Math.abs(new Date(iso).getTime()-Date.now())<20*60e3;
const deg=(v:number|null|undefined,unit:string)=>v==null?'—':`${number(v)}${unit==='%'?' %':' °C'}`;

/** What the gesture is, in the header of the graph. */
export function horizonHead(h:Horizon):string{
  const r=h.result;
  switch(h.kind){
    case 'cool':return `ouvrez de ${hour(r.open_from as string)} à ${hour(r.open_until as string)}`;
    case 'air':case 'dry':return `aérez ${r.minutes} min ${soon(r.at as string)?'maintenant':'vers '+hour(r.at as string)}`;
    // The sun far ahead (at night, tomorrow's) is only announced: it spares no heating now.
    case 'sun':{const from=h.bands[0]?.[0];if(from&&new Date(from).getTime()-Date.now()>3*3600e3)return `soleil ${hour(from)}`;
      return r.cold?'le soleil réchauffe : inutile de chauffer':'le soleil va réchauffer la pièce';}
    case 'trend':return 'sans rien faire';
  }
  return '';
}
/** What it changes, under the graph. */
export function horizonResult(h:Horizon):TemplateResult{
  const r=h.result;
  switch(h.kind){
    case 'cool':return html`demain ${hour(r.peak_time as string)} : <b>${deg(r.aired as number,'°C')}</b> au lieu de ${deg(r.shut as number,'°C')}`;
    case 'air':return html`<b>−${number(r.drop as number)} °C</b>${r.back?html`, revenu vers ${hour(r.back as string)}`:html` · pas revenu dans les 24 h`}`;
    // The night after only when it says something more than the top.
    case 'sun':return html`au plus haut <b>${deg(r.top as number,'°C')}</b> vers ${hour(r.top_time as string)}${r.night!=null&&(r.top as number)-(r.night as number)>=0.3?html` · <b>${deg(r.night as number,'°C')}</b> vers ${hour(r.night_time as string)}`:nothing}`;
    case 'dry':return html`<b>${deg(r.with as number,'%')}</b> au lieu de ${deg(r.without as number,'%')} vers ${hour(r.time as string)}`;
    case 'trend':return html`au plus haut <b>${deg(r.top as number,'°C')}</b> vers ${hour(r.top_time as string)} · au plus bas <b>${deg(r.low as number,'°C')}</b> vers ${hour(r.low_time as string)}`;
  }
  return html``;
}
const bandLabel:Record<string,string>={cool:'ouvrir',air:'aérer',sun:'le soleil chauffe',dry:'aérer'};
const baseLabel:Record<string,string>={cool:'fermé',air:'sans aérer',sun:'prévue',dry:'sans aérer',trend:'prévue'};
const gestureLabel:Record<string,string>={cool:'aéré',air:'en aérant',dry:'en aérant'};

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
  const ticks:TemplateResult[]=[svg`<text x="0" y=${H+30} text-anchor="start" class="nc-h-tick nc-h-start">maintenant</text>`];
  for(let i=0;i<n;i++){const d=new Date(t0+i*stepMs);if(d.getMinutes()===0&&d.getHours()%6===0&&X(d.getTime())>=48){const x=X(d.getTime());
    ticks.push(svg`<text x=${x} y=${H+30} text-anchor=${x<12?'start':x>W-12?'end':'middle'} class="nc-h-tick">${d.getHours()===0?'minuit':d.getHours()+' h'}</text>`);}}
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
  return html`<div class="nw-legend nc-legend nc-h-legend">${h.gesture?html`<span><i class="k-h-base"></i>${baseLabel[h.kind]}</span><span><i class="k-h-line" style=${'border-color:'+color}></i>${gestureLabel[h.kind]}</span>`:html`<span><i class="k-h-line" style=${'border-color:'+color}></i>${baseLabel[h.kind]}</span>`}${h.bands.length?html`<span><i class="k-h-band" style=${'background:'+color}></i>${bandLabel[h.kind]}</span>`:nothing}${h.extra.length?html`<span><i class="k-h-band keep"></i>fermé, soleil</span>`:nothing}</div>`;
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
  const h=shown[o.second&&shown.length>1?1:0],label=(s:HorizonSubject)=>s==='humidity'?'Humidité':'Température';
  return html`<div class="nc-h-fold ${open?'open':''}" aria-hidden=${open?'false':'true'} ?inert=${!open}><div class="nc-h-inner"><div class="nc-sec nw-glass nc-horizon">
    <div class="nc-h-head"><span class="nw-label">Prochaines heures</span>${shown.length>1?html`<span class="nc-h-tabs" role="tablist">${shown.map((x,i)=>html`<button role="tab" aria-selected=${x===h} class=${x===h?'on':''} @click=${()=>{if((i===1)!==o.second)o.onTab();}}>${label(x.subject)}</button>`)}</span>`:nothing}<b class="nc-h-gesture" style=${'color:'+(COLORS[h.kind]??'inherit')}>${horizonHead(h)}</b></div>
    ${horizonChart(h,o.plage(h.subject))}
    <p class="nc-h-result">${horizonResult(h)}</p>
    ${horizonLegend(h)}
  </div></div></div>`;
}
