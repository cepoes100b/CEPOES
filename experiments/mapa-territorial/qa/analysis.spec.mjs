import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {PNG} from 'pngjs';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
const OUTPUT=process.env.QA_OUTPUT||path.resolve('qa-output'),BASE='http://127.0.0.1:4173',ROUTE='/laboratorio/mapa-territorial/';
const ANALYZE=ROUTE+'?modo=analizar&vista=3d&escala=comuna&indicador=sin-cobertura-salud';
const capture=async(page,selector,name)=>{await page.evaluate(()=>scrollTo(0,0));await page.mouse.move(0,0);await page.waitForTimeout(100);const clip=await page.locator(selector).boundingBox();await page.screenshot({path:path.join(OUTPUT,name+'.jpg'),clip,fullPage:true,type:'jpeg',quality:60,animations:'disabled'});};
const save=(name,report)=>writeFile(path.join(OUTPUT,name+'.json'),JSON.stringify(report,null,2));
const ready=page=>page.waitForFunction(()=>window.__CEPOES_MAP_QA?.map==='ready'&&window.__CEPOES_MAP_QA?.analysis?.status==='ready'&&window.__CEPOES_MAP_QA?.analysis?.animation==='idle'&&window.__CEPOES_MAP_QA?.analysis?.rendered===true,null,{timeout:30000});
async function proof(page){
 const webgl=await page.locator('#mt-map canvas').evaluate(canvas=>{const gl=canvas.getContext('webgl2');if(!gl)throw new Error('WebGL2 unavailable');const ext=gl.getExtension('WEBGL_debug_renderer_info');return {version:gl.getParameter(gl.VERSION),renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),lost:gl.isContextLost(),width:canvas.width,height:canvas.height};});
 const png=PNG.sync.read(await page.locator('#mt-map canvas').screenshot()),colors=new Set();let colored=0;for(let y=15;y<png.height-15;y+=5)for(let x=15;x<png.width-15;x+=5){const i=(y*png.width+x)*4;colors.add(`${png.data[i]},${png.data[i+1]},${png.data[i+2]}`);if(png.data[i+1]-png.data[i]>18&&png.data[i+2]-png.data[i]>10)colored++;}
 expect(webgl.lost).toBe(false);expect(colors.size).toBeGreaterThan(20);expect(colored,'Analytical features must render the turquoise ramp, not all missing-data gray').toBeGreaterThan(25);
 const analysis=await page.evaluate(()=>window.__CEPOES_MAP_QA.analysis);expect(analysis.renderProof.layerType).toBe('fill-extrusion');expect(analysis.renderProof.visible).toBe('visible');expect(analysis.renderProof.pitch).toBeGreaterThan(40);expect(analysis.renderProof.renderedIds.length).toBeGreaterThan(5);expect(analysis.renderProof.featureStates.every(f=>f.id===f.propertyId&&f.state.available===true&&f.state.ratio>0)).toBe(true);expect(analysis.renderProof.heights.every(r=>r.ratio>0&&r.ratio<1)).toBe(true);
 return {...webgl,sampledColors:colors.size,turquoiseSamples:colored,analysis,note:'Actual Chromium WebGL2 via ANGLE/SwiftShader; software rendering, not physical GPU performance.'};
}
test.beforeAll(async()=>mkdir(OUTPUT,{recursive:true}));
for(const width of [320,390,430,1440])for(const theme of ['light','dark']){
 test(`Analizar ${width}px ${theme}: mismo dato en plano, 3D, ranking y tabla`,async({browser})=>{
  const name=`analysis-${width}-${theme}`,context=await browser.newContext({viewport:{width,height:width===1440?1050:900},isMobile:width<700,hasTouch:width<700,deviceScaleFactor:1,colorScheme:theme,baseURL:BASE});
  await context.addInitScript(t=>localStorage.setItem('cepoes-theme',t),theme);
  const page=await context.newPage(),errors=[],requests=[],failed=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));page.on('response',r=>{if(r.url().startsWith(BASE)&&r.status()>=400)failed.push({url:r.url(),status:r.status()});});
  await context.route('**/*',route=>{const u=new URL(route.request().url());return u.origin===BASE||['fonts.googleapis.com','fonts.gstatic.com'].includes(u.hostname)?route.continue():route.abort('blockedbyclient');});
  const report={name,width,theme,errors,failed};
  try{
   await page.goto(ANALYZE,{waitUntil:'domcontentloaded'});await ready(page);await page.evaluate(()=>document.fonts.ready);report.proof=await proof(page);
   expect(requests.some(r=>r.includes('/data/layers/')),'Analytical URL does not fetch equipment records').toBe(false);
   await expect(page.locator('#mt-map canvas')).toHaveCount(1);await expect(page.locator('#mt-analysis-table tr')).toHaveCount(15);await expect(page.locator('#mt-analysis-rank button')).toHaveCount(15);
   await expect(page.locator('#mt-analysis-context')).not.toHaveAttribute('open');await expect(page.locator('#mt-analysis-period')).toContainText('viviendas particulares');
   report.controlsHeight=(await page.locator('#mt-analysis-controls').boundingBox()).height;if(width<700)expect(report.controlsHeight,'Compact controls keep the mobile map closer to its selector').toBeLessThan(560);
   await page.locator('#mt-analysis-context summary').focus();await page.keyboard.press('Enter');await expect(page.locator('#mt-analysis-universe')).toBeVisible();await expect(page.locator('#mt-analysis-context a')).toHaveAttribute('href','#mt-analysis-method');await page.locator('#mt-analysis-context summary').click();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await expect(page.locator('#mt-analysis-orbit')).toHaveAttribute('aria-pressed','false');
   await page.locator('#mt-analysis-rank [data-territory="comuna:8"]').click();await ready(page);await expect(page.locator('#mt-place-name')).toHaveText('Comuna 8');await expect(page.locator('#mt-analysis-rank [data-territory="comuna:8"]')).toHaveAttribute('aria-pressed','true');expect(page.url()).toContain('territorio=comuna%3A8');
   await page.locator('#mt-analysis-rank [data-territory="comuna:13"]').click();await ready(page);await page.goBack();await ready(page);await expect(page.locator('#mt-place-name')).toHaveText('Comuna 8');
   await expect(page.locator('.mt-analysis-selection')).toHaveCount(1);await expect(page.locator('.mt-analysis-selection')).toBeVisible();await expect(page.locator('.mt-analysis-selection')).toContainText('Comuna 8');await expect(page.locator('#mt-analysis-selection-status')).toHaveText('Seleccionada: Comuna 8');expect(Number(await page.locator('.mt-analysis-selection').getAttribute('data-elevation'))).toBeCloseTo(84747/203888*3200,4);
   const value=await page.locator('#mt-metrics .mt-metric-main strong').textContent();report.selectedValue=value;
   await expect(page.locator('#mt-analysis-table tr').filter({has:page.locator('[data-territory="comuna:8"]')})).toContainText(value);
   const three=await page.locator('#mt-map canvas').screenshot();
   await capture(page,'.mt-workspace',name+'-3d');
   await page.locator('[data-view="flat"]').click();await page.emulateMedia({reducedMotion:'reduce'});await ready(page);await expect(page.locator('.mt-analysis-selection')).toBeHidden();expect(await page.evaluate(()=>window.__CEPOES_MAP_QA.analysis.renderProof.pitch)).toBe(0);await page.emulateMedia({reducedMotion:'no-preference'});await expect(page.locator('#mt-metrics .mt-metric-main strong')).toHaveText(value);const flat=await page.locator('#mt-map canvas').screenshot();expect(three.equals(flat),'3D and flat must genuinely render different pixels').toBe(false);
   await capture(page,'.mt-map-section',name+'-flat');
   await page.locator('[data-view="3d"]').click();await ready(page);await page.locator('#mt-analysis-orbit').click();await expect(page.locator('#mt-analysis-orbit')).toHaveAttribute('aria-pressed','true');await page.locator('#mt-map canvas').focus();await page.keyboard.press('ArrowRight');await expect(page.locator('#mt-analysis-orbit')).toHaveAttribute('aria-pressed','false');
   await page.emulateMedia({reducedMotion:'reduce'});await expect(page.locator('#mt-analysis-orbit')).toBeDisabled();await expect(page.locator('#mt-analysis-animation')).toContainText('Movimiento reducido');
   await page.locator('#mt-level').selectOption('barrio');await expect(page.locator('#mt-analysis-coverage')).toContainText('Sin datos para barrios');await expect(page.locator('#mt-metrics .mt-metric-main strong')).toHaveText('s/d');await expect(page.locator('[data-view="3d"]')).toBeDisabled();
   await page.locator('#mt-analysis-comunas').click();await ready(page);
   const a11y=await new AxeBuilder({page}).include('.mt-shell').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();report.a11y=a11y.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}));expect(report.a11y.filter(v=>['critical','serious'].includes(v.impact))).toEqual([]);
   await page.locator('[data-mode="explore"]').click();await expect(page.locator('#mt-status')).toContainText('86 registros');await expect(page.locator('#mt-analysis-data')).toBeHidden();await expect(page.locator('#mt-map canvas')).toHaveCount(1);await page.goBack();await ready(page);await expect(page.locator('#mt-map canvas')).toHaveCount(1);
   report.runtime=await page.evaluate(()=>({qa:window.__CEPOES_MAP_QA,memory:performance.memory?{usedJSHeapSize:performance.memory.usedJSHeapSize}:null,resources:performance.getEntriesByType('resource').map(r=>({path:new URL(r.name).pathname,bytes:r.transferSize,duration:r.duration}))}));expect(errors).toEqual([]);expect(failed).toEqual([]);report.passed=true;
  }finally{if(!report.passed)try{await page.screenshot({path:path.join(OUTPUT,name+'-failure.jpg'),type:'jpeg',quality:55});}catch{}await save(name,report);await context.close();}
 });
}
test('Analizar: lazy module, retries, no-WebGL2 fallback and shared public URL',async({browser})=>{
 const context=await browser.newContext({viewport:{width:390,height:900},baseURL:BASE}),page=await context.newPage(),requests=[];
 await context.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return /^webgl/.test(type)?null:original.call(this,type,...args);};});page.on('request',r=>requests.push(r.url()));
 try{
  await page.goto(ROUTE);await expect(page.locator('#mt-status')).toContainText('86 registros');expect(requests.some(r=>r.includes('/analysis/'))).toBe(false);
  let fail=true;await page.route('**/data/analysis/indicators.json*',r=>fail?r.fulfill({status:503,body:'Injected QA error'}):r.continue());
  await page.locator('[data-mode="analyze"]').click();await expect(page.locator('#mt-error-text')).toContainText('HTTP 503');await expect(page.locator('#mt-analysis-table tr')).toHaveCount(0);fail=false;await page.locator('#mt-retry').click();await expect(page.locator('#mt-analysis-table tr')).toHaveCount(15);await expect(page.locator('#mt-analysis-availability')).toContainText('no está disponible');
  await page.locator('#mt-analysis-rank [data-territory="comuna:8"]').click();await expect(page.locator('#mt-place-name')).toHaveText('Comuna 8');await page.locator('#mt-share').click();await expect(page.locator('#mt-share-url')).toHaveValue(/modo=analizar/);await expect(page.locator('#mt-share-url')).toHaveValue(/territorio=comuna%3A8/);await expect(page.locator('[data-view="3d"]')).toBeDisabled();
  await page.locator('.mt-workspace').screenshot({path:path.join(OUTPUT,'analysis-no-webgl.jpg'),type:'jpeg',quality:60});await save('analysis-no-webgl',{qa:await page.evaluate(()=>window.__CEPOES_MAP_QA),requests:requests.map(x=>new URL(x).pathname)});
 }finally{await context.close();}
});
test('Analizar: frame cadence during a real flat/3D camera transition',async({browser})=>{
 const context=await browser.newContext({viewport:{width:390,height:900},isMobile:true,hasTouch:true,baseURL:BASE}),page=await context.newPage();
 try{
  await page.goto(ANALYZE+'&territorio=comuna%3A8');await ready(page);await expect(page.locator('.mt-analysis-selection')).toBeVisible();
  const frames=page.evaluate(()=>new Promise(resolve=>{const values=[];let last=performance.now(),start=last;function step(now){values.push(now-last);last=now;if(now-start<2000)requestAnimationFrame(step);else resolve(values);}requestAnimationFrame(step);}));
  await page.locator('[data-view="flat"]').click();await ready(page);await page.locator('[data-view="3d"]').click();await ready(page);const times=await frames,sorted=[...times].sort((a,b)=>a-b);
  await save('performance-analysis',{context:'Chromium ANGLE/SwiftShader at390px, software-rendered CI; camera frame cadence, not physical GPU benchmark',frames:times.length,meanFrameMs:times.reduce((a,b)=>a+b,0)/times.length,p95FrameMs:sorted[Math.floor(sorted.length*.95)],qa:await page.evaluate(()=>window.__CEPOES_MAP_QA)});
 }finally{await context.close();}
});
