#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
P = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-accesibilidad-peatonal.json"
E = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-accesibilidad.json"

assert P.is_file() and P.stat().st_size > 5_000, "Falta deporte-accesibilidad-peatonal.json"
d = json.loads(P.read_text(encoding="utf-8"))
e = json.loads(E.read_text(encoding="utf-8"))
assert d.get("version") == 1
method = d.get("metodologia") or {}
assert method.get("network_type") == "walk"
assert method.get("distancias_m") == [800, 1000]
assert "8x8" in str(method.get("muestreo_intraradio"))
assert "tiempo real" in str(method.get("interpretacion", ""))

base = d.get("base_poblacional") or {}
assert base.get("radios", 0) >= 3500
assert 3_000_000 <= base.get("poblacion_radios", 0) <= 3_200_000
assert base.get("poblacion_radios") == e["base_poblacional"]["poblacion_radios"]
assert base.get("muestras_ponderadas", 0) > 150_000

graph = d.get("grafo_peatonal") or {}
assert graph.get("nodos", 0) > 20_000
assert graph.get("aristas_dirigidas", 0) > 40_000
assert graph.get("margen_m", 0) >= 1000

control = d.get("control_conexion_red") or {}
assert (control.get("estadisticos_m") or {}).get("p50_m", 999) < 30
assert (control.get("umbrales") or {}).get("100", {}).get("poblacion_pct", 99) < 0.5
assert (control.get("umbrales") or {}).get("200", {}).get("poblacion_pct", 99) < 0.1

coverage = d.get("cobertura") or {}
for key in ["clubes", "polideportivos", "red_deportiva"]:
    assert key in coverage
    obj = coverage[key]
    assert obj.get("puntos_georreferenciados", 0) > 0
    for distance in ["800", "1000"]:
        block = (obj.get("distancias") or {}).get(distance) or {}
        city = block.get("ciudad") or {}
        comunas = block.get("comunas") or {}
        assert set(comunas) == {str(i) for i in range(1, 16)}
        pct = city.get("cobertura_pct")
        assert pct is not None and 0 <= pct <= 100
        assert city.get("poblacion_cubierta_estimada", -1) <= city.get("poblacion_base", 0)
        comp = block.get("comparacion_geometrica") or {}
        assert (comp.get("ciudad") or {}).get("euclidiana_pct") == e["cobertura"][key]["distancias"][distance]["ciudad"]["cobertura_pct"]
        # Una ruta por red no puede ser más corta que la distancia geométrica;
        # admitimos 0,5 pp por discretización intrarradio.
        assert pct <= e["cobertura"][key]["distancias"][distance]["ciudad"]["cobertura_pct"] + 0.5
        for c in comunas.values():
            assert 0 <= (c.get("cobertura_pct") or 0) <= 100
            assert c.get("poblacion_cubierta_estimada", -1) <= c.get("poblacion_base", 0)
    assert obj["distancias"]["1000"]["ciudad"]["cobertura_pct"] >= obj["distancias"]["800"]["ciudad"]["cobertura_pct"]

assert coverage["red_deportiva"]["distancias"]["800"]["ciudad"]["cobertura_pct"] >= coverage["clubes"]["distancias"]["800"]["ciudad"]["cobertura_pct"]
assert coverage["red_deportiva"]["distancias"]["800"]["ciudad"]["cobertura_pct"] >= coverage["polideportivos"]["distancias"]["800"]["ciudad"]["cobertura_pct"]
print("OK accesibilidad peatonal · OSM walk · malla 8x8 · 15 comunas · 800/1000 m · controles robustos")
