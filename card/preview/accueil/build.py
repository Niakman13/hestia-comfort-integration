"""Builds maquette.html: a home page for Confort in the Hestia hub, from the real rooms (data.json, not committed)."""
from pathlib import Path
here = Path(__file__).parent
data = (here / "data.json").read_text()
page = r"""<!doctype html>
<html lang="fr" data-theme="dark">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Accueil Confort</title>
<style>
:root{--bg:#f3f5f8;--panel:#fff;--panel2:#f7f9fb;--fg:#1f2937;--fg2:#5b6575;--line:#1f29371a;--accent:#1f6f98;--accent-bg:#1f6f9814;
  --act:#c46a1c;--act-bg:#f3a35a26;--ok:#2f8f63;--ok-bg:#2f8f631f;--warn:#b7791f;color-scheme:light}
:root[data-theme="dark"]{--bg:#16181c;--panel:#1f2227;--panel2:#25292f;--fg:#e8ebf0;--fg2:#9aa3b2;--line:#ffffff17;--accent:#7cc4e8;--accent-bg:#7cc4e81a;
  --act:#f2a65a;--act-bg:#f2a65a1f;--ok:#6fcf97;--ok-bg:#6fcf971a;--warn:#e7b660;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 Roboto,system-ui,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:24px 16px 56px}
.top{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:16px}
h1{font-size:28px;margin:0}.sub{color:var(--fg2);margin:2px 0 0}
.chips{display:flex;gap:8px;flex-wrap:wrap}.chip{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:999px;background:var(--panel);border:1px solid var(--line);font-size:13px;color:var(--fg2)}
.chip b{color:var(--fg);font-weight:600}
.toggle{display:flex;gap:4px;padding:3px;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
.toggle button{border:0;background:none;color:var(--fg2);font:inherit;padding:5px 10px;border-radius:7px;cursor:pointer}.toggle button[aria-pressed="true"]{background:var(--panel2);color:var(--fg);font-weight:600}
.hero{display:grid;grid-template-columns:1fr auto;gap:20px;align-items:center;padding:22px 24px;border-radius:20px;background:var(--panel);border:1px solid var(--line);margin-bottom:18px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;inset:0;background:radial-gradient(120% 140% at 0% 0%,var(--hero) 0%,transparent 60%);pointer-events:none}
.hero>*{position:relative}.hero.action{--hero:var(--act-bg)}.hero.calm{--hero:var(--accent-bg)}
.hero .eyebrow{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--fg2)}
.hero h2{font-size:30px;margin:4px 0 6px}.hero p{margin:0;color:var(--fg2)}
.stats{display:grid;grid-template-columns:repeat(3,minmax(110px,1fr));gap:10px}
.stat{background:var(--panel2);border:1px solid var(--line);border-radius:14px;padding:10px 14px;min-width:120px}.stat b{display:block;font-size:22px}.stat span{font-size:12px;color:var(--fg2)}
.cols{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(300px,1fr);gap:18px;align-items:start}
section{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px 18px;margin-bottom:18px}
section h3{margin:0 0 12px;font-size:16px;display:flex;justify-content:space-between;align-items:center;gap:8px}
section h3 small{font-weight:400;color:var(--fg2);font-size:13px}
.todo{display:grid;gap:10px}
.task{display:grid;grid-template-columns:auto 1fr auto;gap:14px;align-items:center;padding:12px 14px;border-radius:14px;background:var(--act-bg);border:1px solid color-mix(in srgb,var(--act) 35%,transparent)}
.task .ic{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:color-mix(in srgb,var(--act) 25%,transparent);color:var(--act);font-size:18px}
.task b{display:block;font-size:16px}.task .where{font-size:12px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--fg2)}.task .line{color:var(--fg2)}
.pill{font-size:12px;font-weight:600;padding:3px 10px;border-radius:999px;background:var(--panel2);color:var(--fg2);white-space:nowrap}
.pill.opt{background:var(--accent-bg);color:var(--accent)}.pill.ok{background:var(--ok-bg);color:var(--ok)}
.calmnote{display:flex;gap:12px;align-items:center;color:var(--fg2)}
.floor{display:flex;justify-content:space-between;margin:6px 0 8px;font-size:12px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--fg2)}
.rooms{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;margin-bottom:12px}
.room{padding:12px 14px;border-radius:14px;background:var(--panel2);border:1px solid var(--line);cursor:pointer;transition:border-color .2s}
.room:hover{border-color:var(--accent)}.room.action{border-color:color-mix(in srgb,var(--act) 55%,transparent)}
.room .name{display:flex;justify-content:space-between;align-items:center;gap:6px;font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--fg2)}
.room .t{font-size:24px;font-weight:700;margin-top:4px}.room .t small{font-size:13px;font-weight:400;color:var(--fg2)}
.room .h{font-size:13px;color:var(--fg2)}.room .note{font-size:13px;margin-top:4px;display:flex;align-items:center;gap:6px}
.dot{width:8px;height:8px;border-radius:50%;background:var(--fg2);flex:none}.room.action .dot{background:var(--act)}.room .note.watch .dot{background:var(--warn)}
.learnbadge{font-size:11px;font-weight:600;color:var(--ok)}.learnbadge.wip{color:var(--fg2)}
.ring{display:flex;gap:16px;align-items:center;margin-bottom:12px}
.ring svg{width:76px;height:76px;flex:none}.ring b{font-size:18px}.ring p{margin:0;color:var(--fg2)}
.lrow{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:7px 0;border-top:1px solid var(--line);font-size:13px}
.lrow span{color:var(--fg2)}
.q{margin-top:10px;padding:10px 12px;border-radius:12px;background:var(--panel2);border:1px solid var(--line)}
.q p{margin:0 0 8px}.q small{display:block;color:var(--fg2);margin-bottom:8px}.q .b{display:flex;gap:6px;flex-wrap:wrap}
.q button{border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:10px;padding:6px 12px;font:inherit;cursor:pointer}.q button[aria-pressed="true"]{background:var(--accent);color:#111;border-color:var(--accent)}
.empty{color:var(--fg2);font-size:13px;margin:6px 0 0}
.health{display:flex;justify-content:space-between;align-items:center;gap:10px}.health .ok{color:var(--ok);font-weight:600}
.link{background:none;border:0;color:var(--accent);font:inherit;cursor:pointer;padding:0}
.short{display:grid;gap:8px}.short button{display:flex;justify-content:space-between;align-items:center;width:100%;text-align:left;border:1px solid var(--line);background:var(--panel2);color:var(--fg);border-radius:12px;padding:10px 12px;font:inherit;cursor:pointer}
.short button span{color:var(--fg2);font-size:12px}
@media (max-width:900px){.cols{grid-template-columns:1fr}.hero{grid-template-columns:1fr}.stats{grid-template-columns:repeat(3,1fr)}}
@media (max-width:520px){.stats{grid-template-columns:1fr 1fr}.hero h2{font-size:24px}}
</style></head>
<body><div class="wrap" id="app"></div>
<script>
const data=__DATA__;
const fr=(x,d=1)=>x==null?'—':Number(x).toLocaleString('fr-FR',{maximumFractionDigits:d});
const FLOORS=[['Rez-de-chaussée',['Salon','Cuisine','Buanderie','Chambre P']],['Étage 1',['Chambre A','Chambre AL','Chambre M','Salle de bain']]];
// Rooms sharing one air are one: the best equipped speaks.
const seen=new Set(),rooms=[];
for(const r of data.rooms){if(seen.has(r.id))continue;r.partners.forEach(p=>seen.add(p));seen.add(r.id);
  const group=[r,...data.rooms.filter(x=>r.partners.includes(x.id))],lead=group.find(x=>x.title===(r.volume||'').split(' · ')[0])||r;
  rooms.push({...lead,name:r.volume||r.title,members:group.map(x=>x.title),temps:group.map(x=>x.t)});}
const learn=t=>{const p=t&&t.precision;if(!t||t.status!=='ready'||t.days<7)return {label:'En cours',ok:false};if(!p)return {label:'À vérifier',ok:false};
  return p.temperature<=0.5&&p.humidity<=3?{label:'Connue',ok:true}:{label:'À affiner',ok:false};};
const tasks=rooms.filter(r=>['action','urgent'].includes(r.level));
const known=data.rooms.filter(r=>learn(r.twin).ok).length,total=data.rooms.length;
const mean=k=>{const v=data.rooms.map(r=>r[k]).filter(x=>x!=null);return v.length?v.reduce((a,b)=>a+b,0)/v.length:null;};
const out=data.rooms.find(r=>r.te!=null);
const when=new Date(data.at).toLocaleString('fr-FR',{weekday:'long',day:'numeric',month:'long',hour:'2-digit',minute:'2-digit'}).replace(':',' h ');
const ICONS=[['Rallumez','🔥'],['Gardez fermé','🪟'],['Refermez','⇤'],['Fermez','⇤'],['Aérez','🌬'],['Ouvrez','🌬'],['Lancez la VMC','🌀'],['Aération','🌬']];
const icon=t=>(ICONS.find(([k])=>t.startsWith(k))||[,'•'])[1];
const app=document.getElementById('app');
app.innerHTML=`
<div class="top"><div><h1>Confort</h1><p class="sub">${when[0].toUpperCase()+when.slice(1)} · ${total} pièces suivies</p></div>
 <div class="chips"><span class="chip">Dehors <b>${fr(out?.te)} °C</b> · ${fr(out?.he,0)} %${out?.rain?' · pluie':''}</span><span class="chip">Météo : <b>Hestia Weather</b></span>
 <div class="toggle"><button data-t="light">Clair</button><button data-t="dark" aria-pressed="true">Sombre</button></div></div></div>
<div class="hero ${tasks.length?'action':'calm'}"><div><div class="eyebrow">Mon logement</div>
 <h2>${tasks.length?`${tasks.length} geste${tasks.length>1?'s':''} à faire`:'Tout va bien'}</h2>
 <p>${tasks.length?tasks.map(t=>`${t.name} : ${t.advice.title.toLowerCase()}`).join(' · '):'Aucun geste à faire pour l’instant.'}</p></div>
 <div class="stats"><div class="stat"><b>${fr(mean('t'))} °C</b><span>en moyenne dedans</span></div><div class="stat"><b>${fr(mean('h'),0)} %</b><span>d’humidité moyenne</span></div>
 <div class="stat"><b>${known} / ${total}</b><span>pièces connues</span></div></div></div>
<div class="cols"><div>
 <section><h3>À faire maintenant <small>${tasks.length?'le geste et sa raison':''}</small></h3>
  ${tasks.length?`<div class="todo">${tasks.map(t=>`<div class="task"><div class="ic">${icon(t.advice.title)}</div>
   <div><span class="where">${t.name}</span><b>${t.advice.title}</b><span class="line">${t.advice.line}</span></div>
   ${t.advice.learned?'<span class="pill opt">⚗ Conseil optimisé</span>':'<span class="pill">Estimé</span>'}</div>`).join('')}</div>`
  :'<div class="calmnote">✓ Rien à faire : toutes les pièces sont dans votre plage ou n’ont rien à gagner à être aérées.</div>'}</section>
 <section><h3>Pièces <small>un appui ouvre la pièce</small></h3>
  ${FLOORS.map(([f,names])=>{const list=rooms.filter(r=>r.members.some(m=>names.includes(m)));if(!list.length)return '';
   const temps=list.flatMap(r=>r.temps).filter(x=>x!=null),avg=temps.reduce((a,b)=>a+b,0)/temps.length;
   return `<div class="floor"><span>${f}</span><span>${fr(avg)} °C</span></div><div class="rooms">${list.map(r=>{const l=learn(r.twin),act=['action','urgent'].includes(r.level);
    const note=act?r.advice.title:(r.needs[0]||'dans votre plage');return `<div class="room${act?' action':''}"><div class="name"><span>${r.name}</span><span class="learnbadge${l.ok?'':' wip'}">${l.ok?'✓ connue':l.label.toLowerCase()}</span></div>
    <div class="t">${fr(r.t)}<small> °C</small></div><div class="h">${fr(r.h,0)} % d’humidité${r.co2?` · ${fr(r.co2,0)} ppm`:''}</div>
    <div class="note${!act&&r.needs.length?' watch':''}"><span class="dot"></span>${note}</div></div>`;}).join('')}</div>`;}).join('')}</section>
</div><div>
 <section><h3>Apprentissage</h3>
  <div class="ring"><svg viewBox="0 0 36 36"><circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--line)" stroke-width="3.5"/>
   <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--ok)" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="${known/total*100} 100" transform="rotate(-90 18 18)"/></svg>
   <div><b>Apprentissage optimal pour ${known} pièces sur ${total}</b><p>Leurs conseils sont optimisés ; les autres restent estimés pour l’instant.</p></div></div>
  ${data.rooms.map(r=>{const l=learn(r.twin),p=r.twin&&r.twin.precision;return `<div class="lrow"><b>${r.title}</b><span>${p?`±${fr(p.temperature,2)} °C · ±${fr(p.humidity,0)} %`:'—'}</span><span class="pill${l.ok?' ok':''}">${l.label} · ${Math.floor(r.twin?.days||0)} j</span></div>`;}).join('')}
  ${data.rooms.flatMap(r=>(r.questions||[]).map(q=>`<div class="q"><p>${q.text}</p><small>${q.hint}</small><div class="b"><button>Oui</button><button>Non</button><button>Je ne sais pas</button></div></div>`)).join('')}
  <h3 style="margin-top:16px">Cette semaine</h3>${data.rooms.some(r=>r.week&&(r.week.followed||r.week.ignored))?'':'<p class="empty">Le bilan apparaîtra après vos premières aérations conseillées et suivies.</p>'}
 </section>
 <section><h3>État technique</h3><div class="health"><span class="ok">● Tout fonctionne</span><button class="link">Voir le détail</button></div>
  <p class="empty">8 pièces · capteurs à jour · Hestia Weather relié</p></section>
 <section><h3>Raccourcis</h3><div class="short"><button>Ajouter une pièce <span>Entrée est disponible</span></button><button>Extérieur et météo <span>Hestia Weather</span></button><button>Les cartes du tableau de bord <span>Comment les ajouter</span></button><button>Réglages des pièces <span>8 pièces</span></button></div></section>
</div></div>`;
document.querySelectorAll('[data-t]').forEach(b=>b.onclick=()=>{document.documentElement.dataset.theme=b.dataset.t;document.querySelectorAll('[data-t]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));});
document.querySelectorAll('.q').forEach(q=>q.querySelectorAll('button').forEach(b=>b.onclick=()=>q.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)))));
</script></body></html>"""
(here / "maquette.html").write_text(page.replace("__DATA__", data))
print("ok")
