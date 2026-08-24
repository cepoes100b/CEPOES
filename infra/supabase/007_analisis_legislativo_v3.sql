alter table public.expediente_analyses
  add column if not exists analysis_mode text not null default 'full',
  add column if not exists quality_flags text[] not null default '{}';

alter table public.expediente_analyses
  drop constraint if exists expediente_analyses_analysis_mode_check;
alter table public.expediente_analyses
  add constraint expediente_analyses_analysis_mode_check
  check (analysis_mode in ('full','preliminary_insufficient_evidence'));

create or replace function private.guard_automatic_analysis_insert()
returns trigger
language plpgsql
security definer
set search_path = public, private, pg_catalog
as $$
declare
  primary_docs integer := 0;
begin
  if new.analysis_origin = 'automatic' then
    new.review_status := 'borrador';
    new.review_required := true;
    new.created_by := null;
    new.updated_by := null;

    if coalesce(new.source_evidence->>'primary_document_count','') ~ '^\d+$' then
      primary_docs := (new.source_evidence->>'primary_document_count')::integer;
    end if;

    if primary_docs < 1 then
      new.analysis_mode := 'preliminary_insufficient_evidence';
      new.automation_confidence := least(coalesce(new.automation_confidence,0), 0.20);
      new.recommendation := 'sin_definir';
      new.arguments_for := '';
      new.arguments_against := '';
      new.proposed_amendments := '';
      new.intervention_arguments := '';
      if not ('no_primary_document' = any(coalesce(new.quality_flags,'{}'::text[]))) then
        new.quality_flags := array_append(coalesce(new.quality_flags,'{}'::text[]), 'no_primary_document');
      end if;
    else
      new.analysis_mode := coalesce(nullif(new.analysis_mode,''), 'full');
      if coalesce(new.automation_confidence,0) < 0.75 then
        new.recommendation := 'sin_definir';
      end if;
    end if;
  end if;
  return new;
end;
$$;

revoke all on function private.guard_automatic_analysis_insert() from public, anon, authenticated;
grant execute on function private.guard_automatic_analysis_insert() to service_role;

drop trigger if exists guard_automatic_analysis_insert on public.expediente_analyses;
create trigger guard_automatic_analysis_insert
before insert on public.expediente_analyses
for each row execute function private.guard_automatic_analysis_insert();

update public.expediente_analyses
set analysis_mode = 'preliminary_insufficient_evidence',
    quality_flags = case
      when 'no_primary_document' = any(coalesce(quality_flags,'{}'::text[])) then quality_flags
      else array_append(coalesce(quality_flags,'{}'::text[]), 'no_primary_document')
    end,
    recommendation = 'sin_definir',
    arguments_for = '',
    arguments_against = '',
    proposed_amendments = '',
    intervention_arguments = '',
    automation_confidence = least(coalesce(automation_confidence,0),0.20)
where analysis_origin = 'automatic'
  and coalesce(source_evidence->>'primary_document_count','') ~ '^\d+$'
  and (source_evidence->>'primary_document_count')::integer < 1;
