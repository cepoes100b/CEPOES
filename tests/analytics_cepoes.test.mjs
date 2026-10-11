import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';
const source = readFileSync(new URL('../deploy/site-overlay/assets/analytics-cepoes.js', import.meta.url), 'utf8');
function fixture(href = 'https://cepoes.org/territorio/?email=personal%40example.org#token') {
  const scripts = [], listeners = {};
  const window = {addEventListener:()=>{}};
  const location = new URL(href);
  const document = {referrer:'https://example.org/?token=secret',
    createElement:()=>({}), head:{appendChild:s=>scripts.push(s)},
    addEventListener:(n,cb)=>{(listeners[n] ||= []).push(cb);}};
  vm.runInNewContext(source,{window,location,document,URL,Set,Date,Number});
  return {api:window.CEPOES_ANALYTICS,window,scripts,listeners};
}
test('no requests without ID and explicit analytics consent; no private or preview tracking',()=>{
  for (const href of ['https://cepoes.org/', 'https://cepoes.org/privado/', 'https://cepoes.org/admin/', 'http://localhost:8000/']) {
    const f=fixture(href);
    assert.equal(f.api.start({measurementId:'G-TEST123'}),false);
    assert.equal(f.api.start({measurementId:'invalid',analyticsConsent:true}),false);
    if(href!=='https://cepoes.org/') assert.equal(f.api.start({measurementId:'G-TEST123',analyticsConsent:true}),false);
    assert.equal(f.scripts.length,0);
  }
});
test('single page view, URL redaction, no arbitrary event payloads, idempotent startup',()=>{
  const f=fixture();
  assert.equal(f.api.start({measurementId:'G-TEST123',analyticsConsent:true}),true);
  assert.equal(f.api.start({measurementId:'G-TEST123',analyticsConsent:true}),false);
  assert.equal(f.scripts.length,1);
  f.api.event('map_interaction',{email:'personal@example.org',token:'secret',target_path:'/territorio/?token=secret'});
  assert.equal(f.api.event('unknown',{email:'secret'}),false);
  const calls=f.window.dataLayer.map(x=>Array.from(x));
  assert.equal(calls.filter(x=>x[1]==='page_view').length,1);
  assert.doesNotMatch(JSON.stringify(calls),/personal@example|secret|token|example\.org\/\?/);
  assert.equal(calls.find(x=>x[0]==='config')[2].allow_google_signals,false);
});
test('PDF clicks and withdrawal',()=>{
  const f=fixture(); f.api.start({measurementId:'G-TEST123',analyticsConsent:true});
  for (const cb of f.listeners.click) cb({target:{closest:selector=>selector==='a[href]' ? {href:'https://cepoes.org/informe.pdf?token=secret'} : null}});
  assert.equal(f.window.dataLayer.at(-1)[1],'report_download');
  assert.equal(f.window.dataLayer.at(-1)[2].target_path,'/informe.pdf');
  f.api.stop();
  assert.equal(f.window['ga-disable-G-TEST123'],true);
  assert.equal(f.api.event('map_interaction',{}),false);
  assert.equal(f.api.start({measurementId:'G-TEST123',analyticsConsent:true}),false);
});
