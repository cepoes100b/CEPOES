"""Controles para presupuesto_historico.json."""
from __future__ import annotations
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
HIST=BASE/"presupuesto_historico.json"
CUR=BASE/"presupuesto.json"

def main()->int:
    problems=[]
    if not HIST.exists() or not CUR.exists():
        print("✘ faltan presupuesto_historico.json o presupuesto.json"); return 1
    h=json.loads(HIST.read_text(encoding="utf-8")); c=json.loads(CUR.read_text(encoding="utf-8"))
    rows=h.get("periodos") or []
    if len(rows)<6: problems.append(f"serie demasiado corta: {len(rows)} períodos")
    keys=[(int(x.get("ejercicio") or 0),int(x.get("trimestre") or 0)) for x in rows]
    if keys!=sorted(keys): problems.append("períodos fuera de orden")
    if len(set(x.get("periodo") for x in rows))!=len(rows): problems.append("períodos duplicados")
    if rows and rows[-1].get("periodo")!=c.get("periodo"):
        problems.append(f"último histórico {rows[-1].get('periodo')} != actual {c.get('periodo')}")
    for x in rows:
        t=x.get("total") or {}; dev=float(t.get("devengado") or 0); vig=float(t.get("vigente") or 0)
        if dev<=0 or vig<=0: problems.append(f"{x.get('periodo')}: totales no positivos"); continue
        ep=t.get("ejecucion_pct")
        if ep is None or not (0<=float(ep)<=180): problems.append(f"{x.get('periodo')}: ejecución fuera de rango {ep}")
        for group in ("jurisdicciones","finalidades","funciones","incisos"):
            s=sum(float(z.get("devengado") or 0) for z in x.get(group) or [])
            rel=abs(s-dev)/dev*100
            if rel>0.01:
                problems.append(f"{x.get('periodo')} {group}: suma difiere {rel:.4f}%")
                break
    print(f"Presupuesto histórico · {len(rows)} períodos · {rows[0].get('periodo') if rows else '?'} → {rows[-1].get('periodo') if rows else '?'}")
    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for p in problems[:20]: print(f"  · {p}")
        return 1
    print("✔ verificación histórica superada")
    return 0

if __name__=="__main__": raise SystemExit(main())
