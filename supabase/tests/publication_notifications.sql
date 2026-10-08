begin;
-- Test addresses never leave the local database; transaction is rolled back.
insert into public.newsletter_subscriptions(id,email,status,confirmed_at) values
 ('00000000-0000-0000-0000-000000000101','active@example.invalid','active',now()),
 ('00000000-0000-0000-0000-000000000102','pending@example.invalid','pending',null),
 ('00000000-0000-0000-0000-000000000103','unsubscribed@example.invalid','unsubscribed',now());
do $$
declare p jsonb; j public.newsletter_deliveries; frozen text; n integer;
begin
 -- Baseline archive never broadcasts, even after a content edit.
 p='[{"key":"/publicaciones/boletines/boletin-05-septiembre-2026/","url":"/publicaciones/boletines/boletin-05-septiembre-2026/","kind":"boletin","title":"Archivo","summary":"Resumen","date":"2026-09-01"}]';
 perform public.newsletter_enqueue_publications(p);
 if exists(select 1 from public.newsletter_deliveries where publication_key=p->0->>'key') then raise exception 'archive_was_enqueued'; end if;
 p='[{"key":"/publicaciones/notas/qa-new/","url":"/publicaciones/notas/qa-new/","kind":"analisis","title":"Primera versión","summary":"Resumen","date":"2026-10-08"}]';
 perform public.newsletter_enqueue_publications(p);
 perform public.newsletter_enqueue_publications(jsonb_set(p,'{0,title}','"Edición posterior"'));
 select count(*) into n from public.newsletter_deliveries where publication_key='/publicaciones/notas/qa-new/';
 if n<>1 then raise exception 'duplicate_or_unconfirmed_recipient'; end if;
 select payload->>'title' into frozen from public.newsletter_publications where publication_key='/publicaciones/notas/qa-new/';
 if frozen<>'Primera versión' then raise exception 'snapshot_changed'; end if;
 select * into j from public.newsletter_claim_deliveries(5) where publication_key='/publicaciones/notas/qa-new/';
 if j.delivery_id is null then raise exception 'new_publication_not_claimed'; end if;
 perform public.newsletter_finish_publication_delivery(j.delivery_id,j.lease_token,'accepted','local-provider');
 begin
  perform public.newsletter_finish_publication_delivery(j.delivery_id,j.lease_token,'accepted','local-provider');
  raise exception 'accepted_stale_lease';
 exception when others then if sqlerrm<>'stale_delivery_lease' then raise; end if; end;
 -- A new recipient after publication receives no historic job.
 insert into public.newsletter_subscriptions(id,email,status,confirmed_at) values('00000000-0000-0000-0000-000000000104','later@example.invalid','active',now());
 perform public.newsletter_enqueue_publications(p);
 if exists(select 1 from public.newsletter_deliveries where subscription_id='00000000-0000-0000-0000-000000000104') then raise exception 'late_subscriber_backfill'; end if;
 -- Unsubscribing blocks already queued content.
 perform public.newsletter_enqueue_publications('[{"key":"/prensa/qa-notice/","url":"/prensa/qa-notice/","kind":"aviso","title":"Aviso","summary":"Resumen","date":"2026-10-08"}]');
 update public.newsletter_subscriptions set status='unsubscribed' where id in('00000000-0000-0000-0000-000000000101','00000000-0000-0000-0000-000000000104');
 if exists(select 1 from public.newsletter_claim_deliveries(10)) then raise exception 'unsubscribed_claimed'; end if;
 -- RLS and grants keep recipient queues private.
 if has_table_privilege('anon','public.newsletter_publications','select') or has_table_privilege('authenticated','public.newsletter_deliveries','select') then raise exception 'public_table_access'; end if;
 if has_function_privilege('anon','public.newsletter_enqueue_publications(jsonb)','execute') then raise exception 'public_rpc_access'; end if;
end;$$;
rollback;

begin;
insert into public.newsletter_subscriptions(id,email,status,confirmed_at)
select md5('quota-'||g)::uuid,'quota-'||g||'@example.invalid','active',now() from generate_series(1,60) g;
select public.newsletter_enqueue_edition(7,'/publicaciones/boletines/boletin-07-noviembre-2026/','Boletín','Resumen');
select public.newsletter_enqueue_publications('[{"key":"/prensa/qa-quota/","url":"/prensa/qa-quota/","kind":"prensa","title":"Nota","summary":"Resumen","date":"2026-10-08"}]');
do $$
declare j public.newsletter_deliveries; count_jobs integer=0; batch integer;
begin
 loop
  batch=0;
  for j in select * from public.newsletter_claim_deliveries(10) loop
   count_jobs=count_jobs+1;batch=batch+1;
   perform public.newsletter_finish_publication_delivery(j.delivery_id,j.lease_token,'accepted','local-provider');
  end loop;
  exit when batch=0;
  if count_jobs>50 then raise exception 'daily_quota_exceeded'; end if;
 end loop;
 if count_jobs<>50 then raise exception 'unexpected_shared_quota'; end if;
 if (select count(*) from public.newsletter_deliveries where state='pending')<>70 then raise exception 'queued_deliveries_lost'; end if;
 begin
  perform public.newsletter_enqueue_publications('[{"key":"/prensa/qa-atomic/","url":"/prensa/qa-atomic/","kind":"prensa","title":"Nota"},{"key":"/prensa/qa-invalid/","url":"/prensa/qa-invalid/","title":"Sin tipo"}]');
  raise exception 'invalid_feed_accepted';
 exception when others then if sqlerrm<>'invalid_publication' then raise; end if; end;
 if exists(select 1 from public.newsletter_publications where publication_key='/prensa/qa-atomic/') then raise exception 'partial_feed_written'; end if;
end;$$;
rollback;
