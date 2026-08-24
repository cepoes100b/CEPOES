-- CEPOES · Área Legislativa
-- Allowlist privada para convertir una autenticación válida en un perfil habilitado.
-- Las direcciones autorizadas se cargan directamente en Supabase y NO se versionan.

create table if not exists private.access_allowlist (
  email text primary key check (email = lower(email)),
  role text not null check (role in ('legisladora','asesor','investigador','admin')),
  active boolean not null default true,
  created_at timestamptz not null default now()
);

revoke all on private.access_allowlist from public, anon, authenticated;

create or replace function private.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = private, public, pg_catalog
as $$
declare
  approved_role text;
  approved_active boolean;
begin
  select a.role, a.active
    into approved_role, approved_active
  from private.access_allowlist a
  where a.email = lower(coalesce(new.email,''));

  insert into public.profiles (id, display_name, role, active)
  values (
    new.id,
    coalesce(nullif(new.raw_user_meta_data->>'name',''), split_part(coalesce(new.email,''),'@',1)),
    coalesce(approved_role,'asesor'),
    coalesce(approved_active,false)
  )
  on conflict (id) do update
    set role = excluded.role,
        active = excluded.active;
  return new;
end;
$$;

revoke all on function private.handle_new_user() from public, anon, authenticated;

-- Ejemplo operativo (NO versionar correos reales):
-- insert into private.access_allowlist(email,role,active)
-- values ('usuario@dominio.tld','admin',true)
-- on conflict (email) do update set role=excluded.role,active=excluded.active;
