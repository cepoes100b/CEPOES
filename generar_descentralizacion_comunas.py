#!/usr/bin/env python3
"""CEPOES · Descentralización comunal V2.

Mide presupuesto ADMINISTRADO por las 15 Comunas y lo separa del gasto
meramente LOCALIZADO territorialmente en Desc_Geo.

Controles:
- Selecciona el último CSV 2026 de Presupuesto Ejecutado.
- Sólo clasifica como administración comunal si Ent/UE identifica exactamente
  Comuna 1 ... Comuna 15.
- Nunca usa Desc_Geo para inferir administración.
- Contrasta la columna Sanción con los 15 totales oficiales del Decreto
  Distributivo 2026 (Planilla 32).
- Falla cerrado ante cambios de esquema o desvíos materiales.
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
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

CKAN_IDS = ("presupuesto-ejecutado-2026", "presupuesto-ejecutado")
CKAN_BASE = "https://data.buenosaires.gob.ar/api/3/action/package_show?id="
OUT_ROOT = Path("descentralizacion_comunas.json")
OUT_PUBLIC = Path("deploy/site-overlay/assets/data/descentralizacion-comunas.json")
UA = "CEPOES-data-pipeline/2.0"

POP = {
    1:221001, 2:160609, 3:193537, 4:227024, 5:192449,
    6:201764, 7:213262, 8:203888, 9:167908, 10:171896,
    11:201905, 12:235364, 13:262330, 14:247252, 15:195265,
}

# Decreto Distributivo 2026 · Planilla 32 · TOTAL por entidad Comuna.
SANCIONADO_OFICIAL_2026 = {
    1:23551207677,
    2:10847320551,
    3:7876703258,
    4:26178123318,
    5:7637166074,
    6:11425728078,
    7:18239541768,
    8:21459182556,
    9:20255786777,
    10:17349785329,
    11:15960028917,
    12:26112219721,
    13:32423246607,
    14:34681461509,
    15:16407869924,
}
SANCIONADO_OFICIAL_TOTAL = sum(SANCIONADO_OFICIAL_2026.values())
DECRETO_URL = (
    "https://buenosaires.gob.ar/sites/default/files/2026-01/"
    "04-Anexo01PlanillasAnexasDecretoDistributivo.pdf"
)


def norm(v):
    s = unicodedata.normalize("NFKD", str(v or ""))
    s = s.encode("ascii", "ignore").decode("ascii").lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _urlopen(req, timeout):
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as exc:
        target = getattr(req, "full_url", str(req))
        host = (urlparse(target).hostname or "").lower()
        if host == "data.buenosaires.gob.ar" and "CERTIFICATE_VERIFY_FAILED" in str(exc):
            print(
                "ADVERTENCIA TLS: BA Data no presentó una cadena validable por el runner; "
                "reintento acotado sin verificación para data.buenosaires.gob.ar"
            )
            ctx = ssl._create_unverified_context()
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raise


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with _urlopen(req, 60) as r:
        return json.load(r)


def get_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with _urlopen(req, 240) as r:
        return r.read()


def package():
    errors = []
    for pid in CKAN_IDS:
        try:
            x = get_json(CKAN_BASE + pid)
            if x.get("success"):
                print(f"BA Data: dataset resuelto={pid}")
                return x["result"], pid
            errors.append(f"{pid}: success=false")
        except Exception as exc:
            errors.append(f"{pid}: {type(exc).__name__}: {exc}")
    raise RuntimeError("No se pudo resolver dataset presupuesto: " + "; ".join(errors))


def resource_quarter(text):
    t = norm(text)
    patterns = (
        (4, ("cuarto_trimestre", "4_trimestre", "4to_trimestre")),
        (3, ("tercer_trimestre", "tercer_trimestre", "3_trimestre", "3er_trimestre")),
        (2, ("segundo_trimestre", "2_trimestre", "2do_trimestre")),
        (1, ("primer_trimestre", "1_trimestre", "1er_trimestre")),
    )
    for q, keys in patterns:
        if any(k in t for k in keys):
            return q
    return 0


def choose_resource(pkg):
    candidates = []
    for r in pkg.get("resources", []):
        text = " ".join(str(r.get(k, "")) for k in ("name", "description", "url"))
        fmt = str(r.get("format", "")).lower()
        if "2026" not in text:
            continue
        if "csv" not in fmt and not str(r.get("url", "")).lower().endswith(".csv"):
            continue
        q = resource_quarter(text)
        candidates.append((q, str(r.get("last_modified") or r.get("created") or ""), r))

    if not candidates:
        raise RuntimeError("No se encontró CSV de Presupuesto Ejecutado 2026")

    q, _, resource = max(candidates, key=lambda x: (x[0], x[1]))
    if q == 0:
        raise RuntimeError(f"No se pudo inferir trimestre del recurso: {resource.get('name')}")
    return q, resource


def decode(raw):
    text = None
    encoding = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            pass
    if text is None:
        raise RuntimeError("No se pudo decodificar presupuesto")

    try:
        delim = csv.Sniffer().sniff(text[:30000], delimiters=",;\t|").delimiter
    except csv.Error:
        delim = ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    fields = list(reader.fieldnames or [])
    if not fields:
        raise RuntimeError("CSV sin encabezado")
    return fields, reader, encoding, delim


def fnum(v):
    s = str(v or "").strip().replace("\u00a0", "").replace(" ", "")
    if not s or norm(s) in {"nan", "none", "null"}:
        return 0.0
    try:
        return float(s)
    except ValueError:
        pass

    # formatos locales: 1.234.567,89 o 1,234,567.89
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        if s.count(",") > 1:
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError as exc:
        raise RuntimeError(f"Valor monetario no parseable: {v!r}") from exc


def colmap(fields):
    return {norm(f): f for f in fields}


def exact_or_contains(m, exact=(), contains=()):
    for k in exact:
        if k in m:
            return m[k]
    for normalized, original in m.items():
        if all(piece in normalized for piece in contains):
            return original
    return None


def amount_columns(m, quarter):
    suffix = f"trim{quarter}"
    sanc = exact_or_contains(m, exact=("sancion",))
    vig = exact_or_contains(
        m,
        exact=(f"vigente_{suffix}_cont",),
        contains=("vigente", suffix),
    )
    defi = exact_or_contains(
        m,
        exact=(f"definitivo_{suffix}_cont",),
        contains=("definitivo", suffix),
    )
    dev = exact_or_contains(
        m,
        exact=(f"devengado_{suffix}_cont",),
        contains=("devengado", suffix),
    )
    # fallback genérico si BA Data cambia el sufijo pero mantiene una sola columna
    if not vig:
        vig = next((o for n, o in m.items() if "vigente" in n), None)
    if not defi:
        defi = next((o for n, o in m.items() if "definitivo" in n), None)
    if not dev:
        dev = next((o for n, o in m.items() if "devengado" in n), None)
    return sanc, vig, defi, dev


def parse_commune_label(value):
    s = norm(value)
    match = re.fullmatch(r"comuna_?(1[0-5]|[1-9])", s)
    return int(match.group(1)) if match else None


def administrative_commune(row, m):
    candidates = []
    sources = []
    for key in ("ent_desc", "desc_ent", "ue_desc", "desc_ue"):
        col = m.get(key)
        if not col:
            continue
        c = parse_commune_label(row.get(col))
        if c:
            candidates.append(c)
            sources.append((key, col, str(row.get(col) or "").strip()))

    if not candidates:
        return None, []
    if len(set(candidates)) > 1:
        raise RuntimeError(f"Fila con Ent/UE comunales inconsistentes: {sources}")
    return candidates[0], sources


def pct_change(a, b):
    return round((a / b - 1) * 100, 2) if b else None


def checkpoint(actual, expected):
    if expected == 0:
        return actual == 0, 0.0
    diff_pct = (actual / expected - 1) * 100
    # Guardia fuerte pero tolera pequeñas diferencias de redondeo/republicación.
    return abs(diff_pct) <= 0.05, round(diff_pct, 5)


def main():
    pkg, dataset_id = package()
    quarter, res = choose_resource(pkg)
    print(
        f"BA Data: recurso={res.get('name')} · id={res.get('id')} · "
        f"T{quarter} 2026 · url={res.get('url')}"
    )

    raw = get_bytes(res["url"])
    fields, rows, encoding, delimiter = decode(raw)
    m = colmap(fields)
    sanc, vig, defi, dev = amount_columns(m, quarter)

    print("BA Data: campos=", fields)
    print(
        f"BA Data: columnas monetarias sancion={sanc!r} vigente={vig!r} "
        f"definitivo={defi!r} devengado={dev!r} · encoding={encoding} "
        f"delimiter={delimiter!r}"
    )

    if not sanc or not vig or not dev:
        raise SystemExit(f"Columnas monetarias no reconocidas: {fields}")

    inc = m.get("inciso") or m.get("inc")
    incd = m.get("inciso_desc") or m.get("desc_inc") or m.get("inc_desc")
    geod = m.get("geo_desc") or m.get("desc_geo")

    acc = {
        i: {
            "sancionado": 0.0,
            "vigente": 0.0,
            "definitivo": 0.0,
            "devengado": 0.0,
            "rows": 0,
            "incisos": defaultdict(float),
            "ent_labels": Counter(),
            "ue_labels": Counter(),
            "ent_codes": Counter(),
            "ue_codes": Counter(),
            "sources": Counter(),
        }
        for i in range(1, 16)
    }
    territorial = defaultdict(lambda: {"vigente": 0.0, "devengado": 0.0})
    total_vig = total_dev = total_sanc = 0.0
    total_rows = admin_rows = 0

    ent_desc_col = m.get("ent_desc") or m.get("desc_ent")
    ue_desc_col = m.get("ue_desc") or m.get("desc_ue")
    ent_code_col = m.get("ent")
    ue_code_col = m.get("ue")

    for row in rows:
        total_rows += 1
        v = fnum(row.get(vig))
        d = fnum(row.get(dev))
        s = fnum(row.get(sanc))
        df = fnum(row.get(defi)) if defi else 0.0
        total_vig += v
        total_dev += d
        total_sanc += s

        if geod:
            g = parse_commune_label(row.get(geod))
            if g:
                territorial[g]["vigente"] += v
                territorial[g]["devengado"] += d

        c, sources = administrative_commune(row, m)
        if not c:
            continue

        admin_rows += 1
        a = acc[c]
        a["sancionado"] += s
        a["vigente"] += v
        a["definitivo"] += df
        a["devengado"] += d
        a["rows"] += 1
        for src in sources:
            a["sources"][src[0]] += 1

        label = str(row.get(incd) or row.get(inc) or "Sin clasificar").strip()
        a["incisos"][label] += v
        if ent_desc_col:
            a["ent_labels"][str(row.get(ent_desc_col) or "").strip()] += 1
        if ue_desc_col:
            a["ue_labels"][str(row.get(ue_desc_col) or "").strip()] += 1
        if ent_code_col:
            a["ent_codes"][str(row.get(ent_code_col) or "").strip()] += 1
        if ue_code_col:
            a["ue_codes"][str(row.get(ue_code_col) or "").strip()] += 1

    if admin_rows == 0:
        raise SystemExit(
            "No se identificaron filas administradas por Comunas. "
            "Desc_Geo NO se usará como sustituto."
        )

    missing = [c for c in range(1, 16) if acc[c]["rows"] == 0]
    if missing:
        raise SystemExit(f"Faltan entidades/unidades ejecutoras comunales: {missing}")

    checkpoint_detail = {}
    checkpoint_errors = []
    for c in range(1, 16):
        actual = round(acc[c]["sancionado"], 2)
        expected = SANCIONADO_OFICIAL_2026[c]
        ok, diff_pct = checkpoint(actual, expected)
        checkpoint_detail[str(c)] = {
            "actual": actual,
            "expected": expected,
            "difference": round(actual - expected, 2),
            "difference_pct": diff_pct,
            "ok": ok,
        }
        if not ok:
            checkpoint_errors.append(
                f"Comuna {c}: Sanción={actual:.2f}, oficial={expected}, diff={diff_pct}%"
            )

        print(
            f"Comuna {c}: filas={acc[c]['rows']} · sancion={actual:.0f} · "
            f"oficial={expected} · diff={diff_pct}% · "
            f"Ent={list(acc[c]['ent_labels'].keys())[:3]} · "
            f"UE={list(acc[c]['ue_labels'].keys())[:3]}"
        )

    if checkpoint_errors:
        print("✘ Control Decreto Distributivo 2026")
        for e in checkpoint_errors:
            print("  ·", e)
        raise SystemExit(1)

    sum_communes_sanc = sum(x["sancionado"] for x in acc.values())
    sum_communes_vig = sum(x["vigente"] for x in acc.values())
    sum_communes_dev = sum(x["devengado"] for x in acc.values())

    total_ok, total_diff_pct = checkpoint(sum_communes_sanc, SANCIONADO_OFICIAL_TOTAL)
    if not total_ok:
        raise SystemExit(
            f"Total comunas sancionado no coincide: {sum_communes_sanc:.2f} vs "
            f"{SANCIONADO_OFICIAL_TOTAL} ({total_diff_pct}%)"
        )

    out_comm = []
    for c in range(1, 16):
        a = acc[c]
        pop = POP[c]
        out_comm.append({
            "comuna": c,
            "poblacion_censo_2022": pop,
            "administrado": {
                "sancionado": round(a["sancionado"], 2),
                "vigente": round(a["vigente"], 2),
                "definitivo": round(a["definitivo"], 2),
                "devengado": round(a["devengado"], 2),
                "ejecucion_pct": round(a["devengado"] / a["vigente"] * 100, 2)
                    if a["vigente"] else None,
                "variacion_vigente_vs_sancionado_pct": pct_change(
                    a["vigente"], a["sancionado"]
                ),
                "sancionado_por_habitante": round(a["sancionado"] / pop, 2),
                "vigente_por_habitante": round(a["vigente"] / pop, 2),
                "participacion_comunas_pct": round(
                    a["vigente"] / sum_communes_vig * 100, 2
                ) if sum_communes_vig else None,
                "composicion_vigente": dict(sorted(
                    (k, round(v, 2)) for k, v in a["incisos"].items()
                )),
            },
            "gasto_localizado": {
                "vigente": round(territorial[c]["vigente"], 2),
                "devengado": round(territorial[c]["devengado"], 2),
            },
            "clasificacion": {
                "filas": a["rows"],
                "entidades": dict(a["ent_labels"]),
                "unidades_ejecutoras": dict(a["ue_labels"]),
                "codigos_entidad": dict(a["ent_codes"]),
                "codigos_ue": dict(a["ue_codes"]),
                "fuentes_match": dict(a["sources"]),
            },
        })

    per = [x["administrado"]["vigente_por_habitante"] for x in out_comm]

    output = {
        "schema": "cepoes-descentralizacion-comunas-v2",
        "status": "VALIDADO",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "year": 2026,
        "quarter": quarter,
        "headline": {
            "presupuesto_administrado_comunas_sancionado": round(sum_communes_sanc, 2),
            "presupuesto_administrado_comunas_vigente": round(sum_communes_vig, 2),
            "presupuesto_administrado_comunas_devengado": round(sum_communes_dev, 2),
            "variacion_vigente_vs_sancionado_pct": pct_change(
                sum_communes_vig, sum_communes_sanc
            ),
            "participacion_presupuesto_gcba_pct": round(
                sum_communes_vig / total_vig * 100, 4
            ) if total_vig else None,
            "ejecucion_comunas_pct": round(
                sum_communes_dev / sum_communes_vig * 100, 2
            ) if sum_communes_vig else None,
            "brecha_per_capita_max_min": round(max(per) / min(per), 2)
                if min(per) > 0 else None,
        },
        "comunas": out_comm,
        "totales_gcba": {
            "sancionado": round(total_sanc, 2),
            "vigente": round(total_vig, 2),
            "devengado": round(total_dev, 2),
        },
        "methodology": {
            "administrado": (
                "Sólo se considera presupuesto comunal cuando Entidad administrativa "
                "y/o Unidad Ejecutora se identifica exactamente como Comuna 1 a Comuna 15."
            ),
            "territorial": (
                "Desc_Geo se conserva como gasto localizado territorialmente. "
                "Nunca se utiliza para inferir quién administra el crédito."
            ),
            "checkpoint": (
                "La columna Sanción de cada Comuna se contrasta con Planilla 32 "
                "del Decreto Distributivo 2026, con tolerancia máxima de 0,05%."
            ),
            "poblacion": (
                "Población Censo 2022; se usa sólo para indicadores per cápita."
            ),
            "indice_descentralizacion": (
                "Todavía no se calcula. Esta V2 valida el componente presupuestario "
                "que luego se integrará con competencias transferidas y cumplimiento "
                "de la Ley 1.777."
            ),
        },
        "source": {
            "name": res.get("name"),
            "url": res.get("url"),
            "resource_id": res.get("id"),
            "dataset": pkg.get("name"),
            "dataset_id": dataset_id,
            "decreto_distributivo_2026": DECRETO_URL,
        },
        "quality": {
            "total_rows": total_rows,
            "admin_rows": admin_rows,
            "fields": fields,
            "amount_columns": {
                "sancionado": sanc,
                "vigente": vig,
                "definitivo": defi,
                "devengado": dev,
            },
            "sancionado_checkpoint": checkpoint_detail,
            "sancionado_checkpoint_total": {
                "actual": round(sum_communes_sanc, 2),
                "expected": SANCIONADO_OFICIAL_TOTAL,
                "difference_pct": total_diff_pct,
                "ok": total_ok,
            },
        },
    }

    text = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
    for p in (OUT_ROOT, OUT_PUBLIC):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    print(
        f"Descentralización V2 · T{quarter} 2026 · 15 comunas · "
        f"sancionado={sum_communes_sanc:.0f} · vigente={sum_communes_vig:.0f} · "
        f"devengado={sum_communes_dev:.0f} · ejecución="
        f"{output['headline']['ejecucion_comunas_pct']}% · "
        f"peso GCBA={output['headline']['participacion_presupuesto_gcba_pct']}%"
    )


if __name__ == "__main__":
    main()
