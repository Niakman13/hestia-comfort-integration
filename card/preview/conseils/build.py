"""Builds maquette.html: the compiled card and the engine's situations in one file that opens anywhere."""
from pathlib import Path
here = Path(__file__).parent
bundle = (here.parents[2] / "custom_components" / "niak_comfort" / "frontend" / "niak-comfort-card.js").read_text()
scenes = (here / "scenes.json").read_text()
page = """<!doctype html>
<html lang="fr" data-theme="light">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Conseils et À savoir</title>
<style>
:root{--page:#eef1f5;--fg:#253047;--fg2:#5b687b;--line:#2530471f;--field:#fff;
  --primary-text-color:#253047;--secondary-text-color:#5b687b;--card-background-color:#fff;--ha-card-background:#fff;--primary-color:#1f6f98;color-scheme:light}
:root[data-theme="dark"]{--page:#151c25;--fg:#edf1f7;--fg2:#b2bdcd;--line:#ffffff1f;--field:#2a323d;
  --primary-text-color:#edf1f7;--secondary-text-color:#b2bdcd;--card-background-color:#2b333e;--ha-card-background:#2b333e;--primary-color:#7cc4e8;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--fg);font:14px/1.5 Roboto,system-ui,sans-serif}
main{max-width:1320px;margin:0 auto;padding:28px 16px 60px}
h1{font-size:26px;margin:0 0 6px}
.lead{color:var(--fg2);max-width:820px;margin:0 0 6px}
.rule{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin:18px 0 26px}
.rule div{background:var(--field);border:1px solid var(--line);border-radius:14px;padding:12px 16px}
.rule b{display:block;margin-bottom:2px}
.top{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap}
.toggle{display:flex;gap:4px;padding:4px;border:1px solid var(--line);border-radius:10px}
.toggle button{border:0;background:none;color:var(--fg2);font:inherit;padding:6px 12px;border-radius:7px;cursor:pointer}
.toggle button[aria-pressed="true"]{background:var(--field);color:var(--fg);font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:22px;align-items:start}
figure{margin:0}
figcaption{margin:0 0 8px;padding:0 4px}
figcaption b{display:block;font-size:15px}
figcaption span{color:var(--fg2);font-size:13px}
</style>
</head>
<body><main>
<div class="top"><div>
<h1>Conseils et À savoir</h1>
<p class="lead">Maquette avec la vraie carte et le vrai moteur, sur des situations tirées de votre maison (valeurs du 20 octobre) et quelques cas d’hiver.</p>
</div><div class="toggle" role="group" aria-label="Thème"><button data-theme-set="light" aria-pressed="true">Clair</button><button data-theme-set="dark" aria-pressed="false">Sombre</button></div></div>
<div class="rule">
<div><b>Le bandeau = un geste</b><span>Aérez, Refermez, Lancez la VMC, Rallumez le chauffage… ou « Rien à faire ». Jamais une information.</span></div>
<div><b>À savoir = l’information</b><span>Risque de moisissure, air humide dehors, fenêtre ouverte sans effet, maison vide, purificateur en marche. Juste sous le bandeau.</span></div>
<div><b>La couleur suit le geste</b><span>Bleu : rien à faire. Orange : un geste conseillé.</span></div>
</div>
<div class="grid" id="grid"></div>
</main>
<script>customElements.get('home-assistant')||customElements.define('home-assistant',class extends HTMLElement{});</script>
<script type="module">
__BUNDLE__
</script>
<script type="module">
const data=__SCENES__;
await customElements.whenDefined('niak-comfort-card');
const views=Object.fromEntries(data.scenes.map(s=>[s.id,s.view]));
const fresh=v=>({...structuredClone(v),computed_at:new Date().toISOString()});
const dark=()=>document.documentElement.dataset.theme==='dark';
const hass=()=>({themes:{darkMode:dark()},connection:{async subscribeMessage(cb,m){cb({version:1,view:fresh(views[m.entry_id])});return ()=>{};}},
  async callWS(){return data.scenes.map(s=>({entry_id:s.id,title:s.view.title,area_id:s.id}));}});
const grid=document.getElementById('grid'),cards=[];
for(const s of data.scenes){
  const fig=document.createElement('figure');
  fig.innerHTML=`<figcaption><b>${s.title}</b><span>${s.note}</span></figcaption>`;
  const card=document.createElement('niak-comfort-card');
  card.setConfig({type:'custom:niak-comfort-card',entry_id:s.id,format:'tile'});
  fig.append(card);grid.append(fig);cards.push(card);
}
const apply=()=>{const h=hass();for(const c of cards)c.hass=h;};
apply();
document.querySelectorAll('[data-theme-set]').forEach(b=>b.addEventListener('click',()=>{
  document.documentElement.dataset.theme=b.dataset.themeSet;
  document.querySelectorAll('[data-theme-set]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));apply();}));
</script>
</body></html>
"""
(here / "maquette.html").write_text(page.replace("__BUNDLE__", bundle).replace("__SCENES__", scenes))
print("maquette.html", len(page) + len(bundle) + len(scenes))
