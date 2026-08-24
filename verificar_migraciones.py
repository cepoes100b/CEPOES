#!/usr/bin/env python3
import argparse,json,math
from pathlib import Path

ap=argparse.ArgumentParser();ap.add_argument('path',nargs='?',default='deploy/site-overlay/assets/data/migraciones.json');a=ap.parse_args()
d=json.loads(Path(a.path).read_text(encoding='utf-8'))
assert d['schema']=='cepoes-migraciones-v1'
assert d['status']=='VALIDADO'
assert set(d['communes'])=={str(i) for i in range(1,16)}
assert d['headline']['eah']['year']>=2025
assert d['countries']['year']>=2024 and d['countries']['base_year']<=2015
assert len(d['countries']['rows'])>=10
for c,v in d['communes'].items():
    e=v['eah']; assert e['year']==d['headline']['eah']['year']
    for k in ['nacida_caba_pct','prov_ba_pct','otra_provincia_pct','pais_limitrofe_pct','pais_no_limitrofe_pct','migracion_interna_pct','migracion_internacional_pct']:
        assert 0<=float(e[k])<=100,(c,k,e[k])
    total=e['nacida_caba_pct']+e['prov_ba_pct']+e['otra_provincia_pct']+e['pais_limitrofe_pct']+e['pais_no_limitrofe_pct']
    assert 97<=total<=103,(c,total)
    assert abs(e['migracion_interna_pct']-(e['prov_ba_pct']+e['otra_provincia_pct']))<0.11
    assert abs(e['migracion_internacional_pct']-(e['pais_limitrofe_pct']+e['pais_no_limitrofe_pct']))<0.11
h=d['headline']['eah']
for k in ['nacida_caba_pct','prov_ba_pct','otra_provincia_pct','pais_limitrofe_pct','pais_no_limitrofe_pct']:
    assert 0<=float(h[k])<=100
assert 97<=sum(float(h[k]) for k in ['nacida_caba_pct','prov_ba_pct','otra_provincia_pct','pais_limitrofe_pct','pais_no_limitrofe_pct'])<=103
for key in ['activity','schooling','poverty_multidimensional']:
    block=d['socioeconomic'][key]; assert block['year']>=2024 if key!='poverty_multidimensional' else block['year']>=2025
    assert all(math.isfinite(float(v)) for v in block['values'].values())
H=d['recent_migration']; assert len(H['years'])>=5 and max(H['years'])>=2022
for i,y in enumerate(H['years']):
    s=H['prov_ba'][i]+H['otra_provincia'][i]+H['exterior'][i]
    assert 99<=s<=101,(y,s)
print('Migraciones VALIDADO · EAH',d['headline']['eah']['year'],'· países',d['countries']['year'],'· pobreza',d['socioeconomic']['poverty_multidimensional']['year'])
