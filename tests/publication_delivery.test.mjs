import test from 'node:test';
import assert from 'node:assert/strict';
import {validatePublication,publicationEmail,deliverOne} from '../supabase/functions/newsletter-dispatch/logic.js';
const item={key:'/publicaciones/notas/nueva/',url:'/publicaciones/notas/nueva/',kind:'analisis',title:'Título <seguro>',summary:'Resumen & enlace',date:'2026-10-08'};
test('la fecha pública conserva null, mes, día y el contrato de strings existente',()=>{
 for(const date of [null,'2026-09','2026-10-15','','Septiembre 2026','x'.repeat(80)]) {
  const publication={...item,date};
  assert.deepEqual(validatePublication(publication),publication);
  assert.equal(publication.date,date);
 }
});
test('sólo null amplía el contrato de fecha; ausencia, tipos y exceso siguen rechazados',()=>{
 const {date,...missing}=item;
 assert.throws(()=>validatePublication(missing),/invalid_publication/);
 for(const date of [undefined,false,true,0,20261015,[],{},new String('2026-10-15'),'x'.repeat(81)]) {
  assert.throws(()=>validatePublication({...item,date}),/invalid_publication/);
 }
});
test('una fecha nula mantiene las restricciones de identidad y contenido',()=>{
 const undated={...item,date:null};
 const invalidPaths=['https://example.invalid/','/solo/','/publicaciones//nota/','/publicaciones/nota/?x=1','/publicaciones/nota/#x','/publicaciones/nota','/publicaciones/'+ 'x'.repeat(300)+'/','/publicaciones/notas/','/publicaciones/informes/','/publicaciones/boletines/'];
 for(const url of invalidPaths)assert.throws(()=>validatePublication({...undated,url,key:url}));
 for(const change of [{url:null},{key:'/otra/nota/'},{kind:'datos'},{kind:null},{title:null},{title:1},{title:''},{title:'x'.repeat(301)},{summary:null},{summary:1},{summary:'x'.repeat(2001)}]) {
  assert.throws(()=>validatePublication({...undated,...change}),/invalid_publication/);
 }
 const boundaries={...undated,title:'x'.repeat(300),summary:'x'.repeat(2000),url:'/'+ 'x'.repeat(296)+'/a/'};
 boundaries.key=boundaries.url;
 assert.deepEqual(validatePublication(boundaries),boundaries);
 // Null cannot bypass the additional validation for a bulletin.
 assert.throws(()=>validatePublication({...undated,kind:'boletin'}),/invalid_edition/);
});
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
