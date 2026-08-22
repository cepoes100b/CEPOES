"""Genera presupuesto_analitico.json para drill-down, modificaciones y radar.

El archivo deriva exclusivamente del último CSV oficial ya descargado por
`descargar_presupuesto.py`. No altera `presupuesto.json`: agrega una capa
analítica orientada a navegación jerárquica y rankings.
"""
from __future__ import annotations

import json
from pathlib import Path

from generar_presupuesto import (
    METRICS, add, agg_bucket, finish, number, pick, read_rows, desc_field, txt,
)

BASE = Path(__file__).resolve().parent
WORK = BASE / "badata" / "presupuesto"
STATE = BASE / "estado_presupuesto.json"
OUT = BASE / "presupuesto_analitico.json"


def add_drill(groups: dict, key: tuple[str, ...], meta: dict, vals: dict) -> None:
    if key not in groups:
        groups[key] = {"meta": meta, "metrics": agg_bucket()}
    add(groups[key]["metrics"], vals)


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    path = WORK / "ejecutado.csv"
    drill: dict[tuple[str, ...], dict] = {}
    rows = 0
    selected = None

    for fields, row in read_rows(path):
        if selected is None:
            selected = {
                "sancionado": pick(fields, "sancion", prefix="sancion"),
                "vigente": pick(fields, prefix="vigente"),
                "definitivo": pick(fields, prefix="definitivo"),
                "devengado": pick(fields, prefix="devengado"),
                "jur": pick(fields, "jur"), "jur_desc": desc_field(fields, "jur"),
                "fin": pick(fields, "fin"), "fin_desc": desc_field(fields, "fin"),
                "fun": pick(fields, "fun"), "fun_desc": desc_field(fields, "fun"),
                "prog": pick(fields, "prog"), "prog_desc": desc_field(fields, "prog"),
            }
            missing = [m for m in METRICS if not selected[m]]
            if missing:
                raise RuntimeError(f"Faltan columnas monetarias: {missing}")

        vals = {m: number(row.get(selected[m])) for m in METRICS}
        jur_id = txt(row, selected["jur"], "s/c")
        jur = txt(row, selected["jur_desc"])
        fin_id = txt(row, selected["fin"], "s/c")
        fin = txt(row, selected["fin_desc"])
        fun_short = txt(row, selected["fun"], "s/c")
        fun_id = f"{fin_id}-{fun_short}"
        fun = txt(row, selected["fun_desc"])
        prog_id = txt(row, selected["prog"], "s/c")
        prog = txt(row, selected["prog_desc"])
        key = (jur_id, fin_id, fun_id, prog_id, jur, fin, fun, prog)
        add_drill(drill, key, {
            "jurisdiccion_id": jur_id, "jurisdiccion": jur,
            "finalidad_id": fin_id, "finalidad": fin,
            "funcion_id": fun_id, "funcion": fun,
            "programa_id": prog_id, "programa": prog,
        }, vals)
        rows += 1

    records = []
    for payload in drill.values():
        x = {**payload["meta"], **finish(payload["metrics"])}
        sanc = float(x.get("sancionado") or 0)
        x["modificacion_pct_sancionado"] = round(float(x["modificaciones"]) / sanc * 100, 2) if sanc else None
        records.append(x)
    records.sort(key=lambda x: float(x.get("devengado") or 0), reverse=True)

    output = {
        "version": 1,
        "generado": state.get("descargado"),
        "ejercicio": state["ejercicio"],
        "trimestre": state["trimestre"],
        "periodo": f"{state['ejercicio']}-T{state['trimestre']}",
        "fuente": state.get("fuente"),
        "metodologia": {
            "modificaciones": "Crédito vigente menos crédito sancionado.",
            "ejecucion": "Devengado / crédito vigente.",
            "drilldown": "Agregación por jurisdicción → finalidad → función → programa a partir del máximo nivel de desagregación de BA Data.",
        },
        "filas_origen": rows,
        "registros": records,
        "fuente_recurso": state["dataset_ejecutado"]["resource"],
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"presupuesto_analitico.json · {OUT.stat().st_size//1024} KB · {len(records):,} combinaciones jerárquicas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
