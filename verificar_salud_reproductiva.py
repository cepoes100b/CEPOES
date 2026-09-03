#!/usr/bin/env python3
import json,sys
from pathlib import Path
d=json.loads(Path('deploy/site-overlay/assets/data/salud-reproductiva.json').read_text(encoding='utf-8'));err=[]
if d.get('paev',{}).get('public_outcome_series_located') is not False:err.append('El estado de serie PAEV requiere revisión explícita')
if d.get('ive_ile',{}).get('official_series_period')!='2016–2025':err.append('Período IVE/ILE base inesperado')
ids={x.get('id') for x in d.get('documented_facts',[])}
for x in ('autonomy','osc_funding','legislature_request'):
    if x not in ids:err.append(f'Falta hecho documentado {x}')
if len(d.get('transparency_matrix',[]))<8:err.append('Matriz de transparencia incompleta')
if err:
    print('NO se publica salud reproductiva:');[print(' ·',e) for e in err];sys.exit(1)
print(f'salud reproductiva OK · {len(d["transparency_matrix"])} dimensiones')
