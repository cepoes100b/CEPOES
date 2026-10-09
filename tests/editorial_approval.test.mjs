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
  const migration=(await fs.readdir('supabase/migrations')).find(p=>p.endsWith('_editorial_diffusion_approval.sql'));
  await db.exec(await fs.readFile('supabase/migrations/'+migration,'utf8'));
  await db.exec(await fs.readFile('supabase/tests/editorial_diffusion.sql','utf8'));
 } finally {await db.close();}
});
