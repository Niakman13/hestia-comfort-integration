"""Builds technique.html: a technical home page for Confort in the Hestia hub, from the real health report (tech.json)."""
from pathlib import Path
here = Path(__file__).parent
data = (here / "tech.json").read_text()
css = (here / "build.py").read_text().split("<style>")[1].split("</style>")[0]
page = r"""<!doctype html>
<html lang="fr" data-theme="dark">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Accueil Confort</title>
<style>""" + css + r"""
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:18px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:14px 16px}
.kpi b{display:block;font-size:24px}.kpi span{color:var(--fg2);font-size:13px}.kpi.ok b{color:var(--ok)}.kpi.act b{color:var(--act)}
.statusline{display:inline-flex;align-items:center;gap:8px;font-weight:600}.statusline .dot{background:var(--ok)}
table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;font-weight:600;color:var(--fg2);font-size:12px;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:8px;border-bottom:1px solid var(--line);vertical-align:middle}tr:last-child td{border-bottom:0}
.tablewrap{overflow-x:auto}
.c-ok{color:var(--ok)}.c-none{color:var(--fg2)}.c-bad{color:var(--act)}
.mini{width:90px;height:24px;display:block}.mini polyline{fill:none;stroke-width:1.6}.mini .m{stroke:var(--fg2)}.mini .r{stroke:var(--accent);stroke-dasharray:3 2}
.btn{border:1px solid var(--line);background:var(--panel2);color:var(--fg);border-radius:10px;padding:5px 10px;font:inherit;font-size:12px;cursor:pointer}
.btn.primary{background:var(--accent);color:#111;border-color:var(--accent);font-weight:600}
.srow{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--line)}.srow:first-of-type{border-top:0}
.srow span{color:var(--fg2);font-size:13px;text-align:right}
.ok-line{display:flex;align-items:center;gap:8px;color:var(--fg2)}
.legend{display:flex;gap:14px;font-size:12px;color:var(--fg2);margin-top:8px}
@media (max-width:900px){.kpis{grid-template-columns:1fr 1fr}}
</style></head>
<body><div class="wrap" id="app"></div>
<script>
const D=__DATA__,H=D.health;
const fr=(x,d=1)=>x==null?'—':Number(x).toLocaleString('fr-FR',{maximumFractionDigits:d});
const learn=t=>{const p=t&&t.precision;if(!t||t.status!=='ready'||t.days<7)return ['En cours',''];if(!p)return ['À vérifier',''];return p.temperature<=0.5&&p.humidity<=3?['Connue','ok']:['À affiner',''];};
const cells=H.rooms.flatMap(r=>r.cells),answering=cells.filter(c=>c.level==='ok').length,configured=cells.filter(c=>c.level!=='none').length;
const known=D.twins.filter(r=>learn(r.twin)[1]==='ok').length,todo=H.todo.length+H.tips.length;
const spark=c=>{if(!c||c.length<2)return '';const all=c.flatMap(x=>[x.temperature,x.measured_temperature]),lo=Math.min(...all)-.2,hi=Math.max(...all)+.2;
  const l=k=>c.map((x,i)=>`${(i/(c.length-1)*90).toFixed(1)},${(24-(x[k]-lo)/(hi-lo)*24).toFixed(1)}`).join(' ');
  return `<svg class="mini" viewBox="0 0 90 24" preserveAspectRatio="none"><polyline class="m" points="${l('measured_temperature')}"/><polyline class="r" points="${l('temperature')}"/></svg>`;};
const roomOf=title=>D.rooms.find(r=>r.title===title)||{};
const air=title=>{const r=roomOf(title);return [r.co2!=null?'CO₂':null,title==='Salon'?'COV':null].filter(Boolean).join(' · ')||'—';};
const volume=title=>roomOf(title).volume||'—';
document.getElementById('app').innerHTML=`
<div class="top"><div><h1>Confort</h1><p class="sub"><span class="statusline"><span class="dot"></span>${todo?todo+' point'+(todo>1?'s':'')+' à regarder':'Tout fonctionne'}</span> · Intégration 1.2.5 · Hestia Weather 2.6.1 relié (Gardanne) · ${H.rooms.length} pièces</p></div>
 <div class="chips"><button class="btn primary">Ajouter une pièce</button><button class="btn">Extérieur et météo</button>
 <div class="toggle"><button data-t="light">Clair</button><button data-t="dark" aria-pressed="true">Sombre</button></div></div></div>
<div class="kpis">
 <div class="kpi ${answering===configured?'ok':'act'}"><b>${answering} / ${configured}</b><span>capteurs qui répondent</span></div>
 <div class="kpi"><b>${known} / ${D.twins.length}</b><span>pièces en apprentissage optimal</span></div>
 <div class="kpi ${todo?'act':'ok'}"><b>${todo}</b><span>point${todo>1?'s':''} à régler ou améliorer</span></div>
 <div class="kpi ok"><b>${H.sources.filter(s=>s.level==='ok').length} / ${H.sources.length}</b><span>sources partagées en place</span></div></div>
<div class="cols"><div>
 <section><h3>À régler <small>${todo?'':'rien pour l’instant'}</small></h3>${todo?'':'<div class="ok-line"><span class="dot" style="background:var(--ok)"></span>Aucun capteur muet, aucune source manquante, aucune pièce incomplète.</div>'}</section>
 <section><h3>Apprentissage <small>prévisions rejouées sur les dernières 24 h</small></h3><div class="tablewrap"><table>
  <tr><th>Pièce</th><th>État</th><th>Température</th><th>Humidité</th><th>Air appris</th><th>24 h</th></tr>
  ${D.twins.map(r=>{const [l,c]=learn(r.twin),p=r.twin.precision;return `<tr><td><b>${r.title}</b></td><td><span class="pill ${c}">${l} · ${Math.floor(r.twin.days)} j</span></td>
   <td>${p?'±'+fr(p.temperature,2)+' °C':'—'}</td><td>${p?'±'+fr(p.humidity,0)+' %':'—'}</td><td class="${air(r.title)==='—'?'c-none':''}">${air(r.title)}</td><td>${spark(p&&p.curve)}</td></tr>`;}).join('')}
 </table></div><div class="legend"><span>— mesurée</span><span style="color:var(--accent)">- - rejouée</span><span>Optimal : 7 jours, ±0,5 °C et ±3 %</span></div>
 ${D.twins.flatMap(r=>(r.questions||[]).map(q=>`<div class="q"><p>${q.text}</p><small>${q.hint}</small><div class="b"><button>Oui</button><button>Non</button><button>Je ne sais pas</button></div></div>`)).join('')}
 <h3 style="margin-top:16px">Cette semaine</h3><p class="empty">Le bilan apparaîtra après les premières aérations conseillées et suivies.</p></section>
 <section><h3>Pièces et capteurs <button class="btn">Ajouter une pièce</button></h3><div class="tablewrap"><table>
  <tr><th>Pièce</th>${H.columns.map(c=>`<th>${c}</th>`).join('')}<th>Même air</th><th></th></tr>
  ${H.rooms.map(r=>`<tr><td><b>${r.title}</b></td>${r.cells.map(c=>`<td class="c-${c.level}">${c.level==='ok'?'● ':''}${c.text}</td>`).join('')}<td class="${volume(r.title)==='—'?'c-none':''}">${volume(r.title)}</td><td><button class="btn">Configurer</button></td></tr>`).join('')}
 </table></div></section>
</div><div>
 <section><h3>Sources partagées</h3>${H.sources.map(s=>`<div class="srow"><b>${s.label}</b><span>${s.text}</span></div>`).join('')}
  <div class="srow"><b>Présence</b><span>Alarmo · zone Maison</span></div><div class="srow"><b>Soleil</b><span>sun.sun · façades des fenêtres</span></div></section>
 <section><h3>Versions et liens</h3><div class="srow"><b>Intégration</b><span>1.2.5</span></div><div class="srow"><b>Carte</b><span>1.2.5 · embarquée</span></div>
  <div class="srow"><b>Hestia Weather</b><span>2.6.1 · relié à Gardanne</span></div><div class="srow"><b>Interface Maison</b><span>hestia_comfort_api v1</span></div></section>
 <section><h3>Les cartes</h3><p class="empty" style="margin:0 0 10px">Dans un tableau de bord : Ajouter une carte, puis <b>Hestia Confort</b> pour une pièce, ou <b>Hestia Confort · logement</b> pour la synthèse.</p>
  <div class="short"><button>Ajouter une carte pièce <span>8 pièces · Salon · Cuisine en une</span></button><button>Ajouter la carte logement <span>synthèse</span></button></div></section>
</div></div>`;
document.querySelectorAll('[data-t]').forEach(b=>b.onclick=()=>{document.documentElement.dataset.theme=b.dataset.t;document.querySelectorAll('[data-t]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));});
document.querySelectorAll('.q').forEach(q=>q.querySelectorAll('button').forEach(b=>b.onclick=()=>q.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)))));
</script></body></html>"""
(here / "technique.html").write_text(page.replace("__DATA__", data))
print("ok")
