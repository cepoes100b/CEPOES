begin;
insert into public.newsletter_subscriptions(id,email,status,confirmed_at) values
 ('00000000-0000-0000-0000-000000000001','qa@example.invalid','active',now()),
 ('00000000-0000-0000-0000-000000000002','pending@example.invalid','pending',null);
do $$
declare payload jsonb='{"key":"/qa/editorial/","url":"/qa/editorial/","kind":"informe","title":"QA","summary":"Original","date":"2026-10-09"}'; jobs integer;
begin
 perform public.newsletter_enqueue_publications(jsonb_build_array(payload));
 perform public.newsletter_enqueue_publications(jsonb_build_array(payload));
 if exists(select 1 from public.newsletter_deliveries where publication_key='/qa/editorial/') then raise exception 'discovery_sent_email'; end if;
 begin
  perform public.newsletter_approve_publication('/qa/editorial/',payload,'','');
  raise exception 'missing_approval_accepted';
 exception when others then if sqlerrm<>'explicit_authorization_required' then raise; end if; end;
 begin
  perform public.newsletter_approve_publication('/qa/editorial/',jsonb_set(payload,'{title}','"Changed"'),'Editor','Orden expresa QA');
  raise exception 'stale_snapshot_accepted';
 exception when others then if sqlerrm<>'publication_changed_review_again' then raise; end if; end;
 jobs=public.newsletter_approve_publication('/qa/editorial/',payload,'Editor','Orden expresa QA');
 if jobs<>1 then raise exception 'wrong_recipients'; end if;
 if public.newsletter_approve_publication('/qa/editorial/',payload,'Editor','Orden expresa QA')<>0 then raise exception 'duplicate_approval'; end if;
 perform public.newsletter_enqueue_publications(jsonb_build_array(jsonb_set(payload,'{summary}','"Edited"')));
 if (select p.payload->>'summary' from public.newsletter_publications p where publication_key='/qa/editorial/')<>'Original' then raise exception 'approved_snapshot_changed'; end if;
 if (select count(*) from public.newsletter_claim_deliveries(5))<>1 then raise exception 'ready_not_claimed'; end if;
 update public.newsletter_deliveries set state='accepted',accepted_at=now() where publication_key='/qa/editorial/';
 perform public.newsletter_finalize_editorial();
 if (select state from public.newsletter_editorial_publications where publication_key='/qa/editorial/')<>'diffused' then raise exception 'not_finalized'; end if;
 if public.newsletter_approve_publication('/qa/editorial/',payload,'Editor','Otra orden QA')<>0 then raise exception 'diffused_resent'; end if;
 if has_function_privilege('anon','public.newsletter_approve_publication(text,jsonb,text,text)','execute') then raise exception 'public_approval'; end if;
 begin
  perform public.newsletter_enqueue_edition(7,'/qa/boletin/','QA','QA');
  raise exception 'legacy_auto_enqueue';
 exception when others then if sqlerrm<>'editorial_approval_required' then raise; end if; end;
 -- Even a stray queue row cannot be claimed without editorial approval.
 payload=jsonb_set(jsonb_set(payload,'{key}','"/qa/not-approved/"'),'{url}','"/qa/not-approved/"');
 perform public.newsletter_enqueue_publications(jsonb_build_array(payload));
 insert into public.newsletter_deliveries(publication_key,subscription_id) values('/qa/not-approved/','00000000-0000-0000-0000-000000000001');
 if exists(select 1 from public.newsletter_claim_deliveries(5)) then raise exception 'unapproved_claim'; end if;
end;$$;
-- Catalog-only maintenance preserves all approval fields and existing deliveries.
do $$
declare item jsonb; before_approval jsonb; before_snapshot jsonb; before_deliveries jsonb; target text;
begin
 foreach target in array array['/qa/maintenance-ready/','/qa/maintenance-diffused/'] loop
  item=jsonb_build_object('key',target,'url',target,'kind','informe','title','Local QA','summary','Approved fixture','date','2026-10-15');
  perform public.newsletter_enqueue_publications(jsonb_build_array(item));
  perform public.newsletter_approve_publication(target,item,'Local editor','Isolated QA fixture authorization');
  if target='/qa/maintenance-diffused/' then
   update public.newsletter_deliveries set state='accepted',accepted_at=now() where publication_key=target;
   perform public.newsletter_finalize_editorial();
  end if;
  select to_jsonb(e)-'catalog_payload' into before_approval from public.newsletter_editorial_publications e where publication_key=target;
  select to_jsonb(p) into before_snapshot from public.newsletter_publications p where publication_key=target;
  select jsonb_agg(to_jsonb(d) order by delivery_id) into before_deliveries from public.newsletter_deliveries d;
  item=jsonb_set(jsonb_set(item,'{date}','null'::jsonb),'{summary}','"Updated catalog only"'::jsonb);
  perform public.newsletter_enqueue_publications(jsonb_build_array(item));
  perform public.newsletter_enqueue_publications(jsonb_build_array(item));
  if (select catalog_payload from public.newsletter_editorial_publications where publication_key=target) is distinct from item then raise exception 'catalog_not_updated'; end if;
  if (select to_jsonb(e)-'catalog_payload' from public.newsletter_editorial_publications e where publication_key=target) is distinct from before_approval then raise exception 'approval_changed'; end if;
  if (select to_jsonb(p) from public.newsletter_publications p where publication_key=target) is distinct from before_snapshot then raise exception 'snapshot_changed'; end if;
  if (select jsonb_agg(to_jsonb(d) order by delivery_id) from public.newsletter_deliveries d) is distinct from before_deliveries then raise exception 'deliveries_changed'; end if;
 end loop;
end;$$;
rollback;
