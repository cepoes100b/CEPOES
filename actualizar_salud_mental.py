#!/usr/bin/env python3
"""CEPOES · Salud Mental · pipeline V3.

Fuente principal:
- Sistema Nacional de Información Criminal (SNIC), bases usuarias oficiales
  agregadas a nivel país y provincia. Código 31: suicidios consumados.
- Serie principal: 2016-2025.
- Red de atención CABA: CeSAC con Psicología/Psiquiatría desde la capa oficial
  ya descargada por CEPOES + cinco efectores especializados vigentes.

Fuente de contraste:
- DEIS, defunciones por suicidio (CIE-10 X60-X84/Y87.0), mantenida separada.
  Si datos.salud.gob.ar no responde o cambia de esquema, se conserva el último
  contraste DEIS previamente validado en salud_mental.json.

El pipeline falla cerrado para la fuente principal SNIC si no reproduce los
puntos oficiales 2025 o si las 24 jurisdicciones no suman el total nacional.
"""
from __future__ import annotations

import csv
import io
import json
import re
import ssl
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SNIC_PAIS_URL = "https://cloud-snic.minseg.gob.ar/Bases/SNIC/snic-pais.csv"
SNIC_PROVINCIAS_URL = "https://cloud-snic.minseg.gob.ar/Bases/SNIC/snic-provincias.csv"
SNIC_MANUAL_URL = "https://cloud-snic.minseg.gob.ar/Bases/SNIC/Manual_de_usuario_Base_SNIC.pdf"
SNIC_REPORT_2025 = "https://cloud-snic.minseg.gob.ar/Informes/SNIC/Informe_SNIC_Nacional_2025.pdf"

DEIS_CKAN = "https://datos.salud.gob.ar/api/3/action/package_show?id=27c588e8-43d0-411a-a40c-7ecc563c2c9f"
DEIS_REPORT_2024 = "https://www.argentina.gob.ar/sites/default/files/serie_5_nro_68_anuario_vitales_v4_revisada_ok.pdf"

OUT_ROOT = Path("salud_mental.json")
OUT_PUBLIC = Path("deploy/site-overlay/assets/data/salud-mental.json")
CESAC_CSV = Path("badata/cesac.csv")
UA = "CEPOES-data-pipeline/3.0 (+https://cepoes.org)"

EXPECTED_ARG = {
    2016: 2897,
    2017: 3304,
    2018: 3903,
    2019: 3647,
    2020: 3262,
    2021: 3648,
    2022: 3959,
    2023: 4205,
    2024: 4249,
    2025: 5209,
}
EXPECTED_ARG_2025_RATE = 11.84
EXPECTED_CABA_2024 = 171
EXPECTED_CABA_2025 = 236
EXPECTED_CABA_2025_RATE = 7.97
EXPECTED_JURISDICTIONS = 24
EXPECTED_JURISDICTIONS_SUM = 5209
EXPECTED_MIN_CESAC_SM = 43

PBA_BREAK_NOTE = (
    "La Provincia de Buenos Aires informó mejoras en sus sistemas de carga y en el "
    "intercambio con la Procuración General provincial y otros organismos, incluido "
    "el cruce con registros de defunciones. El Informe SNIC 2025 caracteriza el "
    "cambio como una ruptura de serie para varias categorías, en particular las "
    "muertes violentas que incluyen suicidios; por eso no se recomiendan comparaciones "
    "interanuales ni históricas para la provincia en las categorías afectadas."
)

EFFECTORS = [
    {
        "nombre": "Hospital de Emergencias Psiquiátricas Torcuato de Alvear",
        "tipo": "hospital_especializado_salud_mental",
        "direccion": "Warnes 2630",
        "barrio": "Agronomía",
    },
    {
        "nombre": "Hospital de Salud Mental J. T. Borda",
        "tipo": "hospital_especializado_salud_mental",
        "direccion": "Dr. Ramón Carrillo 375",
        "barrio": "Barracas",
    },
    {
        "nombre": "Hospital de Salud Mental Braulio Moyano",
        "tipo": "hospital_especializado_salud_mental",
        "direccion": "Brandsen 2570",
        "barrio": "Barracas",
    },
    {
        "nombre": "Hospital Infanto Juvenil C. Tobar García",
        "tipo": "hospital_especializado_salud_mental",
        "direccion": "Dr. Ramón Carrillo 315",
        "barrio": "Barracas",
    },
    {
        "nombre": "Centro de Salud Mental N° 3 Dr. Arturo Ameghino",
        "tipo": "centro_especializado_salud_mental",
        "direccion": "Av. Córdoba 3120",
        "comuna": 3,
    },
]

ASSISTANCE = [
    {
        "nombre": "Orientación y Apoyo en la Urgencia de Salud Mental",
        "telefono": "0800-999-0091",
        "alcance": "nacional",
        "disponibilidad": "24 horas, 365 días",
        "fuente": "https://www.argentina.gob.ar/node/492429",
    },
    {
        "nombre": "SAME",
        "telefono": "107",
        "alcance": "Ciudad Autónoma de Buenos Aires",
        "tipo": "emergencias",
        "fuente": "https://buenosaires.gob.ar/salud",
    },
]

EFFECTORS_SOURCE = (
    "https://boletinoficial.buenosaires.gob.ar/normativaba/norma/843807"
)
CESAC_SOURCE = (
    "https://data.buenosaires.gob.ar/dataset/"
    "centros-salud-accion-comunitaria-cesac"
)


def norm(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or ""))
    s = s.encode("ascii", "ignore").decode("ascii").lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def request_bytes(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json,text/csv,text/plain,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.URLError as exc:
        host = (urlparse(url).hostname or "").lower()
        reason = getattr(exc, "reason", None)
        tls_error = isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc)
        if tls_error and (host == "datos.salud.gob.ar" or host.endswith(".salud.gob.ar")):
            # Workaround acotado al host oficial de Salud; SNIC y cualquier otro
            # dominio siguen usando validación TLS normal.
            print(f"ADVERTENCIA TLS: reintento acotado para {host}")
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return r.read()
        raise


def get_json(url: str) -> dict:
    return json.loads(request_bytes(url, 60).decode("utf-8"))


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
    sample = text[:40000]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise RuntimeError("CSV sin encabezado")
    return list(reader.fieldnames), list(reader)


def canonical(row: dict[str, object]) -> dict[str, object]:
    return {norm(k): v for k, v in row.items()}


def to_year(value: object) -> int | None:
    m = re.search(r"(?:19|20)\d{2}", str(value or ""))
    return int(m.group(0)) if m else None


def to_float(value: object) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not s or norm(s) in {"nan", "na", "none", "s_d", "sd"}:
        return None
    try:
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except ValueError:
        return None


def to_int(value: object) -> int | None:
    if value is None:
        return None
    s = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not s:
        return None
    # Para cantidades, "5.209" o "5,209" puede ser separador de miles.
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):
        s = re.sub(r"[.,]", "", s)
    v = to_float(s)
    if v is None or v < 0 or abs(v - round(v)) > 1e-6:
        return None
    return int(round(v))


def field(row: dict[str, object], *names: str) -> object:
    c = canonical(row)
    for name in names:
        key = norm(name)
        if key in c:
            return c[key]
    return None


def is_suicide_snic(row: dict[str, object]) -> bool:
    code = str(field(row, "codigo_delito_snic_id") or "").strip()
    code = re.sub(r"\.0+$", "", code)
    name = norm(field(row, "codigo_delito_snic_nombre"))
    return code == "31" or "suicid" in name


def get_count(row: dict[str, object]) -> int | None:
    # Para código 31 hechos y víctimas deben coincidir, pero se prioriza víctimas.
    return (
        to_int(field(row, "cantidad_victimas"))
        if field(row, "cantidad_victimas") not in (None, "")
        else to_int(field(row, "cantidad_hechos"))
    )


def get_rate(row: dict[str, object]) -> float | None:
    v = field(row, "tasa_victimas")
    if v in (None, ""):
        v = field(row, "tasa_hechos")
    x = to_float(v)
    return round(x, 2) if x is not None else None


def load_snic() -> tuple[list[dict], list[dict], list[dict], dict]:
    _, pais_rows = decode_csv(request_bytes(SNIC_PAIS_URL))
    _, prov_rows = decode_csv(request_bytes(SNIC_PROVINCIAS_URL))

    nat: dict[int, dict] = {}
    for row in pais_rows:
        if not is_suicide_snic(row):
            continue
        y = to_year(field(row, "anio"))
        if not y or y < 2016 or y > 2025:
            continue
        count = get_count(row)
        rate = get_rate(row)
        if count is None:
            continue
        item = {"anio": y, "suicidios": count, "tasa_100k_mayores_5": rate}
        if y in nat and nat[y]["suicidios"] != count:
            raise RuntimeError(f"SNIC país: duplicado inconsistente para {y}")
        nat[y] = item

    missing = [y for y in range(2016, 2026) if y not in nat]
    if missing:
        raise RuntimeError(f"SNIC país: faltan años 2016-2025: {missing}")

    for y, expected in EXPECTED_ARG.items():
        actual = nat[y]["suicidios"]
        if actual != expected:
            raise RuntimeError(f"SNIC país {y}: {actual} != {expected}")

    rate_arg = nat[2025]["tasa_100k_mayores_5"]
    if rate_arg is None or abs(rate_arg - EXPECTED_ARG_2025_RATE) > 0.06:
        raise RuntimeError(
            f"SNIC país 2025 tasa: {rate_arg} incompatible con {EXPECTED_ARG_2025_RATE}"
        )

    provinces_2025 = []
    caba_series: dict[int, dict] = {}
    seen_2025 = set()

    for row in prov_rows:
        if not is_suicide_snic(row):
            continue
        y = to_year(field(row, "anio"))
        if not y or y < 2016 or y > 2025:
            continue
        name = str(field(row, "provincia_nombre") or "").strip()
        pid = str(field(row, "provincia_id") or "").strip()
        count = get_count(row)
        rate = get_rate(row)
        if not name or count is None:
            continue

        nn = norm(name)
        is_caba = (
            nn in {"caba", "capital_federal"}
            or "ciudad_autonoma_de_buenos_aires" in nn
            or pid in {"2", "02"}
        )
        if is_caba:
            caba_series[y] = {
                "anio": y,
                "suicidios": count,
                "tasa_100k_mayores_5": rate,
            }

        if y == 2025:
            key = (pid, nn)
            if key in seen_2025:
                raise RuntimeError(f"SNIC provincias: jurisdicción 2025 duplicada: {name}")
            seen_2025.add(key)
            provinces_2025.append(
                {
                    "provincia_id": pid,
                    "provincia": name,
                    "suicidios_2025": count,
                    "tasa_100k_mayores_5_2025": rate,
                }
            )

    if len(provinces_2025) != EXPECTED_JURISDICTIONS:
        raise RuntimeError(
            f"SNIC provincias 2025: {len(provinces_2025)} jurisdicciones; "
            f"esperadas={EXPECTED_JURISDICTIONS}"
        )
    prov_sum = sum(x["suicidios_2025"] for x in provinces_2025)
    if prov_sum != EXPECTED_JURISDICTIONS_SUM:
        raise RuntimeError(
            f"SNIC provincias 2025: suma={prov_sum}; esperado={EXPECTED_JURISDICTIONS_SUM}"
        )

    if caba_series.get(2024, {}).get("suicidios") != EXPECTED_CABA_2024:
        raise RuntimeError(
            f"SNIC CABA 2024: {caba_series.get(2024)}; esperado={EXPECTED_CABA_2024}"
        )
    if caba_series.get(2025, {}).get("suicidios") != EXPECTED_CABA_2025:
        raise RuntimeError(
            f"SNIC CABA 2025: {caba_series.get(2025)}; esperado={EXPECTED_CABA_2025}"
        )
    caba_rate = caba_series[2025]["tasa_100k_mayores_5"]
    if caba_rate is None or abs(caba_rate - EXPECTED_CABA_2025_RATE) > 0.06:
        raise RuntimeError(
            f"SNIC CABA 2025 tasa: {caba_rate} incompatible con {EXPECTED_CABA_2025_RATE}"
        )

    caba_var = round(
        (caba_series[2025]["suicidios"] / caba_series[2024]["suicidios"] - 1) * 100,
        1,
    )
    if caba_var != 38.0:
        raise RuntimeError(f"SNIC CABA variación 2025/2024: {caba_var} != 38.0")

    provinces_2025.sort(key=lambda x: norm(x["provincia"]))
    pba = next(
        (
            x
            for x in provinces_2025
            if norm(x["provincia"]) in {"buenos_aires", "provincia_de_buenos_aires"}
        ),
        None,
    )
    if pba:
        pba["comparabilidad"] = "RUPTURA_DE_SERIE_2025"
        pba["advertencia"] = PBA_BREAK_NOTE

    diagnostics = {
        "pais_rows": len(pais_rows),
        "provincias_rows": len(prov_rows),
        "jurisdicciones_2025": len(provinces_2025),
        "suma_jurisdicciones_2025": prov_sum,
        "argentina_2025": nat[2025],
        "caba_2025": caba_series[2025],
        "caba_variacion_2025_2024_pct": caba_var,
    }
    return (
        [nat[y] for y in sorted(nat)],
        [caba_series[y] for y in sorted(caba_series)],
        provinces_2025,
        diagnostics,
    )


def is_suicide_deis(value: object) -> bool:
    s = str(value or "").upper().replace(" ", "")
    if re.match(r"^X(?:6[0-9]|7[0-9]|8[0-4])(?:\.|$|[^0-9])", s):
        return True
    return s in {"Y87.0", "Y870"}


def choose_deis_resources(pkg: dict) -> list[dict]:
    resources = pkg.get("resources") or []
    csvs = [
        r
        for r in resources
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
        if y <= base_year or y in seen or y > datetime.now().year:
            continue
        rr = dict(r)
        rr["_year"] = y
        selected.append(rr)
        seen.add(y)
    return selected


def load_deis_national() -> tuple[list[dict], list[dict]]:
    payload = get_json(DEIS_CKAN)
    if not payload.get("success"):
        raise RuntimeError("DEIS CKAN respondió success=false")
    resources = choose_deis_resources(payload["result"])
    acc = defaultdict(int)
    diagnostics = []

    for res in resources:
        fields, rows = decode_csv(request_bytes(res["url"]))
        nfields = {norm(f): f for f in fields}
        year_col = next(
            (nfields[k] for k in ("anio", "ano", "anio_defuncion", "ano_defuncion") if k in nfields),
            None,
        )
        count_col = next(
            (nfields[k] for k in ("cantidad", "cant", "defunciones", "casos", "frecuencia") if k in nfields),
            None,
        )
        cause_cols = [f for f in fields if "cie" in norm(f) or "causa" in norm(f)]
        if not cause_cols:
            raise RuntimeError(f"DEIS: no se reconocen columnas de causa: {fields}")

        matched = 0
        for row in rows:
            if not any(is_suicide_deis(row.get(c)) for c in cause_cols):
                continue
            y = res.get("_year") or (to_year(row.get(year_col)) if year_col else None)
            if not y or y < 2005:
                continue
            n = to_int(row.get(count_col)) if count_col else 1
            if n is None:
                continue
            acc[y] += n
            matched += n

        diagnostics.append(
            {
                "name": res.get("name"),
                "url": res.get("url"),
                "year_forced": res.get("_year"),
                "rows": len(rows),
                "suicidios_sumados": matched,
            }
        )

    if acc.get(2023) != 3488 or acc.get(2024) != 3614:
        raise RuntimeError(
            f"DEIS checkpoints fallaron: 2023={acc.get(2023)}, 2024={acc.get(2024)}"
        )
    years = [y for y in sorted(acc) if 2005 <= y <= datetime.now().year and acc[y] > 0]
    if not years or years[0] > 2005 or years[-1] < 2024:
        raise RuntimeError(f"DEIS cobertura insuficiente: {years[:2]}…{years[-2:] if years else []}")

    series = [{"anio": y, "defunciones": acc[y]} for y in years]
    return series, diagnostics


def load_previous() -> dict:
    if not OUT_ROOT.exists():
        return {}
    try:
        return json.loads(OUT_ROOT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def previous_deis_series(previous: dict) -> list[dict]:
    if not previous:
        return []
    contrast = previous.get("contraste_deis") or {}
    if isinstance(contrast.get("serie_nacional"), list) and contrast["serie_nacional"]:
        return contrast["serie_nacional"]
    series = previous.get("series") or {}
    old = series.get("argentina_deis")
    return old if isinstance(old, list) else []


def load_deis_with_fallback(previous: dict) -> dict:
    try:
        series, diagnostics = load_deis_national()
        return {
            "estado": "ACTUALIZADO",
            "serie_nacional": series,
            "ultimo_anio": series[-1]["anio"],
            "diagnostico": diagnostics,
            "fuente": DEIS_CKAN,
            "nota": (
                "DEIS se conserva como contraste separado de la serie principal SNIC; "
                "no se fusionan ambas fuentes."
            ),
        }
    except Exception as exc:
        old = previous_deis_series(previous)
        if not old:
            raise RuntimeError(
                f"DEIS falló y no existe último dato validado para conservar: {exc}"
            ) from exc
        print(f"DEIS no disponible; se conserva último dato validado: {type(exc).__name__}: {exc}")
        return {
            "estado": "ULTIMO_DATO_VALIDADO",
            "serie_nacional": old,
            "ultimo_anio": old[-1].get("anio"),
            "error_actualizacion": f"{type(exc).__name__}: {exc}",
            "fuente": DEIS_CKAN,
            "nota": (
                "El servidor DEIS no pudo actualizarse en esta corrida. Se reutiliza "
                "la última serie DEIS previamente validada. La serie principal SNIC "
                "no depende de este fallback."
            ),
        }


def load_cesac_salud_mental() -> list[dict]:
    if not CESAC_CSV.exists():
        raise RuntimeError(f"Falta {CESAC_CSV}; ejecutar primero la actualización territorial")
    raw = CESAC_CSV.read_bytes()
    fields, rows = decode_csv(raw)
    out = []
    for row in rows:
        c = canonical(row)
        specialties = str(c.get("especialid") or c.get("especialidades") or "")
        ns = norm(specialties)
        if "psicolog" not in ns and "psiquiatr" not in ns:
            continue
        out.append(
            {
                "id": str(c.get("id") or "").strip(),
                "nombre": str(c.get("nombre") or "").strip(),
                "direccion": str(c.get("direccion") or "").strip(),
                "barrio": str(c.get("barrio") or "").strip(),
                "comuna": str(c.get("comuna") or "").strip(),
                "telefono": str(c.get("telefono") or "").strip(),
                "web": str(c.get("web") or "").strip(),
                "area_programatica": str(c.get("area_progr") or "").strip(),
                "especialidades": specialties.strip(),
                "geometry": str(c.get("geometry") or "").strip(),
            }
        )
    if len(out) < EXPECTED_MIN_CESAC_SM:
        raise RuntimeError(
            f"CeSAC con oferta de salud mental: {len(out)}; mínimo esperado={EXPECTED_MIN_CESAC_SM}"
        )
    out.sort(key=lambda x: (norm(x["barrio"]), norm(x["nombre"])))
    return out


def main() -> None:
    previous = load_previous()

    argentina, caba, jurisdictions, snic_diag = load_snic()
    deis = load_deis_with_fallback(previous)
    cesac_sm = load_cesac_salud_mental()

    latest_arg = argentina[-1]
    latest_caba = next(x for x in caba if x["anio"] == 2025)
    caba_2024 = next(x for x in caba if x["anio"] == 2024)
    caba_var = round(
        (latest_caba["suicidios"] / caba_2024["suicidios"] - 1) * 100, 1
    )
    arg_2024 = next(x for x in argentina if x["anio"] == 2024)
    arg_var = round(
        (latest_arg["suicidios"] / arg_2024["suicidios"] - 1) * 100, 1
    )

    output = {
        "schema": "cepoes-salud-mental-v3",
        "status": "VALIDADO",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Argentina y Ciudad Autónoma de Buenos Aires",
        "headline": {
            "argentina": {
                "anio": 2025,
                "suicidios_snic": latest_arg["suicidios"],
                "tasa_100k_mayores_5": latest_arg["tasa_100k_mayores_5"],
                "variacion_anual_pct": arg_var,
            },
            "caba": {
                "anio": 2025,
                "suicidios_snic": latest_caba["suicidios"],
                "tasa_100k_mayores_5": latest_caba["tasa_100k_mayores_5"],
                "variacion_anual_pct": caba_var,
            },
        },
        "series": {
            "argentina_snic": argentina,
            "caba_snic": caba,
        },
        "jurisdicciones_2025": jurisdictions,
        "comparabilidad": {
            "buenos_aires": {
                "estado": "RUPTURA_DE_SERIE_2025",
                "advertencia": PBA_BREAK_NOTE,
                "fuente": SNIC_REPORT_2025,
            }
        },
        "contraste_deis": deis,
        "red_atencion_caba": {
            "cesac_con_salud_mental": cesac_sm,
            "cantidad_cesac": len(cesac_sm),
            "efectores_especializados": EFFECTORS,
            "cantidad_efectores_especializados": len(EFFECTORS),
        },
        "intentos_suicidio": {
            "publicado": False,
            "estado": "PANEL_SEPARADO_NO_PUBLICADO",
            "nota": (
                "Los intentos de suicidio se mantienen separados de los suicidios "
                "consumados. No forman parte de la interfaz pública en esta etapa."
            ),
        },
        "asistencia": ASSISTANCE,
        "methodology": {
            "fuente_principal": (
                "SNIC, código 31 Suicidios (consumados), bases usuarias agregadas "
                "a nivel país y provincial. Las tasas corresponden a población de "
                "5 años y más, conforme la metodología oficial."
            ),
            "serie": "2016-2025",
            "territorio": (
                "La tabla jurisdiccional 2025 comprende las 23 provincias y la "
                "Ciudad Autónoma de Buenos Aires."
            ),
            "deis": (
                "DEIS se conserva como contraste epidemiológico separado. No se "
                "fusiona con SNIC ni se usa para reemplazar la serie principal."
            ),
            "caba": (
                "Para CABA se utiliza la observación provincial SNIC y se informa "
                "la variación 2025/2024. No se equipara esta serie con DEIS por residencia."
            ),
            "advertencias": [
                PBA_BREAK_NOTE,
                (
                    "Suicidios consumados e intentos de suicidio son indicadores "
                    "distintos y se mantienen en paneles separados."
                ),
            ],
        },
        "sources": {
            "snic_pais": SNIC_PAIS_URL,
            "snic_provincias": SNIC_PROVINCIAS_URL,
            "snic_manual": SNIC_MANUAL_URL,
            "snic_informe_2025": SNIC_REPORT_2025,
            "deis": DEIS_CKAN,
            "deis_informe_2024": DEIS_REPORT_2024,
            "cesac": CESAC_SOURCE,
            "efectores_especializados": EFFECTORS_SOURCE,
        },
        "quality": {
            "argentina_checkpoints": {
                str(y): {
                    "actual": next(x["suicidios"] for x in argentina if x["anio"] == y),
                    "expected": n,
                    "ok": next(x["suicidios"] for x in argentina if x["anio"] == y) == n,
                }
                for y, n in EXPECTED_ARG.items()
            },
            "argentina_2025_rate_expected": EXPECTED_ARG_2025_RATE,
            "caba_2025_count_expected": EXPECTED_CABA_2025,
            "caba_2025_rate_expected": EXPECTED_CABA_2025_RATE,
            "caba_variacion_2025_2024_expected_pct": 38.0,
            "jurisdicciones_2025_expected": EXPECTED_JURISDICTIONS,
            "jurisdicciones_2025_sum_expected": EXPECTED_JURISDICTIONS_SUM,
            "cesac_salud_mental_min_expected": EXPECTED_MIN_CESAC_SM,
            "snic_diagnostics": snic_diag,
        },
    }

    text = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
    for path in (OUT_ROOT, OUT_PUBLIC):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    print(
        "Salud Mental V3 · "
        f"Argentina 2025={latest_arg['suicidios']} tasa={latest_arg['tasa_100k_mayores_5']} · "
        f"CABA 2025={latest_caba['suicidios']} tasa={latest_caba['tasa_100k_mayores_5']} "
        f"var={caba_var:+.1f}% · jurisdicciones={len(jurisdictions)} suma={sum(x['suicidios_2025'] for x in jurisdictions)} · "
        f"CeSAC={len(cesac_sm)} · efectores={len(EFFECTORS)} · DEIS={deis['estado']}"
    )


if __name__ == "__main__":
    main()
