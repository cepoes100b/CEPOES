begin;
create table public.newsletter_publications (
 publication_key text primary key check(publication_key ~ '^/[a-z0-9/-]+/$'),
 payload jsonb check(payload is null or jsonb_typeof(payload)='object'),
 detected_at timestamptz not null default now()
);
alter table public.newsletter_publications enable row level security;
revoke all on public.newsletter_publications from public,anon,authenticated;
grant all on public.newsletter_publications to service_role;
-- Public URLs known before activation are archive markers, never jobs.
insert into public.newsletter_publications(publication_key) values
 ('/balance/'),
 ('/balance/presupuesto-y-modelo-de-gestion/'),
 ('/balance/salud-publica/'),
 ('/balance/vivienda-y-alquiler/'),
 ('/cepoes/'),
 ('/cepoes/metodologia/'),
 ('/cepoes/metodologia/brechas/'),
 ('/cepoes/metodologia/endeudamiento/'),
 ('/cepoes/metodologia/legislatura/'),
 ('/cepoes/metodologia/migraciones/'),
 ('/cepoes/metodologia/observatorio/'),
 ('/cepoes/metodologia/presupuesto/'),
 ('/cepoes/metodologia/salud-mental/'),
 ('/cepoes/metodologia/territorio/'),
 ('/datos/estado/'),
 ('/legislatura/'),
 ('/legislatura/expediente/'),
 ('/legislatura/reunion/'),
 ('/legislatura/seguimiento/analgesia-peridural/'),
 ('/legislatura/sesion/'),
 ('/observatorio/'),
 ('/observatorio/agenda/'),
 ('/observatorio/condiciones-de-vida/'),
 ('/observatorio/condiciones-de-vida/pobreza/'),
 ('/observatorio/estado/'),
 ('/observatorio/estado/ejecucion-presupuestaria/'),
 ('/observatorio/natalidad/'),
 ('/observatorio/personas-mayores/'),
 ('/observatorio/precios/'),
 ('/observatorio/precios/canasta-consumo/'),
 ('/observatorio/precios/ipc/'),
 ('/observatorio/produccion/'),
 ('/observatorio/produccion/exportaciones/'),
 ('/observatorio/produccion/industria/'),
 ('/observatorio/produccion/locales-vacantes/'),
 ('/observatorio/produccion/pgb/'),
 ('/observatorio/salud-mental/'),
 ('/observatorio/salud-reproductiva/'),
 ('/observatorio/trabajo/'),
 ('/observatorio/trabajo/desocupacion/'),
 ('/observatorio/trabajo/empleo/'),
 ('/prensa/'),
 ('/presupuesto/'),
 ('/presupuesto/descentralizacion/'),
 ('/presupuesto/diagnostico/'),
 ('/presupuesto/ejecucion/'),
 ('/presupuesto/territorio/'),
 ('/propuestas/'),
 ('/publicaciones/'),
 ('/publicaciones/boletines/'),
 ('/publicaciones/boletines/boletin-01-mayo-2026/'),
 ('/publicaciones/boletines/boletin-02-junio-2026/'),
 ('/publicaciones/boletines/boletin-03-julio-2026/'),
 ('/publicaciones/boletines/boletin-04-agosto-2026/'),
 ('/publicaciones/boletines/boletin-05-septiembre-2026/'),
 ('/publicaciones/informe-coyuntura-01-junio-2026/'),
 ('/publicaciones/informe-coyuntura-02-octubre-2026/'),
 ('/publicaciones/informes/'),
 ('/publicaciones/informes/educacion-pisa-fepba-2025/'),
 ('/publicaciones/informes/endeudarse-para-llegar-a-fin-de-mes/'),
 ('/publicaciones/informes/personas-mayores-caba/'),
 ('/publicaciones/informes/plataformas-juventudes-caba/'),
 ('/publicaciones/informes/salud-mental-caba/'),
 ('/publicaciones/informes/situacion-de-calle-caba/'),
 ('/publicaciones/notas/'),
 ('/publicaciones/notas/criar-en-buenos-aires-sala-de-3/'),
 ('/publicaciones/notas/el-boca-river-de-la-mora/'),
 ('/publicaciones/notas/el-dolor-tambien-es-desigual/'),
 ('/publicaciones/notas/prevenir-es-garantizar-ayuda-a-tiempo/'),
 ('/publicaciones/notas/tormenta-negra-seguridad-territorio/'),
 ('/territorio/'),
 ('/territorio/barrios/'),
 ('/territorio/barrios/agronomia/'),
 ('/territorio/barrios/almagro/'),
 ('/territorio/barrios/balvanera/'),
 ('/territorio/barrios/barracas/'),
 ('/territorio/barrios/belgrano/'),
 ('/territorio/barrios/boedo/'),
 ('/territorio/barrios/caballito/'),
 ('/territorio/barrios/chacarita/'),
 ('/territorio/barrios/coghlan/'),
 ('/territorio/barrios/colegiales/'),
 ('/territorio/barrios/constitucion/'),
 ('/territorio/barrios/flores/'),
 ('/territorio/barrios/floresta/'),
 ('/territorio/barrios/la-boca/'),
 ('/territorio/barrios/la-paternal/'),
 ('/territorio/barrios/liniers/'),
 ('/territorio/barrios/mataderos/'),
 ('/territorio/barrios/monserrat/'),
 ('/territorio/barrios/monte-castro/'),
 ('/territorio/barrios/nueva-pompeya/'),
 ('/territorio/barrios/nunez/'),
 ('/territorio/barrios/palermo/'),
 ('/territorio/barrios/parque-avellaneda/'),
 ('/territorio/barrios/parque-chacabuco/'),
 ('/territorio/barrios/parque-chas/'),
 ('/territorio/barrios/parque-patricios/'),
 ('/territorio/barrios/puerto-madero/'),
 ('/territorio/barrios/recoleta/'),
 ('/territorio/barrios/retiro/'),
 ('/territorio/barrios/saavedra/'),
 ('/territorio/barrios/san-cristobal/'),
 ('/territorio/barrios/san-nicolas/'),
 ('/territorio/barrios/san-telmo/'),
 ('/territorio/barrios/velez-sarsfield/'),
 ('/territorio/barrios/versalles/'),
 ('/territorio/barrios/villa-crespo/'),
 ('/territorio/barrios/villa-del-parque/'),
 ('/territorio/barrios/villa-devoto/'),
 ('/territorio/barrios/villa-general-mitre/'),
 ('/territorio/barrios/villa-lugano/'),
 ('/territorio/barrios/villa-luro/'),
 ('/territorio/barrios/villa-ortuzar/'),
 ('/territorio/barrios/villa-pueyrredon/'),
 ('/territorio/barrios/villa-real/'),
 ('/territorio/barrios/villa-riachuelo/'),
 ('/territorio/barrios/villa-santa-rita/'),
 ('/territorio/barrios/villa-soldati/'),
 ('/territorio/barrios/villa-urquiza/'),
 ('/territorio/brechas/'),
 ('/territorio/comparar/'),
 ('/territorio/comuna-1/'),
 ('/territorio/comuna-10/'),
 ('/territorio/comuna-11/'),
 ('/territorio/comuna-12/'),
 ('/territorio/comuna-13/'),
 ('/territorio/comuna-14/'),
 ('/territorio/comuna-15/'),
 ('/territorio/comuna-2/'),
 ('/territorio/comuna-3/'),
 ('/territorio/comuna-4/'),
 ('/territorio/comuna-5/'),
 ('/territorio/comuna-6/'),
 ('/territorio/comuna-7/'),
 ('/territorio/comuna-8/'),
 ('/territorio/comuna-9/'),
 ('/territorio/deporte-salud/'),
 ('/territorio/endeudamiento/'),
 ('/territorio/equipamientos/'),
 ('/territorio/estructura-productiva/'),
 ('/territorio/mapa-tematico/'),
 ('/territorio/migraciones/'),
 ('/territorio/seguridad-barrios-populares/'),
 ('/territorio/tierras-y-soberania/')
on conflict do nothing;
-- Preserve every legacy bulletin job and lease; all kinds share one quota.
alter table public.newsletter_deliveries add column delivery_id uuid not null default gen_random_uuid();
alter table public.newsletter_deliveries add column publication_key text references public.newsletter_publications(publication_key);
alter table public.newsletter_deliveries drop constraint newsletter_deliveries_pkey;
alter table public.newsletter_deliveries alter column edition drop not null;
alter table public.newsletter_deliveries add primary key(delivery_id);
alter table public.newsletter_deliveries add unique(edition,subscription_id);
alter table public.newsletter_deliveries add unique(publication_key,subscription_id);
alter table public.newsletter_deliveries add constraint newsletter_delivery_one_publication
check ((edition is null) <> (publication_key is null));

create function public.newsletter_enqueue_publications(p_publications jsonb)
returns void language plpgsql security invoker set search_path='' as $$
declare item jsonb; key text;
begin
 perform pg_advisory_xact_lock(70310721);
 if jsonb_typeof(p_publications) is distinct from 'array' or jsonb_array_length(p_publications)>2000 then raise exception 'invalid_publications'; end if;
 for item in select value from jsonb_array_elements(p_publications) loop
  key=item->>'key';
  if key is null or key<>coalesce(item->>'url','') or key !~ '^/[a-z0-9/-]+/$'
   or coalesce(item->>'kind','') not in('boletin','informe','analisis','prensa','aviso')
   or coalesce(length(item->>'title'),0)=0 then raise exception 'invalid_publication'; end if;
  insert into public.newsletter_publications(publication_key,payload) values(key,item) on conflict do nothing;
  if not found then continue; end if;
  -- A legacy queue may already own this URL during rollout.
  if exists(select 1 from public.newsletter_editions where url=key) then continue; end if;
  insert into public.newsletter_deliveries(publication_key,subscription_id)
  select key,id from public.newsletter_subscriptions where status='active' and confirmed_at is not null;
 end loop;
end;$$;
create or replace function public.newsletter_claim_deliveries(p_limit integer default 10)
returns setof public.newsletter_deliveries language plpgsql security invoker set search_path='' as $$
declare budget integer;
begin
 -- Serializes quota reservations across overlapping runs.
 perform pg_advisory_xact_lock(70310721);
 update public.newsletter_deliveries set state='review',lease_token=null,lease_until=null
 where state in('pending','sending') and first_attempt_at<now()-interval '18 hours';
 select greatest(0,50-count(*)::integer) into budget from public.newsletter_deliveries
 where first_attempt_at>=date_trunc('day',now());
 return query with eligible as (
 select d.delivery_id,d.subscription_id,d.first_attempt_at,
 sum(case when d.first_attempt_at is null then 1 else 0 end) over
 (order by d.first_attempt_at nulls last,d.delivery_id,d.subscription_id) as new_position
 from public.newsletter_deliveries d join public.newsletter_subscriptions s on s.id=d.subscription_id
 where s.status='active' and ((d.state='pending' and d.next_attempt_at<=now()) or (d.state='sending' and d.lease_until<now()))
 ), candidates as (
 select e.delivery_id,e.subscription_id from eligible e where e.first_attempt_at is not null or e.new_position<=budget
 order by e.first_attempt_at nulls last,e.delivery_id,e.subscription_id limit least(greatest(p_limit,0),10)
 ) update public.newsletter_deliveries d set state='sending',attempts=d.attempts+1,
 first_attempt_at=coalesce(d.first_attempt_at,now()),lease_until=now()+interval '10 minutes',lease_token=gen_random_uuid()
 from candidates c where c.delivery_id=d.delivery_id returning d.*;
end;$$;

create function public.newsletter_finish_publication_delivery(p_delivery uuid,p_lease uuid,p_state text,p_provider_id text default null)
returns void language plpgsql security invoker set search_path='' as $$
begin
 if p_state not in('pending','accepted','cancelled') then raise exception 'invalid_delivery_state'; end if;
 if p_state='accepted' and p_provider_id is null then raise exception 'missing_provider_id'; end if;
 update public.newsletter_deliveries set state=p_state,provider_id=p_provider_id,
 accepted_at=case when p_state='accepted' then now() else null end,
 next_attempt_at=now()+interval '1 hour',lease_until=null,lease_token=null
 where delivery_id=p_delivery and state='sending' and lease_token=p_lease;
 if not found then raise exception 'stale_delivery_lease'; end if;
end;$$;
revoke all on function public.newsletter_enqueue_publications(jsonb),public.newsletter_finish_publication_delivery(uuid,uuid,text,text) from public,anon,authenticated;
grant execute on function public.newsletter_enqueue_publications(jsonb),public.newsletter_finish_publication_delivery(uuid,uuid,text,text) to service_role;
commit;
