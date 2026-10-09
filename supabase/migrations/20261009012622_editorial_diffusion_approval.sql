-- Diffusion is an explicit editorial action, never a deployment side effect.
create table public.newsletter_editorial_publications (
 publication_key text primary key references public.newsletter_publications(publication_key),
 state text not null default 'published' check(state in ('draft','review','published','ready','diffused')),
 catalog_payload jsonb,
 approved_at timestamptz,
 approved_by text,
 authorization_reference text,
 diffused_at timestamptz,
 check(state not in ('ready') or (approved_at is not null and approved_by is not null and authorization_reference is not null))
);
alter table public.newsletter_editorial_publications enable row level security;
revoke all on public.newsletter_editorial_publications from public,anon,authenticated;
grant all on public.newsletter_editorial_publications to service_role;
insert into public.newsletter_editorial_publications(publication_key,state,catalog_payload,diffused_at)
select p.publication_key,case when exists(select 1 from public.newsletter_deliveries d where d.publication_key=p.publication_key and d.state='accepted') then 'diffused' else 'published' end,p.payload,
 (select max(d.accepted_at) from public.newsletter_deliveries d where d.publication_key=p.publication_key)
from public.newsletter_publications p;
-- Preserve prior history and uncertain deliveries; do not automatically resume them.
update public.newsletter_deliveries set state='review',lease_token=null,lease_until=null where state in ('pending','sending');

create or replace function public.newsletter_enqueue_publications(p_publications jsonb)
returns void language plpgsql security invoker set search_path='' as $$
declare item jsonb; key text;
begin
 perform pg_advisory_xact_lock(70310721);
 if jsonb_typeof(p_publications) is distinct from 'array' or jsonb_array_length(p_publications)>2000 then raise exception 'invalid_publications'; end if;
 for item in select value from jsonb_array_elements(p_publications) loop
  key=item->>'key';
  if key is null or key<>coalesce(item->>'url','') or key !~ '^/[a-z0-9/-]+/$' or key like '%//%'
   or coalesce(item->>'kind','') not in ('boletin','informe','analisis','prensa','aviso')
   or coalesce(length(item->>'title'),0)=0 then raise exception 'invalid_publication'; end if;
  insert into public.newsletter_publications(publication_key) values(key) on conflict do nothing;
  insert into public.newsletter_editorial_publications(publication_key,catalog_payload) values(key,item)
  on conflict(publication_key) do update set catalog_payload=excluded.catalog_payload;
 end loop;
 -- Catalog discovery only. It must never create a delivery.
end;$$;

create function public.newsletter_approve_publication(p_key text,p_expected_payload jsonb,p_approved_by text,p_authorization_reference text)
returns integer language plpgsql security invoker set search_path='' as $$
declare piece public.newsletter_editorial_publications; jobs integer;
begin
 perform pg_advisory_xact_lock(70310721);
 if length(trim(coalesce(p_approved_by,'')))<3 or length(trim(coalesce(p_authorization_reference,'')))<10 then raise exception 'explicit_authorization_required'; end if;
 select * into piece from public.newsletter_editorial_publications where publication_key=p_key for update;
 if not found or piece.catalog_payload is null then raise exception 'published_catalog_required'; end if;
 if piece.state in ('ready','diffused') then return 0; end if;
 if piece.state<>'published' then raise exception 'publication_not_ready'; end if;
 if piece.catalog_payload is distinct from p_expected_payload then raise exception 'publication_changed_review_again'; end if;
 if exists(select 1 from public.newsletter_deliveries where publication_key=p_key)
  or exists(select 1 from public.newsletter_editions e join public.newsletter_deliveries d on d.edition=e.edition where e.url=p_key)
 then raise exception 'previous_distribution_requires_separate_review'; end if;
 update public.newsletter_publications set payload=p_expected_payload where publication_key=p_key;
 update public.newsletter_editorial_publications set state='ready',approved_at=now(),approved_by=p_approved_by,authorization_reference=p_authorization_reference where publication_key=p_key;
 insert into public.newsletter_deliveries(publication_key,subscription_id)
 select p_key,id from public.newsletter_subscriptions where status='active' and confirmed_at is not null;
 get diagnostics jobs=row_count;
 return jobs;
end;$$;

create or replace function public.newsletter_enqueue_edition(p_edition integer,p_url text,p_title text,p_summary text)
returns void language plpgsql security invoker set search_path='' as $$
begin raise exception 'editorial_approval_required'; end;$$;

create function public.newsletter_finalize_editorial()
returns void language sql security invoker set search_path='' as $$
 update public.newsletter_editorial_publications e set state='diffused',diffused_at=now()
 where e.state='ready' and not exists(select 1 from public.newsletter_deliveries d where d.publication_key=e.publication_key and d.state not in ('accepted','cancelled'));
$$;

revoke all on function public.newsletter_approve_publication(text,jsonb,text,text),public.newsletter_finalize_editorial() from public,anon,authenticated;
grant execute on function public.newsletter_approve_publication(text,jsonb,text,text),public.newsletter_finalize_editorial() to service_role;

create or replace function public.newsletter_claim_deliveries(p_limit integer default 10)
returns setof public.newsletter_deliveries language plpgsql security invoker set search_path='' as $$
declare budget integer;
begin
 perform pg_advisory_xact_lock(70310721);
 update public.newsletter_deliveries set state='review',lease_token=null,lease_until=null
 where state in ('pending','sending') and first_attempt_at<now()-interval '18 hours';
 select greatest(0,50-count(*)::integer) into budget from public.newsletter_deliveries where first_attempt_at>=date_trunc('day',now());
 return query with eligible as (
 select d.delivery_id,d.first_attempt_at,
 sum(case when d.first_attempt_at is null then 1 else 0 end) over (order by d.first_attempt_at nulls last,d.delivery_id) as new_position
 from public.newsletter_deliveries d join public.newsletter_subscriptions s on s.id=d.subscription_id
 join public.newsletter_editorial_publications e on e.publication_key=d.publication_key and e.state='ready'
 where s.status='active' and s.confirmed_at is not null
 and ((d.state='pending' and d.next_attempt_at<=now()) or (d.state='sending' and d.lease_until<now()))
 ), candidates as (
 select e.delivery_id from eligible e where e.first_attempt_at is not null or e.new_position<=budget
 order by e.first_attempt_at nulls last,e.delivery_id limit least(greatest(p_limit,0),10)
 ) update public.newsletter_deliveries d set state='sending',attempts=d.attempts+1,
 first_attempt_at=coalesce(d.first_attempt_at,now()),lease_until=now()+interval '10 minutes',lease_token=gen_random_uuid()
 from candidates c where c.delivery_id=d.delivery_id returning d.*;
end;$$;

