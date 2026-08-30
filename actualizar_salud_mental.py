#!/usr/bin/env python3
"""CEPOES · Monitor de Salud Mental V2.

Arquitectura de fuentes:
- Argentina: defunciones por suicidio DEIS (CIE-10 X60-X84 / Y87.0), 2005→último año.
- CABA: suicidios consumados SNIC-SAT, 2017→último año disponible.
- DEIS-CABA se conserva sólo como diagnóstico de calidad y NO como indicador
  reciente, debido a la advertencia oficial de DEIS sobre pérdida de atributos
  en la jurisdicción.

El pipeline falla cerrado si las bases cambian de esquema o si la extracción
SNIC no reproduce los puntos de control oficiales 2022-2024.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

DEIS_CKAN = "https://datos.salud.gob.ar/api/3/action/package_show?id=27c588e8-43d0-411a-a40c-7ecc563c2c9f"
SNIC_DIR = "https://cloud-snic.minseg.gob.ar/Bases/SAT/SS/"
SNIC_REPORT_2024 = "https://cloud-snic.minseg.gob.ar/Informes/SAT/SAT_SS/Informe_Suicidios_2024.pdf"
DEIS_REPORT_2024 = "https://www.argentina.gob.ar/sites/default/files/serie_5_nro_68_anuario_vitales_v4_revisada_ok.pdf"

OUT_ROOT = Path("salud_mental.json")
OUT_PUBLIC = Path("deploy/site-overlay/assets/data/salud-mental.json")
UA = "CEPOES-data-pipeline/2.0"

# INDEC · Proyecciones provinciales 2010-2040 (vintage utilizado por la V1).
# Sólo se usa para una tasa nacional CEPOES hasta 2024. No se usa para SNIC-CABA.
POP_ARG = {
    2010:40788453,2011:41261490,2012:41733271,2013:42202935,2014:42669500,
    2015:43131966,2016:43590368,2017:44044811,2018:44494502,2019:44938712,
    2020:45376763,2021:45808747,2022:46234830,2023:46654581,2024:47067641,
}
INDEC_URL = "https://www.indec.gob.ar/ftp/cuadros/publicaciones/proyecciones_prov_2010_2040.pdf"

# Puntos de control publicados en Tabla 4 del Informe SNIC-SAT 2024.
SNIC_CABA_CHECKPOINTS = {2022: 242, 2023: 184, 2024: 171}
SNIC_CABA_OFFICIAL_RATES_5PLUS = {2022: 8.4, 2023: 6.4, 2024: 5.9}
DEIS_NATIONAL_CHECKPOINTS = {2023: 3488, 2024: 3614}


def norm(value: object) -> str:
    x = unicodedata.normalize("NFKD", str(value or ""))
    x = x.encode("ascii", "ignore").decode("ascii").lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", x).strip("_")


def request(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url: str) -> dict:
    return json.loads(request(url, 60).decode("utf-8"))


def decode_csv(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise RuntimeError("No se pudo decodificar CSV")

    sample = text[:30000]
    try:
        delim = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        delim = ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    if not reader.fieldnames:
        raise RuntimeError("CSV sin encabezado")
    return list(reader.fieldnames), list(reader)


def pick_col(fields: list[str], exact=(), contains=()) -> str | None:
    mapped = {norm(f): f for f in fields}
    for key in exact:
        if key in mapped:
            return mapped[key]
    for f in fields:
        nf = norm(f)
        if any(token in nf for token in contains):
            return f
    return None


def to_year(value: object) -> int | None:
    s = str(value or "").strip()
    m = re.search(r"(?:19|20)\d{2}", s)
    return int(m.group(0)) if m else None


def to_count(value: object) -> int | None:
    if value is None:
        return None
    s = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not s:
        return None
    try:
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(".", "").replace(",", ".")
        v = float(s)
        if v < 0 or abs(v - round(v)) > 1e-6:
            return None
        return int(round(v))
    except Exception:
        return None


def is_suicide(value: object) -> bool:
    """DEIS: X60-X84 y secuelas Y87.0/Y870."""
    s = str(value or "").upper().replace(" ", "")
    if re.match(r"^X(?:6[0-9]|7[0-9]|8[0-4])(?:\.|$|[^0-9])", s):
        return True
    if s in {"Y87.0", "Y870"}:
        return True
    return False


def caba_value(value: object) -> bool:
    s = norm(value)
    return (
        s in {"2", "02", "002", "caba", "capital_federal"}
        or "ciudad_autonoma_de_buenos_aires" in s
    )


def rate(n: int, pop: int | None) -> float | None:
    return round(n / pop * 100000, 2) if pop else None


# ---------- DEIS: serie nacional + diagnóstico CABA ----------

def choose_deis_resources(pkg: dict) -> list[dict]:
    resources = pkg.get("resources", [])
    csvs = [
        r for r in resources
        if "csv" in str(r.get("format", "")).lower()
        or str(r.get("url", "")).lower().endswith(".csv")
    ]
    consolidated, annual = [], []
    for r in csvs:
        text = f"{r.get('name','')} {r.get('description','')} {r.get('url','')}"
        years = [int(y) for y in re.findall(r"20\d{2}", text)]
        if "2005" in text and years:
            consolidated.append((max(years), r))
        elif years:
            annual.append((max(years), r))

    if not consolidated:
        raise RuntimeError("DEIS: no se identificó recurso consolidado desde 2005")

    base_year, base = max(consolidated, key=lambda x: x[0])
    selected = [dict(base)]
    seen = set()
    for y, r in sorted(annual, key=lambda x: x[0]):
        if y <= base_year or y > datetime.now().year:
            continue
        if y in seen:
            continue
        rr = dict(r)
        rr["_year"] = y
        selected.append(rr)
        seen.add(y)
    return selected


def pick_deis_residence(fields: list[str]) -> tuple[str | None, str | None]:
    mapped = {norm(f): f for f in fields}
    name_keys = (
        "jurisdicion_residencia_nombre",  # typo real del recurso 2023/2024
        "jurisdiccion_residencia_nombre",
        "jurisdiccion_de_residencia_nombre",
        "provincia_residencia_nombre",
        "provincia_de_residencia_nombre",
        "prov_res",
    )
    id_keys = (
        "jurisdiccion_de_residencia_id",
        "jurisdiccion_residencia_id",
        "provincia_de_residencia_id",
        "provincia_residencia_id",
        "prov_res_id",
    )
    name_col = next((mapped[k] for k in name_keys if k in mapped), None)
    id_col = next((mapped[k] for k in id_keys if k in mapped), None)

    if not name_col:
        for f in fields:
            nf = norm(f)
            if "resid" in nf and any(x in nf for x in ("jurisd", "prov")) and not any(x in nf for x in ("_id", "cod", "codigo")):
                name_col = f
                break
    if not id_col:
        for f in fields:
            nf = norm(f)
            if "resid" in nf and any(x in nf for x in ("jurisd", "prov")) and any(x in nf for x in ("_id", "cod", "codigo")):
                id_col = f
                break
    return name_col, id_col


def process_deis(fields, rows, forced_year, national, caba_raw) -> dict:
    year_col = pick_col(fields, ("anio", "ano", "anio_defuncion", "ano_defuncion"), ("anio", "ano"))
    prov_col, prov_id_col = pick_deis_residence(fields)
    count_col = pick_col(fields, ("cantidad", "cant", "defunciones", "casos", "frecuencia"), ("cantidad", "defunc", "frecuenc"))
    cause_cols = [f for f in fields if any(t in norm(f) for t in ("causa", "cie"))]
    if not cause_cols:
        raise RuntimeError(f"DEIS: no se reconoce causa. Campos={fields}")
    if len(rows) < 150000 and not count_col:
        raise RuntimeError(f"DEIS: recurso agregado sin columna cantidad. Campos={fields}")

    matched_rows = 0
    matched_sum = 0
    caba_sum = 0
    count_failures = 0

    for row in rows:
        if not any(is_suicide(row.get(c, "")) for c in cause_cols):
            continue
        y = forced_year or (to_year(row.get(year_col)) if year_col else None)
        if not y or y < 2005:
            continue

        n = to_count(row.get(count_col)) if count_col else 1
        if n is None:
            count_failures += 1
            continue

        matched_rows += 1
        matched_sum += n
        national[y] += n

        is_caba = False
        if prov_id_col and caba_value(row.get(prov_id_col)):
            is_caba = True
        elif prov_col and caba_value(row.get(prov_col)):
            is_caba = True
        if is_caba:
            caba_raw[y] += n
            caba_sum += n

    return {
        "year": forced_year,
        "rows": len(rows),
        "suicide_rows": matched_rows,
        "suicide_sum": matched_sum,
        "caba_sum": caba_sum,
        "count_failures": count_failures,
        "columns": {
            "year": year_col,
            "residence": prov_col,
            "residence_id": prov_id_col,
            "count": count_col,
            "cause": cause_cols,
        },
    }


def load_deis() -> tuple[dict[int, int], dict[int, int], list[dict], list[dict]]:
    payload = get_json(DEIS_CKAN)
    if not payload.get("success"):
        raise RuntimeError("DEIS CKAN: success=false")
    resources = choose_deis_resources(payload["result"])
    national = defaultdict(int)
    caba_raw = defaultdict(int)
    diagnostics = []

    for r in resources:
        fields, rows = decode_csv(request(r["url"]))
        diag = process_deis(fields, rows, r.get("_year"), national, caba_raw)
        diag["name"] = r.get("name")
        diag["url"] = r.get("url")
        diagnostics.append(diag)
        if r.get("_year") in (2023, 2024):
            y = r["_year"]
            print(
                f"DEIS {y}: nacional={diag['suicide_sum']} · "
                f"CABA_raw={diag['caba_sum']} · filas_suicidio={diag['suicide_rows']}"
            )

    for y, expected in DEIS_NATIONAL_CHECKPOINTS.items():
        if national.get(y) != expected:
            raise RuntimeError(
                f"DEIS: punto de control nacional {y}={national.get(y)}; esperado={expected}"
            )

    return dict(national), dict(caba_raw), diagnostics, resources


# ---------- SNIC-SAT: serie CABA ----------

def discover_snic_csv() -> tuple[str, int, str]:
    html = request(SNIC_DIR, 60).decode("utf-8", "replace")
    matches = re.findall(
        r'href=["\']([^"\']*SAT-SS-BU_(20\d{2})-(20\d{2})\.csv)["\']',
        unescape(html),
        flags=re.I,
    )
    if not matches:
        # fallback actual conocido
        filename = "SAT-SS-BU_2017-2024.csv"
        return urljoin(SNIC_DIR, filename), 2024, filename

    candidates = sorted(
        ((int(end), href, start, end) for href, start, end in matches),
        reverse=True,
    )
    latest_end, href, start, end = candidates[0]
    return urljoin(SNIC_DIR, href), latest_end, f"SAT-SS-BU_{start}-{end}.csv"


def pick_snic_columns(fields: list[str]) -> dict[str, str | None]:
    year = pick_col(fields, ("anio", "ano", "year"), ("anio",))
    province_id = pick_col(
        fields,
        ("provincia_id", "jurisdiccion_id", "provincia_codigo", "jurisdiccion_codigo"),
        ("provincia_id", "jurisdiccion_id"),
    )
    province_name = pick_col(
        fields,
        ("provincia_nombre", "jurisdiccion_nombre", "provincia", "jurisdiccion"),
        ("provincia_nombre", "jurisdiccion_nombre"),
    )
    event_id = pick_col(
        fields,
        ("id_hecho", "hecho_id", "id_evento", "evento_id"),
        ("id_hecho", "hecho_id"),
    )
    role = pick_col(
        fields,
        ("rol", "rol_persona", "tipo_persona", "persona_rol", "tipo_involucrado"),
        ("rol_persona", "tipo_persona", "rol"),
    )
    return {
        "year": year,
        "province_id": province_id,
        "province_name": province_name,
        "event_id": event_id,
        "role": role,
    }


def role_is_suicide_victim(value: object) -> bool:
    s = norm(value)
    if not s:
        return False
    if "testig" in s:
        return False
    return any(t in s for t in ("suicid", "victim", "fallecid"))


def count_candidate(rows, cols, filter_role=False, unique=False) -> dict[int, int]:
    by_year = defaultdict(int)
    seen = defaultdict(set)

    for i, row in enumerate(rows):
        if cols["province_id"]:
            is_caba = caba_value(row.get(cols["province_id"]))
        else:
            is_caba = caba_value(row.get(cols["province_name"]))
        if not is_caba:
            continue

        if filter_role and cols["role"] and not role_is_suicide_victim(row.get(cols["role"])):
            continue

        y = to_year(row.get(cols["year"])) if cols["year"] else None
        if not y or y < 2017:
            continue

        if unique and cols["event_id"]:
            eid = str(row.get(cols["event_id"], "")).strip()
            if not eid:
                eid = f"__row_{i}"
            seen[y].add(eid)
        else:
            by_year[y] += 1

    if unique and cols["event_id"]:
        return {y: len(ids) for y, ids in seen.items()}
    return dict(by_year)


def checkpoint_score(series: dict[int, int]) -> tuple[bool, dict[int, dict]]:
    detail = {}
    ok = True
    for y, expected in SNIC_CABA_CHECKPOINTS.items():
        actual = series.get(y)
        same = actual == expected
        detail[y] = {"actual": actual, "expected": expected, "ok": same}
        ok = ok and same
    return ok, detail


def load_snic_caba() -> tuple[dict[int, int], dict]:
    url, advertised_end, filename = discover_snic_csv()
    raw = request(url, 180)
    fields, rows = decode_csv(raw)
    cols = pick_snic_columns(fields)

    if not cols["year"] or not (cols["province_id"] or cols["province_name"]):
        raise RuntimeError(f"SNIC-SAT: esquema territorial/año no reconocido. Campos={fields}")

    candidates = {}
    # Orden de preferencia: una fila/hecho único de víctima, luego hecho único,
    # luego filas de víctima, y por último todas las filas CABA.
    if cols["event_id"] and cols["role"]:
        candidates["unique_victim_event"] = count_candidate(rows, cols, filter_role=True, unique=True)
    if cols["event_id"]:
        candidates["unique_event"] = count_candidate(rows, cols, filter_role=False, unique=True)
    if cols["role"]:
        candidates["victim_rows"] = count_candidate(rows, cols, filter_role=True, unique=False)
    candidates["rows"] = count_candidate(rows, cols, filter_role=False, unique=False)

    diagnostics = {}
    selected_method = None
    selected = None
    for method, series in candidates.items():
        ok, detail = checkpoint_score(series)
        diagnostics[method] = {
            "checkpoints": detail,
            "years": sorted(series),
            "latest": series.get(max(series)) if series else None,
        }
        if ok and selected_method is None:
            selected_method = method
            selected = series

    if selected_method is None:
        print(json.dumps({
            "fields": fields,
            "columns": cols,
            "candidates": diagnostics,
            "rows": len(rows),
            "url": url,
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        raise RuntimeError(
            "SNIC-SAT: ningún método de conteo reproduce los puntos oficiales "
            "CABA 2022=242, 2023=184, 2024=171"
        )

    years = sorted(selected)
    if not years or min(years) > 2017 or max(years) < 2024:
        raise RuntimeError(f"SNIC-SAT: cobertura CABA insuficiente: {years}")

    print(
        f"SNIC-SAT: método={selected_method} · archivo={filename} · "
        f"CABA 2022={selected.get(2022)} · 2023={selected.get(2023)} · "
        f"2024={selected.get(2024)} · último={max(years)}"
    )

    return dict(selected), {
        "url": url,
        "filename": filename,
        "advertised_end_year": advertised_end,
        "rows": len(rows),
        "fields": fields,
        "columns": cols,
        "selected_method": selected_method,
        "candidate_validation": diagnostics,
    }


def main() -> None:
    deis_national, deis_caba_raw, deis_diag, deis_resources = load_deis()
    snic_caba, snic_diag = load_snic_caba()

    deis_years = sorted(y for y, n in deis_national.items() if n > 0)
    snic_years = sorted(y for y, n in snic_caba.items() if n > 0)

    if not deis_years or deis_years[0] > 2005 or deis_years[-1] < 2024:
        raise RuntimeError(f"DEIS: cobertura nacional inválida: {deis_years}")
    if not snic_years or snic_years[0] > 2017 or snic_years[-1] < 2024:
        raise RuntimeError(f"SNIC-SAT: cobertura CABA inválida: {snic_years}")

    argentina_series = [
        {
            "anio": y,
            "defunciones": deis_national[y],
            "tasa_100k_cepoes": rate(deis_national[y], POP_ARG.get(y)),
            "denominador": "INDEC proyecciones 2010-2040" if y in POP_ARG else None,
        }
        for y in range(2005, deis_years[-1] + 1)
        if deis_national.get(y, 0) > 0
    ]

    caba_series = [
        {
            "anio": y,
            "suicidios": snic_caba[y],
            "tasa_100k_mayores_5": SNIC_CABA_OFFICIAL_RATES_5PLUS.get(y),
            "tasa_fuente": (
                "Tabla 4 Informe SNIC-SAT 2024"
                if y in SNIC_CABA_OFFICIAL_RATES_5PLUS
                else None
            ),
        }
        for y in snic_years
    ]

    deis_caba_diag_series = [
        {"anio": y, "defunciones_codificadas_como_suicidio": deis_caba_raw.get(y, 0)}
        for y in sorted(deis_caba_raw)
    ]

    latest_arg = argentina_series[-1]
    latest_caba = caba_series[-1]
    change_22_24 = round((snic_caba[2024] / snic_caba[2022] - 1) * 100, 1)
    change_23_24 = round((snic_caba[2024] / snic_caba[2023] - 1) * 100, 1)

    output = {
        "schema": "cepoes-salud-mental-v2",
        "status": "VALIDADO",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Argentina y Ciudad Autónoma de Buenos Aires",
        "headline": {
            "argentina": {
                "anio": latest_arg["anio"],
                "defunciones_suicidio_deis": latest_arg["defunciones"],
                "tasa_100k_cepoes": latest_arg["tasa_100k_cepoes"],
            },
            "caba": {
                "anio": latest_caba["anio"],
                "suicidios_snic_sat": latest_caba["suicidios"],
                "tasa_100k_mayores_5": latest_caba["tasa_100k_mayores_5"],
                "variacion_2022_2024_pct": change_22_24,
                "variacion_2023_2024_pct": change_23_24,
            },
        },
        "series": {
            "argentina_deis": argentina_series,
            "caba_snic_sat": caba_series,
            "caba_deis_diagnostico": deis_caba_diag_series,
        },
        "methodology": {
            "argentina": (
                "Serie de defunciones por causa básica DEIS CIE-10 X60-X84 y Y87.0/Y870. "
                "La serie se utiliza a nivel nacional."
            ),
            "caba": (
                "Serie de suicidios consumados del Sistema Nacional de Información Criminal, "
                "módulo SAT-Suicidios. Es una fuente de ocurrencia/intervención de seguridad, "
                "no una estadística vital por residencia."
            ),
            "separacion_fuentes": (
                "No se fusionan DEIS y SNIC en una única serie. Para CABA, el dato DEIS reciente "
                "se conserva sólo como diagnóstico de calidad, no como indicador sustantivo."
            ),
            "tasas_caba": (
                "Las tasas CABA 2022-2024 son las publicadas por SNIC-SAT y usan población "
                "de 5 años y más. Para otros años la V2 publica conteos y deja la tasa nula "
                "hasta incorporar denominadores comparables validados."
            ),
            "advertencias": [
                (
                    "DEIS advierte pérdida de atributos particularmente notoria en CABA, "
                    "que resta validez al cálculo de algunos indicadores de esa jurisdicción."
                ),
                (
                    "SNIC-SAT no es exhaustivo: depende de la vinculación entre instituciones "
                    "de salud y seguridad y puede diferir de DEIS."
                ),
                (
                    "El Informe SNIC-SAT 2024 señala que CABA auditó 2022-2024 y que la "
                    "auditoría 2024 estaba en proceso, por lo que los valores pueden rectificarse."
                ),
                (
                    "Suicidios consumados no deben confundirse con intentos de suicidio "
                    "notificados al SNVS/BES."
                ),
            ],
        },
        "sources": {
            "deis": {
                "name": "DEIS · Defunciones ocurridas y registradas",
                "package_api": DEIS_CKAN,
                "annual_report_2024": DEIS_REPORT_2024,
                "resources_used": [
                    {"name": r.get("name"), "url": r.get("url")}
                    for r in deis_resources
                ],
            },
            "snic_sat": {
                "name": "SNIC · Sistema de Alerta Temprana Suicidios",
                "directory": SNIC_DIR,
                "csv": snic_diag["url"],
                "report_2024": SNIC_REPORT_2024,
            },
            "indec": {
                "name": "INDEC · Proyecciones provinciales de población 2010-2040",
                "url": INDEC_URL,
            },
        },
        "quality": {
            "deis_national_checkpoints": {
                str(y): {"actual": deis_national.get(y), "expected": n, "ok": deis_national.get(y) == n}
                for y, n in DEIS_NATIONAL_CHECKPOINTS.items()
            },
            "snic_caba_checkpoints": {
                str(y): {"actual": snic_caba.get(y), "expected": n, "ok": snic_caba.get(y) == n}
                for y, n in SNIC_CABA_CHECKPOINTS.items()
            },
            "snic_method": snic_diag["selected_method"],
            "snic_diagnostics": snic_diag,
            "deis_diagnostics": deis_diag,
            "deis_caba_recent_quality": "NO_VALIDO_PARA_INDICADOR",
        },
    }

    text = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
    for path in (OUT_ROOT, OUT_PUBLIC):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    print(
        f"Salud mental V2 · Argentina DEIS {latest_arg['anio']}={latest_arg['defunciones']} · "
        f"CABA SNIC {latest_caba['anio']}={latest_caba['suicidios']} · "
        f"CABA 2022→2024={change_22_24}%"
    )


if __name__ == "__main__":
    main()
