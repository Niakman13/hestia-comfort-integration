"""Builds maquette.html: learned versus estimated advice on the card, and the « Apprentissage » box of the Confort home."""
from pathlib import Path
here = Path(__file__).parent
bundle = (here.parents[2] / "custom_components" / "hestia_comfort" / "frontend" / "hestia-comfort-card.js").read_text()
scenes = (here / "scenes.json").read_text()
twins = (here / "twins.json").read_text()
style = (here.parent / "conseils" / "build.py").read_text().split("<style>")[1].split("</style>")[0]
page = """<!doctype html>
<html lang="fr" data-theme="light">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Conseils optimisés</title>
<style>""" + style + """
h2{font-size:19px;margin:34px 0 4px}
.grid{grid-template-columns:repeat(auto-fill,minmax(340px,1fr))}
.hub{background:var(--field);border:1px solid var(--line);border-radius:18px;padding:18px 20px;max-width:1100px}
.hub h3{margin:0 0 2px;font-size:18px}.hub .sum{color:var(--fg2);margin:0 0 14px}
.rooms{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.room{border:1px solid var(--line);border-radius:14px;padding:12px 14px}
.room .head{display:flex;justify-content:space-between;align-items:center;gap:8px}
.pill{font-size:12px;font-weight:600;padding:3px 9px;border-radius:999px;background:color-mix(in srgb,var(--fg) 8%,transparent);color:var(--fg2)}
.pill.ok{background:color-mix(in srgb,var(--primary-color) 16%,transparent);color:var(--primary-color)}
.room ul{margin:8px 0 0;padding-left:18px;color:var(--fg2);font-size:13px}.room li{margin:3px 0}
.room .prec{font-size:12px;color:var(--fg2);margin-top:6px}
.ask{margin-top:16px;display:grid;gap:10px}
.q{border:1px solid var(--line);border-radius:14px;padding:12px 14px;display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.q p{margin:0;max-width:640px}.q small{display:block;color:var(--fg2)}
.q .btns{display:flex;gap:6px}.q button{border:1px solid var(--line);background:var(--page);color:var(--fg);border-radius:10px;padding:7px 12px;font:inherit;cursor:pointer}
.q button[aria-pressed="true"]{background:var(--primary-color);color:#fff;border-color:var(--primary-color)}
.week{margin-top:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
.week div{border:1px solid var(--line);border-radius:14px;padding:10px 14px}.week b{display:block;font-size:22px}.week span{color:var(--fg2);font-size:13px}
.ex{font-size:12px;color:var(--fg2);font-style:italic}
</style></head>
<body><main>
<div class="top"><div>
<h1>Conseils optimisés</h1>
<p class="lead">Quand l’apprentissage d’une pièce est optimal, son conseil est « optimisé » : il annonce le résultat chiffré. Sinon, le conseil reste estimé, et À savoir dit où en est l’apprentissage. Chiffres de vos pièces du 20 octobre.</p>
</div><div class="toggle" role="group" aria-label="Thème"><button data-theme-set="light" aria-pressed="true">Clair</button><button data-theme-set="dark" aria-pressed="false">Sombre</button></div></div>
<h2>1. Un conseil optimisé sur la carte</h2>
<p class="lead">« Conseil optimisé » remplace « Geste conseillé » en haut à droite ; le conseil annonce son résultat chiffré, avec la durée apprise.</p>
<div class="grid" id="marks"></div>
<h2>2. Les autres cas</h2>
<div class="grid" id="others"></div>
<h2>3. L’accueil Confort du hub Hestia : l’encart Apprentissage</h2>
<div class="hub" id="hub"></div>
</main>
<script>customElements.get('home-assistant')||customElements.define('home-assistant',class extends HTMLElement{});</script>
<script type="module">
""" + bundle + """
</script>
<script type="module">
const data=__SCENES__,twins=__TWINS__;
await customElements.whenDefined('hestia-comfort-card');
const views=Object.fromEntries(data.scenes.map(s=>[s.id,s.view]));
{const e=structuredClone(views.appris);e.entry_id='estime';delete e.assessment.features.learned;e.twin={status:'ready',days:5,samples:240,next_hour:null,precision:null};views.estime=e;}
const fresh=v=>({...structuredClone(v),computed_at:new Date().toISOString()});
const dark=()=>document.documentElement.dataset.theme==='dark';
const hass=()=>({themes:{darkMode:dark()},connection:{async subscribeMessage(cb,m){const send=()=>cb({version:1,view:fresh(views[m.entry_id])});send();const t=setInterval(send,30000);return ()=>clearInterval(t);}},async callWS(){return [];}});
const MARKS=[['Conseil optimisé','Apprentissage optimal pour la cuisine : le conseil vient de son apprentissage.',''],['Conseil estimé, pour comparer','La même situation, apprentissage en cours : pas de chiffre promis.','']];
const cards=[];
const make=(where,id,title,note,css)=>{const fig=document.createElement('figure');fig.innerHTML=`<figcaption><b>${title}</b><span>${note}</span></figcaption>`;
  const c=document.createElement('hestia-comfort-card');c.setConfig({type:'custom:hestia-comfort-card',entry_id:id,format:'tile'});fig.append(c);document.getElementById(where).append(fig);cards.push([c,css]);};
make('marks','appris',MARKS[0][0],MARKS[0][1],'');make('marks','estime',MARKS[1][0],MARKS[1][1],'');
for(const s of data.scenes.slice(1))make('others',s.id,s.title,s.note,'');
const apply=()=>{const h=hass();for(const [c] of cards)c.hass=h;setTimeout(()=>{for(const [c,css] of cards){if(!css||!c.shadowRoot)continue;let s=c.shadowRoot.querySelector('style[data-v]');if(!s){s=document.createElement('style');s.dataset.v='';c.shadowRoot.append(s);}s.textContent=css;}},300);};
apply();
document.querySelectorAll('[data-theme-set]').forEach(b=>b.addEventListener('click',()=>{document.documentElement.dataset.theme=b.dataset.themeSet;
  document.querySelectorAll('[data-theme-set]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));apply();}));
// The « Apprentissage » box, from what the twins really learned.
const fr=(x,d=1)=>Number(x).toLocaleString('fr-FR',{maximumFractionDigits:d});
// The hub is the technical side: the precision stays in figures, under a plain sentence.
const prec=r=>`prévisions justes à ±${fr(r.precision.temperature,r.precision.temperature<1?2:1)} °C et ±${fr(r.precision.humidity,0)} %`;
const status=r=>!r.precision.temperature?['À vérifier','','Vérification en attente : il manque une journée de mesures complète']
  :r.precision.temperature<=0.5&&r.precision.humidity<=3?['Connue','ok',`Apprentissage optimal : ${prec(r)}`]
  :['À affiner','',`Apprentissage en cours : ${prec(r)}`];
// What the twin learned, in words: a scale, never hours, degrees or air changes.
const facts=r=>{const o=r.room||{},out=[];const h=o.inertia_hours,sun=o.sun_degrees,air=o.air_changes_per_hour;
  if(h)out.push(h<24?'se refroidit vite':h<72?'garde bien sa température':'garde très longtemps sa température');
  if(sun!=null)out.push(sun<0.5?'le soleil la réchauffe peu':sun<1.5?'le soleil la réchauffe un peu':'le soleil la réchauffe beaucoup');
  if(air)out.push(1/air<4?'fenêtres fermées, son air se renouvelle bien':'fenêtres fermées, son air se renouvelle lentement');
  return out.slice(0,3);};
const rooms=[...twins.rooms].sort((a,b)=>(status(a)[1]==='ok'?0:1)-(status(b)[1]==='ok'?0:1)||a.title.localeCompare(b.title,'fr'));
const ok=rooms.filter(r=>status(r)[1]==='ok').length;
document.getElementById('hub').innerHTML=`<h3>Apprentissage</h3><p class="sum">Apprentissage optimal pour ${ok} pièces sur ${rooms.length} : leurs conseils sont optimisés. Les autres restent estimés pour l’instant.</p>
<div class="rooms">${rooms.map(r=>{const [label,cls,why]=status(r);return `<div class="room"><div class="head"><b>${r.title}</b><span class="pill ${cls}">${label} · ${fr(r.days,0)} jours</span></div>
<div class="prec">${why}</div><ul>${facts(r).map(f=>`<li>${f}</li>`).join('')}</ul></div>`;}).join('')}</div>
<div class="ask"><b>Pour affiner l’apprentissage</b>
<div class="q"><p>L’humidité de la salle de bain monte souvent vers 21 h en semaine. Est-ce la douche ?<small>Votre réponse précise la cause ; sans elle, aucune cause n’est affichée.</small></p><div class="btns"><button>Oui</button><button>Non</button><button>Je ne sais pas</button></div></div>
<div class="q"><p>La fenêtre de la Chambre AL est souvent entrouverte la nuit. Est-ce voulu ?<small>Si oui, elle ne sera plus signalée comme un oubli.</small></p><div class="btns"><button>Oui</button><button>Non</button><button>Je ne sais pas</button></div></div></div>
<div class="ask"><b>Cette semaine</b> <span class="ex">(exemple : arrivera avec la boucle de retour)</span></div>
<div class="week"><div><b>6</b><span>conseils suivis</span></div><div><b>−7 %</b><span>d’humidité en moyenne après une aération</span></div><div><b>5 sur 6</b><span>prévisions tenues</span></div><div><b>Cuisine</b><span>la pièce qui gagne le plus à être aérée</span></div></div>`;
document.querySelectorAll('.q').forEach(q=>q.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>q.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b))))));
</script></body></html>
"""
(here / "maquette.html").write_text(page.replace("__SCENES__", scenes).replace("__TWINS__", twins))
print("ok")
