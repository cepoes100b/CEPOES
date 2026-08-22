#!/usr/bin/env python3
"""Segunda fase de auditoría pública de Mapa de la Deuda.

Extrae el slice barrial público de CABA como referencia de validación y busca
indicios públicos del insumo/proceso postal en el bundle y sourcemaps.
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
    "postcode", "zip code", "codigo postal", "shapefile", "geojson",
    "github.com", ".ipynb", ".py", "barrios_caba", "barrio_caba",
]

GEO_KEYS = ("geo_id", "id", "geography", "geography_id", "geo")
METRIC_HINTS = (
    "deud", "mora", "monto", "deuda", "tasa", "incid", "total",
    "valor", "value", "metric", "situacion", "acreedor",
)


class Scripts(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.srcs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "script":
            return
        d = dict(attrs)
        if d.get("src"):
            self.srcs.append(d["src"])


def get_json(s: requests.Session, url: str):
    r = s.get(url, timeout=(20, 90))
    r.raise_for_status()
    return r.json()


def contexts(text: str, needle: str, radius: int = 180, limit: int = 20):
    low = text.lower()
    n = needle.lower()
    out = []
    start = 0
    while len(out) < limit:
        i = low.find(n, start)
        if i < 0:
            break
        frag = " ".join(text[max(0, i-radius):min(len(text), i+len(n)+radius)].split())
        if frag not in out:
            out.append(frag[:600])
        start = i + max(1, len(n))
    return out


def row_quality(row: dict) -> int:
    keys = [str(k).lower() for k in row]
    score = 0
    if any(k in row for k in GEO_KEYS):
        score += 8
    score += sum(1 for k in keys if any(h in k for h in METRIC_HINTS))
    return score


def extract_records(slice_obj):
    """Encuentra robustamente la colección territorial dentro del slice.

    El contrato público puede representar las geografías como lista de objetos
    o como diccionario indexado por geo_id. Recorremos sólo estructuras JSON
    y priorizamos candidatos de tamaño cercano a los 48 barrios de CABA.
    """
    candidates = []

    def add_candidate(path: str, rows: list[dict], origin: str) -> None:
        if not rows:
            return
        quality = sum(row_quality(r) for r in rows[: min(20, len(rows))])
        # 48 es un criterio de ranking, no una condición rígida.
        size_bonus = max(0, 60 - abs(len(rows) - 48))
        explicit_geo = sum(
            1 for r in rows[: min(20, len(rows))]
            if any(k in r and str(r.get(k, "")).strip() for k in GEO_KEYS)
        )
        score = quality + size_bonus + explicit_geo * 3
        candidates.append((score, -abs(len(rows) - 48), path, origin, rows))

    def visit(node, path: str = "$", depth: int = 0) -> None:
        if depth > 7:
            return

        if isinstance(node, list):
            dict_rows = [x for x in node if isinstance(x, dict)]
            if dict_rows and len(dict_rows) >= max(1, int(len(node) * 0.8)):
                add_candidate(path, [dict(x) for x in dict_rows], "list")
            for i, child in enumerate(node[:100]):
                if isinstance(child, (dict, list)):
                    visit(child, f"{path}[{i}]", depth + 1)
            return

        if not isinstance(node, dict):
            return

        # Caso frecuente en APIs agregadas: {"geo_id_1": {...}, ...}.
        dict_items = [(k, v) for k, v in node.items() if isinstance(v, dict)]
        if len(dict_items) >= 2 and len(dict_items) >= int(len(node) * 0.7):
            rows = []
            for key, value in dict_items:
                row = dict(value)
                if not any(k in row for k in GEO_KEYS):
                    row["geo_id"] = str(key)
                rows.append(row)
            add_candidate(path, rows, "dict_indexed")

        for key, child in node.items():
            if isinstance(child, (dict, list)):
                visit(child, f"{path}.{key}", depth + 1)

    visit(slice_obj)
    if not candidates:
        top = list(slice_obj.keys())[:100] if isinstance(slice_obj, dict) else []
        raise RuntimeError(
            "No se encontró una colección de geografías en el slice barrial; "
            f"tipo={type(slice_obj).__name__}, claves_superiores={top}"
        )

    candidates.sort(reverse=True, key=lambda x: (x[0], x[1]))
    score, _distance, path, origin, rows = candidates[0]
    return {"path": path, "origin": origin, "score": score}, rows


def collect_lookup_barrios(lookup_obj):
    """Recupera barrios del lookup aunque estén anidados."""
    encontrados = {}

    def visit(node, depth: int = 0):
        if depth > 8:
            return
        if isinstance(node, dict):
            level = str(node.get("level") or node.get("nivel") or "")
            scope = str(node.get("scope") or node.get("scope_id") or "")
            gid = node.get("geo_id") or node.get("id")
            if level == "barrio_caba" and (scope in ("", "02")) and gid is not None:
                encontrados[str(gid)] = node
            for child in node.values():
                if isinstance(child, (dict, list)):
                    visit(child, depth + 1)
        elif isinstance(node, list):
            for child in node:
                if isinstance(child, (dict, list)):
                    visit(child, depth + 1)

    visit(lookup_obj)
    return encontrados


def main():
    s = requests.Session()
    s.headers.update({"User-Agent": "CEPOES-public-method-audit/2.1"})

    barrios = get_json(s, BARRIOS_URL)
    lookup = get_json(s, LOOKUP_URL)
    collection_meta, rows = extract_records(barrios)
    lookup_barrios = collect_lookup_barrios(lookup)

    ids = []
    normalized_rows = []
    for row in rows:
        gid = str(
            row.get("geo_id") or row.get("id") or row.get("geography")
            or row.get("geography_id") or row.get("geo") or ""
        )
        ids.append(gid)
        geo = lookup_barrios.get(gid, {})
        normalized_rows.append({
            "geo_id": gid,
            "nombre": (
                geo.get("nombre") or geo.get("name")
                or row.get("nombre") or row.get("name")
            ),
            "bbox": geo.get("bbox"),
            "source": geo.get("source"),
            "source_layer": geo.get("source_layer"),
            "metricas_publicas": row,
        })

    home = s.get(HOME, timeout=(20, 60))
    home.raise_for_status()
    parser = Scripts()
    parser.feed(home.text)
    js_urls = [urljoin(HOME, x) for x in parser.srcs if x]

    bundle_audit = []
    for url in js_urls:
        try:
            r = s.get(url, timeout=(20, 90))
            r.raise_for_status()
            text = r.text
        except Exception as e:
            bundle_audit.append({"url": url, "error": str(e)})
            continue

        found = {}
        for n in NEEDLES:
            cc = contexts(text, n)
            if cc:
                found[n] = cc

        sm = re.search(r"sourceMappingURL\s*=\s*([^\s*]+)", text)
        sm_urls = []
        if sm:
            sm_urls.append(urljoin(url, sm.group(1).strip()))
        if url.endswith(".js"):
            sm_urls.append(url + ".map")

        sourcemaps = []
        for sm_url in dict.fromkeys(sm_urls):
            try:
                rr = s.get(sm_url, timeout=(15, 45), allow_redirects=True)
                ct = rr.headers.get("content-type", "")
                entry = {
                    "url": sm_url,
                    "status": rr.status_code,
                    "content_type": ct,
                    "bytes": len(rr.content),
                }
                if rr.status_code == 200 and (
                    "json" in ct.lower() or rr.text.lstrip().startswith("{")
                ):
                    sm_text = rr.text
                    hits = {}
                    for n in NEEDLES:
                        cc = contexts(sm_text, n, radius=220, limit=30)
                        if cc:
                            hits[n] = cc
                    entry["indicios"] = hits
                    try:
                        sm_obj = rr.json()
                        entry["sources_count"] = (
                            len(sm_obj.get("sources", []))
                            if isinstance(sm_obj, dict) else None
                        )
                        entry["sources_relevantes"] = [
                            x for x in sm_obj.get("sources", [])
                            if isinstance(x, str)
                            and any(
                                n.lower() in x.lower()
                                for n in ("postal", "geo", "barrio", "deuda", "data")
                            )
                        ][:200]
                    except Exception:
                        pass
                sourcemaps.append(entry)
            except Exception as e:
                sourcemaps.append({"url": sm_url, "error": str(e)})

        bundle_audit.append({
            "url": url,
            "bytes": len(r.content),
            "indicios": found,
            "sourcemaps": sourcemaps,
        })

    payload = {
        "schema": "cepoes-mapadeladeuda-barrio-reference-v2",
        "period": PERIOD,
        "source_slice": BARRIOS_URL,
        "source_lookup": LOOKUP_URL,
        "slice_collection": collection_meta,
        "barrios_en_slice": len(rows),
        "barrios_en_lookup": len(lookup_barrios),
        "ids_unicos": len(set(ids)),
        "ids_vacios": sum(1 for x in ids if not x),
        "ids_sin_lookup": sorted(x for x in set(ids) - set(lookup_barrios) if x),
        "barrios": normalized_rows,
        "auditoria_bundle": bundle_audit,
        "nota": (
            "Los valores barriales son referencia pública para validar una futura "
            "réplica; no se usan para asignar personas a barrios."
        ),
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps({
        "slice_collection": collection_meta,
        "barrios_en_slice": payload["barrios_en_slice"],
        "barrios_en_lookup": payload["barrios_en_lookup"],
        "ids_unicos": payload["ids_unicos"],
        "ids_vacios": payload["ids_vacios"],
        "ids_sin_lookup": payload["ids_sin_lookup"],
        "bundles": len(bundle_audit),
    }, ensure_ascii=False, indent=2))
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
