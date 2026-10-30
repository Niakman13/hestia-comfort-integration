import {html,nothing} from 'lit';
import {frame,t,fr} from './socle/ui';
import type {Hass} from './model';

/** One state of the banner and what the light does then. */
export interface LightLook {colour:string|null;effect:string;brightness:number}
/** A light that shows the advice: which one, what it follows, when it may act, and its looks. */
export interface LightRule {entity_id:string;follow:string;wake:boolean;night:boolean;presence:boolean;states:Record<string,LightLook>}
/** « Lumières »: one light for the whole home, or one per room (in its Notifications tab). */
export interface Lights {mode:'home'|'rooms';home:LightRule|null;rooms:Record<string,LightRule>}

// The banner's states, with the card's colours (hestia-charte.css): blue all is well, green a benefit, orange a gesture.
export const lightStates:{key:string;label:string;colour:string;text:string}[]=[
 {key:'calm',label:fr('Tout va bien'),colour:'#aad6e5',text:'#0c3f52'},
 {key:'benefit',label:fr('À saisir'),colour:'#a5d6ae',text:'#1f4a27'},
 {key:'action',label:fr('Geste conseillé'),colour:'#f1b277',text:'#5a3108'},
 {key:'airing',label:fr('Aération en cours'),colour:'#aad6e5',text:'#0c3f52'},
 {key:'urgent',label:fr('Attention'),colour:'#e8857f',text:'#5c1714'}];
const defaults:Record<string,LightLook>={calm:{colour:'#aad6e5',effect:'keep',brightness:40},benefit:{colour:'#a5d6ae',effect:'solid',brightness:50},
 action:{colour:'#f1b277',effect:'solid',brightness:70},airing:{colour:'#aad6e5',effect:'solid',brightness:60},urgent:{colour:'#e8857f',effect:'flash',brightness:100}};
// Hestia's own effects; a light's own list (WLED: Breathe, Blink, Rainbow…) comes after them.
const ownEffects:[string,string][]=[['keep',fr('Ne rien changer')],['off',fr('Éteindre')],['solid',fr('Fixe')],['flash',fr('Clignoter')]];

export const noLights=():Lights=>({mode:'home',home:null,rooms:{}});
export function newRule(entity_id:string,follow='home'):LightRule{return {entity_id,follow,wake:false,night:true,presence:true,states:structuredClone(defaults)};}
export function look(rule:LightRule,key:string):LightLook{return rule.states[key]??defaults[key];}
const named=(effects:unknown,name:string)=>(Array.isArray(effects)?effects as string[]:[]).find(e=>String(e).toLowerCase()===name);

/** The lights that can show a colour; a plain on/off or dimmable bulb cannot. */
export function colourLights(hass?:Hass,wled=true){const states=hass?.states??{};
 return Object.keys(states).filter(id=>id.startsWith('light.')&&((states[id].attributes?.supported_color_modes as string[]|undefined)??[]).some(m=>!['onoff','brightness','white'].includes(m)))
  .filter(id=>wled||hass?.entities?.[id]?.platform!=='wled').map(id=>{const e=hass?.entities?.[id],device=e?.device_id?hass?.devices?.[e.device_id]:undefined;
   return {id,name:String(states[id].attributes?.friendly_name??id),wled:e?.platform==='wled',strip:e?.platform==='wled'?String(device?.name_by_user??device?.name??'WLED'):''};}).sort((a,b)=>a.name.localeCompare(b.name));}
/** A WLED strip cut into segments: each segment is a light of its own, able to show another room. */
export function segmentsOf(hass:Hass|undefined,strip:string){return colourLights(hass,true).filter(l=>l.wled&&l.strip===strip);}

function rgb(hex:string){return [1,3,5].map(i=>parseInt(hex.slice(i,i+2),16));}
/** Shows a state's look on the light at once, from the hub: the « Essayer » button. Fitted as the driver does
 * (engine/light_plan.py fit): no flash → its « Blink » effect; « Fixe » stops an effect already running. */
export function tryLook(hass:Hass|undefined,rule:LightRule,key:string){const l=look(rule,key);if(!hass?.callService||l.effect==='keep')return;
 if(l.effect==='off'){void hass.callService('light','turn_off',{entity_id:rule.entity_id});return;}
 const data:Record<string,unknown>={entity_id:rule.entity_id,brightness_pct:l.brightness,...(l.colour?{rgb_color:rgb(l.colour)}:{})};
 const a=hass.states?.[rule.entity_id]?.attributes??{},canFlash=(Number(a.supported_features??0)&8)!==0;
 if(l.effect==='flash'){const blink=named(a.effect_list,'blink');if(canFlash)data.flash='long';else if(blink)data.effect=blink;}
 else if(l.effect!=='solid')data.effect=l.effect;else{const solid=named(a.effect_list,'solid');if(solid)data.effect=solid;}
 void hass.callService('light','turn_on',data);}

// What an effect looks like on the preview strip; a light's own effect is drawn by its name (WLED: Breathe, Blink, Rainbow…).
function motion(effect:string){const e=effect.toLowerCase();
 return e==='flash'||/blink|strobe/.test(e)?'blink':/breath|fade/.test(e)?'breathe':/rainbow|colorloop|palette/.test(e)?'rainbow':/wave|running|scan|chase|fire|flicker|twinkle/.test(e)?'wave':'';}
/** The strip under the table shows the state just tried or changed, drawn straight in the page: no save waits on it. */
function preview(e:Event,label:string,l:LightLook){const root=(e.target as HTMLElement).closest('.li-host');const strip=root?.querySelector<HTMLElement>('.li-strip');if(!root||!strip)return;
 root.querySelector('.li-pname')!.textContent=t(label);
 const name=ownEffects.find(([v])=>v===l.effect)?.[1];
 root.querySelector('.li-pdesc')!.textContent=(name?t(name):l.effect)+(l.effect==='keep'||l.effect==='off'?'':' · '+l.brightness+' %');
 strip.className='li-strip '+(l.effect==='keep'?'keep':l.effect==='off'?'off':motion(l.effect));
 strip.style.setProperty('--li-c',l.colour??'#aad6e5');strip.style.setProperty('--li-b',String(.7+l.brightness/330));}
/** The light's settings, as in the approved mockup; every change is handed back to be saved at once. */
export function lightEditor(o:{hass?:Hass;wled:boolean;rule:LightRule|null;taken?:string;follows?:{value:string;label:string}[];busy:boolean;change:(rule:LightRule|null)=>void}){
 const lights=colourLights(o.hass,o.wled),rule=o.rule,current=rule?lights.find(l=>l.id===rule.entity_id):undefined;
 const list=current?.wled||!o.hass?.entities?.[rule?.entity_id??'']||o.hass.entities[rule!.entity_id].platform!=='wled'?(o.hass?.states?.[rule?.entity_id??'']?.attributes?.effect_list as string[]|undefined)??[]:[];
 const set=(change:Partial<LightRule>)=>rule&&o.change({...rule,...change});
 const setLook=(key:string,change:Partial<LightLook>)=>rule&&o.change({...rule,states:{...rule.states,[key]:{...look(rule,key),...change}}});
 const pick=html`<label class="zone">${t('Lumière à piloter')}<select ?disabled=${o.busy} @change=${(e:Event)=>{const id=(e.target as HTMLSelectElement).value;o.change(id?(rule?{...rule,entity_id:id}:newRule(id,o.follows?.[0]?.value??'home')):null);}}>
  <option value="" ?selected=${!rule}>${t('Aucune')}</option>${lights.filter(l=>!l.wled).map(l=>html`<option value=${l.id} ?selected=${l.id===rule?.entity_id}>${l.name}</option>`)}
  ${[...new Set(lights.filter(l=>l.wled).map(l=>l.strip))].map(strip=>html`<optgroup label=${'WLED · '+strip}>${lights.filter(l=>l.wled&&l.strip===strip).map(l=>html`<option value=${l.id} ?selected=${l.id===rule?.entity_id}>${l.name}</option>`)}</optgroup>`)}
  ${rule&&!current?html`<option value=${rule.entity_id} selected>${t('Introuvable · choisissez-en une autre')}</option>`:nothing}</select></label>`;
 if(!lights.length&&!rule)return frame(t('Lumière'),html`<p class="hint">${t('Aucune lumière couleur trouvée dans Home Assistant. Un bandeau WLED ou une ampoule couleur conviennent.')}</p>`,{className:'nk-field-section nk-plain'});
 return frame(t('Lumière'),html`<div class="li-host"><p class="hint">${t('Hestia ne la commande que dans les conditions choisies ici.')}</p>
  <div class="li-grid">${pick}${rule&&o.follows?.length?html`<label class="zone">${t('Suit le conseil de')}<select ?disabled=${o.busy} @change=${(e:Event)=>set({follow:(e.target as HTMLSelectElement).value})}>
   ${o.follows.map(f=>html`<option value=${f.value} ?selected=${f.value===rule.follow}>${f.label}</option>`)}</select></label>`:nothing}</div>
  ${current?.wled?html`<p class="hint"><em class="ex-badge benefit">WLED</em> ${t('Ses effets sont proposés pour chaque état.')}${segmentsOf(o.hass,current.strip).length>1?' '+t('Ce bandeau a {n} segments : chacun peut montrer une autre pièce.',{n:segmentsOf(o.hass,current.strip).length}):''}</p>`:nothing}
  ${o.taken?html`<p class="warning hint">${t('Cette lumière montre déjà {room}. Choisissez un autre segment ou une autre lumière.',{room:o.taken})}</p>`:nothing}
  ${rule?html`<div class="li-when" role="radiogroup" aria-label=${t('Quand agir')}>
    <label class="check"><input type="radio" name="li-wake" .checked=${!rule.wake} ?disabled=${o.busy} @change=${()=>set({wake:false})}>${t('Seulement quand elle est déjà allumée')}</label>
    <label class="check"><input type="radio" name="li-wake" .checked=${rule.wake} ?disabled=${o.busy} @change=${()=>set({wake:true})}>${t('L’allumer pour un geste ou une alerte, puis la rendre comme avant')}</label>
    <label class="check"><input type="checkbox" .checked=${rule.night} ?disabled=${o.busy} @change=${(e:Event)=>set({night:(e.target as HTMLInputElement).checked})}>${t('Jamais la nuit (de 22 h à 7 h)')}</label>
    <label class="check"><input type="checkbox" .checked=${rule.presence} ?disabled=${o.busy} @change=${(e:Event)=>set({presence:(e.target as HTMLInputElement).checked})}>${t('Seulement si quelqu’un est à la maison')}</label></div>
   <div class="li-box"><div class="li-head"><h4>${t('Pour chaque état')}</h4><button class="nk-edit" ?disabled=${o.busy} @click=${()=>set({states:structuredClone(defaults)})}>${t('Couleurs Hestia')}</button></div>
   <div class="li-table"><div class="li-row li-cols" aria-hidden="true"><span>${t('État')}</span><span>${t('Couleur')}</span><span>${t('Effet')}</span><span>${t('Luminosité')}</span><span></span></div>
   ${lightStates.map(s=>{const l=look(rule,s.key),plain=l.effect==='keep'||l.effect==='off',show=(e:Event)=>preview(e,s.label,{...l,colour:l.colour??s.colour});
    return html`<div class="li-row"><span class="li-pill" style="background:${s.colour};color:${s.text}">${t(s.label)}</span>
     <label class="li-swatch ${plain?'plain':''}" style="--li-c:${l.colour??s.colour}"><input type="color" aria-label=${t('Couleur : {state}',{state:t(s.label)})} .value=${l.colour??s.colour} ?disabled=${o.busy||plain} @change=${(e:Event)=>{const colour=(e.target as HTMLInputElement).value;setLook(s.key,{colour});preview(e,s.label,{...l,colour});}}></label>
     <select aria-label=${t('Effet : {state}',{state:t(s.label)})} ?disabled=${o.busy} @change=${(e:Event)=>{const effect=(e.target as HTMLSelectElement).value;setLook(s.key,{effect});preview(e,s.label,{...l,colour:l.colour??s.colour,effect});}}>
      ${ownEffects.map(([v,label])=>html`<option value=${v} ?selected=${v===l.effect}>${t(label)}</option>`)}
      ${list.length?html`<optgroup label=${t('Effets de la lumière')}>${list.map(v=>html`<option value=${v} ?selected=${v===l.effect}>${v}</option>`)}</optgroup>`:nothing}</select>
     <label class="li-bright"><input type="range" min="5" max="100" step="5" .value=${String(l.brightness)} aria-label=${t('Luminosité : {state}',{state:t(s.label)})} ?disabled=${o.busy||plain}
      @input=${(e:Event)=>{const b=Number((e.target as HTMLInputElement).value);((e.target as HTMLElement).nextElementSibling as HTMLElement).textContent=b+' %';}}
      @change=${(e:Event)=>{const brightness=Number((e.target as HTMLInputElement).value);setLook(s.key,{brightness});preview(e,s.label,{...l,colour:l.colour??s.colour,brightness});}}><span>${plain?'—':l.brightness+' %'}</span></label>
     <button class="li-try" ?disabled=${o.busy||l.effect==='keep'} aria-label=${t('Essayer sur la lumière')} title=${t('Essayer sur la lumière')} @click=${(e:Event)=>{show(e);tryLook(o.hass,rule,s.key);}}>
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M8 5v14l11-7Z"></path></svg></button></div>`;})}</div></div>
   <div class="li-preview"><div class="li-preview-head"><span>${t('Aperçu : {state}',{state:''})}<strong class="li-pname"></strong></span><span class="li-pdesc"></span></div><div class="li-strip"></div></div>
   <p class="hint">${t('« Essayer » montre l’état sur la lumière tout de suite. Ensuite, Hestia la change quand le conseil change, et la rend comme avant quand tout va bien.')}</p>`:nothing}</div>`,{className:'nk-field-section nk-plain'});}
