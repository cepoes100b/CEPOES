"""Controles de publicación para presupuesto_territorial.json."""
from __future__ import annotations

import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
PATH = BASE / "presupuesto_territorial.json"


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def main() -> int:
    problems = []
    if not PATH.exists():
        print("✘ falta presupuesto_territorial.json")
        return 1
    p = json.loads(PATH.read_text(encoding="utf-8"))
    rows = p.get("comunas") or []
    if len(rows) != 15:
        problems.append(f"se esperaban 15 comunas y hay {len(rows)}")
    ids = [int(x.get("comuna") or 0) for x in rows]
    if sorted(ids) != list(range(1, 16)):
        problems.append(f"identificadores de comuna inválidos: {ids}")

    totals = p.get("totales") or {}
    total_pop = float(totals.get("poblacion") or 0)
    classified = float(totals.get("devengado_clasificado_comunas") or 0)
    total_dev = float(totals.get("devengado_total") or 0)
    if total_pop < 2_000_000:
        problems.append(f"población total fuera de escala: {total_pop}")
    if classified <= 0 or total_dev <= 0 or classified > total_dev * 1.001:
        problems.append("totales presupuestarios territoriales inconsistentes")
    pct = totals.get("clasificado_comunas_pct_total")
    if pct is None or not (0 < float(pct) <= 100.1):
        problems.append(f"porcentaje clasificado inválido: {pct}")

    share_budget = 0.0
    share_pop = 0.0
    weighted_index = 0.0
    pc_ranks = set()
    gap_ranks = set()
    for x in rows:
        cid = x.get("comuna")
        pop = float(x.get("poblacion") or 0)
        if pop <= 0:
            problems.append(f"Comuna {cid}: población no positiva")
            continue
        t = x.get("territorio") or {}
        b = x.get("presupuesto") or {}
        dims = t.get("dimensiones") or {}
        if len(dims) != 10:
            problems.append(f"Comuna {cid}: {len(dims)} dimensiones, se esperaban 10")
        positions = int(t.get("dimensiones_debajo_caba") or 0) + int(t.get("dimensiones_cerca_caba") or 0) + int(t.get("dimensiones_encima_caba") or 0)
        if positions != 10:
            problems.append(f"Comuna {cid}: posiciones territoriales suman {positions}")
        pc = b.get("devengado_por_habitante")
        idx = b.get("indice_por_habitante_caba_100")
        if not finite(pc) or float(pc) <= 0 or not finite(idx) or float(idx) <= 0:
            problems.append(f"Comuna {cid}: clasificación por habitante inválida")
        sb = float(b.get("participacion_clasificacion_pct") or 0)
        sp = float(b.get("participacion_poblacion_pct") or 0)
        share_budget += sb
        share_pop += sp
        weighted_index += float(idx or 0) * sp / 100
        pc_ranks.add(int(b.get("ranking_por_habitante") or 0))
        gap_ranks.add(int(t.get("ranking_brechas_relativas") or 0))

    if abs(share_budget - 100) > 0.1:
        problems.append(f"participaciones presupuestarias suman {share_budget:.4f}%")
    if abs(share_pop - 100) > 0.1:
        problems.append(f"participaciones poblacionales suman {share_pop:.4f}%")
    if abs(weighted_index - 100) > 0.2:
        problems.append(f"índice por habitante ponderado no centra en 100: {weighted_index:.3f}")
    if pc_ranks != set(range(1, 16)):
        problems.append("ranking presupuestario incompleto")
    if gap_ranks != set(range(1, 16)):
        problems.append("ranking territorial incompleto")

    print(f"Presupuesto + territorio · {p.get('periodo')} · {len(rows)} comunas · clasificación {pct}%")
    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for problem in problems[:20]:
            print(f"  · {problem}")
        return 1
    print("✔ verificación presupuesto + territorio superada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
