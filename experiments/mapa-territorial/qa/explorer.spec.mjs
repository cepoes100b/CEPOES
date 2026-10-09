import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {PNG} from 'pngjs';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
const OUTPUT=process.env.QA_OUTPUT||path.resolve('qa-output');
const BASE='http://127.0.0.1:4173';const ROUTE='/laboratorio/mapa-territorial/';
const save=async(name,obj)=>writeFile(path.join(OUTPUT,name+'.json'),JSON.stringify(obj,null,2));
async function ready(page){await page.waitForFunction(()=>window.__CEPOES_MAP_QA?.map==='ready'&&window.__CEPOES_MAP_QA?.status==='ready',null,{timeout:30000});await page.locator('#mt-map-loading').waitFor({state:'detached'});}
async function webglProof(page){
  const info=await page.locator('#mt-map canvas').evaluate(c=>{const gl=c.getContext('webgl2')||c.getContext('webgl');if(!gl)throw new Error('No live WebGL context');const ext=gl.getExtension('WEBGL_debug_renderer_info');return {version:gl.getParameter(gl.VERSION),renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),lost:gl.isContextLost(),width:c.width,height:c.height};});
  expect(info.lost).toBe(false);expect(info.width).toBeGreaterThan(200);
  const png=PNG.sync.read(await page.locator('#mt-map canvas').screenshot({type:'png'}));
  const colors=new Set();for(let y=20;y<png.height-20;y+=5)for(let x=20;x<png.width-20;x+=5){const i=(y*png.width+x)*4;colors.add(`${png.data[i]},${png.data[i+1]},${png.data[i+2]}`);}
  expect(colors.size,'Map canvas must contain non-uniform real rendered pixels').toBeGreaterThan(20);
  return {...info,sampledColors:colors.size,rendererNote:'Actual Chromium WebGL rendered through ANGLE/SwiftShader; not a physical-device GPU benchmark.'};
}
async function getMetrics(page){return page.evaluate(()=>({qa:window.__CEPOES_MAP_QA,resources:performance.getEntriesByType('resource').map(r=>({name:new URL(r.name).pathname,bytes:r.transferSize,encoded:r.encodedBodySize,decoded:r.decodedBodySize,duration:r.duration})),memory:performance.memory?{usedJSHeapSize:performance.memory.usedJSHeapSize,totalJSHeapSize:performance.memory.totalJSHeapSize}:null,device:{userAgent:navigator.userAgent,cores:navigator.hardwareConcurrency,dpr:devicePixelRatio,width:innerWidth,height:innerHeight}}));}
test.beforeAll(async()=>mkdir(OUTPUT,{recursive:true}));
for(const width of [320,390,430,1440])for(const theme of ['light','dark']){
 test(`2D ${width}px ${theme}: WebGL, selección, filtros y accesibilidad`,async({browser})=>{
  const name=`2d-${width}-${theme}`,context=await browser.newContext({viewport:{width,height:width===1440?1050:900},isMobile:width<700,hasTouch:width<700,deviceScaleFactor:1,colorScheme:theme,baseURL:BASE});
  const page=await context.newPage(),errors=[],failedLocal=[],requests=[];
  await context.addInitScript(t=>localStorage.setItem('cepoes-theme',t),theme);
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  page.on('response',r=>{if(r.url().startsWith(BASE)&&r.status()>=400)failedLocal.push({url:r.url(),status:r.status()});});
  await context.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin===BASE||['fonts.googleapis.com','fonts.gstatic.com'].includes(u.hostname))return route.continue();return route.abort('blockedbyclient');});
  const report={name,width,theme,started:new Date().toISOString(),errors,failedLocal};
  try{
   await page.goto(ROUTE,{waitUntil:'domcontentloaded'});await ready(page);await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(350);
   report.webgl=await webglProof(page);report.initial=await getMetrics(page);
   expect(requests.some(x=>x.includes('/layers/educacion.geojson'))).toBe(false);expect(requests.some(x=>x.includes('/layers/verdes.geojson'))).toBe(false);
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No horizontal page overflow').toBe(true);
   await expect(page.locator('#mt-status')).toContainText('86 registros');await expect(page.locator('#mt-territory option')).toHaveCount(49);
   await page.locator('.mt-workspace').screenshot({path:path.join(OUTPUT,name+'.jpg'),type:'jpeg',quality:65,animations:'disabled'});
   if(width===1440)await page.screenshot({path:path.join(OUTPUT,name+'-overview.jpg'),type:'jpeg',quality:65,animations:'disabled'});
   // Real button-driven zoom: detect actual compositor pixels changing.
   const before=await page.locator('#mt-map canvas').screenshot();await page.getByRole('button',{name:'Acercar',exact:true}).click();await page.waitForTimeout(500);const after=await page.locator('#mt-map canvas').screenshot();expect(before.equals(after)).toBe(false);
   await page.locator('#mt-fit').click();await page.waitForTimeout(500);
   const canvasBox=await page.locator('#mt-map canvas').boundingBox();
   await page.locator('#mt-map canvas').click({position:{x:canvasBox.width*.5,y:canvasBox.height*.5}});
   await expect(page.locator('#mt-place-name')).not.toHaveText('Toda la Ciudad');
   report.mapClickSelection=await page.locator('#mt-place-name').textContent();
   await page.locator('#mt-search').focus();await page.keyboard.type('Parque Patricios');await page.keyboard.press('Enter');await expect(page.locator('#mt-place-name')).toHaveText('Parque Patricios');expect(page.url()).toContain('territorio=barrio%3Aparque-patricios');
   await page.locator('#mt-level').selectOption('comuna');await expect(page.locator('#mt-territory option')).toHaveCount(16);await page.locator('#mt-territory').selectOption('comuna:8');await expect(page.locator('#mt-place-name')).toHaveText('Comuna 8');
   const filterStart=performance.now();await page.locator('[data-layer="educacion"]').click();await expect(page.locator('#mt-source-short')).toContainText('2.732');report.educationInteractionMs=performance.now()-filterStart;
   await page.locator('#mt-category').selectOption('Estatal');await expect(page.locator('#mt-service-card')).toBeHidden();
   await page.locator('#mt-reset').click();await expect(page.locator('#mt-status')).toContainText('60 sin punto verificable');
   await page.locator('[data-layer="verdes"]').click();await expect(page.locator('#mt-status')).toContainText('2.135 puntos verificados');await expect(page.locator('#mt-metrics')).toContainText('en revisión');
   await page.locator('[data-layer="salud"]').click();await expect(page.locator('#mt-status')).toContainText('86 registros');
   await page.goBack();await expect(page.locator('#mt-status')).toContainText('2.135 puntos verificados');await page.goForward();await expect(page.locator('#mt-status')).toContainText('86 registros');
   // Fallback must preserve data and restore checkbox after provider failure.
   await page.locator('#mt-streets').check();await expect(page.locator('#mt-base-status')).toContainText('no está disponible');await expect(page.locator('#mt-streets')).not.toBeChecked();
   await page.locator('#mt-accessible summary').click();await expect(page.locator('#mt-territory-table tr')).toHaveCount(15);
   const a11y=await new AxeBuilder({page}).include('.mt-shell').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
   report.a11y=a11y.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}));
   expect(report.a11y.filter(v=>v.impact==='critical'||v.impact==='serious'),'No critical/serious axe violations in explorer').toEqual([]);
   report.final=await getMetrics(page);expect(errors).toEqual([]);expect(failedLocal).toEqual([]);report.passed=true;
  }finally{
   report.finished=new Date().toISOString();if(!report.passed){try{await page.screenshot({path:path.join(OUTPUT,name+'-failure.jpg'),type:'jpeg',quality:60});}catch{}}
   await save(name,report);await context.close();
  }
 });
}
test('2D recovery: HTTP error, retry, reduced motion and frame timing',async({browser})=>{
 const context=await browser.newContext({viewport:{width:390,height:900},hasTouch:true,isMobile:true,reducedMotion:'reduce',baseURL:BASE});const page=await context.newPage();
 try{
  await page.goto(ROUTE);await ready(page);let failures=1;
  await page.route('**/data/layers/educacion.geojson*',route=>failures-- >0?route.fulfill({status:503,contentType:'text/plain',body:'Injected QA failure'}):route.continue());
  await page.locator('[data-layer="educacion"]').click();await expect(page.locator('#mt-error-text')).toContainText('HTTP 503');await expect(page.locator('#mt-territory-table tr')).toHaveCount(0);
  await page.locator('#mt-retry').click();await expect(page.locator('#mt-status')).toContainText('2.732 registros');
  const frames=page.evaluate(()=>new Promise(resolve=>{const values=[];let previous=performance.now(),start=previous;function frame(now){values.push(now-previous);previous=now;if(now-start<2000)requestAnimationFrame(frame);else resolve(values);}requestAnimationFrame(frame);}));
  await page.locator('#mt-map canvas').focus();await page.keyboard.press('+');await page.keyboard.press('ArrowRight');await page.keyboard.press('ArrowDown');const times=await frames;
  const sorted=[...times].sort((a,b)=>a-b);await save('performance-mobile',{context:'390px Chromium ANGLE/SwiftShader, CI runner, reduced motion; frame cadence is not hardware GPU FPS',frames:times.length,meanFrameMs:times.reduce((a,b)=>a+b,0)/times.length,p95FrameMs:sorted[Math.floor(sorted.length*.95)],...await getMetrics(page)});
  await expect(page.locator('#mt-map canvas')).toBeVisible();
 }finally{await context.close();}
});
