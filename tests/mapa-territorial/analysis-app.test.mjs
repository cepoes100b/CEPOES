// DOM/state regressions only. Fixtures are for tests; no visual/WebGL claim.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const ROOT=new URL('../../',import.meta.url).pathname;
const require=createRequire(ROOT+'/experiments/mapa-territorial/package.json');
const {JSDOM}=require('jsdom');
const base=pathToFileURL(ROOT+'/experiments/mapa-territorial/public/');
const waitUntil=async predicate=>{const start=Date.now();while(!predicate()){if(Date.now()-start>5000)throw new Error('DOM condition timed out');await new Promise(r=>setTimeout(r,10));}};
const fixture=()=>({schema:'cepoes-territorial-analysis-v1',sources:[{id:'test',name:'Test fixture only',publisher:'Test',license:'Test only',checked_at:'2026-10-09',url:'https://example.org/test'}],indicators:[{id:'test-rate',status:'verified',level:'comuna',name:'Test rate',unit:'%',period:'2022',universe:'Test universe',method:'Test ratio',numerator_label:'N',denominator_label:'D',multiplier:100,source_ids:['test'],rows:Array.from({length:15},(_,i)=>({id:`comuna:${i+1}`,value:20,numerator:20,denominator:100}))}]});
test('analytical navigation rejects stale equipment data and preserves keyboard focus',async t=>{
 const dom=new JSDOM(await readFile(new URL('laboratorio/mapa-territorial/index.html',base),'utf8'),{url:'https://preview.invalid/laboratorio/mapa-territorial/'}),win=dom.window;
 const globals={window:win,document:win.document,location:win.location,history:win.history,MutationObserver:win.MutationObserver,matchMedia:()=>({matches:false,addEventListener(){},removeEventListener(){}}),requestAnimationFrame:fn=>setTimeout(fn,0),cancelAnimationFrame:clearTimeout};
 Object.assign(globalThis,globals);win.HTMLElement.prototype.scrollIntoView=function(){};
 const {TerritorialMap}=await import(new URL('assets/mapa-territorial/engine.mjs',base));
 const originalCreate=TerritorialMap.create;TerritorialMap.create=async()=>{throw new Error('Intentional nonvisual DOM test: map disabled');};
 let releaseEducation,resolveEducationRead,releaseGreen;const greenGate=new Promise(r=>releaseGreen=r);const gate=new Promise(r=>releaseEducation=r),educationRead=new Promise(r=>resolveEducationRead=r);
 const calls=[];
 globalThis.fetch=async input=>{const rel=new URL(input).pathname.split('/assets/mapa-territorial/data/')[1];calls.push(rel);if(rel==='analysis/indicators.json')return {ok:true,json:async()=>fixture()};if(rel==='layers/verdes.geojson'){await greenGate;return {ok:false,status:503};}if(rel==='layers/educacion.geojson')await gate;const data=JSON.parse(await readFile(new URL('assets/mapa-territorial/data/'+rel,base)));return {ok:true,json:async()=>{if(rel==='layers/educacion.geojson')resolveEducationRead();return data;}};};
 const $=id=>win.document.getElementById(id),clickMode=mode=>win.document.querySelector(`[data-mode="${mode}"]`).click();
 try{
  await import(new URL('assets/mapa-territorial/app.mjs?review-regression',base));
  await waitUntil(()=>win.__CEPOES_MAP_QA.status==='ready'&&win.__CEPOES_MAP_QA.map==='unavailable');
  clickMode('analyze');await waitUntil(()=>win.__CEPOES_MAP_QA.analysis?.status==='ready');
  clickMode('explore');win.document.querySelector('[data-layer="educacion"]').click();
  await waitUntil(()=>calls.includes('layers/educacion.geojson'));
  win.history.pushState(null,'','?capa=salud&escala=comuna&modo=analizar&vista=plana&indicador=test-rate');win.dispatchEvent(new win.PopStateEvent('popstate'));
  releaseEducation();await educationRead;await new Promise(r=>setTimeout(r,30));
  clickMode('explore');await waitUntil(()=>$('mt-record-count').textContent!=='Cargando…');
  await t.test('pending education never populates the restored health layer',()=>{
   assert.match(win.location.search,/capa=salud/);
   assert.match($('mt-records-title').textContent,/Salud/);
   assert.match($('mt-status').textContent,/86 registros/);
   assert.match($('mt-metrics').textContent,/86registros de salud/);
   assert.equal(win.document.querySelector('[data-layer][aria-pressed="true"]').dataset.layer,'salud');
  });
  clickMode('analyze');await waitUntil(()=>win.__CEPOES_MAP_QA.analysis?.status==='ready');
  await t.test('ranking keeps focus on the selected control',()=>{
   const button=$('mt-analysis-rank').querySelector('[data-territory="comuna:8"]');button.focus();button.click();
   assert.equal(win.document.activeElement,$('mt-analysis-rank').querySelector('[data-territory="comuna:8"]'));
   assert.equal(win.document.activeElement.getAttribute('aria-pressed'),'true');
  });
  await t.test('table keeps focus on the selected control',()=>{
   const button=$('mt-analysis-table').querySelector('[data-territory="comuna:6"]');button.focus();button.click();
   assert.equal(win.document.activeElement,$('mt-analysis-table').querySelector('[data-territory="comuna:6"]'));
   assert.equal(win.document.activeElement.getAttribute('aria-pressed'),'true');
  });
  await t.test('a late equipment failure cannot overwrite the analytical status',async()=>{
   clickMode('explore');win.document.querySelector('[data-layer="verdes"]').click();await waitUntil(()=>calls.includes('layers/verdes.geojson'));clickMode('analyze');await waitUntil(()=>win.__CEPOES_MAP_QA.analysis?.status==='ready');releaseGreen();await new Promise(r=>setTimeout(r,30));
   assert.equal(win.__CEPOES_MAP_QA.status,'ready');assert.equal($('mt-error').hidden,true);assert.match($('mt-status').textContent,/Test rate/);assert.equal($('mt-analysis-table').rows.length,15);
  });
 }finally{TerritorialMap.create=originalCreate;dom.window.close();}
});
