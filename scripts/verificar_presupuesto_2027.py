#!/usr/bin/env python3
"""Controles aritméticos y de trazabilidad del informe de proyecto 2027."""
import json,re,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'deploy/site-overlay'
d=json.loads((SITE/'assets/data/presupuesto-2027.json').read_text())
assert len(d['funciones'])==20
assert sum(x['proyecto_2027'] for x in d['funciones'])==d['total_2027']
# Cuadro 2.4: cada renglón publicado con una décima de millón.
assert abs(sum(x['vigente_2026_06_30'] for x in d['funciones'])-d['vigente_2026_06_30'])<=20*50000
h=next(x for x in d['funciones'] if x['nombre']=='Salud')
assert h['proyecto_2027']==d['salud']['funcion_total']
assert sum(x['monto'] for x in d['salud']['composicion_economica'])==h['proyecto_2027']
assert sum(x['cargos'] for x in d['salud']['dotacion'])==d['salud']['dotacion_total']==42395
share0=h['vigente_2026_06_30']/d['vigente_2026_06_30']
share1=h['proyecto_2027']/d['total_2027']
assert round(share0*100,2)==16.89 and round(share1*100,2)==16.46
assert round((d['total_2027']*share0-h['proyecto_2027'])/1e6)==102419
assert [round((h['proyecto_2027']/h['vigente_2026_06_30']/s['factor']-1)*100,1) for s in d['escenarios']]==[-2.8,-3.9]
assert len(d['obras_seleccionadas'])==30
keys=[(x['efector'],x['obra']) for x in d['obras_seleccionadas']]
assert len(set(keys))==30
assert all(x['pagina_pdf'] and x['proyecto_2027']>=0 for x in d['obras_seleccionadas'])
assert len(d['comunas_entidad'])==15
source=(SITE/'presupuesto/2027/index.html').read_text()
ids=re.findall(r'\bid="([^"]+)"',source)
assert len(set(ids))==len(ids)
assert all(a[1:] in ids for a in re.findall(r'href="(#[^"]+)"',source))
assert source.count('data-real-row=')==20 and source.count('data-work-type=')==30
assert '/presupuesto/ejecucion/' in source
spec=importlib.util.spec_from_file_location('normalizer',ROOT/'deploy/preparar_sitio_publico.py')
normalizer=importlib.util.module_from_spec(spec);spec.loader.exec_module(normalizer)
for url in ('/presupuesto/index.html','/presupuesto/ejecucion/index.html'):
 s='<main><h1>Presupuesto</h1></main>'
 once=normalizer.inject_budget_2027_bridge(s,url)
 assert once==normalizer.inject_budget_2027_bridge(once,url)
 assert once.count('id="budget-2027-bridge"')==1
 assert '/presupuesto/2027/' in once
print('Datos, participaciones, escenarios, dotación, inversiones, anclas y puentes: OK')
