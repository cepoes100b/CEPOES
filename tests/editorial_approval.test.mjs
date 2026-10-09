import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

test('Postgres: editorial approval is mandatory and idempotent',async()=>{
 const modulePath=process.env.PGLITE_MODULE;
 assert.ok(modulePath,'Set PGLITE_MODULE to the pinned PGlite installation');
 const {PGlite}=await import(pathToFileURL(modulePath).href);
 const db=new PGlite();
 try {
  await db.exec(`create role anon;create role authenticated;create role service_role;
  create table public.newsletter_subscriptions(id uuid primary key,email text,status text,confirmed_at timestamptz);
  grant all on public.newsletter_subscriptions to service_role;`);
  await db.exec(await fs.readFile('supabase/migrations/20261007151727_newsletter_delivery_outbox.sql','utf8'));
  await db.exec('alter table public.newsletter_editions add column email_content jsonb;');
  await db.exec(await fs.readFile('supabase/migrations/20261008153824_publication_notifications.sql','utf8'));
  await db.exec(`insert into newsletter_subscriptions values('00000000-0000-0000-0000-000000000099','legacy@example.invalid','unsubscribed',now());
  insert into newsletter_editions(edition,url,title,summary) values(5,'/publicaciones/boletines/boletin-05-septiembre-2026/','Historical','Historical');
  insert into newsletter_deliveries(edition,subscription_id,state,accepted_at) values(5,'00000000-0000-0000-0000-000000000099','accepted',now());`);
  const migration=(await fs.readdir('supabase/migrations')).find(p=>p.endsWith('_editorial_diffusion_approval.sql'));
  await db.exec(await fs.readFile('supabase/migrations/'+migration,'utf8'));
  assert.equal((await db.query("select state from newsletter_editorial_publications where publication_key='/publicaciones/boletines/boletin-05-septiembre-2026/'")).rows[0].state,'diffused');
  assert.equal((await db.query("select count(*)::int n from newsletter_deliveries where edition=5 and state='accepted'")).rows[0].n,1);
  await db.exec(await fs.readFile('supabase/tests/editorial_diffusion.sql','utf8'));
 } finally {await db.close();}
});
