"""Genera presupuesto.json a partir de los CSV oficiales de BA Data.

El resumen conserva montos corrientes y produce aperturas para la web sin
publicar el archivo transaccional completo. No proyecta el cierre anual ni
interpreta la clasificación geográfica como gasto efectivamente localizado.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
WORK = BASE / "badata" / "presupuesto"
STATE = BASE / "estado_presupuesto.json"
OUT = BASE / "presupuesto.json"

METRICS = ("sancionado", "vigente", "definitivo", "devengado")


def norm(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def number(value: object) -> float:
    """Convierte números monetarios tolerando formatos AR, US y notación científica.

    BA Data ha publicado series con formatos distintos según recurso/exportación.
    Debemos aceptar, entre otros: 11035922029; 11035922029.0;
    11.035.922.029,00; 11,035,922,029.00 y 1.422609e+09.
    """
    if value is None:
        return 0.0
    s = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not s:
        return 0.0
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    s = re.sub(r"[^0-9,\.eE+\-]", "", s)
    if not s:
        return 0.0

    if "e" in s.lower():
        try:
            x = float(s.replace(",", "."))
            return -x if negative else (x if math.isfinite(x) else 0.0)
        except ValueError:
            return 0.0

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
            s = "".join(parts)
        elif len(parts) == 2 and len(parts[1]) == 3 and len(parts[0].lstrip("+-")) <= 3:
            s = "".join(parts)
        else:
            s = "".join(parts[:-1]) + "." + parts[-1]
    elif "." in s:
        parts = s.split(".")
        if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
            s = "".join(parts)
        elif len(parts) == 2 and len(parts[1]) == 3 and len(parts[0].lstrip("+-")) <= 3:
            s = "".join(parts)

    try:
        x = float(s)
        if negative:
            x = -abs(x)
        return x if math.isfinite(x) else 0.0
    except ValueError:
        return 0.0


def decode_csv(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    raise RuntimeError(f"No se pudo decodificar {path}")


def read_rows(path: Path):
    text = decode_csv(path)
    sample = text[:65536]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delim = dialect.delimiter
    except csv.Error:
        delim = ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    if not reader.fieldnames:
        raise RuntimeError(f"CSV sin encabezados: {path}")
    fields = {norm(x): x for x in reader.fieldnames if x is not None}
    for row in reader:
        yield fields, row


def pick(fields: dict[str, str], *aliases: str, prefix: str | None = None) -> str | None:
    """Busca una columna tolerando las distintas convenciones históricas de BA Data.

    Los recursos recientes usan encabezados como ``sancion`` o ``vigente...``.
    Algunos recursos históricos fueron exportados desde tablas dinámicas y usan
    encabezados como ``SumaDeSancion`` o ``SumaDeVigente_Trim2_Cont``. Primero
    priorizamos coincidencias exactas/prefijo y sólo después una coincidencia
    contenida, evitando columnas descriptivas.
    """
    for alias in aliases:
        key = norm(alias)
        if key in fields:
            return fields[key]
    if prefix:
        p = norm(prefix)
        for key, original in fields.items():
            if key.startswith(p):
                return original
        candidates = []
        for key, original in fields.items():
            if p not in key:
                continue
            if key.startswith(("desc_", "descripcion_")) or "_desc_" in key:
                continue
            # Las exportaciones históricas más comunes comienzan con sumade.
            # Se priorizan antes que cualquier otra coincidencia contenida.
            rank = 0 if key.startswith("sumade") else 1
            candidates.append((rank, len(key), key, original))
        if candidates:
            candidates.sort()
            return candidates[0][3]
    return None


def desc_field(fields: dict[str, str], short: str) -> str | None:
    return pick(fields, f"{short}_desc", f"desc_{short}")


def txt(row: dict, field: str | None, fallback: str = "Sin clasificar") -> str:
    if not field:
        return fallback
    value = str(row.get(field) or "").strip()
    return value or fallback


def agg_bucket() -> dict:
    return {m: 0.0 for m in METRICS}


def add(bucket: dict, vals: dict) -> None:
    for m in METRICS:
        bucket[m] += vals[m]


def finish(bucket: dict) -> dict:
    out = {m: round(float(bucket[m]), 2) for m in METRICS}
    out["modificaciones"] = round(out["vigente"] - out["sancionado"], 2)
    out["ejecucion_pct"] = round(out["devengado"] / out["vigente"] * 100, 2) if out["vigente"] else None
    out["definitivo_pct"] = round(out["definitivo"] / out["vigente"] * 100, 2) if out["vigente"] else None
    return out


def group_list(groups: dict[str, dict], *, top: int | None = None) -> list[dict]:
    rows = []
    for key, payload in groups.items():
        vals = finish(payload["metrics"])
        rows.append({"id": key, "nombre": payload["nombre"], **vals})
    rows.sort(key=lambda x: x["devengado"], reverse=True)
    return rows[:top] if top else rows


def add_group(groups: dict, key: str, name: str, vals: dict) -> None:
    if key not in groups:
        groups[key] = {"nombre": name, "metrics": agg_bucket()}
    add(groups[key]["metrics"], vals)


def process_executed(path: Path) -> tuple[dict, int, dict]:
    total = agg_bucket()
    groups = {name: {} for name in ("jurisdicciones", "finalidades", "funciones", "incisos", "geografia", "programas")}
    row_count = 0
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
                "inc": pick(fields, "inc", "inciso"), "inc_desc": pick(fields, "inc_desc", "desc_inc", "desc_inciso"),
                "prog": pick(fields, "prog"), "prog_desc": desc_field(fields, "prog"),
                "geo": pick(fields, "geo"), "geo_desc": desc_field(fields, "geo"),
            }
            missing = [m for m in METRICS if not selected[m]]
            if missing:
                raise RuntimeError(f"Faltan columnas monetarias en ejecutado: {missing}. Encabezados={list(fields)}")

        vals = {m: number(row.get(selected[m])) for m in METRICS}
        add(total, vals)
        row_count += 1

        jur_code = txt(row, selected["jur"], "s/c")
        jur_name = txt(row, selected["jur_desc"])
        add_group(groups["jurisdicciones"], jur_code, jur_name, vals)

        fin_code = txt(row, selected["fin"], "s/c")
        fin_name = txt(row, selected["fin_desc"])
        add_group(groups["finalidades"], fin_code, fin_name, vals)

        fun_code = f"{fin_code}-{txt(row, selected['fun'], 's/c')}"
        fun_name = txt(row, selected["fun_desc"])
        add_group(groups["funciones"], fun_code, fun_name, vals)

        inc_code = txt(row, selected["inc"], "s/c")
        inc_name = txt(row, selected["inc_desc"])
        add_group(groups["incisos"], inc_code, inc_name, vals)

        geo_code = txt(row, selected["geo"], "s/c")
        geo_name = txt(row, selected["geo_desc"])
        add_group(groups["geografia"], geo_code, geo_name, vals)

        prog_code = f"{jur_code}-{txt(row, selected['prog'], 's/c')}"
        prog_name = f"{jur_name} · {txt(row, selected['prog_desc'])}"
        add_group(groups["programas"], prog_code, prog_name, vals)

    if not row_count:
        raise RuntimeError("Presupuesto ejecutado sin filas")

    out_groups = {
        "jurisdicciones": group_list(groups["jurisdicciones"]),
        "finalidades": group_list(groups["finalidades"]),
        "funciones": group_list(groups["funciones"]),
        "incisos": group_list(groups["incisos"]),
        "geografia": group_list(groups["geografia"]),
        "programas_top": group_list(groups["programas"], top=100),
        "programas_total": len(groups["programas"]),
    }
    return finish(total), row_count, out_groups


def process_sanctioned(path: Path) -> tuple[float, int]:
    total = 0.0
    rows = 0
    money_field = None
    for fields, row in read_rows(path):
        if money_field is None:
            money_field = pick(fields, "sancion", prefix="sancion")
            if not money_field:
                raise RuntimeError(f"No se encontró columna sanción en {path}")
        total += number(row.get(money_field))
        rows += 1
    if not rows:
        raise RuntimeError("Presupuesto sancionado sin filas")
    return round(total, 2), rows


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    total, rows_exec, groups = process_executed(WORK / "ejecutado.csv")
    sanc_check, rows_sanc = process_sanctioned(WORK / "sancionado.csv")
    diff_pct = abs(total["sancionado"] - sanc_check) / sanc_check * 100 if sanc_check else None

    comunas = []
    otros_geo = []
    for row in groups["geografia"]:
        m = re.search(r"\bcomuna\s+(\d{1,2})\b", row["nombre"], flags=re.I)
        if m and 1 <= int(m.group(1)) <= 15:
            comunas.append({"comuna": int(m.group(1)), **row})
        else:
            otros_geo.append(row)
    comunas.sort(key=lambda x: x["comuna"])

    output = {
        "version": 1,
        "generado": state.get("descargado"),
        "ejercicio": state["ejercicio"],
        "trimestre": state["trimestre"],
        "periodo": f"{state['ejercicio']}-T{state['trimestre']}",
        "fuente": state.get("fuente"),
        "metodologia": {
            "moneda": "pesos corrientes",
            "ejecucion": "Devengado / crédito vigente",
            "alcance_total": "Suma de los créditos distribuidos por BA Data. Incluye gastos corrientes y de capital y aplicaciones financieras; por eso no debe compararse sólo con el artículo 1 de la Ley de Presupuesto.",
            "criterio_geografico": "Clasificación geográfica presupuestaria informada por la fuente. No equivale necesariamente a gasto físicamente materializado en cada comuna.",
            "proyeccion": "No se anualiza ni se proyecta el cierre del ejercicio.",
        },
        "total": total,
        "control": {
            "filas_ejecutado": rows_exec,
            "filas_sancionado": rows_sanc,
            "sancionado_archivo_anual": sanc_check,
            "diferencia_sancionado_pct": round(diff_pct, 4) if diff_pct is not None else None,
        },
        "jurisdicciones": groups["jurisdicciones"],
        "finalidades": groups["finalidades"],
        "funciones": groups["funciones"],
        "incisos": groups["incisos"],
        "programas_top": groups["programas_top"],
        "programas_total": groups["programas_total"],
        "geografia": {"comunas": comunas, "otros": otros_geo},
        "fuentes": {
            "ejecutado": state["dataset_ejecutado"],
            "sancionado": state["dataset_sancionado"],
        },
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"presupuesto.json · {OUT.stat().st_size//1024} KB · {state['ejercicio']} T{state['trimestre']} · {rows_exec:,} filas")
    print(f"  vigente: {total['vigente']/1e12:.3f} billones · devengado: {total['devengado']/1e12:.3f} billones · ejecución: {total['ejecucion_pct']:.2f}%")
    print(f"  control sancionado: {sanc_check/1e12:.3f} billones · diferencia {diff_pct:.4f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
