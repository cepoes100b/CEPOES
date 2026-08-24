-- CEPOES · soporte para análisis legislativo automático.
-- No contiene comisiones, usuarios ni datos internos reales.

alter table public.expediente_analyses
  add column if not exists analysis_origin text not null default 'manual',
  add column if not exists is_current boolean not null default true,
  add column if not exists automation_source_hash text,
  add column if not exists automation_model text,
  add column if not exists automation_confidence numeric(4,3),
  add column if not exists automation_generated_at timestamptz,
  add column if not exists review_required boolean not null default false,
  add column if not exists source_evidence jsonb not null default '{}'::jsonb,
  add column if not exists affected_actors text not null default '',
  add column if not exists arguments_for text not null default '',
  add column if not exists arguments_against text not null default '',
  add column if not exists evidence_gaps text[] not null default '{}';

alter table public.expediente_analyses
  drop constraint if exists expediente_analyses_analysis_origin_check;
alter table public.expediente_analyses
  add constraint expediente_analyses_analysis_origin_check
  check (analysis_origin in ('manual','automatic'));

alter table public.expediente_analyses
  drop constraint if exists expediente_analyses_automation_confidence_check;
alter table public.expediente_analyses
  add constraint expediente_analyses_automation_confidence_check
  check (automation_confidence is null or (automation_confidence >= 0 and automation_confidence <= 1));

create unique index if not exists expediente_analyses_auto_source_uniq
  on public.expediente_analyses(expediente_numero, document_kind, automation_source_hash)
  where analysis_origin = 'automatic' and automation_source_hash is not null;

create index if not exists expediente_analyses_current_idx
  on public.expediente_analyses(expediente_numero, document_kind, is_current, updated_at desc);

-- La configuración concreta de foco se carga sólo en Supabase y nunca se versiona.
create table if not exists private.analysis_focus_commissions (
  commission_name text primary key,
  enabled boolean not null default true,
  priority smallint not null default 100,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
revoke all on private.analysis_focus_commissions from public, anon, authenticated;
