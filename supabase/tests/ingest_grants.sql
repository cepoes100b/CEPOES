-- Ejecutar exclusivamente en PostgreSQL descartable vacío (no en Supabase real).
-- Sin credenciales, extensiones descargadas, cambios de defaults ni datos reales.
\set ON_ERROR_STOP on
begin;
-- Fallar antes de modificar si parece una instalación existente.
do $$ begin
  if to_regnamespace('auth') is not null
     or exists(select 1 from pg_roles where rolname in ('anon','authenticated','service_role'))
     or exists(select 1 from pg_class where relnamespace='public'::regnamespace and relkind='r')
     or exists(select 1 from pg_default_acl) then
    raise exception 'Se requiere un clúster vacío y descartable, sin roles Supabase ni default ACL';
  end if;
end $$;
create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;
grant usage on schema public to anon, authenticated, service_role;
create schema auth;
create table auth.users(id uuid primary key, email text, raw_user_meta_data jsonb);
create function auth.uid() returns uuid language sql stable as $$ select null::uuid $$;
grant usage on schema auth to anon, authenticated, service_role;
\ir ../../infra/supabase/legislativa.sql
\ir ../../infra/supabase/002_harden_legislativa.sql
\ir ../../infra/supabase/004_analisis_legislativo_automatico.sql
\ir ../../infra/supabase/005_focus_analisis_rls.sql
\ir ../../infra/supabase/006_guardrails_analisis_automatico.sql
\ir ../../infra/supabase/007_analisis_legislativo_v3.sql
\ir ../../infra/supabase/008_prensa_editorial.sql

do $$ declare t text; p text; expected boolean; begin
  foreach t in array array['expediente_analyses','press_notes'] loop
    foreach p in array array['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] loop
      expected := p in ('SELECT','INSERT') or (t='expediente_analyses' and p='UPDATE');
      if has_table_privilege('service_role','public.'||t,p) <> expected then
        raise exception 'Grant incorrecto: % %', t, p;
      end if;
    end loop;
    if not (select relrowsecurity from pg_class where oid=('public.'||t)::regclass) then
      raise exception 'RLS desactivado: %', t;
    end if;
    foreach p in array array['SELECT','INSERT','UPDATE','DELETE'] loop
      if not has_table_privilege('authenticated','public.'||t,p) then
        raise exception 'Permiso authenticated ausente: % %', t, p;
      end if;
    end loop;
  end loop;
  if has_table_privilege('anon','public.expediente_analyses','SELECT')
     or not has_table_privilege('anon','public.press_notes','SELECT') then
    raise exception 'Permisos anon incorrectos';
  end if;
end $$;

set local role service_role;
insert into public.expediente_analyses(expediente_numero,title,analysis_origin,automation_source_hash)
values ('TEST-1','Fixture sintético','automatic',repeat('a',64)) returning id,version;
select id,version from public.expediente_analyses where expediente_numero='TEST-1';
update public.expediente_analyses set is_current=false where expediente_numero='TEST-1';
do $$ begin
  if not exists(select 1 from public.expediente_analyses where expediente_numero='TEST-1' and not is_current) then
    raise exception 'UPDATE no modificó la fila';
  end if;
  begin
    delete from public.expediente_analyses where expediente_numero='TEST-1';
    raise exception 'DELETE análisis permitido inesperadamente';
  exception when insufficient_privilege then null;
  end;
end $$;
insert into public.press_notes(slug,topic,title,source_hash)
values ('fixture-grants','test','Fixture sintético',repeat('b',64));
select id,status,origin,source_hash from public.press_notes where source_hash=repeat('b',64);
select id,status,origin,source_hash from public.press_notes where slug='fixture-grants';
do $$ begin
  begin
    update public.press_notes set title='No permitido' where slug='fixture-grants';
    raise exception 'UPDATE prensa permitido inesperadamente';
  exception when insufficient_privilege then null;
  end;
  begin
    delete from public.press_notes where slug='fixture-grants';
    raise exception 'DELETE prensa permitido inesperadamente';
  exception when insufficient_privilege then null;
  end;
end $$;
set local role anon;
do $$ begin
  if exists(select 1 from public.press_notes where slug='fixture-grants') then
    raise exception 'RLS expuso un borrador a anon';
  end if;
  begin
    perform id from public.expediente_analyses;
    raise exception 'anon accedió a análisis';
  exception when insufficient_privilege then null;
  end;
end $$;
set local role authenticated;
do $$ begin
  if exists(select 1 from public.expediente_analyses)
     or exists(select 1 from public.press_notes) then
    raise exception 'RLS expuso filas sin perfil activo';
  end if;
end $$;
reset role;
rollback;
\echo 'PASS: grants mínimos, operaciones permitidas/denegadas y RLS; rollback completo'
