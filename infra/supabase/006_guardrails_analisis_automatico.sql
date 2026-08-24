-- CEPOES · guardrails server-side para borradores automáticos.
-- La recomendación nunca se habilita con evidencia primaria insuficiente o confianza < 0.75.

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
      new.automation_confidence := least(coalesce(new.automation_confidence,0), 0.45);
      new.recommendation := 'sin_definir';
    elsif coalesce(new.automation_confidence,0) < 0.75 then
      new.recommendation := 'sin_definir';
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
