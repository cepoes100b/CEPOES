#!/usr/bin/env python3
"""Compara diagnósticos peatonales 4x4 y 8x8. No publica resultados."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
A = BASE / "diagnostico_accesibilidad_peatonal_g4.json"
B = BASE / "diagnostico_accesibilidad_peatonal_g8.json"
OUT = BASE / "diagnostico_sensibilidad_peatonal.json"
UNIVERSES = ("clubes", "polideportivos", "red_deportiva")
DISTANCES = (800, 1000)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    a = load(A)
    b = load(B)
    result = {
        "estado": "diagnostico_no_publicado",
        "comparacion": "malla 8x8 menos malla 4x4",
        "base": {
            "g4_muestras": a["muestreo"]["muestras"],
            "g8_muestras": b["muestreo"]["muestras"],
            "g4_poblacion": a["muestreo"]["poblacion_reconstruida"],
            "g8_poblacion": b["muestreo"]["poblacion_reconstruida"],
        },
        "cobertura": {},
    }
    stable_all = True
    for universe in UNIVERSES:
        result["cobertura"][universe] = {}
        for distance in DISTANCES:
            sa = a["cobertura"][universe]["distancias"][str(distance)]
            sb = b["cobertura"][universe]["distancias"][str(distance)]
            city_a = float(sa["ciudad"]["cobertura_pct"])
            city_b = float(sb["ciudad"]["cobertura_pct"])
            deltas = {
                cid: round(float(sb["comunas"][cid]["cobertura_pct"]) - float(sa["comunas"][cid]["cobertura_pct"]), 2)
                for cid in map(str, range(1, 16))
            }
            worst_cid = max(deltas, key=lambda cid: abs(deltas[cid]))
            city_delta = round(city_b - city_a, 2)
            max_commune = round(abs(deltas[worst_cid]), 2)
            stable = abs(city_delta) <= 1.0 and max_commune <= 3.0
            stable_all = stable_all and stable
            result["cobertura"][universe][str(distance)] = {
                "g4_pct": city_a,
                "g8_pct": city_b,
                "diferencia_ciudad_pp": city_delta,
                "max_diferencia_comuna_abs_pp": max_commune,
                "comuna_max_diferencia": worst_cid,
                "diferencias_comunas_pp": deltas,
                "estable_criterio_exploratorio": stable,
            }
    result["estable_global_criterio_exploratorio"] = stable_all
    result["criterio_exploratorio"] = "|Δ ciudad| ≤ 1 pp y máximo |Δ comuna| ≤ 3 pp"
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Sensibilidad 4x4 vs 8x8 · estable global: {stable_all}")
    for universe in UNIVERSES:
        print(f"  · {universe}")
        for distance in DISTANCES:
            row = result["cobertura"][universe][str(distance)]
            print(
                f"    {distance} m: {row['g4_pct']}% → {row['g8_pct']}% "
                f"(Δ ciudad {row['diferencia_ciudad_pp']} pp; máximo comuna "
                f"{row['max_diferencia_comuna_abs_pp']} pp en C{row['comuna_max_diferencia']})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
