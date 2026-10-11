import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';
const source = readFileSync(new URL('../deploy/site-overlay/assets/compartir.js', import.meta.url), 'utf8');
function fixture({nativeError, clipboardError, imageAvailable=false, canShareFile=false} = {}) {
  function element() { return {listeners:{}, hidden:true, addEventListener(n,fn){const before=this.listeners[n];this.listeners[n]=before ? async event=>{await before(event);await fn(event);} : fn;}, querySelector(){return status;}}; }
  const status={textContent:''}, dialog=element(); dialog.open=false; dialog.children=[]; dialog.appendChild=e=>dialog.children.push(e);
  dialog.showModal=()=>{dialog.open=true;}; dialog.close=()=>{dialog.open=false;};
  const selectors={dialog,'.share-status':status};
  for(const name of ['copy','native','instagram','close','caption','file']) selectors[`[data-share-${name}]`]=element();
  const anchors=['whatsapp','x','facebook'].map(platform=>({...element(),dataset:{sharePlatform:platform}}));
  const manual=[];
  const root={appendChild:e=>manual.push(e),dataset:{shareTitle:'Informe de salud',shareUrl:'https://cepoes.org/territorio/equipamientos/',shareImage:'/assets/compartir/test'},querySelector:s=>selectors[s],querySelectorAll:()=>anchors};
  const copied=[],tracked=[],shares=[];
  const navigator={clipboard:{writeText:async text=>{if(clipboardError)throw clipboardError;copied.push(text);}}, share:async data=>{if(nativeError)throw nativeError;shares.push(data);},canShare:()=>canShareFile};
  vm.runInNewContext(source,{document:{querySelectorAll:()=>[root],createElement:()=>({setAttribute(){},focus(){this.focused=true;},select(){this.selected=true;}})}, window:{CEPOES_ANALYTICS:{event:(...args)=>tracked.push(args)}},navigator,URL,location:{href:'https://cepoes.org/territorio/equipamientos/?comuna=7&categoria=salud&email=secreto%40test.com&q=personal&token=privado'},File:class File{constructor(parts,name,options){this.name=name;this.type=options.type;this.parts=parts;}},fetch:async()=>({ok:imageAvailable,blob:async()=>({type:'image/png'})})});
  return {selectors,anchors,copied,tracked,shares,dialog,manual};
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

test('clipboard denial offers selected manual text without success tracking',async()=>{
  const f=fixture({clipboardError:new Error('denied')});
  await f.selectors['[data-share-copy]'].listeners.click();
  assert.equal(f.manual.length,1); assert.match(f.manual[0].value,/utm_source=copy/);
  assert.equal(f.manual[0].selected,true); assert.equal(f.manual[0].focused,true);
  assert.equal(f.tracked.length,0);
});
test('caption fallback remains inside the open Instagram dialog',async()=>{
  const f=fixture({clipboardError:new Error('denied')});
  await f.selectors['[data-share-instagram]'].listeners.click();
  await f.selectors['[data-share-caption]'].listeners.click();
  assert.equal(f.dialog.children.length,1); assert.match(f.dialog.children[0].value,/utm_source=instagram/);
  assert.equal(f.manual.length,0); assert.equal(f.tracked.length,0);
});
test('Instagram image sharing appears only after a supported image loads',async()=>{
  const f=fixture({imageAvailable:true,canShareFile:true});
  assert.equal(f.selectors['[data-share-file]'].hidden,true);
  await f.selectors['[data-share-instagram]'].listeners.click();
  assert.equal(f.selectors['[data-share-file]'].hidden,false);
  await f.selectors['[data-share-file]'].listeners.click();
  assert.equal(f.shares[0].files[0].name,'cepoes-historia.png');
  assert.equal(f.shares[0].files[0].type,'image/png');
  assert.deepEqual(JSON.parse(JSON.stringify(f.tracked[0])),['share',{platform:'instagram',method:'native_image'}]);
});
test('unsupported file sharing retains download route and cancellation is not tracked',async()=>{
  const unsupported=fixture({imageAvailable:true});
  await unsupported.selectors['[data-share-instagram]'].listeners.click();
  assert.equal(unsupported.selectors['[data-share-file]'].hidden,true);
  const cancelled=fixture({imageAvailable:true,canShareFile:true,nativeError:{name:'AbortError'}});
  await cancelled.selectors['[data-share-instagram]'].listeners.click();
  await cancelled.selectors['[data-share-file]'].listeners.click();
  assert.equal(cancelled.tracked.length,0);
});
