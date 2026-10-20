"""Builds maquette.html: out-of-range tiles with and without a gesture, five proposals (data: ../volume/scenes.json)."""
from pathlib import Path
here = Path(__file__).parent
bundle = (here.parents[2] / "custom_components" / "niak_comfort" / "frontend" / "niak-comfort-card.js").read_text()
scenes = (here.parent / "volume" / "scenes.json").read_text()
style = (here.parent / "conseils" / "build.py").read_text().split("<style>")[1].split("</style>")[0]
VARIANTS = [
    ("A", "Pastille", "Cadre neutre ; une petite pastille orange fixe devant « trop humide ». (Proposée par défaut.)", ""),
    ("B", "Valeur colorée", "Cadre neutre ; le chiffre lui-même passe en orange.",
     ".nc-tile.out.soft em::before{display:none}.nc-tile.out.soft b{color:color-mix(in oklab,var(--c) 75%,var(--nw-fg))}"),
    ("C", "Pastille en coin", "Cadre neutre ; un point orange dans le coin de la tuile.",
     ".nc-tile.out.soft em::before{display:none}.nc-tile.out.soft::after{content:'';position:absolute;top:10px;right:10px;width:9px;height:9px;border-radius:50%;background:var(--c)}"),
    ("D", "Liseré", "Cadre neutre ; seulement le liseré orange à gauche, et la pastille.",
     ".nc-tile.out.soft::before{display:block!important}"),
    ("E", "Icône", "Cadre neutre ; seule l’icône de la mesure passe en orange.",
     ".nc-tile.out.soft em::before{display:none}.nc-tile.out.soft .nc-ic{background:var(--c)!important;color:color-mix(in oklab,var(--c) 30%,#1d2530)!important}"),
]
variants = ",".join("{id:%r,name:%r,note:%r,css:%r}" % v for v in VARIANTS)
page = """<!doctype html>
<html lang="fr" data-theme="light">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mesures hors plage</title>
<style>""" + style + """
h2{font-size:19px;margin:34px 0 4px}
.grid{grid-template-columns:repeat(auto-fill,minmax(360px,1fr))}
</style></head>
<body><main>
<div class="top"><div>
<h1>Mesures hors de votre plage</h1>
<p class="lead">Le cadre orange reste réservé aux gestes. Quand il n’y a rien à faire, la mesure hors plage garde un repère discret : cinq propositions, sur votre carte Salon · Cuisine.</p>
</div><div class="toggle" role="group" aria-label="Thème"><button data-theme-set="light" aria-pressed="true">Clair</button><button data-theme-set="dark" aria-pressed="false">Sombre</button></div></div>
<h2>Avec un geste à faire : inchangé</h2>
<p class="lead">« Aérez 6 à 15 min » : les mesures en cause gardent leur cadre orange.</p>
<div class="grid" id="action"></div>
<h2>Sans geste : « Rien à faire », humidité au-dessus de votre plage</h2>
<div class="grid" id="calm"></div>
</main>
<script>customElements.get('home-assistant')||customElements.define('home-assistant',class extends HTMLElement{});</script>
<script type="module">
""" + bundle + """
</script>
<script type="module">
const data=__SCENES__,variants=[__VARIANTS__];
await customElements.whenDefined('niak-comfort-card');
const views={};for(const s of data.scenes){views[s.salon.entry_id]=s.salon;views[s.cuisine.entry_id]=s.cuisine;}
const fresh=v=>({...structuredClone(v),computed_at:new Date().toISOString()});
const dark=()=>document.documentElement.dataset.theme==='dark';
const hass=()=>({themes:{darkMode:dark()},connection:{async subscribeMessage(cb,m){cb({version:1,view:fresh(views[m.entry_id])});return ()=>{};}},async callWS(){return data.entries;}});
const cards=[];
const make=(where,id,title,note,css)=>{const fig=document.createElement('figure');fig.innerHTML=`<figcaption><b>${title}</b><span>${note}</span></figcaption>`;
  const c=document.createElement('niak-comfort-card');c.setConfig({type:'custom:niak-comfort-card',entry_id:id,format:'full',measures_open:true});
  fig.append(c);document.getElementById(where).append(fig);cards.push([c,css]);};
make('action','aerer-salon','Avec un geste','Cadre orange, comme aujourd’hui.','');
for(const v of variants)make('calm','calme-salon',`${v.id}. ${v.name}`,v.note,v.css);
const apply=()=>{const h=hass();for(const [c] of cards)c.hass=h;
  setTimeout(()=>{for(const [c,css] of cards){if(!css||!c.shadowRoot)continue;let s=c.shadowRoot.querySelector('style[data-variant]');
    if(!s){s=document.createElement('style');s.dataset.variant='';c.shadowRoot.append(s);}s.textContent=css;}},300);};
apply();
document.querySelectorAll('[data-theme-set]').forEach(b=>b.addEventListener('click',()=>{document.documentElement.dataset.theme=b.dataset.themeSet;
  document.querySelectorAll('[data-theme-set]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));apply();}));
</script></body></html>
"""
(here / "maquette.html").write_text(page.replace("__SCENES__", scenes).replace("__VARIANTS__", variants))
print("ok")
