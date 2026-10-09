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
rollback;
