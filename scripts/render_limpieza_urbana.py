#!/usr/bin/env python3
"""Actualiza exclusivamente los metadatos del módulo desde sus agregados."""
import argparse,datetime,html,json,re
from pathlib import Path
MONTHS=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
def render(page,data,status=None):
 d=data;source=page.read_text();start=datetime.date.fromisoformat(d['periodStart']);end=datetime.date.fromisoformat(d['periodEnd']);days=(end-start).days+1
 def fmt(n):return f'{n:,}'.replace(',','.')
 period=f'{MONTHS[start.month-1]}. {start.year} — {MONTHS[end.month-1]}. {end.year}'
 values={'lu-period':period,'lu-kpi-total':fmt(d['total']),'lu-kpi-daily':fmt(round(d['total']/days)),'lu-days':f'En los {fmt(days)} días del período disponible','lu-kpi-cutoff':f'{MONTHS[end.month-1].capitalize()}. {end.year}','lu-start':f'Inicio: {MONTHS[start.month-1]}. {start.year}','lu-updated':f'Corte: {end.strftime("%d/%m/%Y")}',
 'lu-method-period':f'Unidad: contacto registrado en la categoría HIGIENE. Período disponible: {start.strftime("%d/%m/%Y")} al {end.strftime("%d/%m/%Y")}. Comparación: cantidades absolutas por barrio, comuna, mes, tema y tipo de contacto.'+(' El último mes tiene cobertura parcial y sus cifras se muestran acumuladas hasta el corte.' if d['lastMonthPartial'] else ''),
 'lu-method-coverage':f'Cobertura: {fmt(d["total"])} contactos únicos de higiene; {fmt(d["missingBarrio"])} sin barrio informado. Se omitieron {fmt(d["duplicatesRemoved"])} duplicados idénticos. En {fmt(d["comunaConflictsResolvedFromBarrio"])} contactos se utilizó la comuna oficial del barrio ante una asignación de origen diferente o faltante.',
 'lu-check':f'Última versión de datos: {d["retrieved"]}. Última comprobación satisfactoria de la fuente: {(status or {}).get("checkedAt",d["retrieved"])}. La fecha de comprobación indica la revisión de disponibilidad; el corte estadístico se informa por separado.'}
 for ident,text in values.items():
  pattern=rf'(<(?P<tag>span|strong|p)\b[^>]*\bid="{ident}"[^>]*>).*?(</(?P=tag)>)'
  source,n=re.subn(pattern,lambda m:m[1]+html.escape(text)+m[3],source,flags=re.S)
  if n!=1:raise ValueError('Marcador de metadatos inválido: '+ident)
 page.write_text(source)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--page',type=Path,required=True);p.add_argument('--status',type=Path);a=p.parse_args();render(a.page,json.loads(a.data.read_text()),json.loads(a.status.read_text()) if a.status and a.status.exists() else None)
