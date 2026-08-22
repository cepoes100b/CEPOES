"""Genera diagnostico_presupuestario.json con señales descriptivas y reproducibles.

El producto identifica situaciones que merecen análisis a partir de reglas transparentes.
No califica políticas como buenas/malas ni infiere causalidad. En particular, la
clasificación geográfica presupuestaria NO se interpreta como inversión físicamente
realizada en una comuna ni como gasto sectorial destinado a resolver una brecha.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from statistics import median

BASE = Path(__file__).resolve().parent
BUDGET = BASE / "presupuesto.json"
HIST = BASE / "presupuesto_historico.json"
TERR = BASE / "presupuesto_territorial.json"
OUT = BASE / "diagnostico_presupuestario.json"


def num(v, default=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def norm(s):
    x = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", x).strip()


def pct_change(a, b):
    a = num(a); b = num(b)
    return (a / b - 1) * 100 if b else None


def aggregate_modifications(rows, total_sanc, level):
    eligible = []
    for r in rows or []:
        sanc = num(r.get("sancionado")); vig = num(r.get("vigente")); mod = num(r.get("modificaciones"), vig - sanc)
        if not (sanc or vig or mod):
            continue
        # Se descartan movimientos diminutos: deben representar al menos 0,15% del sancionado total
        # o una modificación absoluta de 0,25% del total.
        if max(abs(sanc), abs(vig)) < total_sanc * 0.0015 and abs(mod) < total_sanc * 0.0025:
            continue
        eligible.append({
            "nivel": level,
            "id": r.get("id"),
            "nombre": r.get("nombre") or "Sin denominación",
            "sancionado": sanc,
            "vigente": vig,
            "devengado": num(r.get("devengado")),
            "ejecucion_pct": r.get("ejecucion_pct"),
            "modificacion": mod,
            "modificacion_pct_sancionado": round(mod / sanc * 100, 2) if sanc else None,
        })
    increases = sorted((x for x in eligible if x["modificacion"] > 0), key=lambda x: x["modificacion"], reverse=True)[:8]
    cuts = sorted((x for x in eligible if x["modificacion"] < 0), key=lambda x: x["modificacion"])[:8]
    return increases, cuts


def execution_signals(functions, total_vig):
    # Comparación sólo entre funciones de escala material (>=0,75% del crédito vigente total).
    eligible = [r for r in (functions or []) if num(r.get("vigente")) >= total_vig * 0.0075 and r.get("ejecucion_pct") is not None]
    vals = [num(r.get("ejecucion_pct")) for r in eligible]
    med = median(vals) if vals else None
    out = []
    if med is None:
        return med, out
    for r in eligible:
        ep = num(r.get("ejecucion_pct")); delta = ep - med
        if abs(delta) < 8:
            continue
        out.append({
            "id": r.get("id"),
            "nombre": r.get("nombre") or "Sin denominación",
            "vigente": num(r.get("vigente")),
            "devengado": num(r.get("devengado")),
            "ejecucion_pct": round(ep, 2),
            "mediana_funciones_pct": round(med, 2),
            "diferencia_mediana_pp": round(delta, 2),
            "posicion": "por_encima" if delta > 0 else "por_debajo",
        })
    out.sort(key=lambda x: abs(x["diferencia_mediana_pp"]), reverse=True)
    return med, out[:10]


def interannual_signals(hist):
    periods = hist.get("periodos") or []
    if len(periods) < 2:
        return None, []
    cur = periods[-1]
    y = int(cur.get("ejercicio") or 0); q = int(cur.get("trimestre") or 0)
    prev = next((p for p in periods if int(p.get("ejercicio") or 0) == y - 1 and int(p.get("trimestre") or 0) == q), None)
    if not prev:
        return None, []
    prev_map = {norm(x.get("nombre")): x for x in (prev.get("funciones") or []) if norm(x.get("nombre"))}
    total_vig = num((cur.get("total") or {}).get("vigente"))
    out = []
    for r in cur.get("funciones") or []:
        k = norm(r.get("nombre")); old = prev_map.get(k)
        if not old or num(r.get("vigente")) < total_vig * 0.0075:
            continue
        now_ep = r.get("ejecucion_pct"); old_ep = old.get("ejecucion_pct")
        if now_ep is None or old_ep is None:
            continue
        delta = num(now_ep) - num(old_ep)
        yoy_dev = pct_change(r.get("devengado"), old.get("devengado"))
        if abs(delta) < 5:
            continue
        out.append({
            "id": r.get("id"),
            "nombre": r.get("nombre") or "Sin denominación",
            "periodo_actual": cur.get("periodo"),
            "periodo_comparacion": prev.get("periodo"),
            "ejecucion_actual_pct": round(num(now_ep), 2),
            "ejecucion_anterior_pct": round(num(old_ep), 2),
            "diferencia_ejecucion_pp": round(delta, 2),
            "variacion_nominal_devengado_pct": round(yoy_dev, 2) if yoy_dev is not None else None,
        })
    out.sort(key=lambda x: abs(x["diferencia_ejecucion_pp"]), reverse=True)
    return prev.get("periodo"), out[:10]


def territorial_signals(terr):
    rows = terr.get("comunas") or []
    out = []
    for r in rows:
        t = r.get("territorio") or {}; b = r.get("presupuesto") or {}
        below = int(t.get("dimensiones_debajo_caba") or 0)
        budget_idx = b.get("indice_por_habitante_caba_100")
        med_idx = t.get("indice_mediano_caba_100")
        if below < 5:
            continue
        # Priorización para lectura: amplitud de brechas + baja posición territorial mediana
        # + clasificación presupuestaria por habitante por debajo del promedio. No es causal.
        score = below * 10 + max(0, 100 - num(med_idx)) * 0.35 + max(0, 100 - num(budget_idx)) * 0.20
        weakest = []
        for key, d in ((t.get("dimensiones") or {}).items()):
            idx = d.get("indice_caba_100")
            if idx is not None and num(idx) < 95:
                weakest.append({"id": key, "label": d.get("label") or key, "indice_caba_100": round(num(idx), 2)})
        weakest.sort(key=lambda x: x["indice_caba_100"])
        out.append({
            "comuna": int(r.get("comuna") or 0),
            "nombre": r.get("nombre"),
            "dimensiones_debajo_caba": below,
            "indice_territorial_mediano_caba_100": med_idx,
            "indice_presupuestario_por_habitante_caba_100": budget_idx,
            "ejecucion_pct": b.get("ejecucion_pct"),
            "dimensiones_mas_rezagadas": weakest[:4],
            "puntaje_prioridad_lectura": round(score, 2),
        })
    out.sort(key=lambda x: x["puntaje_prioridad_lectura"], reverse=True)
    return out[:8]


def geography_concentration(terr):
    rows = sorted(terr.get("comunas") or [], key=lambda x: num((x.get("presupuesto") or {}).get("participacion_clasificacion_pct")), reverse=True)
    top = []
    for r in rows[:5]:
        b = r.get("presupuesto") or {}
        top.append({
            "comuna": r.get("comuna"),
            "nombre": r.get("nombre"),
            "participacion_clasificacion_pct": b.get("participacion_clasificacion_pct"),
            "participacion_poblacion_pct": b.get("participacion_poblacion_pct"),
            "indice_participacion_caba_100": b.get("indice_participacion_caba_100"),
        })
    return top


def main():
    for p in (BUDGET, HIST, TERR):
        if not p.exists():
            raise SystemExit(f"Falta {p.name}")
    budget = json.loads(BUDGET.read_text(encoding="utf-8"))
    hist = json.loads(HIST.read_text(encoding="utf-8"))
    terr = json.loads(TERR.read_text(encoding="utf-8"))
    total = budget.get("total") or {}
    total_sanc = num(total.get("sancionado")); total_vig = num(total.get("vigente"))

    jur_inc, jur_cut = aggregate_modifications(budget.get("jurisdicciones"), total_sanc, "jurisdiccion")
    fun_inc, fun_cut = aggregate_modifications(budget.get("funciones"), total_sanc, "funcion")
    exec_median, exec_sig = execution_signals(budget.get("funciones"), total_vig)
    prev_period, yoy_sig = interannual_signals(hist)
    terr_sig = territorial_signals(terr)
    geo_top = geography_concentration(terr)

    out = {
        "version": 1,
        "generado": budget.get("generado"),
        "periodo": budget.get("periodo"),
        "fuente": "BA Data · Ministerio de Hacienda y Finanzas GCBA + fuentes territoriales oficiales procesadas por CEPOES",
        "metodologia": {
            "naturaleza": "Señales automáticas basadas en reglas explícitas para priorizar análisis. No constituyen evaluación causal ni juicio de desempeño.",
            "modificaciones": "Se destacan movimientos de escala material en crédito vigente respecto del sancionado. Un aumento o reducción no implica por sí mismo una valoración positiva o negativa.",
            "ejecucion_relativa": "Se comparan funciones de escala material con la mediana de ejecución de funciones en el mismo trimestre. Diferencias temporales pueden responder al perfil propio de cada gasto.",
            "interanual": "Se compara el porcentaje de ejecución contra el mismo trimestre del año anterior cuando la denominación funcional es comparable. Los montos interanuales se expresan nominalmente.",
            "territorio": "La coexistencia de brechas de Oferta territorial y una posición presupuestaria por habitante se usa sólo para priorizar preguntas. La clasificación geográfica NO equivale a inversión físicamente realizada ni a gasto sectorial destinado a resolver esas brechas.",
            "concentracion": "La participación comunal refiere a clasificación geográfica informada por la fuente; no se redistribuyen partidas con otras clasificaciones.",
        },
        "resumen": {
            "ejecucion_total_pct": total.get("ejecucion_pct"),
            "modificaciones_totales": total.get("modificaciones"),
            "mediana_ejecucion_funciones_pct": round(exec_median, 2) if exec_median is not None else None,
            "periodo_comparacion_interanual": prev_period,
            "senales_territoriales": len(terr_sig),
            "senales_ejecucion": len(exec_sig),
            "senales_interanuales": len(yoy_sig),
        },
        "modificaciones": {
            "jurisdicciones_mayores_ampliaciones": jur_inc,
            "jurisdicciones_mayores_reducciones": jur_cut,
            "funciones_mayores_ampliaciones": fun_inc,
            "funciones_mayores_reducciones": fun_cut,
        },
        "ejecucion_relativa": exec_sig,
        "interanual": yoy_sig,
        "territorio": terr_sig,
        "concentracion_geografica": geo_top,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"diagnostico_presupuestario.json · {OUT.stat().st_size//1024} KB · {budget.get('periodo')}")
    print(f"  territorio: {len(terr_sig)} · ejecución: {len(exec_sig)} · interanual: {len(yoy_sig)}")
    print(f"  modificaciones: {len(jur_inc)+len(jur_cut)+len(fun_inc)+len(fun_cut)} señales")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
