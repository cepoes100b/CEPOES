#!/usr/bin/env python3
import json,sys
from pathlib import Path
p=Path('deploy/site-overlay/assets/data/natalidad.json');d=json.loads(p.read_text(encoding='utf-8'));err=[]
b={x['year']:x['value'] for x in d.get('argentina',{}).get('births',[])}
for y,v in {2014:777012,2020:533299,2024:413135}.items():
    if b.get(y)!=v:err.append(f'Argentina {y}: {b.get(y)} != {v}')
t={x['year']:x['value'] for x in d.get('caba',{}).get('tgf',[])}
for y,v in {2014:1.85,2019:1.48,2020:1.20,2024:0.99}.items():
    if abs(t.get(y,99)-v)>.011:err.append(f'CABA TGF {y}: {t.get(y)} != {v}')
if d.get('argentina',{}).get('replacement_reference')!=2.1:err.append('Referencia de reemplazo alterada')
if err:
    print('NO se publica natalidad:');[print(' ·',e) for e in err];sys.exit(1)
print(f'natalidad OK · {len(b)} puntos nacionales · {len(t)} puntos TGF CABA')
