-- CEPOES · Área Legislativa
-- Esquema privado para Supabase/Postgres.
-- IMPORTANTE: este archivo define estructura y permisos; nunca contiene datos internos reales.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  role text not null default 'asesor' check (role in ('legisladora','asesor','investigador','admin')),
  active boolean not null default false,
  commission_filters text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.expediente_analyses (
  id uuid primary key default gen_random_uuid(),
  expediente_numero text not null,
  document_kind text not null default 'proyecto' check (document_kind in ('proyecto','dictamen','despacho','sesion','otro')),
  title text not null,
  source_url text,
  executive_summary text not null default '',
  fiscal_impact text not null default '',
  territorial_impact text not null default '',
  legal_impact text not null default '',
  risks text not null default '',
  internal_priority text not null default 'media' check (internal_priority in ('critica','alta','media','baja')),
  recommendation text not null default 'sin_definir' check (recommendation in ('acompanar','acompanar_con_modificaciones','abstenerse','rechazar','sin_definir')),
  rationale text not null default '',
  proposed_amendments text not null default '',
  committee_questions text[] not null default '{}',
  intervention_arguments text not null default '',
  tags text[] not null default '{}',
  review_status text not null default 'borrador' check (review_status in ('borrador','revision','validado')),
  version integer not null default 1 check (version > 0),
  created_by uuid references public.profiles(id),
  updated_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists expediente_analyses_exp_idx on public.expediente_analyses(expediente_numero);
create index if not exists expediente_analyses_updated_idx on public.expediente_analyses(updated_at desc);

create table if not exists public.session_briefs (
  id uuid primary key default gen_random_uuid(),
  session_date date not null,
  title text not null,
  official_session_id text,
  executive_summary text not null default '',
  status text not null default 'borrador' check (status in ('borrador','revision','validado','cerrado')),
  created_by uuid references public.profiles(id),
  updated_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists session_briefs_date_idx on public.session_briefs(session_date desc);

create table if not exists public.session_brief_items (
  id uuid primary key default gen_random_uuid(),
  brief_id uuid not null references public.session_briefs(id) on delete cascade,
  item_order integer not null default 0,
  expediente_numero text,
  title text,
  internal_priority text not null default 'media' check (internal_priority in ('critica','alta','media','baja')),
  recommendation text not null default 'sin_definir' check (recommendation in ('acompanar','acompanar_con_modificaciones','abstenerse','rechazar','sin_definir')),
  key_argument text not null default '',
  controversy text not null default '',
  notes text not null default '',
  analysis_id uuid references public.expediente_analyses(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists session_brief_items_brief_idx on public.session_brief_items(brief_id,item_order);

create table if not exists public.project_bank (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  area text not null default '',
  problem_statement text not null default '',
  evidence text not null default '',
  policy_objective text not null default '',
  draft_text text not null default '',
  territorial_scope text not null default '',
  fiscal_notes text not null default '',
  legal_notes text not null default '',
  stage text not null default 'idea' check (stage in ('idea','diagnostico','anteproyecto','revision_juridica','listo_presentar','presentado','en_comision','sancionado','archivado')),
  owner_id uuid references public.profiles(id),
  owner_name text not null default '',
  tags text[] not null default '{}',
  created_by uuid references public.profiles(id),
  updated_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists project_bank_stage_idx on public.project_bank(stage,updated_at desc);

create table if not exists public.internal_comments (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null check (entity_type in ('analysis','brief','project')),
  entity_id uuid not null,
  body text not null check (length(trim(body)) > 0),
  created_by uuid not null references public.profiles(id),
  created_at timestamptz not null default now()
);
create index if not exists internal_comments_entity_idx on public.internal_comments(entity_type,entity_id,created_at);

-- Un usuario creado en Auth nace deshabilitado. Un administrador debe activarlo explícitamente.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id,display_name,role,active)
  values (
    new.id,
    coalesce(nullif(new.raw_user_meta_data->>'name',''), split_part(coalesce(new.email,''),'@',1)),
    'asesor',
    false
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

create or replace function public.is_active_member()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists(select 1 from public.profiles p where p.id = auth.uid() and p.active = true);
$$;

create or replace function public.current_app_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select p.role from public.profiles p where p.id = auth.uid() and p.active = true limit 1;
$$;

create or replace function public.can_write_intelligence()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(public.current_app_role() in ('admin','asesor','investigador'),false);
$$;

create or replace function public.is_app_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(public.current_app_role() = 'admin',false);
$$;

-- RLS: nada es accesible mediante la API sin una sesión válida y perfil activo.
alter table public.profiles enable row level security;
alter table public.expediente_analyses enable row level security;
alter table public.session_briefs enable row level security;
alter table public.session_brief_items enable row level security;
alter table public.project_bank enable row level security;
alter table public.internal_comments enable row level security;

-- Profiles
create policy "profiles_select_own_or_admin" on public.profiles for select to authenticated
using (id = auth.uid() or public.is_app_admin());
create policy "profiles_update_admin" on public.profiles for update to authenticated
using (public.is_app_admin()) with check (public.is_app_admin());

-- Analyses
create policy "analyses_select_members" on public.expediente_analyses for select to authenticated
using (public.is_active_member());
create policy "analyses_insert_writers" on public.expediente_analyses for insert to authenticated
with check (public.can_write_intelligence() and created_by = auth.uid() and updated_by = auth.uid());
create policy "analyses_update_writers" on public.expediente_analyses for update to authenticated
using (public.can_write_intelligence()) with check (public.can_write_intelligence() and updated_by = auth.uid());
create policy "analyses_delete_admin" on public.expediente_analyses for delete to authenticated
using (public.is_app_admin());

-- Session briefs
create policy "briefs_select_members" on public.session_briefs for select to authenticated
using (public.is_active_member());
create policy "briefs_insert_writers" on public.session_briefs for insert to authenticated
with check (public.can_write_intelligence() and created_by = auth.uid() and updated_by = auth.uid());
create policy "briefs_update_writers" on public.session_briefs for update to authenticated
using (public.can_write_intelligence()) with check (public.can_write_intelligence() and updated_by = auth.uid());
create policy "briefs_delete_admin" on public.session_briefs for delete to authenticated
using (public.is_app_admin());

create policy "brief_items_select_members" on public.session_brief_items for select to authenticated
using (public.is_active_member());
create policy "brief_items_insert_writers" on public.session_brief_items for insert to authenticated
with check (public.can_write_intelligence());
create policy "brief_items_update_writers" on public.session_brief_items for update to authenticated
using (public.can_write_intelligence()) with check (public.can_write_intelligence());
create policy "brief_items_delete_admin" on public.session_brief_items for delete to authenticated
using (public.is_app_admin());

-- Project bank
create policy "projects_select_members" on public.project_bank for select to authenticated
using (public.is_active_member());
create policy "projects_insert_writers" on public.project_bank for insert to authenticated
with check (public.can_write_intelligence() and created_by = auth.uid() and updated_by = auth.uid());
create policy "projects_update_writers" on public.project_bank for update to authenticated
using (public.can_write_intelligence()) with check (public.can_write_intelligence() and updated_by = auth.uid());
create policy "projects_delete_admin" on public.project_bank for delete to authenticated
using (public.is_app_admin());

-- Comments: todos los miembros activos pueden comentar; sólo admin borra.
create policy "comments_select_members" on public.internal_comments for select to authenticated
using (public.is_active_member());
create policy "comments_insert_members" on public.internal_comments for insert to authenticated
with check (public.is_active_member() and created_by = auth.uid());
create policy "comments_delete_admin" on public.internal_comments for delete to authenticated
using (public.is_app_admin());

-- Mantener timestamps de edición del lado servidor.
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end; $$;

drop trigger if exists touch_profiles on public.profiles;
create trigger touch_profiles before update on public.profiles for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_analyses on public.expediente_analyses;
create trigger touch_analyses before update on public.expediente_analyses for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_briefs on public.session_briefs;
create trigger touch_briefs before update on public.session_briefs for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_brief_items on public.session_brief_items;
create trigger touch_brief_items before update on public.session_brief_items for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_project_bank on public.project_bank;
create trigger touch_project_bank before update on public.project_bank for each row execute procedure public.touch_updated_at();

-- No otorgar privilegios al rol anónimo sobre la capa privada.
revoke all on public.profiles from anon;
revoke all on public.expediente_analyses from anon;
revoke all on public.session_briefs from anon;
revoke all on public.session_brief_items from anon;
revoke all on public.project_bank from anon;
revoke all on public.internal_comments from anon;

grant select on public.profiles to authenticated;
grant select,insert,update,delete on public.expediente_analyses to authenticated;
grant select,insert,update,delete on public.session_briefs to authenticated;
grant select,insert,update,delete on public.session_brief_items to authenticated;
grant select,insert,update,delete on public.project_bank to authenticated;
grant select,insert,delete on public.internal_comments to authenticated;
