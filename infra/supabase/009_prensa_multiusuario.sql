-- CEPOES · Sistema editorial multiusuario de Prensa.

create table if not exists public.press_members (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  press_role text not null check (press_role in ('redactor','revisor','editor','admin')),
  active boolean not null default true,
  added_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.press_members enable row level security;
grant select on public.press_members to authenticated;
revoke insert, update, delete on public.press_members from anon, authenticated;

insert into public.press_members(user_id,press_role,active)
select id,'admin',active from public.profiles where role='admin'
on conflict(user_id) do update set press_role='admin',active=excluded.active,updated_at=now();

create or replace function private.current_press_role()
returns text language sql stable security definer
set search_path=''
as $$
  select pm.press_role from public.press_members pm
  where pm.user_id=(select auth.uid()) and pm.active and (select auth.uid()) is not null
$$;
revoke all on function private.current_press_role() from public,anon,authenticated;
grant execute on function private.current_press_role() to authenticated;

create or replace function private.press_role_rank()
returns integer language sql stable security invoker
set search_path=''
as $$
  select case private.current_press_role()
    when 'redactor' then 1 when 'revisor' then 2 when 'editor' then 3 when 'admin' then 4 else 0 end
$$;
revoke all on function private.press_role_rank() from public,anon,authenticated;
grant execute on function private.press_role_rank() to authenticated;

drop policy if exists "press_members_read" on public.press_members;
create policy "press_members_read" on public.press_members for select to authenticated
using(private.press_role_rank()>=1);
drop policy if exists "profiles_select_press_team" on public.profiles;
create policy "profiles_select_press_team" on public.profiles for select to authenticated
using(private.press_role_rank()>=1);

alter table public.press_notes drop constraint if exists press_notes_status_check;
update public.press_notes set status='archivada' where status='descartada';
alter table public.press_notes add constraint press_notes_status_check
check(status in ('borrador','revision','cambios','lista','publicada','archivada'));

alter table public.press_notes
  add column if not exists tags text[] not null default '{}',
  add column if not exists reviewer_id uuid references public.profiles(id),
  add column if not exists submitted_at timestamptz,
  add column if not exists ready_at timestamptz,
  add column if not exists first_published_at timestamptz,
  add column if not exists public_updated_at timestamptz,
  add column if not exists archived_at timestamptz;

update public.press_notes
set first_published_at=coalesce(first_published_at,published_at),
    public_updated_at=coalesce(public_updated_at,published_at)
where status='publicada';

update public.press_notes set tags=array['clubes de barrio','accesibilidad','comunas','deporte'] where slug='brecha-acceso-deporte' and cardinality(tags)=0;
update public.press_notes set tags=array['migración internacional','comunas','EAH 2025'] where slug='migraciones-geografia-comunal' and cardinality(tags)=0;
update public.press_notes set tags=array['empresas','comercio','comunas','actividad económica'] where slug='empresas-y-ocupacion-comercial' and cardinality(tags)=0;
update public.press_notes set tags=array['endeudamiento','mora','barrios','BCRA'] where slug='mora-brecha-barrios' and cardinality(tags)=0;

create index if not exists press_notes_topic_idx on public.press_notes(topic);
create index if not exists press_notes_tags_idx on public.press_notes using gin(tags);
create index if not exists press_notes_reviewer_idx on public.press_notes(reviewer_id);
create index if not exists press_notes_updated_idx on public.press_notes(updated_at desc);

create table if not exists public.press_note_versions (
  id bigint generated always as identity primary key,
  note_id uuid not null references public.press_notes(id) on delete cascade,
  version_no integer not null,
  snapshot jsonb not null,
  changed_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  unique(note_id,version_no)
);
alter table public.press_note_versions enable row level security;
grant select on public.press_note_versions to authenticated;
revoke insert,update,delete on public.press_note_versions from anon,authenticated;
create policy "press_versions_read" on public.press_note_versions for select to authenticated
using(private.press_role_rank()>=1);

create table if not exists public.press_note_comments (
  id uuid primary key default gen_random_uuid(),
  note_id uuid not null references public.press_notes(id) on delete cascade,
  body text not null check(length(trim(body))>0),
  created_by uuid not null references public.profiles(id),
  created_at timestamptz not null default now()
);
alter table public.press_note_comments enable row level security;
grant select,insert on public.press_note_comments to authenticated;
revoke update,delete on public.press_note_comments from anon,authenticated;
create index if not exists press_comments_note_idx on public.press_note_comments(note_id,created_at);
create policy "press_comments_read" on public.press_note_comments for select to authenticated
using(private.press_role_rank()>=1);
create policy "press_comments_add" on public.press_note_comments for insert to authenticated
with check(private.press_role_rank()>=1 and created_by=(select auth.uid()));

create table if not exists public.press_note_activity (
  id bigint generated always as identity primary key,
  note_id uuid not null references public.press_notes(id) on delete cascade,
  action text not null,
  from_status text,
  to_status text,
  actor_id uuid references public.profiles(id),
  created_at timestamptz not null default now()
);
alter table public.press_note_activity enable row level security;
grant select on public.press_note_activity to authenticated;
revoke insert,update,delete on public.press_note_activity from anon,authenticated;
create index if not exists press_activity_note_idx on public.press_note_activity(note_id,created_at desc);
create policy "press_activity_read" on public.press_note_activity for select to authenticated
using(private.press_role_rank()>=1);

drop policy if exists "press_members_select" on public.press_notes;
drop policy if exists "press_writers_insert" on public.press_notes;
drop policy if exists "press_writers_update" on public.press_notes;
drop policy if exists "press_admin_delete" on public.press_notes;

create policy "press_team_select" on public.press_notes for select to authenticated
using(private.press_role_rank()>=1);
create policy "press_team_insert" on public.press_notes for insert to authenticated
with check(private.press_role_rank()>=1 and created_by=(select auth.uid()) and updated_by=(select auth.uid()) and status='borrador');
create policy "press_team_update" on public.press_notes for update to authenticated
using(private.press_role_rank()>=1 and (created_by=(select auth.uid()) or private.press_role_rank()>=2))
with check(private.press_role_rank()>=1 and (created_by=(select auth.uid()) or private.press_role_rank()>=2) and updated_by=(select auth.uid()));
create policy "press_admin_delete" on public.press_notes for delete to authenticated
using(private.press_role_rank()>=4);

create or replace function private.guard_press_note()
returns trigger language plpgsql security invoker set search_path='' as $$
declare role_rank integer:=private.press_role_rank();
begin
  new.updated_at=now();
  if row(new.title,new.summary,new.body,new.quote,new.methodology,new.source_label,new.source_section,new.tags,new.topic,new.source_period)
    is distinct from row(old.title,old.summary,old.body,old.quote,old.methodology,old.source_label,old.source_section,old.tags,old.topic,old.source_period) then
    if old.status='publicada' and role_rank<3 then raise exception 'Solo edición puede modificar una nota publicada'; end if;
    if old.status in ('lista','archivada') and role_rank<2 then raise exception 'La nota requiere un rol de revisión o edición'; end if;
  end if;
  if new.status is distinct from old.status then
    if role_rank<2 and not (old.status='borrador' and new.status='revision') and not (old.status='cambios' and new.status in ('borrador','revision')) then
      raise exception 'El rol redactor solo puede enviar su nota a revisión';
    end if;
    if new.status in ('lista','cambios') and role_rank<2 then
      raise exception 'Solo revisión o edición puede validar o solicitar cambios';
    end if;
    if (new.status in ('publicada','archivada') or old.status='publicada') and role_rank<3 then
      raise exception 'Solo edición o administración puede publicar, retirar o archivar';
    end if;
    if new.status='revision' then new.submitted_at=now(); end if;
    if new.status='lista' then new.ready_at=now(); new.approved_by=auth.uid(); new.approved_at=now(); end if;
    if new.status='publicada' then
      new.approved_by=coalesce(new.approved_by,auth.uid()); new.approved_at=coalesce(new.approved_at,now());
      new.published_at=now(); new.first_published_at=coalesce(new.first_published_at,now());
      new.public_updated_at=now(); new.archived_at=null;
    elsif old.status='publicada' then
      new.published_at=null;
    end if;
    if new.status='archivada' then new.archived_at=now(); else new.archived_at=null; end if;
  elsif new.status='publicada' and row(new.title,new.summary,new.body,new.quote,new.methodology,new.source_label,new.source_section,new.tags)
    is distinct from row(old.title,old.summary,old.body,old.quote,old.methodology,old.source_label,old.source_section,old.tags) then
    new.public_updated_at=now();
  end if;
  return new;
end $$;
revoke all on function private.guard_press_note() from public,anon,authenticated;

create or replace function private.capture_press_version()
returns trigger language plpgsql security definer set search_path='' as $$
declare next_version integer;
begin
  select coalesce(max(version_no),0)+1 into next_version from public.press_note_versions where note_id=old.id;
  insert into public.press_note_versions(note_id,version_no,snapshot,changed_by)
  values(old.id,next_version,to_jsonb(old),auth.uid());
  return new;
end $$;
revoke all on function private.capture_press_version() from public,anon,authenticated;

create or replace function private.log_press_activity()
returns trigger language plpgsql security definer set search_path='' as $$
begin
  if tg_op='INSERT' then
    insert into public.press_note_activity(note_id,action,to_status,actor_id) values(new.id,'creada',new.status,auth.uid());
  elsif new.status is distinct from old.status then
    insert into public.press_note_activity(note_id,action,from_status,to_status,actor_id) values(new.id,'estado',old.status,new.status,auth.uid());
  else
    insert into public.press_note_activity(note_id,action,from_status,to_status,actor_id) values(new.id,'editada',old.status,new.status,auth.uid());
  end if;
  return new;
end $$;
revoke all on function private.log_press_activity() from public,anon,authenticated;

drop trigger if exists press_note_guard on public.press_notes;
drop trigger if exists press_note_capture_version on public.press_notes;
drop trigger if exists press_note_activity_log on public.press_notes;
create trigger press_note_guard before update on public.press_notes for each row execute function private.guard_press_note();
create trigger press_note_capture_version after update on public.press_notes for each row execute function private.capture_press_version();
create trigger press_note_activity_log after insert or update on public.press_notes for each row execute function private.log_press_activity();

create table if not exists private.press_invites (
  email text primary key check(email=lower(email)),
  press_role text not null check(press_role in ('redactor','revisor','editor','admin')),
  active boolean not null default true,
  invited_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table private.press_invites enable row level security;
revoke all on private.press_invites from public,anon,authenticated;

insert into private.press_invites(email,press_role,active,invited_by)
select lower(u.email),'admin',p.active,p.id from public.profiles p join auth.users u on u.id=p.id
where p.role='admin' and u.email is not null
on conflict(email) do update set press_role='admin',active=excluded.active,updated_at=now();

create or replace function public.manage_press_invite(invite_email text,invite_role text,invite_active boolean default true)
returns void language plpgsql security definer set search_path='' as $$
declare normalized text:=lower(trim(invite_email)); existing_user uuid;
begin
  if (select auth.uid()) is null or coalesce(private.current_press_role(),'')<>'admin' then raise exception 'Acceso denegado'; end if;
  if invite_role not in ('redactor','revisor','editor','admin') then raise exception 'Rol editorial inválido'; end if;
  insert into private.press_invites(email,press_role,active,invited_by)
  values(normalized,invite_role,invite_active,auth.uid())
  on conflict(email) do update set press_role=excluded.press_role,active=excluded.active,updated_at=now();
  insert into private.access_allowlist(email,role,active)
  values(normalized,case when invite_role='admin' then 'admin' else 'investigador' end,invite_active)
  on conflict(email) do update set active=excluded.active,
    role=case when private.access_allowlist.role='admin' then 'admin' else excluded.role end;
  select id into existing_user from auth.users where lower(email)=normalized limit 1;
  if existing_user is not null then
    update public.profiles set active=invite_active where id=existing_user;
    insert into public.press_members(user_id,press_role,active,added_by)
    values(existing_user,invite_role,invite_active,auth.uid())
    on conflict(user_id) do update set press_role=excluded.press_role,active=excluded.active,updated_at=now();
  end if;
end $$;
revoke all on function public.manage_press_invite(text,text,boolean) from public,anon,authenticated;
grant execute on function public.manage_press_invite(text,text,boolean) to authenticated;

create or replace function public.list_press_team()
returns table(user_id uuid,email text,display_name text,press_role text,active boolean,last_sign_in_at timestamptz)
language plpgsql stable security definer set search_path='' as $$
begin
  if (select auth.uid()) is null or coalesce(private.current_press_role(),'')<>'admin' then raise exception 'Acceso denegado'; end if;
  return query
  select u.id,i.email,p.display_name,i.press_role,i.active,u.last_sign_in_at
  from private.press_invites i
  left join auth.users u on lower(u.email)=i.email
  left join public.profiles p on p.id=u.id
  order by i.active desc,coalesce(p.display_name,i.email);
end $$;
revoke all on function public.list_press_team() from public,anon,authenticated;
grant execute on function public.list_press_team() to authenticated;

create or replace function private.handle_new_user()
returns trigger language plpgsql security definer set search_path='' as $$
declare approved_role text; approved_active boolean; invited_press_role text; press_active boolean;
begin
  select a.role,a.active into approved_role,approved_active from private.access_allowlist a where a.email=lower(coalesce(new.email,''));
  insert into public.profiles(id,display_name,role,active)
  values(new.id,coalesce(nullif(new.raw_user_meta_data->>'name',''),split_part(coalesce(new.email,''),'@',1)),coalesce(approved_role,'asesor'),coalesce(approved_active,false))
  on conflict(id) do update set role=excluded.role,active=excluded.active;
  select i.press_role,i.active into invited_press_role,press_active from private.press_invites i where i.email=lower(coalesce(new.email,''));
  if invited_press_role is not null then
    insert into public.press_members(user_id,press_role,active)
    values(new.id,invited_press_role,press_active)
    on conflict(user_id) do update set press_role=excluded.press_role,active=excluded.active,updated_at=now();
  end if;
  return new;
end $$;
revoke all on function private.handle_new_user() from public,anon,authenticated;

create index if not exists press_members_added_by_idx on public.press_members(added_by);
create index if not exists press_invites_invited_by_idx on private.press_invites(invited_by);
create index if not exists press_comments_created_by_idx on public.press_note_comments(created_by);
create index if not exists press_versions_changed_by_idx on public.press_note_versions(changed_by);
create index if not exists press_activity_actor_idx on public.press_note_activity(actor_id);

create or replace function private.manage_press_invite_internal(invite_email text,invite_role text,invite_active boolean)
returns void language plpgsql security definer set search_path='' as $$
declare normalized text:=lower(trim(invite_email)); existing_user uuid;
begin
  if (select auth.uid()) is null or coalesce(private.current_press_role(),'')<>'admin' then raise exception 'Acceso denegado'; end if;
  if invite_role not in ('redactor','revisor','editor','admin') then raise exception 'Rol editorial inválido'; end if;
  insert into private.press_invites(email,press_role,active,invited_by) values(normalized,invite_role,invite_active,auth.uid())
  on conflict(email) do update set press_role=excluded.press_role,active=excluded.active,updated_at=now();
  insert into private.access_allowlist(email,role,active) values(normalized,case when invite_role='admin' then 'admin' else 'investigador' end,invite_active)
  on conflict(email) do update set active=excluded.active,role=case when private.access_allowlist.role='admin' then 'admin' else excluded.role end;
  select id into existing_user from auth.users where lower(email)=normalized limit 1;
  if existing_user is not null then
    update public.profiles set active=invite_active where id=existing_user;
    insert into public.press_members(user_id,press_role,active,added_by) values(existing_user,invite_role,invite_active,auth.uid())
    on conflict(user_id) do update set press_role=excluded.press_role,active=excluded.active,updated_at=now();
  end if;
end $$;
revoke all on function private.manage_press_invite_internal(text,text,boolean) from public,anon,authenticated;
grant execute on function private.manage_press_invite_internal(text,text,boolean) to authenticated;

create or replace function private.list_press_team_internal()
returns table(user_id uuid,email text,display_name text,press_role text,active boolean,last_sign_in_at timestamptz)
language plpgsql stable security definer set search_path='' as $$
begin
  if (select auth.uid()) is null or coalesce(private.current_press_role(),'')<>'admin' then raise exception 'Acceso denegado'; end if;
  return query select u.id,i.email,p.display_name,i.press_role,i.active,u.last_sign_in_at from private.press_invites i left join auth.users u on lower(u.email)=i.email left join public.profiles p on p.id=u.id order by i.active desc,coalesce(p.display_name,i.email);
end $$;
revoke all on function private.list_press_team_internal() from public,anon,authenticated;
grant execute on function private.list_press_team_internal() to authenticated;

create or replace function public.manage_press_invite(invite_email text,invite_role text,invite_active boolean default true)
returns void language sql security invoker set search_path=''
as $$ select private.manage_press_invite_internal(invite_email,invite_role,invite_active) $$;
create or replace function public.list_press_team()
returns table(user_id uuid,email text,display_name text,press_role text,active boolean,last_sign_in_at timestamptz)
language sql stable security invoker set search_path=''
as $$ select * from private.list_press_team_internal() $$;
revoke all on function public.manage_press_invite(text,text,boolean) from public,anon,authenticated;
revoke all on function public.list_press_team() from public,anon,authenticated;
grant execute on function public.manage_press_invite(text,text,boolean) to authenticated;
grant execute on function public.list_press_team() to authenticated;
