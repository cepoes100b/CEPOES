#!/usr/bin/env python3
from __future__ import annotations

import io
import hashlib
import math
import os
import tempfile
from html.parser import HTMLParser
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from openpyxl import load_workbook
from pypdf import PdfReader

OUT = Path("deploy/site-overlay/assets/data/estructura-productiva/actual.json")
TIMEOUT = 180
UA = {"User-Agent": "CEPOES-data/1.0 (+https://cepoes.org/)"}
OEDE_URL = "https://www.argentina.gob.ar/sites/default/files/provinciales_serie_empresas1_2.xlsx"
IDECBA_INDEX = "https://www.estadisticaciudad.gob.ar/eyc/categoria-banco-datos/ejes-comerciales/"
RUBRO_FALLBACK = "https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/06/AC_EJ_2026_08.xlsx"
IND_FALLBACK = "https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/06/AC_EJ_2026_04.xlsx"
IDECBA_PUBLICATIONS = "https://www.estadisticaciudad.gob.ar/eyc/publicaciones/"
COMUNA_IDS = {str(i) for i in range(1, 16)}
# The official workbook stores full-precision rates/deltas. Fail closed if that
# contract changes, rather than silently weakening reconciliation.
SOURCE_TOLERANCE = 1e-8
COMUNAS_URL = "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/innovacion-transformacion-digital/comunas/comunas.geojson"
GEO_OUT = Path("deploy/site-overlay/assets/data/estructura-productiva/comunas.geojson")
INTERANUAL_2026Q1 = {
    "1": -0.5, "2": -4.6, "3": -1.1, "4": -0.3, "5": -2.0,
    "6": 0.0, "7": -0.4, "8": -1.7, "9": 0.7, "10": -2.5,
    "11": 0.8, "12": -1.0, "13": -3.3, "14": -2.1, "15": -3.5,
}


def clean(v):
    return re.sub(r"\s+", " ", str(v).strip()) if v is not None else ""


def norm(v):
    return unicodedata.normalize("NFKD", clean(v)).encode("ascii", "ignore").decode().lower().strip()


def number(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = clean(v).replace("%", "")
    if not s or norm(s) in {"s.d.", "s/d", "sd", "-", "..."}:
        return None
    if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})*(?:,\d+)?", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def as_int(v):
    n = number(v)
    return int(round(n)) if n is not None else None


def get(url):
    r = requests.get(url, timeout=TIMEOUT, headers=UA)
    r.raise_for_status()
    return r.content


def get_text(url):
    r = requests.get(url, timeout=TIMEOUT, headers=UA)
    r.raise_for_status()
    return r.text


def hrefs(html, base):
    out = []
    for raw in re.findall(r'''(?:^|\s)href\s*=\s*["']([^"']+)["']''', html, re.I):
        u = urljoin(base, raw.replace("&amp;", "&"))
        if u.startswith("https://www.estadisticaciudad.gob.ar/"):
            out.append(u)
    return list(dict.fromkeys(out))


def period(text):
    s = norm(text)
    years = [int(x) for x in re.findall(r"(?:19|20)\d{2}", s)]
    if not years:
        return None
    matches = re.findall(r"\b([123])(?:er|ro|do)?\.?\s*cuatr(?:imestre|\.)?\s*(?:de\s*)?((?:19|20)\d{2})", s.replace("-", " "))
    periods = {(int(year), int(q)) for q, year in matches}
    return next(iter(periods)) if len(periods) == 1 else None


class PublicationHeadings(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts = []
        self.headings = []

    def handle_starttag(self, tag, attrs):
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.depth += 1
            self.parts = []

    def handle_data(self, text):
        if self.depth:
            self.parts.append(text)

    def handle_endtag(self, tag):
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self.depth:
            self.headings.append(" ".join(self.parts))
            self.depth -= 1


def discover_report(p):
    ordinal = {1: "1er", 2: "2do", 3: "3er"}[p[1]]
    page = f"{IDECBA_PUBLICATIONS}ejes-comerciales-ciudad-de-buenos-aires-{ordinal}-cuatrimestre-de-{p[0]}/"
    html = get_text(page)
    headings = PublicationHeadings()
    headings.feed(html)
    matching = [h for h in headings.headings if "ejes comerciales" in norm(h)]
    if len(matching) != 1 or period(matching[0]) != p:
        raise RuntimeError(f"IDECBA informe: título/período de publicación inválido para {p}")
    pdfs = [u for u in hrefs(html, page) if re.search(r"/ir_\d{4}_\d+\.pdf(?:\?|$)", u, re.I)]
    if len(pdfs) != 1:
        raise RuntimeError(f"IDECBA informe: PDF ausente o ambiguo ({len(pdfs)})")
    raw = get(pdfs[0])
    cover = PdfReader(io.BytesIO(raw)).pages[0].extract_text() or ""
    if "ejes comerciales" not in norm(cover) or period(cover) != p:
        raise RuntimeError(f"IDECBA informe: período del PDF no coincide con {p}")
    report_id = re.search(r"informe de resultados\s*(\d+)", norm(cover))
    if not report_id or not re.search(rf"/ir_\d{{4}}_{report_id.group(1)}\.pdf(?:\?|$)", pdfs[0]):
        raise RuntimeError("IDECBA informe: número de portada no coincide con URL")
    return {"nombre": "IDECBA · Ejes comerciales · Informe de resultados", "url": pdfs[0],
            "numero": int(report_id.group(1)),
            "pagina": page, "periodo": {"anio": p[0], "cuatrimestre": p[1]},
            "periodo_verificado": {"anio": p[0], "cuatrimestre": p[1]},
            "sha256": hashlib.sha256(raw).hexdigest(),
            "extraido": datetime.now(timezone.utc).isoformat()}


def discover():
    rubros = [RUBRO_FALLBACK]
    indicadores = [IND_FALLBACK]
    try:
        html = get_text(IDECBA_INDEX)
        pages = [u for u in hrefs(html, IDECBA_INDEX) if "/banco-datos/" in u]
        for page in pages[:50]:
            np = norm(page)
            if "locales-ocupados-por-comuna-segun-rubro" not in np and "locales-relevados-ocupados-densidad-comercial" not in np:
                continue
            try:
                files = [u for u in hrefs(get_text(page), page) if re.search(r"\.xlsx(?:\?|$)", u, re.I)]
            except Exception:
                continue
            if "locales-ocupados-por-comuna-segun-rubro" in np:
                rubros.extend(files)
            elif "por-comuna" in np:
                indicadores.extend(files)
    except Exception as e:
        print("IDECBA discovery fallback:", e)
    return list(dict.fromkeys(rubros)), list(dict.fromkeys(indicadores))


def latest_book(urls, label):
    best = None
    for url in urls:
        try:
            raw = get(url)
            wb = load_workbook(io.BytesIO(raw), read_only=False, data_only=True)
            wb.cepoes_source = {"sha256": hashlib.sha256(raw).hexdigest(), "extraido": datetime.now(timezone.utc).isoformat()}
            ps = [period(s) for s in wb.sheetnames if period(s)]
            p = max(ps) if ps else (0, 0)
            print(f"{label}: {url} -> {p}")
            if best is None or p > best[0]:
                best = (p, url, wb)
        except Exception as e:
            print(f"{label}: descarto {url}: {e}")
    if best is None or best[0][0] < 2026:
        raise RuntimeError(f"{label}: no hay libro 2026 válido")
    return best


def sheet_for(wb, p):
    sheets = [ws for ws in wb.worksheets if period(ws.title) == p]
    if len(sheets) != 1:
        raise RuntimeError(f"IDECBA: hoja {p} ausente o ambigua ({len(sheets)})")
    ws = sheets[0]
    title = clean(ws.cell(1, 1).value)
    if period(title) != p or "48 ejes comerciales" not in norm(title):
        raise RuntimeError(f"IDECBA: título/período/alcance inválido en {ws.title}")
    return ws


def latest_sheet(wb):
    ps = [period(ws.title) for ws in wb.worksheets if period(ws.title)]
    if not ps:
        raise RuntimeError("IDECBA: no hay hoja por cuatrimestre")
    p = max(ps)
    return p, sheet_for(wb, p)


def require_number(value, context):
    n = number(value)
    if n is None or not math.isfinite(n):
        raise RuntimeError(f"IDECBA: número ausente/no finito en {context}")
    return n


def require_count(value, context):
    n = require_number(value, context)
    if n < 0 or not n.is_integer():
        raise RuntimeError(f"IDECBA: conteo inválido en {context}: {value}")
    return int(n)


def parse_rubros(wb):
    p, ws = latest_sheet(wb)
    headers = []
    for r in range(1, min(15, ws.max_row) + 1):
        labels = [norm(ws.cell(r, c).value) for c in range(1, ws.max_column + 1)]
        if all(x in labels for x in ("rubro", "total", "comuna")):
            if any(labels.count(x) != 1 for x in ("rubro", "total", "comuna")):
                raise RuntimeError("IDECBA rubros: columnas ambiguas")
            headers.append((r, labels.index("rubro") + 1, labels.index("total") + 1))
    if len(headers) != 1:
        raise RuntimeError("IDECBA rubros: encabezado ausente o ambiguo")
    header, label_col, total_col = headers[0]
    positions = {}
    for c in range(1, ws.max_column + 1):
        value = ws.cell(header + 1, c).value
        if value is None:
            continue
        cid = require_count(value, f"encabezado rubros {header + 1}/{c}")
        if str(cid) not in COMUNA_IDS or cid in positions:
            raise RuntimeError("IDECBA rubros: comuna duplicada/fuera de rango")
        positions[cid] = c
    if set(positions) != set(range(1, 16)):
        raise RuntimeError("IDECBA rubros: no detecté las 15 comunas")
    out = []
    for r in range(header + 2, ws.max_row + 1):
        label = clean(ws.cell(r, label_col).value)
        if not label or norm(label).startswith(("fuente", "nota")):
            continue
        total = require_count(ws.cell(r, total_col).value, f"rubro {label}, total")
        counts = {str(c): require_count(ws.cell(r, positions[c]).value, f"rubro {label}, comuna {c}") for c in range(1, 16)}
        if sum(counts.values()) != total:
            raise RuntimeError(f"IDECBA rubros: fila {label} no suma su total")
        out.append({"rubro": label, "total": total, "comunas": counts})
    totals = [x for x in out if norm(x["rubro"]) == "total"]
    if len(totals) != 1 or totals[0]["total"] < 9000:
        raise RuntimeError("IDECBA rubros: total ausente, duplicado o inválido")
    totalrow = totals[0]
    rubros = [x for x in out if norm(x["rubro"]) != "total"]
    if len(rubros) != 19 or len({norm(x["rubro"]) for x in rubros}) != 19:
        raise RuntimeError("IDECBA rubros: se requieren 19 rubros únicos")
    if sum(x["total"] for x in rubros) != totalrow["total"]:
        raise RuntimeError("IDECBA rubros: composición inconsistente")
    if any(sum(x["comunas"][c] for x in rubros) != totalrow["comunas"][c] for c in COMUNA_IDS):
        raise RuntimeError("IDECBA rubros: totales por comuna inconsistentes")
    return p, totalrow["total"], totalrow["comunas"], rubros


def indicator_header(ws):
    required = {"comuna", "locales relevados", "locales ocupados"}
    rows = []
    for r in range(1, min(ws.max_row, 12) + 1):
        labels = [norm(ws.cell(r, c).value) for c in range(1, ws.max_column + 1)]
        if required <= set(labels):
            rows.append((r, labels))
    if len(rows) != 1:
        raise RuntimeError("IDECBA indicadores: encabezado ausente o ambiguo")
    r, labels = rows[0]
    cols = {}
    for name in (*sorted(required), "tasa de ocupacion", "variacion interanual"):
        hits = [c for c, text in enumerate(labels, 1) if text == name or (name not in required and text.startswith(name))]
        if len(hits) != 1:
            raise RuntimeError(f"IDECBA indicadores: columna {name} ausente o ambigua")
        cols[name] = hits[0]
    return r, cols


def semantic_column(ws, needle):
    # Search only the unique table header, never a merged title such as A1.
    r, _ = indicator_header(ws)
    hits = [c for c in range(1, ws.max_column + 1) if norm(needle) in norm(ws.cell(r, c).value)]
    if len(hits) != 1:
        raise RuntimeError(f"IDECBA indicadores: columna {needle} ausente o ambigua")
    return hits[0]


def read_indicator_sheet(ws, require_delta):
    header, cols = indicator_header(ws)
    rows = {}
    for r in range(header + 1, ws.max_row + 1):
        marker = clean(ws.cell(r, cols["comuna"]).value)
        if not marker or norm(marker).startswith(("fuente", "nota", ". dato")):
            continue
        if norm(marker) == "total":
            cid = "total"
        else:
            token = re.sub(r"^comuna\s*", "", norm(marker))
            cid = str(require_count(token, f"ID comuna fila {r}"))
            if cid not in COMUNA_IDS:
                raise RuntimeError(f"IDECBA indicadores: comuna fuera de rango {cid}")
        if cid in rows:
            raise RuntimeError(f"IDECBA indicadores: comuna/total duplicado {cid}")
        relevados = require_count(ws.cell(r, cols["locales relevados"]).value, f"{cid} relevados")
        ocupados = require_count(ws.cell(r, cols["locales ocupados"]).value, f"{cid} ocupados")
        tasa = require_number(ws.cell(r, cols["tasa de ocupacion"]).value, f"{cid} tasa")
        if relevados <= 0 or ocupados > relevados or not 75 <= tasa <= 100:
            raise RuntimeError(f"IDECBA indicadores: conteos/tasa improbables {cid}")
        if abs(100 * ocupados / relevados - tasa) > SOURCE_TOLERANCE:
            raise RuntimeError(f"IDECBA indicadores: tasa no reconcilia con conteos {cid}")
        entry = {"relevados": relevados, "ocupados": ocupados, "tasa_ocupacion": tasa}
        if require_delta:
            delta = require_number(ws.cell(r, cols["variacion interanual"]).value, f"{cid} variación interanual")
            if not -10 <= delta <= 10:
                raise RuntimeError(f"IDECBA indicadores: variación interanual improbable {cid}")
            entry["variacion_interanual_pp"] = delta
        rows[cid] = entry
    if set(rows) != COMUNA_IDS | {"total"}:
        raise RuntimeError("IDECBA indicadores: faltan comunas o total")
    for key in ("relevados", "ocupados"):
        if sum(rows[c][key] for c in COMUNA_IDS) != rows["total"][key]:
            raise RuntimeError(f"IDECBA indicadores: {key} no suman el total")
    if not 12000 <= rows["total"]["relevados"] <= 14000 or not 11000 <= rows["total"]["ocupados"] <= 12500:
        raise RuntimeError("IDECBA indicadores: totales improbables")
    return rows


def parse_indicadores(wb, occupied_by_comuna, include_comparison=False):
    p, ws = latest_sheet(wb)
    rows = read_indicator_sheet(ws, require_delta=True)
    previous = read_indicator_sheet(sheet_for(wb, (p[0] - 1, p[1])), require_delta=False)
    if set(occupied_by_comuna) != COMUNA_IDS:
        raise RuntimeError("IDECBA indicadores: comunas de rubros inválidas")
    for cid, entry in rows.items():
        prev = previous[cid]["tasa_ocupacion"]
        if abs(entry["tasa_ocupacion"] - prev - entry["variacion_interanual_pp"]) > SOURCE_TOLERANCE:
            raise RuntimeError(f"IDECBA indicadores: comparación interanual inconsistente {cid}")
        if cid != "total" and entry["ocupados"] != occupied_by_comuna[cid]:
            raise RuntimeError(f"IDECBA: ocupados por comuna no coinciden {cid}")
        entry["tasa_ocupacion_anterior"] = prev
    # Only round at the output boundary; subtraction of rounded rates caused
    # 0.1 p.p. errors in C1 and C2. Keep the independently verified C1 deltas.
    if p == (2026, 1) and {c: round(rows[c]["variacion_interanual_pp"], 1) for c in COMUNA_IDS} != INTERANUAL_2026Q1:
        raise RuntimeError("IDECBA: variaciones C1 difieren del informe verificado")
    def serialized(entry):
        return {k: round(v, 1) if k.startswith(("tasa_", "variacion_")) else v for k, v in entry.items()}
    comunas = {str(c): serialized(rows[str(c)]) for c in range(1, 16)}
    total = serialized(rows["total"])
    result = (p, total["relevados"], total["ocupados"], total["tasa_ocupacion"], comunas)
    if include_comparison:
        comp = {"desde": {"anio": p[0] - 1, "cuatrimestre": p[1]},
                "hasta": {"anio": p[0], "cuatrimestre": p[1]},
                "tasa_ocupacion_desde": total["tasa_ocupacion_anterior"],
                "variacion_total_pp": total["variacion_interanual_pp"],
                "nota": "Las tasas previas corresponden al mismo cuatrimestre del año anterior en la planilla oficial de IDECBA; la variación interanual se valida antes del redondeo."}
        return (*result, comp)
    return result


def parse_comunas_geojson(raw):
    data = json.loads(raw.decode("utf-8"))
    if data.get("type") != "FeatureCollection":
        raise RuntimeError("Comunas: GeoJSON no es FeatureCollection")
    features = []
    ids = set()
    for f in data.get("features") or []:
        props = f.get("properties") or {}
        raw_id = props.get("comuna", props.get("COMUNA", props.get("id")))
        try:
            cid = str(int(raw_id))
        except (TypeError, ValueError):
            continue
        geom = f.get("geometry")
        if cid not in {str(i) for i in range(1, 16)} or not geom:
            continue
        ids.add(cid)
        features.append({
            "type": "Feature",
            "properties": {"comuna": int(cid), "barrios": props.get("barrios", props.get("BARRIOS", ""))},
            "geometry": geom,
        })
    if ids != {str(i) for i in range(1, 16)} or len(features) != 15:
        raise RuntimeError(f"Comunas: geometrías inválidas: {sorted(ids)} / {len(features)}")
    features.sort(key=lambda f: f["properties"]["comuna"])
    return {"type": "FeatureCollection", "features": features}


def parse_oede(raw):
    wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb["Capital Federal"]
    years = {}
    header = None
    for r in range(1, 10):
        found = {}
        for c in range(1, ws.max_column + 1):
            y = as_int(ws.cell(r, c).value)
            if y and 1990 <= y <= 2035:
                found[y] = c
        if len(found) >= 20:
            years, header = found, r
            break
    if not years:
        raise RuntimeError("OEDE: no detecté serie anual")
    latest = max(years)
    if latest < 2024:
        raise RuntimeError(f"OEDE: último año {latest}")
    rows = []
    for r in range(header + 1, ws.max_row + 1):
        code = clean(ws.cell(r, 1).value).upper()
        label = clean(ws.cell(r, 2).value)
        if re.fullmatch(r"[A-Z]", code) and label:
            rows.append((r, code, label))
    if not 8 <= len(rows) <= 25:
        raise RuntimeError(f"OEDE: {len(rows)} secciones; posible tabla duplicada")

    def total(y):
        return sum(as_int(ws.cell(r, years[y]).value) or 0 for r, _, _ in rows)

    total_latest = total(latest)
    if not 80000 <= total_latest <= 180000:
        raise RuntimeError(f"OEDE: total {latest} improbable: {total_latest}")
    sectors = [{"codigo": code, "sector": label.title(), "empresas": as_int(ws.cell(r, years[latest]).value) or 0} for r, code, label in rows]
    sectors.sort(key=lambda x: x["empresas"], reverse=True)
    return {
        "periodo": latest,
        "empresas": total_latest,
        "sectores": sectors,
        "serie": [{"anio": y, "empresas": total(y)} for y in sorted(y for y in years if y >= 2015)],
        "nota": "Empresas privadas con empleo asalariado registrado; una firma puede contabilizarse en más de una jurisdicción si declara personal en distintas provincias.",
    }


def main():
    rubro_urls, ind_urls = discover()
    rp, rubro_url, rubro_wb = latest_book(rubro_urls, "IDECBA rubros")
    ip, ind_url, ind_wb = latest_book(ind_urls, "IDECBA indicadores")
    if rp != ip:
        raise RuntimeError(f"IDECBA: períodos distintos {rp} / {ip}")
    _, ocupados_rubro, ocupados_comuna, rubros = parse_rubros(rubro_wb)
    _, relevados, ocupados, tasa, comunas, comparacion = parse_indicadores(ind_wb, ocupados_comuna, include_comparison=True)
    informe = discover_report(rp)
    if ocupados != ocupados_rubro:
        raise RuntimeError(f"IDECBA: ocupados no coinciden {ocupados} / {ocupados_rubro}")
    oede = parse_oede(get(OEDE_URL))
    comunas_geo = parse_comunas_geojson(get(COMUNAS_URL))

    ejes = {
        "periodo": {"anio": rp[0], "cuatrimestre": rp[1]},
        "locales_relevados": relevados,
        "locales_ocupados": ocupados,
        "tasa_ocupacion": tasa,
        "comunas": comunas,
        "rubros": rubros,
        "universo": "48 ejes comerciales de alta densidad; no representa la totalidad de los locales de CABA.",
    }
    ejes["comparacion_interanual"] = comparacion
    ejes["provisorio"] = True

    d = {
        "schema": 1,
        "generado": datetime.now(timezone.utc).isoformat(),
        "panorama": {"empresas_registradas": oede, "ejes_comerciales": ejes},
        "fuentes": {
            "oede": {"nombre": "OEDE · SIPA", "url": OEDE_URL, "unidad": "empresa privada con empleo asalariado registrado", "periodo": oede["periodo"]},
            "idecba_rubros": {"nombre": "IDECBA · Locales ocupados por comuna según rubro · 48 ejes comerciales", "url": rubro_url, "unidad": "local comercial ocupado", "periodo": {"anio": rp[0], "cuatrimestre": rp[1]}, **rubro_wb.cepoes_source},
            "idecba_indicadores": {"nombre": "IDECBA · Locales relevados y ocupados por comuna · 48 ejes comerciales", "url": ind_url, "unidad": "local comercial relevado/ocupado", "periodo": {"anio": ip[0], "cuatrimestre": ip[1]}, **ind_wb.cepoes_source},
            "idecba_informe": informe,
            "comunas": {"nombre": "Buenos Aires Data · Comunas", "url": COMUNAS_URL, "unidad": "límite administrativo de comuna"},
        },
        "criterio": {
            "actualidad": "La vista principal usa el último dato oficial disponible de cada universo. No se interpola RUS 2017 para estimar un stock 2026.",
            "unidades": "Empresa registrada, local comercial ocupado, habilitación aprobada y establecimiento RUS son unidades distintas y se muestran por separado.",
            "historico": "El RUS 2017 se conserva exclusivamente como capa histórica de alta resolución territorial hasta nivel manzana.",
            "territorial": "El perfil comunal vigente refiere a los 48 ejes comerciales relevados por IDECBA y no a la totalidad de establecimientos de cada comuna.",
        },
    }
    from verificar_estructura_actual import validate
    validate(d, comunas_geo)
    # Reject a stale fallback before touching either published file.
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        old_period = old["panorama"]["ejes_comerciales"]["periodo"]
        if (old_period["anio"], old_period["cuatrimestre"]) > rp:
            raise RuntimeError("IDECBA: se rechaza retroceso respecto del último válido")
    publish_json({GEO_OUT: comunas_geo, OUT: d})
    print(f"{OUT} · OEDE {oede['periodo']} {oede['empresas']} · IDECBA {rp} {ocupados}/{relevados} · interanual=sí")


def publish_json(documents):
    """Validate first; stage all bytes before atomic replacement, rollback errors.

    Each destination is replaced atomically. This is not a multi-file filesystem
    transaction under process termination; actual.json is the final commit point.
    """
    staged = {}
    previous = {}
    replaced = []
    try:
        for path, document in documents.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            previous[path] = path.read_bytes() if path.exists() else None
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
                staged[path] = Path(tmp.name)
                tmp.write(json.dumps(document, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"))
                tmp.flush()
                os.fsync(tmp.fileno())
        for path, temporary in staged.items():
            os.replace(temporary, path)
            replaced.append(path)
    except BaseException:
        for path in reversed(replaced):
            if previous[path] is None:
                path.unlink(missing_ok=True)
            else:
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
                    tmp.write(previous[path])
                    rollback = Path(tmp.name)
                os.replace(rollback, path)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
