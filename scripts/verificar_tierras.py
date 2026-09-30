"""Verifica el corte RNTR 2025-08 y su correspondencia con la página publicada."""
import argparse,json,re,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--directorio',default='deploy/site-overlay/territorio/tierras-y-soberania');args=p.parse_args()
root=Path(args.directorio);data=json.loads((root/'rntr.json').read_text());rows=data['registros'];s=(root/'index.html').read_text()
assert len(rows)==513 and len({r['id'] for r in rows})==513
assert len({r['id_georef'] for r in rows})==512
assert sum(r['pct'] is not None and r['pct']>15 for r in rows)==31
assert len([r for r in rows if r['estado']=='duplicado_en_fuente'])==1
assert len(re.findall(r'<tr data-id=',s))==513
paths=dict(re.findall(r'<path data-id="([^"]+)"[^>]*fill="([^"]+)"',s))
def color(v):
 if v is None:return '#d9dfe4'
 if v>30:return '#7f1734'
 if v>15:return '#bd3c53'
 if v>=9:return '#df846e'
 if v>=5:return '#eac29e'
 return '#c9dcd5'
for r in rows:
 assert r['id_georef'] in paths
 assert r['rural_ha']>=0
 if r['estado']!='duplicado_en_fuente':assert paths[r['id_georef']]==color(r['pct'])
 if r['extranjera_ha'] is not None and r['rural_ha'] and r['pct'] is not None:
  assert abs(100*r['extranjera_ha']/r['rural_ha']-r['pct'])<=.011
assert math.isclose(sum(r['extranjera_ha'] or 0 for r in rows),13262719.20,abs_tol=.01)
assert data['totales']['nacion']['extranjera_ha']==13262725.64
assert any(r['extranjera_ha'] is None for r in rows),'Celdas vacías perdidas'
for name,v in [('Malargue',14.74),('Chilecito',14.86)]:assert next(r for r in rows if r['departamento']==name)['pct']==v
print('513 filas, 512 jurisdicciones, 31 sobre 15%, cifras, vacíos y colores: correctos')
