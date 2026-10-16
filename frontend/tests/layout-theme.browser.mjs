import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync,existsSync,mkdirSync} from 'node:fs';
import {once} from 'node:events';
import {chromium,firefox} from '../../card/node_modules/playwright/index.mjs';
import {harness,comfort,weather} from './hub-harness.mjs';
const root=new URL('../../custom_components/niak_comfort/frontend/',import.meta.url),other=new URL('../../../niak-weather-integration/custom_components/niak_weather/frontend/',import.meta.url);
const legacy=process.env.NIAK_LEGACY_WEATHER_JS,withWeather=process.env.NIAK_TEST_COMFORT_ONLY!=='1'&&existsSync(other);
const server=createServer((req,res)=>{const path=new URL(req.url,'http://localhost').pathname;let source;
 if(path==='/shell.js')source=readFileSync(new URL('niak-socle.js',root));
 else if(path==='/comfort.js')source=readFileSync(new URL('panel.js',root));
 else if(path==='/weather.js')source=readFileSync(legacy??new URL('panel.js',other));
 else if(/^\/manrope-\d+\.ttf$/.test(path)){res.setHeader('Content-Type','font/ttf');res.end(readFileSync(new URL(path.slice(1),root)));return;}
 if(source){res.setHeader('Content-Type','text/javascript');res.end(source);return;}
 if(path==='/comfort.json'||path==='/weather.json'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify(path==='/comfort.json'?comfort:weather));return;}
 res.setHeader('Content-Type','text/html');res.end(harness(withWeather));
});
server.listen(0,'127.0.0.1');await once(server,'listening');const origin='http://127.0.0.1:'+server.address().port;
const output=process.env.NIAK_HUB_OUTPUT;if(output)mkdirSync(output,{recursive:true});let checks=0;
async function nav(page,group,label){const shell=page.locator('niak-socle-1-7');if(await shell.locator('.mobile-bar').isVisible())await shell.getByRole('button',{name:'Ouvrir la navigation Niak',exact:true}).click();await shell.getByRole('navigation',{name:group,exact:true}).getByRole('link',{name:label,exact:true}).click();}
async function height(page){await page.waitForFunction(()=>{const el=document.querySelector('niak-socle-1-7'),r=el.getBoundingClientRect();return Math.abs(r.bottom-innerHeight)<2&&document.documentElement.scrollHeight<=innerHeight+2;});checks++;}
try{for(const engine of [chromium,firefox]){const browser=await engine.launch();try{for(const width of [1440,390,320]){
 const page=await browser.newPage({viewport:{width,height:940}});const errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(10000);
 await page.goto(origin+'/niak?bricks='+(withWeather?'mixed':'comfort'));const shell=page.locator('niak-socle-1-7');await shell.getByRole('heading',{name:'Votre logement, connecté',exact:true}).waitFor();await height(page);
 // HA panel wrapper intentionally has no set height; keep safe areas within the viewport.
 await page.evaluate(()=>{document.body.style.setProperty('--safe-area-inset-bottom','18px');document.querySelector('ha-panel-custom').style.paddingBottom='18px';window.dispatchEvent(new Event('resize'));});
 await page.waitForFunction(()=>Math.abs(document.querySelector('niak-socle-1-7').getBoundingClientRect().bottom-(innerHeight-18))<2);checks++;
 await page.evaluate(()=>{document.body.style.removeProperty('--safe-area-inset-bottom');document.querySelector('ha-panel-custom').style.paddingBottom='';window.dispatchEvent(new Event('resize'));});await height(page);
 if(withWeather){assert.equal(await shell.locator('nav[aria-label=Weather] a').count(),1);checks++;}
 // Unique HA colors and font must propagate through the shell and brick shadow roots.
 await page.evaluate(()=>{for(const [k,v]of Object.entries({'primary-background-color':'#263746','card-background-color':'#34495a','primary-text-color':'#f2eed8','secondary-text-color':'#bdc9b6','divider-color':'#74816a','primary-color':'#abcf84','secondary-background-color':'#405263','ha-font-family-body':'serif'}))document.body.style.setProperty('--'+k,v);});
 await nav(page,'Accueil Niak','Réglages');const selector=shell.getByLabel('Apparence',{exact:true});assert.equal(await selector.inputValue(),'niak');await selector.selectOption('ha');await page.waitForFunction(()=>getComputedStyle(document.querySelector('niak-socle-1-7')).backgroundColor==='rgb(38, 55, 70)').catch(async e=>{console.log(await shell.evaluate(e=>({appearance:e.getAttribute('data-appearance'),bg:getComputedStyle(e).backgroundColor,value:getComputedStyle(e).getPropertyValue('--primary-background-color'),parent:getComputedStyle(e.parentElement).getPropertyValue('--primary-background-color'),theme:e.overview.theme})));throw e;});checks++;
 await page.reload();await shell.getByLabel('Apparence',{exact:true}).waitFor();assert.equal(await shell.getByLabel('Apparence',{exact:true}).inputValue(),'ha');checks++;
 await page.evaluate(()=>{document.body.style.setProperty('--primary-background-color','#263746');document.body.style.setProperty('--ha-font-family-body','serif');});
 await nav(page,'Confort','Vue d’ensemble');const panel=page.locator('niak-comfort-setup');await panel.getByRole('heading',{name:'Pièces du logement',exact:true}).waitFor();assert.equal(await panel.evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(38, 55, 70)');assert.equal(await panel.evaluate(e=>getComputedStyle(e).fontFamily),'serif');checks+=2;await height(page);
 await panel.locator('.room').filter({hasText:'Salon'}).getByRole('button',{name:'Configurer',exact:true}).click();await panel.getByRole('heading',{name:'Configurer Salon',exact:true}).waitFor();
 const rect=await panel.evaluate(e=>{const rows=[...e.shadowRoot.querySelectorAll('.room-menu-row')].map(x=>x.getBoundingClientRect().width);return {rows,field:e.shadowRoot.querySelector('.nk-field-section').getBoundingClientRect().width};});assert.ok(rect.rows.every(w=>Math.abs(w-rect.field)<2),JSON.stringify(rect));checks++;
 await page.setViewportSize({width,height:700});await height(page);await page.setViewportSize({width,height:940});await height(page);
 if(withWeather){await nav(page,'Weather','Vue d’ensemble');await page.locator('niak-weather-setup').getByRole('heading',{name:'Maison',exact:true}).waitFor();assert.equal(await page.locator('niak-weather-setup').evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(38, 55, 70)');checks++;await height(page);}
 await nav(page,'Accueil Niak','Réglages');await shell.getByLabel('Apparence',{exact:true}).selectOption('niak');await page.waitForFunction(()=>getComputedStyle(document.querySelector('niak-socle-1-7')).backgroundColor==='rgb(27, 28, 30)');checks++;await page.evaluate(()=>toggleTheme());await page.waitForFunction(()=>getComputedStyle(document.querySelector('niak-socle-1-7')).backgroundColor==='rgb(250, 249, 247)');checks++;await height(page);
 if(output&&engine===chromium)await page.screenshot({path:output+'/theme-settings-'+width+'.png'});
 assert.deepEqual(errors,[]);checks++;page.on('dialog',d=>d.accept());await page.close();
 }}finally{await browser.close();}}}finally{server.close();}
console.log(JSON.stringify({checks,engines:['Chromium','Firefox'],widths:[1440,390,320],legacyWeather:!!legacy}));
