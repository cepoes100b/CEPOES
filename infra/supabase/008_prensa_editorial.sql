-- CEPOES · Bandeja editorial privada y publicación controlada de notas de prensa.
create table if not exists public.press_notes (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  topic text not null,
  title text not null check (length(trim(title)) > 0),
  summary text not null default '',
  facts jsonb not null default '[]'::jsonb check (jsonb_typeof(facts)='array'),
  body text[] not null default '{}',
  quote text not null default '',
  methodology text not null default '',
  source_label text not null default '',
  source_section text not null default '',
  status text not null default 'borrador' check (status in ('borrador','revision','publicada','descartada')),
  origin text not null default 'automatico' check (origin in ('automatico','manual')),
  source_period text not null default '', source_hash text,
  created_by uuid references public.profiles(id), updated_by uuid references public.profiles(id),
  approved_by uuid references public.profiles(id), approved_at timestamptz, published_at timestamptz,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
alter table public.press_notes enable row level security;
create index press_notes_created_by_idx on public.press_notes(created_by);
create index press_notes_updated_by_idx on public.press_notes(updated_by);
create index press_notes_approved_by_idx on public.press_notes(approved_by);
create index press_notes_status_published_idx on public.press_notes(status,published_at desc);
create unique index press_notes_source_hash_uniq on public.press_notes(source_hash) where source_hash is not null;
grant select on public.press_notes to anon, authenticated;
grant insert,update,delete on public.press_notes to authenticated;
create policy "press_public_select_published" on public.press_notes for select to anon using(status='publicada');
create policy "press_members_select" on public.press_notes for select to authenticated using(private.is_active_member());
create policy "press_writers_insert" on public.press_notes for insert to authenticated with check(private.can_write_intelligence() and created_by=(select auth.uid()) and updated_by=(select auth.uid()) and status<>'publicada');
create policy "press_writers_update" on public.press_notes for update to authenticated using(private.can_write_intelligence()) with check(private.can_write_intelligence() and updated_by=(select auth.uid()) and (status<>'publicada' or private.is_app_admin()));
create policy "press_admin_delete" on public.press_notes for delete to authenticated using(private.is_app_admin());

create or replace function private.guard_press_note() returns trigger language plpgsql security invoker set search_path=public,private,pg_catalog as $$
begin
  new.updated_at=now();
  if new.status='publicada' and old.status is distinct from 'publicada' then
    if not private.is_app_admin() then raise exception 'Solo una persona administradora puede publicar'; end if;
    new.approved_by=auth.uid(); new.approved_at=now(); new.published_at=coalesce(new.published_at,now());
  elsif new.status<>'publicada' and old.status='publicada' then
    if not private.is_app_admin() then raise exception 'Solo una persona administradora puede retirar una publicación'; end if;
    new.published_at=null;
  end if;
  return new;
end $$;
revoke all on function private.guard_press_note() from public,anon,authenticated;
create trigger press_note_guard before update on public.press_notes for each row execute function private.guard_press_note();
