begin;
create table public.newsletter_editions (
 edition integer primary key check(edition>0),url text not null unique,title text not null,summary text not null,
 detected_at timestamptz not null default now()
);
create table public.newsletter_deliveries (
 edition integer not null references public.newsletter_editions(edition),
 subscription_id uuid not null references public.newsletter_subscriptions(id),
 state text not null default 'pending' check(state in('pending','sending','accepted','cancelled','review')),
 attempts integer not null default 0, first_attempt_at timestamptz,
 next_attempt_at timestamptz not null default now(),lease_until timestamptz,lease_token uuid,
 provider_id text,accepted_at timestamptz,
 primary key(edition,subscription_id)
);
alter table public.newsletter_editions enable row level security;
alter table public.newsletter_deliveries enable row level security;
revoke all on public.newsletter_editions,public.newsletter_deliveries from anon,authenticated;
grant all on public.newsletter_editions,public.newsletter_deliveries to service_role;

create function public.newsletter_enqueue_edition(p_edition integer,p_url text,p_title text,p_summary text)
returns void language plpgsql security invoker set search_path='' as $$
begin
 -- First activation begins with the next issue; never broadcast the archive.
 if p_edition<=5 then return; end if;
 insert into public.newsletter_editions(edition,url,title,summary) values(p_edition,p_url,p_title,p_summary)
 on conflict(edition) do nothing;
 if not found then return; end if;
 insert into public.newsletter_deliveries(edition,subscription_id)
 select p_edition,id from public.newsletter_subscriptions where status='active' and confirmed_at is not null;
end;$$;
create function public.newsletter_claim_deliveries(p_limit integer default 10)
returns setof public.newsletter_deliveries language plpgsql security invoker set search_path='' as $$
declare budget integer;
begin
 -- Serializes quota reservations across overlapping runs.
 perform pg_advisory_xact_lock(70310721);
 update public.newsletter_deliveries set state='review',lease_token=null,lease_until=null
 where state in('pending','sending') and first_attempt_at<now()-interval '18 hours';
 select greatest(0,50-count(*)::integer) into budget from public.newsletter_deliveries
 where first_attempt_at>=date_trunc('day',now());
 return query with eligible as (
 select d.edition,d.subscription_id,d.first_attempt_at,
 sum(case when d.first_attempt_at is null then 1 else 0 end) over
 (order by d.first_attempt_at nulls last,d.edition,d.subscription_id) as new_position
 from public.newsletter_deliveries d join public.newsletter_subscriptions s on s.id=d.subscription_id
 where s.status='active' and ((d.state='pending' and d.next_attempt_at<=now()) or (d.state='sending' and d.lease_until<now()))
 ), candidates as (
 select e.edition,e.subscription_id from eligible e where e.first_attempt_at is not null or e.new_position<=budget
 order by e.first_attempt_at nulls last,e.edition,e.subscription_id limit least(greatest(p_limit,0),10)
 ) update public.newsletter_deliveries d set state='sending',attempts=d.attempts+1,
 first_attempt_at=coalesce(d.first_attempt_at,now()),lease_until=now()+interval '10 minutes',lease_token=gen_random_uuid()
 from candidates c where c.edition=d.edition and c.subscription_id=d.subscription_id returning d.*;
end;$$;
create function public.newsletter_finish_delivery(p_edition integer,p_subscription uuid,p_lease uuid,p_state text,p_provider_id text default null)
returns void language plpgsql security invoker set search_path='' as $$
begin
 if p_state not in('pending','accepted','cancelled') then raise exception 'invalid_delivery_state'; end if;
 if p_state='accepted' and p_provider_id is null then raise exception 'missing_provider_id'; end if;
 update public.newsletter_deliveries set state=p_state,provider_id=p_provider_id,
 accepted_at=case when p_state='accepted' then now() else null end,
 next_attempt_at=now()+interval '1 hour',lease_until=null,lease_token=null
 where edition=p_edition and subscription_id=p_subscription and state='sending' and lease_token=p_lease;
 if not found then raise exception 'stale_delivery_lease'; end if;
end;$$;
revoke all on function public.newsletter_enqueue_edition(integer,text,text,text),
public.newsletter_claim_deliveries(integer),public.newsletter_finish_delivery(integer,uuid,uuid,text,text) from public,anon,authenticated;
grant execute on function public.newsletter_enqueue_edition(integer,text,text,text),
public.newsletter_claim_deliveries(integer),public.newsletter_finish_delivery(integer,uuid,uuid,text,text) to service_role;
commit;
