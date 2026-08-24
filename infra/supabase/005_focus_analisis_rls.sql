-- CEPOES · el foco concreto sigue siendo privado aunque la tabla viva en public.
-- Motivo: la Edge Function accede vía Data API; RLS + revocación impiden acceso de clientes.

alter table if exists private.analysis_focus_commissions set schema public;
alter table public.analysis_focus_commissions enable row level security;
revoke all on public.analysis_focus_commissions from public, anon, authenticated;
grant select on public.analysis_focus_commissions to service_role;

-- No crear políticas para anon/authenticated. El service_role del backend omite RLS.
