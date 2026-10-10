import {test,expect} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
const OUT=process.env.QA_OUTPUT||path.resolve('qa-output');
const BASE='http://127.0.0.1:4173',URL=BASE+'/laboratorio/mapa-territorial/';
test('2D touch: real two-finger pan, tap, record dismissal and empty search',async({browser})=>{
 const context=await browser.newContext({viewport:{width:390,height:900},isMobile:true,hasTouch:true,reducedMotion:'reduce'});
 const page=await context.newPage();const report={context:'Chromium CDP touch emulation, real MapLibre WebGL; not a physical touchscreen'};
 try{
  await page.goto(URL);await page.waitForFunction(()=>window.__CEPOES_MAP_QA?.map==='ready'&&window.__CEPOES_MAP_QA?.status==='ready');
  const canvas=page.locator('#mt-map canvas');await canvas.scrollIntoViewIfNeeded();await page.waitForTimeout(350);
  const box=await canvas.boundingBox(),before=await canvas.screenshot();const cdp=await context.newCDPSession(page);
  const points=dy=>[{id:1,x:box.x+box.width*.4,y:box.y+box.height*.5+dy},{id:2,x:box.x+box.width*.65,y:box.y+box.height*.5+dy}];
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:points(0)});
  for(let dy=5;dy<=60;dy+=5){await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:points(dy)});await page.waitForTimeout(20);}
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await page.waitForTimeout(450);
  report.twoFingerPanChangedPixels=!(await canvas.screenshot()).equals(before);expect(report.twoFingerPanChangedPixels).toBe(true);await cdp.detach();
  await page.locator('#mt-fit').tap();await page.locator('#mt-territory').selectOption('barrio:parque-patricios');await expect(page.locator('#mt-place-name')).toHaveText('Parque Patricios');
  await mkdir(OUT,{recursive:true});await page.locator('.mt-workspace').screenshot({path:path.join(OUT,'2d-touch-selected.jpg'),type:'jpeg',quality:65});
  await page.locator('#mt-reset').tap();await page.locator('#mt-record-list [data-record]').first().tap();await expect(page.locator('#mt-service-card')).toBeVisible();
  await page.locator('#mt-close-record').tap();await expect(page.locator('#mt-service-card')).toBeHidden();await expect(page.locator('#mt-territory')).toBeFocused();
  await page.locator('#mt-record-search').fill('qa-sin-registro-xyz');await expect(page.locator('#mt-record-count')).toContainText('0 registros');await expect(page.locator('#mt-record-list')).toContainText('La fuente no registra resultados');
  await page.locator('#mt-record-search').fill('');await expect(page.locator('#mt-record-count')).toContainText('86 registros');report.passed=true;
 }finally{await mkdir(OUT,{recursive:true});await writeFile(path.join(OUT,'2d-touch.json'),JSON.stringify(report,null,2));await context.close();}
});
test('2D accessible alternative when WebGL is unavailable (injected)',async({browser})=>{
 const context=await browser.newContext({viewport:{width:320,height:900}});const page=await context.newPage();
 try{
  await context.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return /webgl/i.test(type)?null:original.call(this,type,...args);};});
  await page.goto(URL);await page.waitForFunction(()=>window.__CEPOES_MAP_QA?.map==='unavailable'&&window.__CEPOES_MAP_QA?.status==='ready');
  await expect(page.locator('#mt-map')).toContainText('Podés explorar todos los barrios');await expect(page.locator('#mt-fit')).toBeDisabled();
  await page.locator('#mt-territory').selectOption('barrio:parque-patricios');await expect(page.locator('#mt-place-name')).toHaveText('Parque Patricios');
  await page.locator('#mt-accessible summary').click();await expect(page.locator('#mt-territory-table tr')).toHaveCount(48);
  await mkdir(OUT,{recursive:true});await writeFile(path.join(OUT,'2d-no-webgl.json'),JSON.stringify({injectedFailure:true,passed:true,tableRows:48,selection:'Parque Patricios'}));
 }finally{await context.close();}
});
