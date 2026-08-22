"""Controles de consistencia para diagnostico_presupuestario.json."""
from __future__ import annotations
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
DIAG=BASE/"diagnostico_presupuestario.json"
BUDGET=BASE/"presupuesto.json"
TERR=BASE/"presupuesto_territorial.json"

def main()->int:
    problems=[]
    if not DIAG.exists() or not BUDGET.exists() or not TERR.exists():
        print("✘ faltan archivos para verificar diagnóstico"); return 1
    d=json.loads(DIAG.read_text(encoding="utf-8")); b=json.loads(BUDGET.read_text(encoding="utf-8")); t=json.loads(TERR.read_text(encoding="utf-8"))
    if d.get("periodo")!=b.get("periodo") or d.get("periodo")!=t.get("periodo"):
        problems.append("períodos no coinciden")
    m=d.get("metodologia") or {}
    if "NO equivale" not in str(m.get("territorio") or ""):
        problems.append("falta cautela territorial explícita")
    terr=d.get("territorio") or []
    if len(terr)<3: problems.append(f"pocas señales territoriales: {len(terr)}")
    seen=set()
    for x in terr:
        cid=int(x.get("comuna") or 0)
        if not 1<=cid<=15: problems.append(f"comuna inválida: {cid}")
        if cid in seen: problems.append(f"comuna duplicada: {cid}")
        seen.add(cid)
        if int(x.get("dimensiones_debajo_caba") or 0)<5: problems.append(f"C{cid}: señal territorial sin umbral de brecha")
    mods=d.get("modificaciones") or {}
    if not (mods.get("jurisdicciones_mayores_ampliaciones") or []): problems.append("sin ampliaciones jurisdiccionales")
    if not (mods.get("funciones_mayores_ampliaciones") or []): problems.append("sin ampliaciones funcionales")
    execs=d.get("ejecucion_relativa") or []
    for x in execs:
        if abs(float(x.get("diferencia_mediana_pp") or 0))<7.99: problems.append("señal de ejecución por debajo del umbral")
    geo=d.get("concentracion_geografica") or []
    if len(geo)!=5: problems.append(f"ranking geográfico incompleto: {len(geo)}")
    shares=[float(x.get("participacion_clasificacion_pct") or 0) for x in geo]
    if shares!=sorted(shares,reverse=True): problems.append("ranking geográfico fuera de orden")
    if d.get("resumen",{}).get("ejecucion_total_pct")!=b.get("total",{}).get("ejecucion_pct"):
        problems.append("ejecución total no coincide con presupuesto.json")
    print(f"Diagnóstico presupuestario · {d.get('periodo')} · {len(terr)} territoriales · {len(execs)} ejecución relativa · {len(d.get('interanual') or [])} interanuales")
    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for p in problems[:25]: print(f"  · {p}")
        return 1
    print("✔ verificación de diagnóstico superada")
    return 0

if __name__=="__main__": raise SystemExit(main())
