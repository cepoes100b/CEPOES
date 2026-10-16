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
 'lu-method-period':f'Unidad: contacto registrado en la categoría HIGIENE. Período disponible: {start.strftime("%d/%m/%Y")} al {end.strftime("%d/%m/%Y")}. Comparación: cantidades absolutas por barrio, comuna, mes, tema y naturaleza del motivo.'+(' El último mes tiene cobertura parcial y sus cifras se muestran acumuladas hasta el corte.' if d['lastMonthPartial'] else ''),
 'lu-method-coverage':f'Cobertura: {fmt(d["total"])} contactos únicos de higiene; {fmt(d["missingBarrio"])} sin barrio informado. Se omitieron {fmt(d["duplicatesRemoved"])} duplicados idénticos. En {fmt(d["comunaConflictsResolvedFromBarrio"])} contactos se utilizó la comuna oficial del barrio ante una asignación de origen diferente o faltante.',
 'lu-check':f'Última versión de datos: {d["retrieved"]}. Última comprobación satisfactoria de la fuente: {(status or {}).get("checkedAt",d["retrieved"])}. La fecha de comprobación indica la revisión de disponibilidad; el corte estadístico se informa por separado.'}
 for ident,text in values.items():
  pattern=rf'(<(?P<tag>span|strong|p)\b[^>]*\bid="{ident}"[^>]*>).*?(</(?P=tag)>)'
  source,n=re.subn(pattern,lambda m:m[1]+html.escape(text)+m[3],source,flags=re.S)
  if n!=1:raise ValueError('Marcador de metadatos inválido: '+ident)
 # Bloques editoriales derivados del mismo agregado que utiliza el mapa.
 nature={n:sum(row[5] for row in d['counts'] if row[6]==n) for n in d['natures']}
 cards=''.join('<article class="lu-panel"><h3>'+title+'</h3><p>'+body+'</p></article>' for title,body in [
 ('Demandas diferentes',f"{fmt(nature['Problemas reportados'])} problemas reportados y {fmt(nature['Servicios solicitados'])} servicios solicitados. La clasificación conserva el motivo del contacto entre años. Otros contactos: {fmt(nature['Otros contactos'])}."),
 ('Cobertura interrumpida',f"{len(d['quality']['discontinuities'])} prestaciones dejan de aparecer durante meses completos. La ausencia requiere aclarar la cobertura de la fuente para evaluar la evolución."),
 ('Del aviso a la solución','La demanda registrada ayuda a localizar problemas. Para evaluar la respuesta hacen falta recorridos cumplidos, inspecciones e intervenciones verificadas.')])
 gaps=''.join('<tr><td>'+html.escape(g['prestacion'])+'</td><td>'+datetime.date.fromisoformat(g['lastRecord']).strftime('%d/%m/%Y')+'</td><td>'+html.escape(g['firstMissingMonth'])+'</td></tr>' for g in d['quality']['discontinuities'])
 changes=''.join('<tr><td>'+html.escape(c['prestacion'])+'</td><td>'+c['fromYear']+': '+html.escape(c['fromKind'])+' ('+fmt(c['fromCount'])+'/'+fmt(c['fromTotal'])+')</td><td>'+c['toYear']+': '+html.escape(c['toKind'])+' ('+fmt(c['toCount'])+'/'+fmt(c['toTotal'])+')</td></tr>' for c in d['quality']['originalTypeChanges'])
 detail='<p>Se detecta una interrupción cuando una prestación con al menos tres meses consecutivos de actividad y un promedio de 50 contactos mensuales pasa a dos meses completos sin registros. Se conserva el mes del último registro como tramo de cobertura incompleta.</p><div class="lu-table-scroll"><table><thead><tr><th>Prestación</th><th>Último registro</th><th>Primer mes completo sin registros</th></tr></thead><tbody>'+gaps+'</tbody></table></div><p>La causa de estas interrupciones no está documentada en las fuentes consultadas. Se revisó el archivo completo, incluidas las demás categorías, sin encontrar continuidad bajo otra denominación de barrido. La advertencia se mantiene hasta contar con una explicación verificable.</p><p>También cambia la etiqueta administrativa predominante de ocho motivos entre archivos anuales. Las cifras siguientes indican contactos con esa etiqueta sobre el total del motivo en cada año disponible; 2026 tiene corte parcial.</p><div class="lu-table-scroll"><table><thead><tr><th>Motivo</th><th>Archivo 2025</th><th>Archivo 2026</th></tr></thead><tbody>'+changes+'</tbody></table></div>'
 for ident,content in [('lu-insight-cards',cards),('lu-quality-detail',detail)]:
  marker='<!-- '+ident+':start -->';end='<!-- '+ident+':end -->'
  if marker not in source:
   source,n=re.subn(r'(<div\b[^>]*id="'+ident+r'"[^>]*>)(</div>)',lambda m:m[1]+marker+end+m[2],source)
   if n!=1:raise ValueError('Bloque editorial inválido: '+ident)
  source=re.sub(re.escape(marker)+'.*?'+re.escape(end),lambda m:marker+content+end,source,flags=re.S)
 page.write_text(source)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--page',type=Path,required=True);p.add_argument('--status',type=Path);a=p.parse_args();render(a.page,json.loads(a.data.read_text()),json.loads(a.status.read_text()) if a.status and a.status.exists() else None)
