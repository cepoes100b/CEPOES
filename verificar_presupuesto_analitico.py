"""Controles de publicación para presupuesto_analitico.json."""
from __future__ import annotations
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ANA = BASE / "presupuesto_analitico.json"
CUR = BASE / "presupuesto.json"


def main() -> int:
    problems=[]
    if not ANA.exists() or not CUR.exists():
        print("✘ faltan archivos analíticos o presupuesto.json")
        return 1
    a=json.loads(ANA.read_text(encoding="utf-8")); p=json.loads(CUR.read_text(encoding="utf-8"))
    if a.get("periodo") != p.get("periodo"):
        problems.append(f"periodo analítico {a.get('periodo')} != presupuesto {p.get('periodo')}")
    rows=a.get("registros") or []
    if len(rows) < 100:
        problems.append(f"muy pocos registros jerárquicos: {len(rows)}")
    base=float((p.get("total") or {}).get("devengado") or 0)
    s=sum(float(x.get("devengado") or 0) for x in rows)
    rel=abs(s-base)/base*100 if base else 0
    if rel > 0.01:
        problems.append(f"drill-down: suma devengado difiere {rel:.4f}%")
    required=("jurisdiccion","finalidad","funcion","programa","vigente","devengado","modificaciones","ejecucion_pct")
    for i,x in enumerate(rows[:1000]):
        miss=[k for k in required if k not in x]
        if miss:
            problems.append(f"registro {i} sin {miss}")
            break
    print(f"Presupuesto analítico · {a.get('periodo')} · {len(rows):,} registros · cobertura {100-rel:.4f}%")
    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for x in problems: print(f"  · {x}")
        return 1
    print("✔ verificación analítica superada")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
