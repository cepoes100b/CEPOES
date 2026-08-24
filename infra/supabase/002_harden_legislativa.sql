-- Endurecimiento aplicado al proyecto CEPOES después de la auditoría de Supabase.
create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

-- Helpers internos fuera del API público.
create or replace function private.is_active_member()
returns boolean language sql stable security definer
set search_path = public, pg_catalog
as $$ select exists(select 1 from public.profiles p where p.id = auth.uid() and p.active = true); $$;

create or replace function private.current_app_role()
returns text language sql stable security definer
set search_path = public, pg_catalog
as $$ select p.role from public.profiles p where p.id = auth.uid() and p.active = true limit 1; $$;

create or replace function private.can_write_intelligence()
returns boolean language sql stable security definer
set search_path = private, public, pg_catalog
as $$ select coalesce(private.current_app_role() in ('admin','asesor','investigador'),false); $$;

create or replace function private.is_app_admin()
returns boolean language sql stable security definer
set search_path = private, public, pg_catalog
as $$ select coalesce(private.current_app_role() = 'admin',false); $$;

create or replace function private.handle_new_user()
returns trigger language plpgsql security definer
set search_path = public, pg_catalog
as $$
begin
  insert into public.profiles (id,display_name,role,active)
  values (new.id, coalesce(nullif(new.raw_user_meta_data->>'name',''), split_part(coalesce(new.email,''),'@',1)), 'asesor', false)
  on conflict (id) do nothing;
  return new;
end;
$$;

create or replace function private.touch_updated_at()
returns trigger language plpgsql set search_path = pg_catalog
as $$ begin new.updated_at = now(); return new; end; $$;

revoke all on all functions in schema private from public, anon;
grant execute on function private.is_active_member() to authenticated;
grant execute on function private.current_app_role() to authenticated;
grant execute on function private.can_write_intelligence() to authenticated;
grant execute on function private.is_app_admin() to authenticated;

-- Nota: la migración aplicada en Supabase reemplaza las políticas y triggers iniciales
-- para que apunten a estas funciones privadas y elimina las versiones public.* anteriores.
