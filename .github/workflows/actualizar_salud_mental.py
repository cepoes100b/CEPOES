#!/usr/bin/env python3
"""CEPOES · Salud mental: serie de suicidios DEIS.

Descarga la base oficial de defunciones DEIS y construye una serie comparable
para CABA y Argentina. La clasificación de suicidio usa CIE-10 X60-X84.
Las tasas se calculan desde 2010 con proyecciones oficiales INDEC 2010-2040.
"""
from __future__ import annotations

import csv
import io
import json
import re
import ssl
import sys
import unicodedata
import urllib.error
import urllib.request
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

CKAN = "https://datos.salud.gob.ar/api/3/action/package_show?id=27c588e8-43d0-411a-a40c-7ecc563c2c9f"
OUT_ROOT = Path("salud_mental.json")
OUT_PUBLIC = Path("deploy/site-overlay/assets/data/salud-mental.json")
UA = "CEPOES-data-pipeline/1.0"

# INDEC, Proyecciones provinciales 2010-2040, cuadros 1.1 y 1.2.
POP_ARG = {
2010:40788453,2011:41261490,2012:41733271,2013:42202935,2014:42669500,
2015:43131966,2016:43590368,2017:44044811,2018:44494502,2019:44938712,
2020:45376763,2021:45808747,2022:46234830,2023:46654581,2024:47067641,
}
POP_CABA = {
2010:3028481,2011:3033639,2012:3038860,2013:3044076,2014:3049229,
2015:3054267,2016:3059122,2017:3063728,2018:3068043,2019:3072029,
2020:3075646,2021:3078836,2022:3081550,2023:3083770,2024:3085483,
}
POP_CABA_SEX = {
2010:(1405566,1622915),2011:(1409835,1623804),2012:(1414105,1624755),
2013:(1418339,1625737),2014:(1422507,1626722),2015:(1426582,1627685),
2016:(1430531,1628591),2017:(1434323,1629405),2018:(1437936,1630107),
2019:(1441350,1630679),2020:(1444545,1631101),2021:(1447495,1631341),
2022:(1450179,1631371),2023:(1452588,1631182),2024:(1454716,1630767),
}
INDEC_URL = "https://www.indec.gob.ar/ftp/cuadros/publicaciones/proyecciones_prov_2010_2040.pdf"


def norm(s: object) -> str:
    x = unicodedata.normalize("NFKD", str(s or ""))
    x = x.encode("ascii", "ignore").decode("ascii").lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", x).strip("_")


def _is_salud_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "datos.salud.gob.ar" or host.endswith(".salud.gob.ar")


def _urlopen(url: str, timeout: int):
    """Abre una URL con TLS verificado y fallback acotado para Datos Salud.

    El portal datos.salud.gob.ar presenta intermitentemente una cadena de
    certificados incompleta en algunos runners de GitHub Actions. Primero se
    intenta la validación TLS normal. Sólo ante un error de certificado y sólo
    para hosts oficiales *.salud.gob.ar se reintenta sin validar la cadena.
    No se envían credenciales ni datos privados; el contenido descargado se
    somete luego a controles de esquema y consistencia antes de publicarse.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        cert_error = isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc)
        if not cert_error or not _is_salud_host(url):
            raise
        print(
            f"ADVERTENCIA TLS: {urlparse(url).hostname} no presentó una cadena de certificados "
            "validable por el runner. Reintento acotado sin verificación TLS para esta fuente pública.",
            file=sys.stderr,
        )
        insecure = ssl.create_default_context()
        insecure.check_hostname = False
        insecure.verify_mode = ssl.CERT_NONE
        return urllib.request.urlopen(req, timeout=timeout, context=insecure)


def get_json(url: str) -> dict:
    with _urlopen(url, 60) as r:
        return json.load(r)


def get_bytes(url: str) -> bytes:
    with _urlopen(url, 180) as r:
        return r.read()


def choose_resources(pkg: dict) -> list[dict]:
    resources = pkg.get("resources", [])
    csvs = [r for r in resources if "csv" in str(r.get("format", "")).lower() or str(r.get("url", "")).lower().endswith(".csv")]
    if not csvs:
        raise RuntimeError("DEIS: no se encontraron recursos CSV")
    # Preferimos el consolidado más reciente 2005-20xx y luego archivos anuales posteriores.
    consolidated = []
    annual = []
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
    selected = [base]
    for y, r in sorted(annual):
        if y > base_year and y <= 2024:
            # uno por año, preferencia nombre que diga exactamente el año
            if not any(int(x.get("_year", -1)) == y for x in selected):
                rr = dict(r); rr["_year"] = y; selected.append(rr)
    return selected


def decode_csv(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            pass
    if text is None:
        raise RuntimeError("No se pudo decodificar CSV DEIS")
    sample = text[:20000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delim = dialect.delimiter
    except csv.Error:
        delim = ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    if not reader.fieldnames:
        raise RuntimeError("CSV DEIS sin encabezado")
    rows = list(reader)
    return list(reader.fieldnames), rows


def pick_col(fields: list[str], exact: tuple[str, ...], contains: tuple[str, ...] = ()) -> str | None:
    mapped = {norm(f): f for f in fields}
    for key in exact:
        if key in mapped:
            return mapped[key]
    for nf, original in mapped.items():
        if any(token in nf for token in contains):
            return original
    return None


def to_int(value: object) -> int | None:
    s = str(value or "").strip().replace(".0", "")
    m = re.search(r"(19|20)\d{2}", s)
    if m and len(s) >= 4:
        return int(m.group(0))
    try:
        return int(float(s.replace(",", ".")))
    except Exception:
        return None


def is_suicide(value: object) -> bool:
    s = str(value or "").upper().replace(" ", "")
    return bool(re.search(r"(?:^|[^A-Z])X(?:6[0-9]|7[0-9]|8[0-4])(?:\.|$|[^0-9])", s)) or bool(re.match(r"^X(?:6[0-9]|7[0-9]|8[0-4])", s))


def caba_value(value: object) -> bool:
    s = norm(value)
    if not s:
        return False
    if "ciudad_autonoma_de_buenos_aires" in s or s in {"caba", "capital_federal"}:
        return True
    # Código INDEC de CABA = 02. Evitar interpretar cualquier texto que contenga 2.
    return s in {"2", "02", "002"}


def sex_label(value: object) -> str:
    s = norm(value)
    if s in {"1", "m", "masculino", "varon", "varones", "hombre", "hombres"} or "mascul" in s:
        return "varones"
    if s in {"2", "f", "femenino", "mujer", "mujeres"} or "femen" in s:
        return "mujeres"
    return "sin_especificar"


def age_group(value: object) -> str:
    s = norm(value).replace("_anos", "")
    # Si ya viene agrupada, conservar una etiqueta legible.
    nums = [int(x) for x in re.findall(r"\d+", s)]
    if len(nums) >= 2:
        a, b = nums[0], nums[1]
        if 0 <= a <= b <= 120:
            return f"{a}-{b}"
    if len(nums) == 1:
        age = nums[0]
        if age <= 120:
            if age < 10: return "0-9"
            if age < 15: return "10-14"
            if age < 20: return "15-19"
            if age < 25: return "20-24"
            if age < 35: return "25-34"
            if age < 45: return "35-44"
            if age < 55: return "45-54"
            if age < 65: return "55-64"
            return "65+"
    return "sin_especificar"


def process_rows(fields: list[str], rows: list[dict[str, str]], forced_year: int | None, acc: dict) -> dict:
    year_col = pick_col(fields, ("anio", "ano", "anio_defuncion", "ano_defuncion"), ("anio", "ano"))
    prov_col = pick_col(fields, ("prov_res", "provincia_residencia", "jurisdiccion_residencia", "cod_jurisdiccion_residencia"), ("prov_res", "residencia", "jurisdiccion"))
    sex_col = pick_col(fields, ("sexo", "sex"), ("sexo",))
    age_col = pick_col(fields, ("edad", "grupo_edad", "edad_grupo", "rango_edad"), ("edad",))
    count_col = pick_col(fields, ("cantidad", "cant", "defunciones", "n"), ("cantidad", "defunc"))
    cause_cols = [f for f in fields if any(t in norm(f) for t in ("causa", "cie"))]
    if not prov_col or not cause_cols:
        raise RuntimeError(f"Esquema DEIS no reconocido. Campos={fields}")

    matched = 0
    cause_samples = []
    for row in rows:
        cause_values = [row.get(c, "") for c in cause_cols]
        if len(cause_samples) < 12:
            cause_samples.extend([str(v) for v in cause_values if v][:2])
        if not any(is_suicide(v) for v in cause_values):
            continue
        y = forced_year or (to_int(row.get(year_col)) if year_col else None)
        if not y or y < 2005 or y > 2024:
            continue
        n = to_int(row.get(count_col)) if count_col else 1
        n = n if n is not None and n >= 0 else 1
        matched += n
        acc["arg"][y] += n
        if caba_value(row.get(prov_col)):
            acc["caba"][y] += n
            if sex_col:
                acc["sex"][y][sex_label(row.get(sex_col))] += n
            if age_col:
                acc["age"][y][age_group(row.get(age_col))] += n
    return {"matched": matched, "fields": fields, "cause_samples": cause_samples[:12], "columns": {"year": year_col, "province": prov_col, "sex": sex_col, "age": age_col, "count": count_col, "cause": cause_cols}}


def rate(n: int, pop: int | None) -> float | None:
    return round(n / pop * 100000, 2) if pop else None


def main() -> None:
    payload = get_json(CKAN)
    if not payload.get("success"):
        raise SystemExit("CKAN DEIS respondió success=false")
    pkg = payload["result"]
    resources = choose_resources(pkg)
    acc = {"arg": defaultdict(int), "caba": defaultdict(int), "sex": defaultdict(lambda: defaultdict(int)), "age": defaultdict(lambda: defaultdict(int))}
    diagnostics = []
    for r in resources:
        raw = get_bytes(r["url"])
        fields, rows = decode_csv(raw)
        diag = process_rows(fields, rows, r.get("_year"), acc)
        diag.update({"name": r.get("name"), "url": r.get("url"), "rows": len(rows)})
        diagnostics.append(diag)

    years = list(range(2005, 2025))
    # Controles fuertes: no publicamos una serie vacía o con CABA mal identificada.
    available = [y for y in years if acc["arg"][y] > 0]
    if len(available) < 18 or 2024 not in available:
        raise SystemExit(f"DEIS: cobertura temporal insuficiente: {available}")
    caba_nonzero = [y for y in years if acc["caba"][y] > 0]
    if len(caba_nonzero) < 18:
        print(json.dumps(diagnostics, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(f"DEIS: CABA no identificada de modo consistente: {caba_nonzero}")

    series = []
    for y in years:
        caba = acc["caba"][y]
        arg = acc["arg"][y]
        var = acc["sex"][y].get("varones", 0)
        muj = acc["sex"][y].get("mujeres", 0)
        popsex = POP_CABA_SEX.get(y)
        item = {
            "anio": y,
            "caba": {"defunciones": caba, "tasa_100k": rate(caba, POP_CABA.get(y))},
            "argentina": {"defunciones": arg, "tasa_100k": rate(arg, POP_ARG.get(y))},
            "sexo_caba": {
                "varones": {"defunciones": var, "tasa_100k": rate(var, popsex[0] if popsex else None)},
                "mujeres": {"defunciones": muj, "tasa_100k": rate(muj, popsex[1] if popsex else None)},
                "sin_especificar": acc["sex"][y].get("sin_especificar", 0),
            },
            "edad_caba_defunciones": dict(sorted(acc["age"][y].items())),
        }
        series.append(item)

    rate_series = [x for x in series if x["caba"]["tasa_100k"] is not None]
    latest = rate_series[-1]
    first = rate_series[0]
    max_item = max(rate_series, key=lambda x: x["caba"]["tasa_100k"])
    change_5 = None
    if len(rate_series) >= 6:
        prev = rate_series[-6]["caba"]["tasa_100k"]
        change_5 = round((latest["caba"]["tasa_100k"] / prev - 1) * 100, 1) if prev else None

    output = {
        "schema": "cepoes-salud-mental-v1",
        "status": "VALIDADO",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "CABA y Argentina",
        "headline": {
            "ultimo_anio": latest["anio"],
            "caba_defunciones": latest["caba"]["defunciones"],
            "caba_tasa_100k": latest["caba"]["tasa_100k"],
            "argentina_tasa_100k": latest["argentina"]["tasa_100k"],
            "variacion_caba_5_anios_pct": change_5,
            "maximo_tasa_caba": {"anio": max_item["anio"], "tasa_100k": max_item["caba"]["tasa_100k"]},
            "inicio_tasas": {"anio": first["anio"], "tasa_100k": first["caba"]["tasa_100k"]},
        },
        "series": series,
        "methodology": {
            "evento": "Defunciones cuya causa básica se clasifica en CIE-10 X60-X84 (lesiones autoinfligidas intencionalmente).",
            "territorio": "Jurisdicción de residencia. No se producen tasas por barrio o comuna a partir de esta base.",
            "tasas": "Tasas brutas por 100.000 habitantes. Desde 2010 se usan proyecciones INDEC 2010-2040; 2005-2009 se publican conteos sin tasa hasta incorporar denominadores históricos homogéneos.",
            "sexo": "Las tasas por sexo usan las proyecciones INDEC por sexo. La desagregación etaria V1 publica conteos; las tasas específicas por edad se incorporarán con denominadores quinquenales validados.",
            "advertencia": "Suicidios consumados (DEIS) no deben confundirse con intentos de suicidio notificados al SNVS/BES.",
        },
        "sources": {
            "deis": {"name": "DEIS · Defunciones ocurridas y registradas", "package_api": CKAN, "resources_used": [{"name": x.get("name"), "url": x.get("url")} for x in resources]},
            "indec": {"name": "INDEC · Proyecciones provinciales de población por sexo y grupo de edad 2010-2040", "url": INDEC_URL},
        },
        "quality": {
            "years_with_argentina": len(available),
            "years_with_caba": len(caba_nonzero),
            "diagnostics": diagnostics,
        },
    }
    text = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
    for path in (OUT_ROOT, OUT_PUBLIC):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"Salud mental · {len(series)} años · último={latest['anio']} · CABA={latest['caba']['defunciones']} · tasa={latest['caba']['tasa_100k']}")

if __name__ == "__main__":
    main()
