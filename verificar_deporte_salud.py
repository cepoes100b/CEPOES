#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
P = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-salud.json"
assert P.is_file() and P.stat().st_size > 1000, "Falta deporte-salud.json o está vacío"
d = json.loads(P.read_text(encoding="utf-8"))
assert d.get("version") == 1
assert set((d.get("comunas") or {}).keys()) == {str(i) for i in range(1, 16)}
r = d.get("resumen") or {}
assert r.get("clubes", 0) > 100
assert r.get("sedes_clubes", 0) >= r.get("clubes", 0)
assert r.get("polideportivos", 0) >= 10
assert r.get("estaciones_saludables", 0) >= 10
assert r.get("cesac", 0) >= 20
assert len((d.get("capas") or {}).get("clubes", {}).get("items") or []) == r["sedes_clubes"]
assert len((d.get("capas") or {}).get("polideportivos", {}).get("items") or []) == r["polideportivos"]
assert all((d["comunas"][str(i)].get("poblacion") or 0) > 0 for i in range(1, 16))
for layer in ["clubes", "polideportivos", "estaciones", "cesac"]:
    for item in d["capas"][layer]["items"]:
        c = item.get("coord")
        if c is not None:
            assert len(c) == 2 and -58.7 <= c[0] <= -58.2 and -34.85 <= c[1] <= -34.45, (layer, item.get("id"), c)
assert "programas_desactualizados" in (d.get("alertas") or {})
print(
    "OK deporte-salud · "
    f"{r['clubes']} clubes / {r['sedes_clubes']} sedes · {r['polideportivos']} polideportivos · "
    f"{r['estaciones_saludables']} estaciones · {r['cesac']} CeSAC · 15 comunas"
)
