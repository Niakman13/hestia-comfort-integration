"""Builds maquette.html: the compiled card, the engine's situations, one file that opens anywhere."""
from pathlib import Path
here = Path(__file__).parent
bundle = (here.parents[2] / "custom_components" / "niak_comfort" / "frontend" / "niak-comfort-card.js").read_text()
scenes = (here / "scenes.json").read_text()
style = (here.parent / "conseils" / "build.py").read_text().split("<style>")[1].split("</style>")[0]
page = """<!doctype html>
<html lang="fr" data-theme="light">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Salon · Cuisine</title>
<style>""" + style + """
h2{font-size:19px;margin:34px 0 4px}
.pair{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:22px;align-items:start}
.picker{max-width:420px;background:var(--field);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.picker .head{padding:10px 16px;font-size:12px;color:var(--fg2);border-bottom:1px solid var(--line)}
.picker div.opt{padding:12px 16px}.picker div.opt.on{background:color-mix(in srgb,var(--primary-color) 12%,transparent);color:var(--primary-color);font-weight:600}
.home{max-width:560px}
</style></head>
<body><main>
<div class="top"><div>
<h1>Salon · Cuisine : une seule carte</h1>
<p class="lead">Maquette avec la vraie carte et le vrai moteur, valeurs de votre maison. Les capteurs de chaque pièce restent dans Home Assistant ; seule la carte devient commune.</p>
</div><div class="toggle" role="group" aria-label="Thème"><button data-theme-set="light" aria-pressed="true">Clair</button><button data-theme-set="dark" aria-pressed="false">Sombre</button></div></div>
<h2>1. Le choix de la pièce, dans les réglages de la carte</h2>
<p class="lead">Salon et Cuisine ne sont plus proposées séparément : un seul choix « Salon · Cuisine ».</p>
<div class="picker" id="picker"><div class="head">Pièce</div></div>
<h2>2. Avant : deux cartes pour un même air</h2>
<div class="pair" id="before"></div>
<h2>3. Après : une seule carte, dans quatre situations</h2>
<div class="pair" id="after"></div>
<h2>4. La carte complète</h2>
<div class="pair" id="full"></div>
<h2>5. Mon logement : une seule tuile « Salon · Cuisine »</h2>
<div class="home" id="home"></div>
</main>
<script>customElements.get('home-assistant')||customElements.define('home-assistant',class extends HTMLElement{});</script>
<script type="module">
""" + bundle + """
</script>
<script type="module">
const data=__SCENES__;
await customElements.whenDefined('niak-comfort-card');
const views={};
for(const s of data.scenes){views[s.salon.entry_id]=s.salon;views[s.cuisine.entry_id]=s.cuisine;
  // « Avant » : the same rooms as two separate cards, without the shared air.
  for(const r of [s.salon,s.cuisine]){const b=structuredClone(r);b.entry_id='avant-'+r.entry_id;b.volume=[];b.volume_name=null;views[b.entry_id]=b;}}
const fresh=v=>({...structuredClone(v),computed_at:new Date().toISOString()});
const dark=()=>document.documentElement.dataset.theme==='dark';
const hass=()=>({themes:{darkMode:dark()},connection:{async subscribeMessage(cb,m){
    if(m.type==='niak_comfort/home_subscribe')cb({...data.home,rooms:data.home.rooms.map(fresh)});
    else cb({version:1,view:fresh(views[m.entry_id])});return ()=>{};}},
  async callWS(){return data.entries;}});
// The room picker, grouped as the card editor now groups it.
const picker=document.getElementById('picker'),done=new Set();
for(const e of data.entries){if(done.has(e.entry_id))continue;[e.entry_id,...e.volume].forEach(id=>done.add(id));
  const d=document.createElement('div');d.className='opt'+(e.volume.length?' on':'');d.textContent=e.volume.length?e.volume_name:e.title;picker.append(d);}
const cards=[];
const make=(where,id,format,title,note)=>{const fig=document.createElement('figure');fig.innerHTML=`<figcaption><b>${title}</b><span>${note??''}</span></figcaption>`;
  const c=document.createElement('niak-comfort-card');c.setConfig({type:'custom:niak-comfort-card',entry_id:id,format});fig.append(c);document.getElementById(where).append(fig);cards.push(c);};
const first=data.scenes[0];
make('before','avant-'+first.salon.entry_id,'tile','Salon','Aujourd’hui, deux bandeaux pour un même air.');
make('before','avant-'+first.cuisine.entry_id,'tile','Cuisine','');
for(const s of data.scenes)make('after',s.salon.entry_id,'tile',s.title,s.note);
make('full',data.scenes[2].salon.entry_id,'full','Porte-fenêtre ouverte, format complet','Les mesures de chaque pièce sous son nom.');
const home=document.createElement('niak-comfort-home-card');home.setConfig({type:'custom:niak-comfort-home-card',rooms_open:true});
document.getElementById('home').append(home);cards.push(home);
const apply=()=>{const h=hass();for(const c of cards)c.hass=h;};apply();
document.querySelectorAll('[data-theme-set]').forEach(b=>b.addEventListener('click',()=>{document.documentElement.dataset.theme=b.dataset.themeSet;
  document.querySelectorAll('[data-theme-set]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));apply();}));
</script></body></html>
"""
(here / "maquette.html").write_text(page.replace("__SCENES__", scenes))
print("ok")
