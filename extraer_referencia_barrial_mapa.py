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


def extract_records(slice_obj):
    # Contrato actual: buscar de manera robusta la lista de objetos que contenga geo_id.
    candidates = []
    if isinstance(slice_obj, dict):
        for k, v in slice_obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                score = sum(1 for row in v[:10] if any(x in row for x in ("geo_id", "id", "geography")))
                if score:
                    candidates.append((score, k, v))
    if not candidates:
        raise RuntimeError("No se encontró una lista de geografías en el slice barrial")
    candidates.sort(reverse=True, key=lambda x: x[0])
    return candidates[0][1], candidates[0][2]


def main():
    s = requests.Session()
    s.headers.update({"User-Agent": "CEPOES-public-method-audit/2.0"})

    barrios = get_json(s, BARRIOS_URL)
    lookup = get_json(s, LOOKUP_URL)
    list_key, rows = extract_records(barrios)

    lookup_features = lookup.get("features", []) if isinstance(lookup, dict) else []
    lookup_barrios = {
        str(x.get("geo_id")): x
        for x in lookup_features
        if isinstance(x, dict) and x.get("level") == "barrio_caba" and x.get("scope") == "02"
    }

    ids = []
    normalized_rows = []
    for row in rows:
        gid = str(row.get("geo_id") or row.get("id") or row.get("geography") or "")
        ids.append(gid)
        geo = lookup_barrios.get(gid, {})
        normalized_rows.append({
            "geo_id": gid,
            "nombre": geo.get("nombre") or row.get("nombre") or row.get("name"),
            "bbox": geo.get("bbox"),
            "source": geo.get("source"),
            "source_layer": geo.get("source_layer"),
            "metricas_publicas": row,
        })

    home = s.get(HOME, timeout=(20, 60))
    home.raise_for_status()
    parser = Scripts(); parser.feed(home.text)
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
        # También probar convención .js.map, sin asumir que existe.
        if url.endswith(".js"):
            sm_urls.append(url + ".map")

        sourcemaps = []
        for sm_url in dict.fromkeys(sm_urls):
            try:
                rr = s.get(sm_url, timeout=(15, 45), allow_redirects=True)
                ct = rr.headers.get("content-type", "")
                entry = {"url": sm_url, "status": rr.status_code, "content_type": ct, "bytes": len(rr.content)}
                if rr.status_code == 200 and ("json" in ct.lower() or rr.text.lstrip().startswith("{")):
                    sm_text = rr.text
                    hits = {}
                    for n in NEEDLES:
                        cc = contexts(sm_text, n, radius=220, limit=30)
                        if cc:
                            hits[n] = cc
                    entry["indicios"] = hits
                    try:
                        sm_obj = rr.json()
                        entry["sources_count"] = len(sm_obj.get("sources", [])) if isinstance(sm_obj, dict) else None
                        entry["sources_relevantes"] = [
                            x for x in sm_obj.get("sources", [])
                            if isinstance(x, str) and any(n.lower() in x.lower() for n in ("postal", "geo", "barrio", "deuda", "data"))
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
        "schema": "cepoes-mapadeladeuda-barrio-reference-v1",
        "period": PERIOD,
        "source_slice": BARRIOS_URL,
        "source_lookup": LOOKUP_URL,
        "slice_list_key": list_key,
        "barrios_en_slice": len(rows),
        "barrios_en_lookup": len(lookup_barrios),
        "ids_unicos": len(set(ids)),
        "ids_sin_lookup": sorted(set(ids) - set(lookup_barrios)),
        "barrios": normalized_rows,
        "auditoria_bundle": bundle_audit,
        "nota": "Los valores barriales son referencia pública para validar una futura réplica; no se usan para asignar personas a barrios.",
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "barrios_en_slice": payload["barrios_en_slice"],
        "barrios_en_lookup": payload["barrios_en_lookup"],
        "ids_unicos": payload["ids_unicos"],
        "ids_sin_lookup": payload["ids_sin_lookup"],
        "bundles": len(bundle_audit),
    }, ensure_ascii=False, indent=2))
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
