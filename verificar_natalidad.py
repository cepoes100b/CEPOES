#!/usr/bin/env python3
import json,sys
from pathlib import Path
p=Path('deploy/site-overlay/assets/data/natalidad.json');d=json.loads(p.read_text(encoding='utf-8'));err=[]
b={x['year']:x['value'] for x in d.get('argentina',{}).get('births',[])}
for y,v in {2014:777012,2020:533299,2024:413135}.items():
    if b.get(y)!=v:err.append(f'Argentina {y}: {b.get(y)} != {v}')
t={x['year']:x['value'] for x in d.get('caba',{}).get('tgf',[])}
for y,v in {2014:1.85,2019:1.48,2020:1.20,2022:1.09,2024:0.99,2025:0.90}.items():
    if abs(t.get(y,99)-v)>1e-9:err.append(f'CABA TGF {y}: {t.get(y)} != {v}')
if d.get('argentina',{}).get('replacement_reference')!=2.1:err.append('Referencia de reemplazo alterada')
if Path('natalidad.json').read_bytes()!=p.read_bytes():err.append('Copias JSON divergentes')
years=[x['year'] for x in d['caba']['tgf']]
if years!=list(range(2010,2026)):err.append('Serie CABA incompleta, desordenada o duplicada')
for key,value in {'births_2024':21366,'births_2025':20444,'birth_rate_2024_per_1000':6.9,'mean_maternal_age_2024':32.5,'mean_maternal_age_2025':32.8}.items():
    if d['caba'].get(key)!=value:err.append(f'CABA {key}: valor inesperado')
if d['argentina']['tgf'][-1]!={'year':2019,'value':1.8}:err.append('Ancla RENAPER 2019 alterada')
review=d['caba'].get('review',{})
cells=review.get('cells',{})
if round(cells.get('idecba_pb3_14',{}).get('AT11',0),2)!=t.get(2025):err.append('Redondeo TGF 2025 inconsistente')
if round(cells.get('idecba_pb3_14',{}).get('AT13',0),1)!=d['caba']['mean_maternal_age_2025']:err.append('Redondeo edad 2025 inconsistente')
if cells.get('idecba_nps',{}).get('B37')!=d['caba']['births_2025']:err.append('Nacimientos 2025 inconsistentes')
if err:
    print('NO se publica natalidad:');[print(' ·',e) for e in err];sys.exit(1)
print(f'natalidad OK · {len(b)} puntos nacionales · {len(t)} puntos TGF CABA')
