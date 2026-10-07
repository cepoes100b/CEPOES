import test from 'node:test';
import assert from 'node:assert/strict';
import {deliverOne,newsletterEmail,validateEdition} from '../supabase/functions/newsletter-dispatch/logic.js';
const job={edition:6,subscription_id:'test-id'};
test('una respuesta incierta conserva la misma clave al reintentar',async()=>{
 const keys=[];let attempts=0;
 const adapter={isActive:async()=>true,send:async(j,key)=>{keys.push(key);if(!attempts++)throw Error('timeout');return{id:'provider-id'};},finish:async()=>{},retry:async()=>{}};
 assert.equal(await deliverOne(job,adapter),'retry');assert.equal(await deliverOne(job,adapter),'accepted');assert.equal(keys[0],keys[1]);
});
test('una baja impide enviar un trabajo en cola',async()=>{
 let sent=false,state;
 const outcome=await deliverOne(job,{isActive:async()=>false,send:async()=>{sent=true;},finish:async(j,s)=>{state=s;}});
 assert.equal(outcome,'cancelled');assert.equal(state,'cancelled');assert.equal(sent,false);
});
test('si falla el registro posterior al envío se reintenta con idempotencia',async()=>{
 let retried=false;assert.equal(await deliverOne(job,{isActive:async()=>true,send:async()=>({id:'provider-id'}),finish:async()=>{throw Error('db');},retry:async()=>{retried=true;}}),'retry');assert.equal(retried,true);
});
test('el contenido editorial se escapa y ofrece baja en HTML y texto',()=>{
 const edition=validateEdition({edition:6,url:'/publicaciones/boletines/boletin-6-octubre-2026/',title:'<script>test</script>',summary:'A & B'});
 const email=newsletterEmail(edition,'https://example.com/unsubscribe');assert.ok(!email.html.includes('<script>'));assert.ok(email.html.includes('&amp;'));assert.ok(email.text.includes('Dar de baja'));
 assert.throws(()=>validateEdition({...edition,url:'https://untrusted.example/'}));
});
