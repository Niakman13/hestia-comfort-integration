// La vraie carte compilée, nourrie par les situations que le moteur Python a calculées (scenes.py → scenes.json).
// Toujours la dernière compilation : le navigateur ne doit pas resservir une ancienne carte.
await import('../../../custom_components/niak_comfort/frontend/niak-comfort-card.js?t='+Date.now());
const data=await (await fetch('./scenes.json')).json();
const fresh=v=>({...structuredClone(v),computed_at:new Date().toISOString()});
const views=Object.fromEntries(data.scenes.map(s=>[s.id,s.view]));
const dark=()=>{const t=document.documentElement.dataset.theme;return t?t==='dark':matchMedia('(prefers-color-scheme: dark)').matches;};
const hass=()=>({themes:{darkMode:dark()},
  connection:{async subscribeMessage(callback,message){
    if(message.type==='niak_comfort/home_subscribe')callback({...data.home,rooms:data.home.rooms.map(fresh)});
    else callback({version:1,view:fresh(views[message.entry_id])});
    return ()=>{};}},
  async callWS(){return data.scenes.map(s=>({entry_id:s.id,title:s.view.title,area_id:s.id}));}});
const grid=document.getElementById('live098'),cards=[];
for(const s of data.scenes){
  const fig=document.createElement('figure');fig.className='live-fig';
  fig.innerHTML=`<figcaption><b>${s.title}</b><span>${s.note}</span></figcaption>`;
  const card=document.createElement('niak-comfort-card');card.setConfig({type:'custom:niak-comfort-card',entry_id:s.id,format:'full'});
  fig.append(card);grid.append(fig);cards.push(card);
}
const home=document.createElement('niak-comfort-home-card');home.setConfig({type:'custom:niak-comfort-home-card'});
document.getElementById('live098home').append(home);cards.push(home);
// Les réglages : ceux d'une carte pièce et ceux, nouveaux, de la carte logement.
const roomEditor=document.createElement('niak-comfort-card-editor'),homeEditor=document.createElement('niak-comfort-home-card-editor');
roomEditor.setConfig({type:'custom:niak-comfort-card',entry_id:'geste',format:'full'});homeEditor.setConfig({type:'custom:niak-comfort-home-card'});
homeEditor.addEventListener('config-changed',e=>home.setConfig(e.detail.config));
document.getElementById('live098home-editor').append(homeEditor);document.getElementById('live098room-editor').append(roomEditor);
const apply=()=>{const h=hass();for(const c of [...cards,roomEditor])c.hass=h;};
apply();
document.querySelectorAll('[data-theme-set]').forEach(b=>b.addEventListener('click',()=>setTimeout(apply)));
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',apply);
