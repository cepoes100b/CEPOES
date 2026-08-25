#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
P=BASE/'deploy'/'site-overlay'/'assets'/'data'/'deporte-accesibilidad.json'
assert P.is_file() and P.stat().st_size>1000, 'Falta deporte-accesibilidad.json'
d=json.loads(P.read_text(encoding='utf-8'))
assert d.get('version')==1
base=d.get('base_poblacional') or {}
assert base.get('radios',0)>=3500
assert 3_000_000 <= base.get('poblacion_radios',0) <= 3_200_000
assert base.get('diferencia_pct',1) < 0.1
assert d.get('metodologia',{}).get('distancias_m')==[800,1000]
coverage=d.get('cobertura') or {}
for key in ['clubes','polideportivos','red_deportiva']:
    assert key in coverage
    obj=coverage[key]
    assert obj.get('puntos_georreferenciados',0)>0
    for dist in ['800','1000']:
        block=(obj.get('distancias') or {}).get(dist) or {}
        city=block.get('ciudad') or {}
        comunas=block.get('comunas') or {}
        assert set(comunas)=={str(i) for i in range(1,16)}
        pct=city.get('cobertura_pct')
        assert pct is not None and 0 <= pct <= 100
        assert city.get('poblacion_cubierta_estimada',-1) <= city.get('poblacion_base',0)
        for c in comunas.values():
            assert 0 <= (c.get('cobertura_pct') or 0) <= 100
            assert c.get('poblacion_cubierta_estimada',-1) <= c.get('poblacion_base',0)
    assert obj['distancias']['1000']['ciudad']['cobertura_pct'] >= obj['distancias']['800']['ciudad']['cobertura_pct']
assert coverage['red_deportiva']['distancias']['800']['ciudad']['cobertura_pct'] >= coverage['clubes']['distancias']['800']['ciudad']['cobertura_pct']
assert coverage['red_deportiva']['distancias']['800']['ciudad']['cobertura_pct'] >= coverage['polideportivos']['distancias']['800']['ciudad']['cobertura_pct']
print('OK accesibilidad deportiva · 3816 radios aprox. · 15 comunas · 800/1000 m · control poblacional consistente')
