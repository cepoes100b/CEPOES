"""Controles de publicación para presupuesto.json."""
from __future__ import annotations

import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
PATH = BASE / "presupuesto.json"


def finite_positive(v) -> bool:
    try:
        x = float(v)
        return math.isfinite(x) and x > 0
    except Exception:
        return False


def main() -> int:
    problems = []
    if not PATH.exists():
        print("✘ falta presupuesto.json")
        return 1
    p = json.loads(PATH.read_text(encoding="utf-8"))
    total = p.get("total") or {}
    year = int(p.get("ejercicio") or 0)
    quarter = int(p.get("trimestre") or 0)

    if year < 2026:
        problems.append(f"ejercicio inesperado: {year}")
    if quarter not in (1, 2, 3, 4):
        problems.append(f"trimestre inválido: {quarter}")
    for key in ("sancionado", "vigente", "devengado"):
        if not finite_positive(total.get(key)):
            problems.append(f"total {key} no positivo")
    ep = total.get("ejecucion_pct")
    if ep is None or not (0 <= float(ep) <= 150):
        problems.append(f"ejecución global fuera de rango: {ep}")

    ctl = p.get("control") or {}
    if int(ctl.get("filas_ejecutado") or 0) < 1000:
        problems.append("muy pocas filas en presupuesto ejecutado")
    diff = ctl.get("diferencia_sancionado_pct")
    if diff is None or float(diff) > 1.0:
        problems.append(f"sancionado ejecutado vs archivo anual difiere {diff}% (>1%)")

    for group in ("jurisdicciones", "finalidades", "funciones", "incisos"):
        rows = p.get(group) or []
        if not rows:
            problems.append(f"apertura vacía: {group}")
            continue
        s = sum(float(x.get("devengado") or 0) for x in rows)
        base = float(total.get("devengado") or 0)
        rel = abs(s - base) / base * 100 if base else 0
        if rel > 0.01:
            problems.append(f"{group}: suma devengado difiere {rel:.4f}%")

    geo = p.get("geografia") or {}
    geo_rows = (geo.get("comunas") or []) + (geo.get("otros") or [])
    if not geo_rows:
        problems.append("apertura geográfica vacía")
    else:
        s = sum(float(x.get("devengado") or 0) for x in geo_rows)
        base = float(total.get("devengado") or 0)
        rel = abs(s - base) / base * 100 if base else 0
        if rel > 0.01:
            problems.append(f"geografía: suma devengado difiere {rel:.4f}%")

    fuentes = p.get("fuentes") or {}
    for k in ("ejecutado", "sancionado"):
        r = ((fuentes.get(k) or {}).get("resource") or {})
        if not r.get("id") or not r.get("url"):
            problems.append(f"fuente {k} sin trazabilidad de recurso")

    print(f"Presupuesto · {year} T{quarter} · {ctl.get('filas_ejecutado',0)} filas · ejecución {ep}%")
    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for x in problems:
            print(f"  · {x}")
        return 1
    print("✔ verificación presupuestaria superada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
