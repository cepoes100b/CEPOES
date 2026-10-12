import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';
const source = readFileSync(new URL('../deploy/site-overlay/assets/compartir.js', import.meta.url), 'utf8');
function fixture({nativeError, clipboardError, imageAvailable=false, canShareFile=false, mediaEnabled=false, nativeAvailable=true} = {}) {
  function element() { return {listeners:{}, hidden:true, addEventListener(n,fn){const before=this.listeners[n];this.listeners[n]=before ? async event=>{await before(event);await fn(event);} : fn;}, querySelector(){return status;}}; }
  const status={textContent:''}, dialog=element(); dialog.open=false; dialog.children=[]; dialog.appendChild=e=>dialog.children.push(e);
  dialog.showModal=()=>{dialog.open=true;}; dialog.close=()=>{dialog.open=false;};
  const media=element(); media.open=false; media.children=[]; media.appendChild=e=>media.children.push(e); media.showModal=()=>{media.open=true;}; media.close=()=>{media.open=false;};
  const mediaNodes={'.share-status':{textContent:''}};
  for(const name of ['title','help','link','file','close','caption','download'])mediaNodes[`[data-media-${name}]`]=element();
  media.querySelector=s=>mediaNodes[s];
  const selectors={dialog,'.share-status':status,'.share-media-dialog':mediaEnabled ? media : null};
  for(const name of ['copy','native','instagram','close','caption','file']) selectors[`[data-share-${name}]`]=element();
  const anchors=['whatsapp','x','facebook'].map(platform=>({...element(),dataset:{sharePlatform:platform}}));
  const manual=[];
  const root={appendChild:e=>manual.push(e),dataset:{shareTitle:'Informe de salud',shareUrl:'https://cepoes.org/territorio/equipamientos/',shareImage:'/assets/compartir/test'},querySelector:s=>selectors[s],querySelectorAll:()=>anchors};
  const copied=[],tracked=[],shares=[];
  const navigator={clipboard:{writeText:async text=>{if(clipboardError)throw clipboardError;copied.push(text);}}, share:async data=>{if(nativeError)throw nativeError;shares.push(data);},canShare:()=>canShareFile};
  if(!nativeAvailable){delete navigator.share;delete navigator.canShare;}
  vm.runInNewContext(source,{document:{querySelectorAll:()=>[root],createElement:()=>({setAttribute(){},focus(){this.focused=true;},select(){this.selected=true;}})}, window:{CEPOES_ANALYTICS:{event:(...args)=>tracked.push(args)}},navigator,URL,location:{href:'https://cepoes.org/territorio/equipamientos/?comuna=7&categoria=salud&email=secreto%40test.com&q=personal&token=privado'},File:class File{constructor(parts,name,options){this.name=name;this.type=options.type;this.parts=parts;}},fetch:async()=>({ok:imageAvailable,blob:async()=>({type:'image/png'})})});
  return {selectors,anchors,copied,tracked,shares,dialog,manual,media,mediaNodes};
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


const clickEvent=()=>({prevented:false,preventDefault(){this.prevented=true;}});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
test('WhatsApp opens image panel and shares actual file plus public link',async()=>{
  const f=fixture({mediaEnabled:true,imageAvailable:true,canShareFile:true});const event=clickEvent();
  f.anchors[0].listeners.click(event);await flush();
  assert.equal(event.prevented,true);assert.equal(f.media.open,true);assert.equal(f.tracked.length,0);
  assert.equal(f.mediaNodes['[data-media-title]'].textContent,'Compartir en WhatsApp');
  await f.mediaNodes['[data-media-file]'].listeners.click();
  assert.equal(f.shares[0].files[0].name,'cepoes-publicacion.png');
  assert.match(f.shares[0].text,/utm_source=whatsapp/);assert.doesNotMatch(f.shares[0].text,/secreto|privado|personal/);
  assert.equal(f.tracked[0][1].method,'native_image');
});
test('X panel uses X link and copy; choosing link is explicitly measured',async()=>{
  const f=fixture({mediaEnabled:true,imageAvailable:true,canShareFile:true});
  f.anchors[1].listeners.click(clickEvent());await flush();
  assert.equal(f.mediaNodes['[data-media-title]'].textContent,'Compartir en X');
  assert.match(f.mediaNodes['[data-media-link]'].href,/twitter.com\/intent\/tweet/);
  await f.mediaNodes['[data-media-caption]'].listeners.click();assert.match(f.copied[0],/utm_source=x/);
  f.mediaNodes['[data-media-link]'].listeners.click();assert.equal(f.tracked[1][1].method,'open_composer');
});
test('desktop without native share retains download, copy and link actions',async()=>{
  const f=fixture({mediaEnabled:true,nativeAvailable:false});
  f.anchors[0].listeners.click(clickEvent());
  assert.equal(f.media.open,true);assert.equal(f.mediaNodes['[data-media-file]'].hidden,true);
  f.mediaNodes['[data-media-download]'].listeners.click();assert.equal(f.tracked[0][1].method,'download_image');
  await f.mediaNodes['[data-media-caption]'].listeners.click();assert.match(f.copied[0],/utm_source=whatsapp/);
  f.mediaNodes['[data-media-close]'].listeners.click();assert.equal(f.media.open,false);
});
test('failed image and cancelled native image never claim a completed share',async()=>{
  const failed=fixture({mediaEnabled:true});failed.anchors[0].listeners.click(clickEvent());await flush();
  assert.equal(failed.mediaNodes['[data-media-file]'].hidden,true);assert.match(failed.mediaNodes['.share-status'].textContent,/No se pudo cargar/);
  const f=fixture({mediaEnabled:true,imageAvailable:true,canShareFile:true,nativeError:{name:'AbortError'}});
  f.anchors[1].listeners.click(clickEvent());await flush();await f.mediaNodes['[data-media-file]'].listeners.click();
  assert.equal(f.tracked.length,0);
});
test('manual caption fallback is shown inside the active media panel',async()=>{
  const f=fixture({mediaEnabled:true,clipboardError:new Error('denied')});
  f.anchors[0].listeners.click(clickEvent());await f.mediaNodes['[data-media-caption]'].listeners.click();
  assert.equal(f.media.children.length,1);assert.equal(f.dialog.children.length,0);
  assert.match(f.media.children[0].value,/utm_source=whatsapp/);assert.equal(f.tracked.length,0);
});
