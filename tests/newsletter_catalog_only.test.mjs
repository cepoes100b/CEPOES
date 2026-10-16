import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {stripTypeScriptTypes} from 'node:module';
import vm from 'node:vm';
import * as logic from '../supabase/functions/newsletter-dispatch/logic.js';

const publication={key:'/qa/catalog-only/',url:'/qa/catalog-only/',kind:'informe',title:'Prueba local',summary:'Sin destinatarios reales',date:null};
const feed={version:1,publications:[publication]};

// Execute the real TypeScript handler with all I/O replaced before module evaluation.
// The VM has no process, secrets, network implementation or external database.
async function harness({enabled='true',catalog=feed,rpcFailure=false,senderSecrets=true}={}) {
 const calls={rpc:[],from:[],fetch:[],env:[],client:0,delivery:0};
 const values={NEWSLETTER_DISPATCH_SECRET:'local-test-only',NEWSLETTER_ENABLED:enabled,SUPABASE_URL:'https://database.example.invalid',SUPABASE_SERVICE_ROLE_KEY:'local-test-only'};
 if(senderSecrets)Object.assign(values,{RESEND_API_KEY:'local-test-only',NEWSLETTER_FROM:'qa@example.invalid',NEWSLETTER_UNSUBSCRIBE_SECRET:'local-test-only'});
 let handler;
 const context=vm.createContext({
  Response,AbortSignal,TextEncoder,
  console:{error:()=>{}},
  Deno:{env:{get(name){calls.env.push(name);return values[name];}},serve(fn){handler=fn;}},
  fetch:async url=>{
   calls.fetch.push(url);
   assert.equal(url,'https://cepoes.org/assets/data/newsletter-publications.json');
   return Response.json(catalog);
  }
 });
 const client={
  rpc:async(name,args)=>{
   calls.rpc.push({name,args});
   assert.equal(name,'newsletter_enqueue_publications');
   return {data:null,error:rpcFailure?{message:'local failure'}:null};
  },
  from(name){calls.from.push(name);throw Error('table_access_forbidden');}
 };
 const sdk=new vm.SyntheticModule(['createClient'],function(){this.setExport('createClient',()=>{calls.client++;return client;});},{context});
 const pure=new vm.SyntheticModule(Object.keys(logic),function(){
  for(const [key,value] of Object.entries(logic))this.setExport(key,key==='deliverOne'?()=>{calls.delivery++;throw Error('delivery_forbidden');}:value);
 },{context});
 const source=await readFile(new URL('../supabase/functions/newsletter-dispatch/index.ts',import.meta.url),'utf8');
 const module=new vm.SourceTextModule(stripTypeScriptTypes(source),{context});
 await module.link(specifier=>{
  if(specifier==='npm:@supabase/supabase-js@2.95.0')return sdk;
  if(specifier==='./logic.js')return pure;
  throw Error('unexpected_import:'+specifier);
 });
 await module.evaluate();
 return {calls,request:({body={},authorization='Bearer local-test-only',method='POST'}={})=>handler(new Request('https://handler.example.invalid',{method,headers:{authorization},...(method==='POST'?{body:JSON.stringify(body)}:{})}))};
}

function noDelivery(calls) {
 assert.equal(calls.delivery,0);
 assert.deepEqual(calls.from,[]);
 assert.ok(calls.rpc.every(call=>call.name==='newsletter_enqueue_publications'));
 assert.ok(calls.fetch.every(url=>url==='https://cepoes.org/assets/data/newsletter-publications.json'));
 for(const name of ['RESEND_API_KEY','NEWSLETTER_FROM','NEWSLETTER_UNSUBSCRIBE_SECRET'])assert.ok(!calls.env.includes(name));
}

test('catalog-only validates and preserves dates with NEWSLETTER_ENABLED=true and ignores send requests',async()=>{
 const catalog={version:1,publications:[null,'2026-09','2026-10-15'].map((date,i)=>({...publication,key:`/qa/date-${i}/`,url:`/qa/date-${i}/`,date}))};
 const {calls,request}=await harness({catalog});
 for(const body of [{},{mode:'send',send:true,NEWSLETTER_ENABLED:true},{mode:'delivery',catalog_only:false,approved:true}]) {
  const response=await request({body});
  assert.equal(response.status,200);
  assert.deepEqual(await response.json(),{ok:true,mode:'catalog-only',cataloged:3,accepted:0,retry:0,cancelled:0});
 }
 assert.equal(calls.rpc.length,3);
 for(const call of calls.rpc)assert.deepEqual(call.args.p_publications,catalog.publications);
 noDelivery(calls);
});

test('existing disable flag and authorization still fail closed before catalog access',async()=>{
 for(const enabled of ['false',undefined]) {
  const {calls,request}=await harness({enabled:enabled??''});
  assert.equal((await request()).status,503);
  assert.equal(calls.client,0);assert.deepEqual(calls.rpc,[]);assert.deepEqual(calls.fetch,[]);noDelivery(calls);
 }
 for(const change of [{authorization:'Bearer wrong'},{method:'GET'}]) {
  const {calls,request}=await harness();
  assert.equal((await request(change)).status,401);
  assert.equal(calls.client,0);assert.deepEqual(calls.rpc,[]);assert.deepEqual(calls.fetch,[]);noDelivery(calls);
 }
});

test('catalog-only also works without sender configuration',async()=>{
 const {calls,request}=await harness({senderSecrets:false});
 assert.equal((await request()).status,200);
 assert.equal(calls.rpc.length,1);noDelivery(calls);
});

test('invalid feed and dates fail before any RPC; catalog failure cannot continue to delivery',async()=>{
 const invalid=[{version:2,publications:[publication]},{version:1,publications:[]},{version:1,publications:[publication,publication]},...['x'.repeat(81),42,false,{}].map(date=>({version:1,publications:[{...publication,date}]}))];
 for(const catalog of invalid) {
  const {calls,request}=await harness({catalog});
  assert.equal((await request()).status,503);
  assert.deepEqual(calls.rpc,[]);noDelivery(calls);
 }
 const {calls,request}=await harness({rpcFailure:true});
 assert.equal((await request()).status,503);assert.equal(calls.rpc.length,1);noDelivery(calls);
});
