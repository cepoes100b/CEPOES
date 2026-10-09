import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
const OUT=process.env.QA_OUTPUT||path.resolve('qa-output');
const ROOT=new URL('../../../',import.meta.url);const BASE='http://127.0.0.1:4173';
test('Internal D3 reference: real browser, pinned public snapshots',async({browser})=>{
 const context=await browser.newContext({viewport:{width:1440,height:1050}});const page=await context.newPage();
 const data=await readFile(new URL('equipamientos/resumen-territorial.json',ROOT));const geo=await readFile(new URL('badata/barrios.geojson',ROOT));const d3=await readFile(new URL('node_modules/d3/dist/d3.min.js',import.meta.url));
 const report={scope:'Internal original D3 thematic map with its own existing indicators; public input snapshots pinned to checkout. Script/data routes are fulfilled locally so timings measure browser rendering, not external-provider network. Different features/indicators from new explorer: not an equivalent feature benchmark.',viewport:{width:1440,height:1050},inputBytes:{summary:data.length,geometry:geo.length,d3:d3.length}};
 try{
  await context.route('**/*',route=>{const url=route.request().url();const u=new URL(url);if(url.includes('cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js'))return route.fulfill({status:200,contentType:'application/javascript',body:d3});if(url.includes('equipamientos/resumen-territorial.json'))return route.fulfill({status:200,contentType:'application/json',body:data});if(url.includes('/barrios/barrios.geojson'))return route.fulfill({status:200,contentType:'application/json',body:geo});if(u.origin===BASE||['fonts.googleapis.com','fonts.gstatic.com'].includes(u.hostname))return route.continue();return route.abort();});
  await page.goto(BASE+'/territorio/mapa-tematico/',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>document.querySelectorAll('#thematic-map svg path').length===48,null,{timeout:30000});
  report.mapReadyMs=await page.evaluate(()=>performance.now());report.paths=await page.locator('#thematic-map svg path').count();expect(report.paths).toBe(48);
  const start=performance.now();await page.locator('#thematic-indicator').selectOption('salud');await page.waitForTimeout(50);report.filterObservationMs=performance.now()-start;
  report.browser=await page.evaluate(()=>({userAgent:navigator.userAgent,memory:performance.memory?{usedJSHeapSize:performance.memory.usedJSHeapSize}:null,resourceBytes:performance.getEntriesByType('resource').reduce((s,r)=>s+r.transferSize,0)}));
  await mkdir(OUT,{recursive:true});await page.locator('#thematic-map').screenshot({path:path.join(OUT,'reference-d3.jpg'),type:'jpeg',quality:65});report.status='rendered';
 }finally{await mkdir(OUT,{recursive:true});await writeFile(path.join(OUT,'reference-d3.json'),JSON.stringify(report,null,2));await context.close();}
});
