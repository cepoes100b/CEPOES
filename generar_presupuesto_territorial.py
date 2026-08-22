"""Cruza clasificación geográfica presupuestaria y radiografía territorial por comuna.

El producto NO interpreta la clasificación geográfica como inversión físicamente
materializada. Combina dos lentes descriptivas independientes: (a) partidas cuya
clasificación presupuestaria oficial es Comuna 1..15 y (b) disponibilidad relativa
de oferta territorial construida a partir de fuentes oficiales procesadas por CEPOES.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
BUDGET = BASE / "presupuesto.json"
TERR = BASE / "equipamientos" / "resumen-territorial.json"
OUT = BASE / "presupuesto_territorial.json"

DIMENSIONS = [
    "educacion", "salud", "mayores", "infancias", "cultura",
    "deporte", "seguridad", "movilidad", "servicios", "ambiente",
]
NEAR_TOL = 5.0


def num(v, default=0.0) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def caba_refs(summary: dict) -> tuple[int, dict[str, float]]:
    comunas = summary.get("comunas") or {}
    total_pop = sum(int((c or {}).get("poblacion") or 0) for c in comunas.values())
    refs: dict[str, float] = {}
    if total_pop <= 0:
        return 0, refs
    for dim in DIMENSIONS:
        if dim == "ambiente":
            total_m2 = sum(num(((c.get("destacados") or {}).get("ambiente") or {}).get("m2")) for c in comunas.values())
            refs[dim] = total_m2 / total_pop if total_m2 > 0 else 0.0
        else:
            total = sum(num(((c.get("destacados") or {}).get(dim) or {}).get("valor")) for c in comunas.values())
            refs[dim] = total / total_pop * 10000 if total > 0 else 0.0
    return total_pop, refs


def dim_value(scope: dict, dim: str) -> float | None:
    d = ((scope.get("destacados") or {}).get(dim) or {})
    value = d.get("m2_hab") if dim == "ambiente" else d.get("tasa_10k")
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def position(index: float | None) -> str:
    if index is None:
        return "sin_dato"
    if index < 100 - NEAR_TOL:
        return "debajo"
    if index > 100 + NEAR_TOL:
        return "encima"
    return "cerca"


def main() -> int:
    if not BUDGET.exists() or not TERR.exists():
        raise SystemExit("Faltan presupuesto.json o equipamientos/resumen-territorial.json")
    current = json.loads(BUDGET.read_text(encoding="utf-8"))
    terr = json.loads(TERR.read_text(encoding="utf-8"))

    geo = current.get("geografia") or {}
    cur_geo: dict[int, dict] = {}
    for row in geo.get("comunas") or []:
        try:
            cid = int(row.get("comuna") or 0)
        except (TypeError, ValueError):
            cid = 0
        if 1 <= cid <= 15:
            cur_geo[cid] = row

    total_pop, refs = caba_refs(terr)
    if total_pop <= 0:
        raise SystemExit("Población territorial no válida")

    classified_dev = sum(num((cur_geo.get(cid) or {}).get("devengado")) for cid in range(1, 16))
    total_dev = num((current.get("total") or {}).get("devengado"))
    avg_pc = classified_dev / total_pop if classified_dev > 0 else 0.0

    rows = []
    terr_comunas = terr.get("comunas") or {}
    for cid in range(1, 16):
        scope = terr_comunas.get(str(cid)) or {}
        pop = int(scope.get("poblacion") or 0)
        b = cur_geo.get(cid) or {}
        dev = num(b.get("devengado"))
        vig = num(b.get("vigente"))
        sanc = num(b.get("sancionado"))
        exec_pct = b.get("ejecucion_pct")
        pc = dev / pop if pop > 0 else None
        pc_index = pc / avg_pc * 100 if pc is not None and avg_pc > 0 else None
        pop_share = pop / total_pop * 100 if total_pop else None
        budget_share = dev / classified_dev * 100 if classified_dev else None
        share_index = budget_share / pop_share * 100 if pop_share and budget_share is not None else None

        dims = {}
        below = near = above = 0
        valid_indexes = []
        for dim in DIMENSIONS:
            value = dim_value(scope, dim)
            ref = refs.get(dim) or 0.0
            idx = value / ref * 100 if value is not None and ref > 0 else None
            pos = position(idx)
            if pos == "debajo":
                below += 1
            elif pos == "cerca":
                near += 1
            elif pos == "encima":
                above += 1
            if idx is not None:
                valid_indexes.append(idx)
            meta = ((scope.get("destacados") or {}).get(dim) or {})
            dims[dim] = {
                "label": meta.get("label") or dim,
                "valor": value,
                "referencia_caba": round(ref, 4) if ref else None,
                "indice_caba_100": round(idx, 2) if idx is not None else None,
                "posicion": pos,
            }

        valid_indexes.sort()
        med = None
        if valid_indexes:
            n = len(valid_indexes)
            med = valid_indexes[n // 2] if n % 2 else (valid_indexes[n // 2 - 1] + valid_indexes[n // 2]) / 2

        rows.append({
            "comuna": cid,
            "nombre": f"Comuna {cid}",
            "poblacion": pop,
            "territorio": {
                "dimensiones": dims,
                "dimensiones_debajo_caba": below,
                "dimensiones_cerca_caba": near,
                "dimensiones_encima_caba": above,
                "indice_mediano_caba_100": round(med, 2) if med is not None else None,
            },
            "presupuesto": {
                "sancionado": sanc,
                "vigente": vig,
                "devengado": dev,
                "ejecucion_pct": exec_pct,
                "devengado_por_habitante": round(pc, 2) if pc is not None else None,
                "indice_por_habitante_caba_100": round(pc_index, 2) if pc_index is not None else None,
                "participacion_clasificacion_pct": round(budget_share, 4) if budget_share is not None else None,
                "participacion_poblacion_pct": round(pop_share, 4) if pop_share is not None else None,
                "indice_participacion_caba_100": round(share_index, 2) if share_index is not None else None,
            },
        })

    by_pc = sorted(rows, key=lambda x: (num(x["presupuesto"].get("devengado_por_habitante")), -x["comuna"]), reverse=True)
    for rank, row in enumerate(by_pc, 1):
        row["presupuesto"]["ranking_por_habitante"] = rank
    by_gap = sorted(rows, key=lambda x: (-int(x["territorio"]["dimensiones_debajo_caba"]), num(x["territorio"].get("indice_mediano_caba_100")), x["comuna"]))
    for rank, row in enumerate(by_gap, 1):
        row["territorio"]["ranking_brechas_relativas"] = rank

    out = {
        "version": 1,
        "generado": current.get("generado"),
        "periodo": current.get("periodo"),
        "fuentes": {
            "presupuesto": "BA Data · Presupuesto Ejecutado",
            "territorio": terr.get("fuente"),
        },
        "metodologia": {
            "unidad_presupuestaria": "Clasificación geográfica presupuestaria Comuna 1..15. No equivale necesariamente a gasto o inversión físicamente materializada en la comuna.",
            "denominador_presupuestario": "Los índices por habitante comparan únicamente el devengado clasificado como Comuna 1..15; no distribuyen las partidas con otra clasificación geográfica.",
            "oferta_territorial": "Cada dimensión compara su tasa por población con la referencia CABA=100; espacio verde usa m² por habitante. Las dimensiones miden objetos diferentes y no se suman como cantidades homogéneas.",
            "posicion_territorial": "Debajo: índice <95; cerca: 95 a 105; encima: >105 respecto de CABA=100.",
            "lectura_conjunta": "La coexistencia de brechas territoriales y determinada clasificación presupuestaria no demuestra causalidad, suficiencia, necesidad ni impacto del gasto.",
        },
        "referencias_caba": {k: round(v, 4) for k, v in refs.items()},
        "totales": {
            "poblacion": total_pop,
            "devengado_total": round(total_dev, 2),
            "devengado_clasificado_comunas": round(classified_dev, 2),
            "clasificado_comunas_pct_total": round(classified_dev / total_dev * 100, 2) if total_dev else None,
            "devengado_clasificado_promedio_por_habitante": round(avg_pc, 2) if avg_pc else None,
        },
        "comunas": rows,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"presupuesto_territorial.json · {OUT.stat().st_size//1024} KB · {len(rows)} comunas · {current.get('periodo')}")
    print(f"  clasificación Comuna 1–15: {classified_dev/1e12:.3f} billones · {out['totales']['clasificado_comunas_pct_total']:.2f}% del devengado total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
