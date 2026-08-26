create table if not exists public.newsletter_subscriptions (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  status text not null default 'active' check (status in ('active', 'unsubscribed')),
  source text not null default 'home' check (source in ('home')),
  privacy_version text not null,
  consent_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint newsletter_email_format check (
    char_length(email) between 5 and 254
    and email = lower(btrim(email))
    and email ~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$'
  )
);

create unique index if not exists newsletter_subscriptions_email_unique
  on public.newsletter_subscriptions (lower(email));

alter table public.newsletter_subscriptions enable row level security;

revoke all on table public.newsletter_subscriptions from anon, authenticated;
grant insert on table public.newsletter_subscriptions to anon;
grant select, insert, update on table public.newsletter_subscriptions to authenticated;

drop policy if exists "public_can_subscribe" on public.newsletter_subscriptions;
create policy "public_can_subscribe"
  on public.newsletter_subscriptions for insert to anon
  with check (
    status = 'active'
    and source = 'home'
    and consent_at is not null
    and privacy_version = '2026-08'
  );

drop policy if exists "admins_manage_newsletter" on public.newsletter_subscriptions;
create policy "admins_manage_newsletter"
  on public.newsletter_subscriptions for all to authenticated
  using ((select private.is_app_admin()))
  with check ((select private.is_app_admin()));

comment on table public.newsletter_subscriptions is
  'Consentimientos de suscripción al boletín de CEPOES; acceso restringido a administradores.';
