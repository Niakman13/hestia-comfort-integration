// Maquette des formats et du panneau de réglages. La carte complète (pièce et logement) est la vraie carte compilée ;
// les autres formats sont dessinés avec la charte commune et les styles de la carte (hestia-charte.css, room.css).
await import('../../../custom_components/hestia_comfort/frontend/hestia-comfort-card.js?t='+Date.now());
const [charte,room,data]=await Promise.all([
  fetch('../../src/ui/hestia-charte.css').then(r=>r.text()),fetch('../../src/ui/room.css').then(r=>r.text()),
  fetch('../refonte/scenes.json').then(r=>r.json())]);
const $=id=>document.getElementById(id);

/* Pictogrammes de la carte (ui/icons.ts), plus ceux des groupes du panneau. */
const P={window:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M12 3v18M4 12h16"/>',open:'<path d="M4 3h16v18H4zM12 3l6 3v12l-6 3V3M4 12h8"/>',
  air:'<path d="M3 8h12a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h6a3 3 0 1 1-3 3"/>',temp:'<path d="M10 14V5a2 2 0 0 1 4 0v9a4 4 0 1 1-4 0Z"/><path d="M12 9v8"/>',
  drop:'<path d="M12 3C10 7 5 11 5 15a7 7 0 0 0 14 0c0-4-5-8-7-12Z"/><path d="M8 15a4 4 0 0 0 4 4"/>',sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  check:'<path d="m5 12 4 4L19 6"/>',info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/>',
  chevron:'<path d="m6 9 6 6 6-6"/>',home:'<path d="m3 11 9-8 9 8M5 9v12h14V9M10 21v-7h4v7"/>',clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  rain:'<path d="M6 14a4 4 0 0 1 0-8 6 6 0 0 1 11-1 4.5 4.5 0 0 1 1 9H6m1 3-1 3m6-3-1 3m6-3-1 3"/>',
  palette:'<circle cx="12" cy="12" r="9"/><circle cx="8" cy="10" r="1.2"/><circle cx="12" cy="7.5" r="1.2"/><circle cx="16" cy="10" r="1.2"/><path d="M12 21a2 2 0 0 1 0-4h1.5a2.5 2.5 0 0 0 0-5"/>',
  banner:'<rect x="3" y="5" width="18" height="6" rx="1.5"/><path d="M3 15h18M3 19h12"/>',scale:'<path d="M3 12h18M6 9v6M18 9v6"/><circle cx="12" cy="12" r="2.5"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  list:'<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',tune:'<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>'};
const ic=(n,c='icon')=>`<svg class="${c}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n]??P.info}</svg>`;

/* Styles propres aux nouveaux formats, posés sur la charte. */
const extra=`
ha-card{display:block}
.f-hero{padding:14px 16px}
.f-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:center;margin-top:8px}
.f-title{margin:2px 0 4px;font-size:24px;font-weight:700;letter-spacing:-.6px;line-height:1.1}
.f-row .nc-line{font-size:var(--nw-fs-small)}
.f-hero .nc-disk{width:62px;height:62px}.f-hero .nc-disk .icon{width:30px;height:30px}.f-hero .nc-diskwrap{margin:12px 8px 4px 0}
.f-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.f-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px 4px 6px;border-radius:999px;border:1px solid var(--nw-line);font-size:var(--nw-fs-small);font-weight:600;
  background:var(--nw-glass-clear);backdrop-filter:var(--nw-frost)}
.f-chip .icon{width:14px;height:14px;color:var(--nw-fg2)}
.f-chip.out{border-color:color-mix(in oklab,var(--nw-watch) 60%,var(--nw-line));background:color-mix(in oklab,var(--nw-watch) 18%,var(--nw-bg))}
.f-chip.out .icon{color:color-mix(in oklab,var(--nw-watch) 45%,var(--nw-fg))}
.f-more{display:flex;align-items:center;gap:10px;padding:10px 16px;border-top:1px solid var(--nw-line-soft)}
.f-more .nw-sum{flex:1;font-size:var(--nw-fs-small);color:var(--nw-fg2)}
.f-mini{display:flex;align-items:center;gap:12px;padding:10px 14px;position:relative;overflow:hidden;isolation:isolate}
.f-mini::after{content:'';position:absolute;inset:0;z-index:-1;background:linear-gradient(90deg,color-mix(in oklab,var(--c) 26%,var(--nw-bg)),var(--nw-bg) 65%)}
.f-mini .nc-disk{width:40px;height:40px;flex:none}.f-mini .nc-disk .icon{width:20px;height:20px}.f-mini .nc-disk::before,.f-mini .nc-disk::after{inset:-5px}
.f-mini .t{flex:1;min-width:0}.f-mini .t b{display:block;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.f-mini .t span{font-size:var(--nw-fs-small);color:var(--nw-fg2)}
.f-mini .v{font-size:var(--nw-fs-title);font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}.f-mini .v small{font-size:var(--nw-fs-small);font-weight:400;color:var(--nw-fg2)}
.f-head{display:flex;align-items:center;gap:8px;padding:14px 16px 0}.f-head h2{margin:0;font-size:var(--nw-fs-title)}
.f-pad{padding:0 16px 16px}
.f-rows{display:grid;padding:6px 8px 10px}
.f-r{display:grid;grid-template-columns:auto minmax(0,max-content) minmax(0,1fr) auto;align-items:center;gap:10px;padding:9px 10px;border-radius:10px}
.f-r:hover{background:color-mix(in srgb,var(--nw-fg) 5%,transparent)}
.f-r i{width:10px;height:10px;border-radius:50%;background:var(--c)}
.f-r b{font-size:var(--nw-fs-text)}.f-r span{font-size:var(--nw-fs-small);color:var(--nw-fg2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.f-r em{font-style:normal;font-size:var(--nw-fs-title);font-weight:700;font-variant-numeric:tabular-nums}.f-r em small{font-size:var(--nw-fs-small);font-weight:400;color:var(--nw-fg2)}
`;
class Mock extends HTMLElement{
  constructor(){super();this.attachShadow({mode:'open'});}
  set html(v){this.shadowRoot.innerHTML=`<style>${charte}${room}${extra}</style>${v}`;}
}
customElements.define('nc-mock',Mock);
const dark=()=>document.documentElement.dataset.theme!=='light';
const mock=html=>{const m=document.createElement('nc-mock');m.style.display='block';m.setAttribute('forced',dark()?'dark':'light');m.html=html;return m;};

/* Les données : les situations calculées par le moteur (refonte/scenes.py). */
const num=v=>v==null?'—':new Intl.NumberFormat('fr-FR',{maximumFractionDigits:1}).format(v);
const CUISINE={name:'Cuisine',pill:'Geste conseillé',title:'Aérez 25 à 35 min',line:'Dehors 78 %, mais l’air froid contient peu d’eau : <b>environ 63 %</b> après l’aération',disk:'open',
  measures:[['temp','21,1 °C',false],['drop','72 %',true],['air','640 ppm',false]]};
const PLUIE={name:'Chambre M',pill:'Attention',title:'Fermez, il pleut',line:'La pluie <b>entre par les ouvrants exposés</b>',disk:'rain',measures:[]};
const ROOMS=[['Cuisine','action','Aérez 25 à 35 min',21.1],['Chambre P','action','Lancez la VMC',20.2],['Salon','calm','Rien à faire',21.5],['Salle de bain','calm','Rien à faire',22.3]];

const disk=d=>`<div class="nc-diskwrap"><div class="nc-disk" data-disk="${d}">${ic(d)}</div></div>`;
const chips=list=>`<div class="f-chips">${list.map(([i,v,out])=>`<span class="f-chip${out?' out':''}">${ic(i)}${v}</span>`).join('')}</div>`;
const top=(name,pill)=>`<div class="nc-top"><h2>${name}</h2><button class="nw-info" aria-label="Pourquoi ?">${ic('info')}</button><span class="nw-chip nc-level">${pill}</span></div>`;
const tileHero=(r,withChips=true)=>`<div class="nc-hero f-hero">${top(r.name,r.pill)}
  <div class="f-row"><div><p class="f-title">${r.title}</p><p class="nc-line">${r.line}</p></div>${disk(r.disk)}</div>${withChips&&r.measures.length?chips(r.measures):''}</div>`;
const tiles=`<div class="nc-tiles">
  <div class="nc-tile out" data-level="watch"><div class="nc-tile-h"><span class="nc-ic">${ic('drop')}</span><span class="nw-label">Humidité</span></div><b>72<small>%</small></b><em>trop humide</em></div>
  <div class="nc-tile" data-level="calm"><div class="nc-tile-h"><span class="nc-ic">${ic('air')}</span><span class="nw-label">CO₂</span></div><b>640<small>ppm</small></b><em>dans votre plage</em></div>
  <div class="nc-tile" data-level="neutral"><div class="nc-tile-h"><span class="nc-ic">${ic('window')}</span><span class="nw-label">Fenêtres</span></div><b>0/1</b><em>toutes fermées</em></div>
  <div class="nc-tile" data-level="neutral"><div class="nc-tile-h"><span class="nc-ic">${ic('sun')}</span><span class="nw-label">Soleil</span></div><b>Doux</b><em>210 W/m²</em></div></div>`;
const scaleBlock=`<div class="nc-sec nw-glass"><div class="nw-label">Température</div><div class="nc-scale" role="img" aria-label="21,1 °C dans votre plage">
  <div class="nc-track"></div><span class="nc-band" style="left:40%;width:42%"></span><span class="nc-day" style="left:36%;width:20%"></span>
  <span class="nc-mk out" style="left:12%"></span><span class="nc-ring" style="left:45%"></span><span class="nw-pill nc-now" style="left:45%">21,1 °C</span>
  <span class="nc-lb" style="left:12%">dehors 10 °C</span><span class="nc-lb" style="left:40%">20 °C</span><span class="nc-lb" style="left:82%">25 °C</span></div></div>`;
const more=(label,sum)=>`<div class="f-more"><span class="nw-label">${label}</span><span class="nw-sum">${sum}</span><span class="nw-chevron">${ic('chevron')}</span></div>`;
const hiddenNote=text=>{const n=document.createElement('div');n.className='hidden-note';n.textContent=text;return n;};
const stack=(...items)=>{const w=document.createElement('div');w.style.display='grid';w.style.gap='10px';w.append(...items);return w;};

/* La vraie carte, nourrie par les situations du moteur (comme refonte/apercu.js). */
const views=Object.fromEntries(data.scenes.map(s=>[s.id,s.view]));
const fresh=v=>({...structuredClone(v),computed_at:new Date().toISOString()});
const hass=()=>({themes:{darkMode:dark()},connection:{async subscribeMessage(cb,m){
  if(m.type==='hestia_comfort/home_subscribe')cb({...data.home,rooms:data.home.rooms.map(fresh)});else cb({version:1,view:fresh(views[m.entry_id])});return ()=>{};}},
  async callWS(){return data.scenes.map(s=>({entry_id:s.id,title:s.view.title}));}});
const roomSettings={format:'full',state:{},real:{}},homeSettings={format:'full',state:{},real:{}};
const realRoom=(format='full',id='geste')=>{const c=document.createElement('hestia-comfort-card');c.setConfig({type:'custom:hestia-comfort-card',entry_id:id,format,...roomSettings.real});c.hass=hass();return c;};
const realHome=(format='full')=>{const c=document.createElement('hestia-comfort-home-card');c.setConfig({type:'custom:hestia-comfort-home-card',format,...homeSettings.real});c.hass=hass();return c;};

/* Les formats de la carte pièce. */
const ROOM={
  full:{label:'Complète',hint:'bandeau, échelle, mesures et détails',make:()=>realRoom('full')},
  tile:{label:'Tuile',hint:'le conseil et trois pastilles ; se déplie d’un appui',make:()=>realRoom('tile')},
  intermediate:{label:'Tuile dépliée',hint:'la même, ouverte au départ',make:()=>realRoom('intermediate')},
  mini:{label:'Mini',hint:'une ligne : le conseil et la température',make:()=>realRoom('mini')},
  measures:{label:'Mesures',hint:'les tuiles de la pièce, sans conseil',make:()=>realRoom('measures')},
  alert:{label:'Alerte',hint:'visible seulement pour un geste urgent ou conseillé',make:()=>stack(realRoom('alert','urgent'),hiddenNote('Tout va bien : la carte disparaît du tableau de bord.'))},
};
/* Les formats de la carte logement. */
const roomScale=`<div class="nc-sec nw-glass"><div class="nw-label">Les pièces</div><div class="nc-scale" role="img" aria-label="Les pièces dans votre plage">
  <div class="nc-track"></div><span class="nc-band" style="left:40%;width:42%"></span><span class="nc-mk out" style="left:10%"></span>
  ${[['C',47,'action'],['P',37,'action'],['S',54,'calm'],['SB',64,'calm']].map(([s,x,l])=>`<span class="nc-mk room" data-level="${l}" style="left:${x}%"></span><span class="nc-lb up" style="left:${x}%"><b>${s}</b></span>`).join('')}
  <span class="nc-lb" style="left:10%">dehors 10 °C</span><span class="nc-lb" style="left:40%">20 °C</span><span class="nc-lb" style="left:82%">25 °C</span></div></div>`;
const rows=`<div class="f-rows">${ROOMS.map(([n,l,a,t])=>`<div class="f-r" data-level="${l}"><i></i><b>${n}</b><span>${a}</span><em>${num(t)}<small> °C</small></em></div>`).join('')}</div>`;
const HOME={
  full:{label:'Complète',hint:'bandeau, échelle des pièces, pièces et détails',make:()=>realHome('full')},
  tile:{label:'Tuile',hint:'le conseil de la pièce qui demande le plus, l’échelle des pièces',make:()=>realHome('tile')},
  list:{label:'Liste des pièces',hint:'une ligne par pièce, la couleur dit s’il y a un geste',make:()=>realHome('list')},
  mini:{label:'Mini',hint:'une ligne pour toute la maison',make:()=>realHome('mini')},
  alert:{label:'Alerte',hint:'visible seulement si une pièce demande un geste',make:()=>stack(realHome('alert'),hiddenNote('Aucune pièce ne demande de geste : la carte disparaît.'))},
};

/* Le panneau de réglages, construit comme celui de Hestia Weather (sans réglage de thème : la carte suit Home Assistant). */
const sw=(key,label,help,on,state)=>`<div class="sw"><div>${label}${help?`<small>${help}</small>`:''}</div><button class="switch" role="switch" data-key="${key}" aria-checked="${state[key]??on}"></button></div>`;
const chipList=(items,help,add)=>`<div class="chips">${items.map(i=>`<span class="chip"><span class="h">≡</span>${i}<span class="x">✕</span></span>`).join('')}</div>
  <span class="add">${ic('list','gico')}${add}</span>${help?`<p class="help">${help}</p>`:''}`;
const group=(title,icon,body,open=false)=>`<details class="group"${open?' open':''}><summary>${ic(icon,'gico')}${title}${ic('chevron','chev')}</summary><div class="in">${body}</div></details>`;
const select=(label,value,help)=>`<div class="field"><label>${label}</label><div class="select"><span>${value}</span>▾</div>${help?`<p class="help">${help}</p>`:''}</div>`;
const look=s=>group('Visuel et performance','palette',sw('animations','Animations','Coupées, la lumière et l’anneau restent fixes et les conseils ne défilent plus seuls.',true,s)
  +sw('glass_effect','Effet verre dépoli','Le flou demande beaucoup de ressources : à couper sur un appareil lent. Coupé, le verre devient plus opaque.',true,s),true);
const tap=simple=>group('Fonctionnalités','tune',select(simple?'Appui':'Appui long','Ouvrir la carte complète en fenêtre','La carte complète par-dessus la page, une page de votre tableau de bord, ou rien.'));
const radios=(formats,f)=>`<div class="field"><label>Format</label><div class="radios">${Object.entries(formats).map(([k,v])=>`<div class="radio" role="radio" data-format="${k}" aria-checked="${k===f}"><i></i><span>${v.label}<small>${v.hint}</small></span></div>`).join('')}</div></div>`;
const tabs=`<div class="tabs"><span>Configuration</span><span>Visibilité</span><span>Mise en page</span></div>`;
function roomSchema(f,s){
  const head=`${tabs}<p class="note">Pièce : <b>Cuisine</b>. Les capteurs et préférences se règlent dans <a href="#">l’intégration Hestia Confort</a>.</p>${select('Pièce','Cuisine')}${radios(ROOM,f)}`;
  if(f==='mini')return head+look(s)+group('Contenu de la ligne','grid',chipList(['Température','Humidité'],'Une ou deux valeurs à droite du conseil.','Valeurs'),true)+tap(true);
  if(f==='alert')return head+look(s)+group('Quand l’afficher','grid',select('Visible','Pour un geste urgent ou conseillé','Cachée quand tout va bien, comme l’alerte de Hestia Weather.'),true)+tap(true);
  if(f==='measures')return head+look(s)+group('Contenu','grid',chipList(['Humidité','Qualité de l’air','Fenêtres','Soleil et volets','Chauffage'],'Cochez les rubriques et faites glisser pour les ordonner.','Rubriques')
    +sw('m_scale','Échelle de température au-dessus','',false,s),true)+tap(false);
  if(f==='tile'||f==='intermediate')return head+look(s)
    +group('Tuile repliée','banner',chipList(['Température','Humidité','CO₂'],'Trois pastilles au plus sous le conseil ; une mesure hors plage passe en ambre.','Pastilles'),true)
    +group('Tuile dépliée','grid',chipList(['Échelle','Mesures','Détails'],'Ce qui s’ouvre d’un appui, dans l’ordre.','Contenu de la tuile dépliée'))+tap(false);
  return head+look(s)
    +group('Bandeau','banner',`<p class="help" style="margin:0 0 6px">Le conseil du moment reste toujours. Cochez ce qui défile après lui, dans l’ordre.</p>`
      +chipList(['Remèdes en cours (purificateur, VMC)','Plus tard (meilleur moment)'],'','Contenu du bandeau')+sw('rotate','Faire défiler les conseils','Toutes les 4,5 s ; décoché, ils changent d’un appui.',true,s),true)
    +group('Échelle de température','scale',chipList(['Votre plage','Min–max 24 h','Dehors'],'Tout décocher retire l’échelle.','Repères'))
    +group('Mesures','grid',chipList(['Humidité','Qualité de l’air','Fenêtres','Soleil et volets','Chauffage'],'Tout décocher retire la section.','Rubriques')+sw('measures_open','Mesures dépliées au départ','Repliées, les mesures hors de votre plage restent visibles.',false,s))
    +group('Détails','list',sw('show_details','Section Détails','',true,s)+sw('details_open','Détails dépliés au départ','',false,s))
    +group('Fonctionnalités','tune',select('Appui sur une mesure','Ouvrir son historique Home Assistant'));
}
function homeSchema(f,s){
  const head=`${tabs}<p class="note">Toutes les pièces de <b>Hestia Confort</b>. Les pièces se règlent dans <a href="#">l’intégration</a>.</p>${select('Titre facultatif','Mon logement')}${radios(HOME,f)}`;
  if(f==='mini'||f==='alert')return head+look(s)+tap(true);
  if(f==='list')return head+look(s)+group('Contenu','list',chipList(['Conseil de la pièce','Température'],'','Contenu des lignes')+select('Ordre des pièces','Celles qui demandent un geste d’abord'),true)
    +group('Fonctionnalités','tune',select('Appui sur une pièce','Ouvrir sa carte en fenêtre'));
  return head+look(s)
    +group('Bandeau','banner',chipList(['Conseils des pièces','Gestes pour toute la maison (air traversant)'],'','Contenu du bandeau')+sw('rotate','Faire défiler les conseils','',true,s),true)
    +group('Échelle des pièces','scale',sw('show_scale','Afficher l’échelle','Votre plage, chaque pièce et dehors.',true,s))
    +group('Pièces','grid',select('Groupement','Par étage')+sw('rooms_open','Pièces dépliées au départ','Repliées, les pièces qui demandent un geste restent visibles.',false,s))
    +group('Détails','list',sw('show_details','Section Détails','',true,s))
    +(f==='full'?'':tap(false));
}
const REAL=['animations','glass_effect','rotate','measures_open','show_details','details_open','show_scale','rooms_open'];
function wire(editId,previewId,schema,set,formats){
  const edit=$(editId),preview=$(previewId);
  const draw=keep=>{const opened=keep?[...edit.querySelectorAll('details')].map(d=>d.open):[];
    edit.innerHTML=schema(set.format,set.state);[...edit.querySelectorAll('details')].forEach((d,k)=>{if(opened[k]!==undefined)d.open=opened[k];});
    preview.replaceChildren(formats[set.format].make());};
  edit.onclick=e=>{
    const r=e.target.closest('[data-format]');if(r){set.format=r.dataset.format;draw(false);return;}
    const s=e.target.closest('.switch');if(s){const k=s.dataset.key,v=s.getAttribute('aria-checked')!=='true';set.state[k]=v;s.setAttribute('aria-checked',v);
      // Les réglages qui existent déjà pilotent la vraie carte complète.
      if(REAL.includes(k)){set.real[k]=v;preview.replaceChildren(formats[set.format].make());}return;}
    const x=e.target.closest('.x');if(x)x.closest('.chip').remove();};
  draw(false);
}
const gallery=(id,formats)=>{$(id).replaceChildren(...Object.values(formats).map(f=>{const fig=document.createElement('figure');fig.innerHTML=`<figcaption><b>${f.label}</b><span>${f.hint}</span></figcaption>`;fig.append(f.make());return fig;}));};
function render(){wire('edit','preview',roomSchema,roomSettings,ROOM);wire('home-edit','home-preview',homeSchema,homeSettings,HOME);gallery('room-formats',ROOM);gallery('home-formats',HOME);}
document.querySelectorAll('[data-t]').forEach(b=>b.onclick=()=>{document.documentElement.dataset.theme=b.dataset.t;document.querySelectorAll('[data-t]').forEach(x=>x.setAttribute('aria-pressed',x===b));render();});
render();
