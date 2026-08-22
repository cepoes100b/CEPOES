#!/usr/bin/env python3
"""Extrae la referencia barrial pública de Mapa de la Deuda.

Contrato confirmado el 22/08/2026: `mobile-slices-v2`, con `columns` y `rows`.
No accede a microdatos ni a recursos autenticados.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import requests

HOME = "https://mapadeladeuda.ar/"
DATA = "https://datos.mapadeladeuda.ar/"
PERIOD = "2026-06"
BARRIOS_URL = f"{DATA}periods/{PERIOD}/slices/barrio_caba/02/default.json"
LOOKUP_URL = f"{DATA}geo/lookup.json"
OUT = Path("referencia_barrial_mapa_2026_06.json")

NEEDLES = [
    "codigo_postal", "código postal", "postal", "pgeocode", "geonames",
    "nominatim", "georef", "geocod", "centroid", "centroide",
    "postcode", "zip code", "shapefile", "geojson", "github.com",
    ".ipynb", ".py", "barrios_caba", "barrio_caba",
]


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.srcs = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            src = dict(attrs).get("src")
            if src:
                self.srcs.append(src)


def get_json(s, url):
    r = s.get(url, timeout=(20, 90))
    r.raise_for_status()
    return r.json()


def contexts(text, needle, radius=180, limit=20):
    low = text.lower(); n = needle.lower(); out = []; start = 0
    while len(out) < limit:
        i = low.find(n, start)
        if i < 0:
            break
        frag = " ".join(text[max(0, i-radius):min(len(text), i+len(n)+radius)].split())
        if frag not in out:
            out.append(frag[:600])
        start = i + max(1, len(n))
    return out


def extract_records(obj):
    if not isinstance(obj, dict):
        raise RuntimeError("El slice no es un objeto JSON")
    if obj.get("contract") != "mobile-slices-v2":
        raise RuntimeError(f"Contrato inesperado: {obj.get('contract')!r}")
    columns = obj.get("columns")
    raw_rows = obj.get("rows")
    if not isinstance(columns, list) or not isinstance(raw_rows, list):
        raise RuntimeError("mobile-slices-v2 sin columns/rows")
    if not columns or not raw_rows:
        raise RuntimeError("mobile-slices-v2 vacío")

    rows = []
    for i, raw in enumerate(raw_rows):
        if isinstance(raw, dict):
            row = dict(raw)
        elif isinstance(raw, list):
            if len(raw) != len(columns):
                raise RuntimeError(
                    f"Fila {i} tiene {len(raw)} valores y columns tiene {len(columns)}"
                )
            row = dict(zip(columns, raw))
        else:
            raise RuntimeError(f"Tipo de fila no soportado en {i}: {type(raw).__name__}")
        rows.append(row)
    return {"path": "$.rows", "origin": "mobile-slices-v2", "columns": columns}, rows


def collect_lookup_barrios(obj):
    found = {}
    def visit(node, depth=0):
        if depth > 8:
            return
        if isinstance(node, dict):
            level = str(node.get("level") or node.get("nivel") or "")
            scope = str(node.get("scope") or node.get("scope_id") or "")
            gid = node.get("geo_id") or node.get("id")
            if level == "barrio_caba" and scope in ("", "02") and gid is not None:
                found[str(gid)] = node
            for child in node.values():
                if isinstance(child, (dict, list)):
                    visit(child, depth + 1)
        elif isinstance(node, list):
            for child in node:
                if isinstance(child, (dict, list)):
                    visit(child, depth + 1)
    visit(obj)
    return found


def audit_bundle(s):
    home = s.get(HOME, timeout=(20, 60)); home.raise_for_status()
    parser = Scripts(); parser.feed(home.text)
    result = []
    for raw_url in parser.srcs:
        url = urljoin(HOME, raw_url)
        try:
            r = s.get(url, timeout=(20, 90)); r.raise_for_status()
            text = r.text
        except Exception as e:
            result.append({"url": url, "error": str(e)})
            continue
        hits = {n: c for n in NEEDLES if (c := contexts(text, n))}
        sourcemaps = []
        candidates = []
        m = re.search(r"sourceMappingURL\s*=\s*([^\s*]+)", text)
        if m:
            candidates.append(urljoin(url, m.group(1).strip()))
        if url.endswith(".js"):
            candidates.append(url + ".map")
        for sm_url in dict.fromkeys(candidates):
            try:
                rr = s.get(sm_url, timeout=(15, 45), allow_redirects=True)
                sourcemaps.append({
                    "url": sm_url,
                    "status": rr.status_code,
                    "content_type": rr.headers.get("content-type", ""),
                    "bytes": len(rr.content),
                })
            except Exception as e:
                sourcemaps.append({"url": sm_url, "error": str(e)})
        result.append({"url": url, "bytes": len(r.content), "indicios": hits, "sourcemaps": sourcemaps})
    return result


def main():
    s = requests.Session()
    s.headers.update({"User-Agent": "CEPOES-public-method-audit/3.0"})
    slice_obj = get_json(s, BARRIOS_URL)
    lookup = get_json(s, LOOKUP_URL)
    collection, rows = extract_records(slice_obj)
    lookup_barrios = collect_lookup_barrios(lookup)

    aliases = slice_obj.get("aliases") or {}
    normalized = []
    ids = []
    for row in rows:
        gid = str(row.get("geo_id") or "")
        ids.append(gid)
        geo = lookup_barrios.get(gid, {})
        metrics_expanded = {}
        for key, value in row.items():
            if key == "geo_id":
                continue
            metrics_expanded[aliases.get(key, key)] = value
        normalized.append({
            "geo_id": gid,
            "nombre": geo.get("nombre") or geo.get("name"),
            "bbox": geo.get("bbox"),
            "source": geo.get("source"),
            "source_layer": geo.get("source_layer"),
            "metricas_publicas": metrics_expanded,
        })

    payload = {
        "schema": "cepoes-mapadeladeuda-barrio-reference-v4",
        "period": PERIOD,
        "source_slice": BARRIOS_URL,
        "source_lookup": LOOKUP_URL,
        "slice_contract": slice_obj.get("contract"),
        "slice_collection": collection,
        "kpis_caba": slice_obj.get("kpis"),
        "metricas": slice_obj.get("metrics"),
        "aliases": aliases,
        "barrios_en_slice": len(rows),
        "barrios_en_lookup": len(lookup_barrios),
        "ids_unicos": len(set(ids)),
        "ids_vacios": sum(1 for x in ids if not x),
        "ids_sin_lookup": sorted(x for x in set(ids) - set(lookup_barrios) if x),
        "barrios": normalized,
        "auditoria_bundle": audit_bundle(s),
        "nota": "Referencia pública de validación; no se usa como mecanismo de asignación de personas a barrios.",
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "contract": payload["slice_contract"],
        "barrios_en_slice": payload["barrios_en_slice"],
        "barrios_en_lookup": payload["barrios_en_lookup"],
        "ids_unicos": payload["ids_unicos"],
        "ids_vacios": payload["ids_vacios"],
        "ids_sin_lookup": payload["ids_sin_lookup"],
        "kpis_caba": payload["kpis_caba"],
    }, ensure_ascii=False, indent=2))
    if len(rows) != 48 or len(set(ids)) != 48 or payload["ids_sin_lookup"]:
        raise SystemExit("La referencia barrial no validó exactamente 48 barrios")
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
