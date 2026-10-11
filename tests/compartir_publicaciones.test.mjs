import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';
const source = readFileSync(new URL('../deploy/site-overlay/assets/compartir.js', import.meta.url), 'utf8');
function fixture({nativeError} = {}) {
  function element() { return {listeners:{}, hidden:true, addEventListener(n,fn){const before=this.listeners[n];this.listeners[n]=before ? async event=>{await before(event);await fn(event);} : fn;}, querySelector(){return status;}}; }
  const status={textContent:''}, dialog=element(); dialog.open=false;
  dialog.showModal=()=>{dialog.open=true;}; dialog.close=()=>{dialog.open=false;};
  const selectors={dialog,'.share-status':status};
  for(const name of ['copy','native','instagram','close','caption','file']) selectors[`[data-share-${name}]`]=element();
  const anchors=['whatsapp','x','facebook'].map(platform=>({...element(),dataset:{sharePlatform:platform}}));
  const root={dataset:{shareTitle:'Informe de salud',shareUrl:'https://cepoes.org/territorio/equipamientos/',shareImage:'/assets/compartir/test'},querySelector:s=>selectors[s],querySelectorAll:()=>anchors};
  const copied=[],tracked=[],shares=[];
  const navigator={clipboard:{writeText:async text=>copied.push(text)}, share:async data=>{if(nativeError)throw nativeError;shares.push(data);},canShare:()=>false};
  vm.runInNewContext(source,{document:{querySelectorAll:()=>[root]}, window:{CEPOES_ANALYTICS:{event:(...args)=>tracked.push(args)}},navigator,URL,location:{href:'https://cepoes.org/territorio/equipamientos/?comuna=7&categoria=salud&email=secreto%40test.com&q=personal&token=privado'},fetch:async()=>({ok:false})});
  return {selectors,anchors,copied,tracked,shares,dialog};
}
test('copy preserves public filters and excludes searches and personal parameters',async()=>{
  const f=fixture(); await f.selectors['[data-share-copy]'].listeners.click();
  const u=new URL(f.copied[0]); assert.equal(u.searchParams.get('comuna'),'7'); assert.equal(u.searchParams.get('categoria'),'salud');
  for(const key of ['email','token','q']) assert.equal(u.searchParams.has(key),false);
  assert.equal(u.searchParams.get('utm_source'),'copy'); assert.equal(f.tracked[0][0],'share');
});
test('platform links compose the canonical URL and title without posting',()=>{
  const f=fixture(); for(const a of f.anchors) {a.listeners.click();assert.match(a.href,/utm_source/);assert.doesNotMatch(a.href,/secreto|privado|personal/);}
  assert.equal(f.shares.length,0); assert.equal(f.tracked.length,3);
});
test('native cancellation produces no success tracking',async()=>{
  const f=fixture({nativeError:{name:'AbortError'}}); await f.selectors['[data-share-native]'].listeners.click();assert.equal(f.tracked.length,0);
});
test('dialog opens and closes, caption contains title and Instagram campaign',async()=>{
  const f=fixture(); await f.selectors['[data-share-instagram]'].listeners.click(); assert.equal(f.dialog.open,true);
  await f.selectors['[data-share-caption]'].listeners.click();assert.match(f.copied[0],/Informe de salud/);assert.match(f.copied[0],/utm_source=instagram/);
  f.selectors['[data-share-close]'].listeners.click();assert.equal(f.dialog.open,false);
});
