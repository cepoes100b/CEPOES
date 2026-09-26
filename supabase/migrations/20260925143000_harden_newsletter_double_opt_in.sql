begin;

alter table public.newsletter_subscriptions
  drop constraint if exists newsletter_subscriptions_status_check;

alter table public.newsletter_subscriptions
  add constraint newsletter_subscriptions_status_check
  check (status = any (array['pending'::text, 'active'::text, 'unsubscribed'::text]));

alter table public.newsletter_subscriptions
  add column if not exists confirmation_token_hash text,
  add column if not exists confirmation_expires_at timestamptz,
  add column if not exists confirmed_at timestamptz,
  add column if not exists last_requested_at timestamptz not null default now(),
  add column if not exists request_count integer not null default 1;

alter table public.newsletter_subscriptions
  drop constraint if exists newsletter_subscriptions_request_count_check;

alter table public.newsletter_subscriptions
  add constraint newsletter_subscriptions_request_count_check
  check (request_count > 0);

update public.newsletter_subscriptions
set confirmed_at = coalesce(confirmed_at, consent_at)
where status = 'active';

create index if not exists newsletter_subscriptions_pending_expiry_idx
  on public.newsletter_subscriptions (confirmation_expires_at)
  where status = 'pending';

drop policy if exists public_can_subscribe on public.newsletter_subscriptions;
revoke insert on table public.newsletter_subscriptions from anon;

create table if not exists public.newsletter_subscription_rate_limits (
  fingerprint_hash text not null,
  window_start timestamptz not null,
  attempts integer not null default 1 check (attempts > 0),
  updated_at timestamptz not null default now(),
  primary key (fingerprint_hash, window_start)
);

comment on table public.newsletter_subscription_rate_limits is
  'Contadores horarios antiabuso. Conserva únicamente una huella HMAC no reversible de la IP.';

alter table public.newsletter_subscription_rate_limits enable row level security;
revoke all on table public.newsletter_subscription_rate_limits from anon, authenticated;
grant select, insert, update, delete on table public.newsletter_subscription_rate_limits to service_role;

drop policy if exists service_role_manage_newsletter_rate_limits
  on public.newsletter_subscription_rate_limits;

create policy service_role_manage_newsletter_rate_limits
  on public.newsletter_subscription_rate_limits
  for all
  to service_role
  using (true)
  with check (true);

create or replace function public.newsletter_check_rate_limit(
  p_fingerprint_hash text,
  p_window_start timestamptz,
  p_limit integer default 5
)
returns boolean
language plpgsql
security invoker
set search_path = ''
as $$
declare
  current_attempts integer;
begin
  if p_fingerprint_hash is null
     or length(p_fingerprint_hash) <> 64
     or p_limit < 1
     or p_limit > 100 then
    return false;
  end if;

  insert into public.newsletter_subscription_rate_limits(
    fingerprint_hash,
    window_start,
    attempts,
    updated_at
  )
  values (
    p_fingerprint_hash,
    date_trunc('hour', p_window_start),
    1,
    now()
  )
  on conflict (fingerprint_hash, window_start)
  do update set
    attempts = public.newsletter_subscription_rate_limits.attempts + 1,
    updated_at = now()
  returning attempts into current_attempts;

  return current_attempts <= p_limit;
end;
$$;

revoke all on function public.newsletter_check_rate_limit(text, timestamptz, integer)
  from public, anon, authenticated;
grant execute on function public.newsletter_check_rate_limit(text, timestamptz, integer)
  to service_role;

commit;
