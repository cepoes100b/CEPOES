import test from 'node:test';
import assert from 'node:assert/strict';
import {validatePublication,publicationEmail,deliverOne} from '../supabase/functions/newsletter-dispatch/logic.js';
const item={key:'/publicaciones/notas/nueva/',url:'/publicaciones/notas/nueva/',kind:'analisis',title:'Título <seguro>',summary:'Resumen & enlace',date:'2026-10-08'};
test('una publicación tiene identidad estable, formatos completos e identidad CEPOES',()=>{
 const mail=publicationEmail(validatePublication(item),'https://example.invalid/unsubscribe');
 assert.ok(mail.html.includes('#00A7E1'));assert.ok(mail.html.includes('#16232F'));
 assert.ok(!mail.html.includes('#edb521'));assert.ok(!mail.html.includes('#0b485a'));
 assert.ok(mail.html.includes('Título &lt;seguro&gt;'));assert.ok(mail.html.includes('Dar de baja'));
 assert.ok(mail.text.includes('Dar de baja'));assert.ok(mail.subject.startsWith('Nueva nota de CEPOES'));
 for(const kind of ['informe','prensa','aviso'])assert.ok(publicationEmail({...item,kind},'https://example.invalid/unsubscribe').html.includes('Leer la publicación'));
 for(const change of [{url:'https://example.invalid/'},{key:'/otro/'},{url:'/publicaciones/notas/',key:'/publicaciones/notas/'},{kind:'datos'}])assert.throws(()=>validatePublication({...item,...change}));
});
test('el reintento usa el UUID estable de la entrega, no el título ni la URL',async()=>{
 const keys=[],job={publication_key:item.key,delivery_id:'stable-delivery',subscription_id:'subscriber'};
 const adapters={isActive:async()=>true,send:async(j,key)=>{keys.push(key);throw Error('timeout');},retry:async()=>{}};
 await deliverOne(job,adapters);await deliverOne(job,adapters);
 assert.equal(keys[0],keys[1]);assert.equal(keys[0],'cepoes-publication-stable-delivery');
});
