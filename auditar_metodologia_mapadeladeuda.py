#!/usr/bin/env python3
"""Audita únicamente recursos públicos de mapadeladeuda.ar para reconstruir
la metodología territorial declarada/implementada.

No descarga microdatos ni intenta acceder a recursos privados. La salida conserva
sólo metadatos, URLs públicas, claves del manifest y contextos acotados alrededor
de términos metodológicos relevantes.
"""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

HOME = "https://mapadeladeuda.ar/"
MANIFEST = "https://datos.mapadeladeuda.ar/manifest.json"
OUT = Path("diagnostico_metodologia_mapadeladeuda.json")
MAX_ASSET_BYTES = 8_000_000
MAX_FOLLOWUP_BYTES = 5_000_000
KEYWORDS = (
    "codigo postal", "código postal", "postal", "cp", "cpa", "barrio",
    "barrio_caba", "comuna", "municipio", "departamento", "ign",
    "instituto geografico", "instituto geográfico", "geocod", "geograf",
    "centroid", "centroide", "polygon", "poligono", "polígono",
    "shapefile", "geojson", "topojson", "lat", "lon", "longitud",
    "latitud", "residencia", "domicilio", "localidad", "mobile-slices-v2",
)
FILE_EXTS = (".json", ".geojson", ".topojson", ".csv", ".tsv", ".parquet", ".pmtiles", ".pbf")


class ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        if tag == "script" and d.get("src"):
            self.scripts.append(d["src"] or "")
        if tag == "link" and d.get("href"):
            self.links.append(d["href"] or "")


def norm_text(s: str) -> str:
    return " ".join(s.split())


def contexts(text: str, radius: int = 220, max_hits: int = 120) -> list[dict[str, str]]:
    low = text.lower()
    hits: list[dict[str, str]] = []
    seen: set[str] = set()
    for kw in KEYWORDS:
        start = 0
        while len(hits) < max_hits:
            i = low.find(kw, start)
            if i < 0:
                break
            snippet = norm_text(text[max(0, i - radius): min(len(text), i + len(kw) + radius)])
            key = snippet[:300]
            if key and key not in seen:
                seen.add(key)
                hits.append({"termino": kw, "contexto": snippet[:700]})
            start = i + max(1, len(kw))
    return hits


def extract_urls_and_files(text: str, base: str) -> list[str]:
    found: set[str] = set()
    for raw in re.findall(r"https?://[^\s\"'<>\\]+", text):
        found.add(raw.rstrip(")],;}"))
    path_re = re.compile(r"(?:[\"'])([^\"']+\.(?:json|geojson|topojson|csv|tsv|parquet|pmtiles|pbf)(?:\?[^\"']*)?)(?:[\"'])", re.I)
    for raw in path_re.findall(text):
        found.add(urljoin(base, raw))
    return sorted(found)


def recursive_strings(obj: Any, path: str = "$") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kp = f"{path}.{k}"
            out.extend(recursive_strings(v, kp))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(recursive_strings(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        out.append((path, obj))
    return out


def keyword_entries_from_json(obj: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for p, s in recursive_strings(obj):
        low = f"{p} {s}".lower()
        if any(k in low for k in KEYWORDS):
            out.append({"ruta": p, "valor": s[:1000]})
    return out[:500]


def get_text(sess: requests.Session, url: str, limit: int) -> tuple[dict[str, Any], str | None]:
    meta: dict[str, Any] = {"url": url}
    try:
        r = sess.get(url, timeout=(20, 60), allow_redirects=True, stream=True)
        meta.update({
            "status": r.status_code,
            "final_url": r.url,
            "content_type": r.headers.get("content-type"),
            "content_length_header": r.headers.get("content-length"),
        })
        r.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in r.iter_content(1 << 16):
            if not chunk:
                continue
            total += len(chunk)
            if total > limit:
                meta["truncado_por_limite"] = True
                break
            chunks.append(chunk)
        data = b"".join(chunks)
        meta["bytes_leidos"] = len(data)
        meta["sha256"] = hashlib.sha256(data).hexdigest()
        enc = r.encoding or "utf-8"
        try:
            text = data.decode(enc, errors="replace")
        except LookupError:
            text = data.decode("utf-8", errors="replace")
        return meta, text
    except Exception as e:
        meta["error"] = f"{type(e).__name__}: {e}"
        return meta, None


def relevant_url(url: str) -> bool:
    low = url.lower()
    return (
        "mapadeladeuda" in low
        or any(x in low for x in FILE_EXTS)
        or any(k.replace(" ", "") in low.replace("-", "").replace("_", "") for k in ("barrio", "geo", "postal", "ign", "manifest"))
    )


def audit_playwright() -> dict[str, Any]:
    result: dict[str, Any] = {"disponible": False, "requests_relevantes": [], "texto_metodologico": []}
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        result["error_import"] = str(e)
        return result

    reqs: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})

        def on_response(resp: Any) -> None:
            if relevant_url(resp.url):
                try:
                    ct = resp.headers.get("content-type")
                except Exception:
                    ct = None
                reqs.append({"url": resp.url, "status": resp.status, "content_type": ct})

        page.on("response", on_response)
        try:
            page.goto(HOME, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(12000)
            result["titulo"] = page.title()
            body = page.locator("body").inner_text(timeout=20000)
            result["texto_metodologico"] = contexts(body, radius=260, max_hits=80)
            result["url_final"] = page.url
            result["disponible"] = True
        except Exception as e:
            result["error_navegacion"] = f"{type(e).__name__}: {e}"
        finally:
            browser.close()
    uniq: dict[str, dict[str, Any]] = {}
    for row in reqs:
        uniq[row["url"]] = row
    result["requests_relevantes"] = list(uniq.values())[:500]
    return result


def main() -> None:
    sess = requests.Session()
    sess.headers.update({"User-Agent": "CEPOES-metodologia-audit/1.0 (+public-resources-only)"})
    out: dict[str, Any] = {
        "schema": "cepoes-mapadeladeuda-method-audit-v1",
        "objetivo": "Reconstruir la ruta pública código postal -> geografía -> barrio declarada o expuesta por mapadeladeuda.ar",
        "limites": [
            "Sólo recursos públicos accesibles sin autenticación.",
            "No se descargan microdatos personales.",
            "Los contextos de código se limitan a fragmentos metodológicos acotados.",
            "La ausencia de una tabla pública no demuestra que no exista en el pipeline privado del productor.",
        ],
    }

    home_meta, home = get_text(sess, HOME, MAX_ASSET_BYTES)
    out["home"] = home_meta
    script_urls: list[str] = []
    if home:
        parser = ScriptParser()
        parser.feed(home)
        script_urls = sorted({urljoin(HOME, s) for s in parser.scripts if s})
        out["home"]["scripts_detectados"] = script_urls
        out["home"]["contextos_metodologicos"] = contexts(home)
        out["home"]["referencias_archivos"] = extract_urls_and_files(home, HOME)[:300]

    assets: list[dict[str, Any]] = []
    all_refs: set[str] = set()
    for url in script_urls[:80]:
        meta, text = get_text(sess, url, MAX_ASSET_BYTES)
        row = dict(meta)
        if text:
            row["contextos_metodologicos"] = contexts(text)
            refs = extract_urls_and_files(text, url)
            row["referencias_relevantes"] = [u for u in refs if relevant_url(u)][:250]
            all_refs.update(refs)
        assets.append(row)
    out["assets_frontend"] = assets

    manifest_meta, manifest_text = get_text(sess, MANIFEST, MAX_FOLLOWUP_BYTES)
    manifest_section: dict[str, Any] = dict(manifest_meta)
    manifest_obj: Any = None
    if manifest_text:
        try:
            manifest_obj = json.loads(manifest_text)
            manifest_section["json_valido"] = True
            if isinstance(manifest_obj, dict):
                manifest_section["claves_raiz"] = list(manifest_obj.keys())
            manifest_section["entradas_metodologicas"] = keyword_entries_from_json(manifest_obj)
            refs = extract_urls_and_files(manifest_text, MANIFEST)
            manifest_section["referencias_archivos"] = refs[:1000]
            all_refs.update(refs)
        except Exception as e:
            manifest_section["json_valido"] = False
            manifest_section["error_json"] = str(e)
            manifest_section["contextos_metodologicos"] = contexts(manifest_text)
    out["manifest"] = manifest_section

    # Seguir sólo referencias públicas potencialmente metodológicas y pequeñas.
    candidates = sorted({u for u in all_refs if relevant_url(u) and u != MANIFEST})
    followups: list[dict[str, Any]] = []
    for url in candidates[:80]:
        low = url.lower()
        if not (any(ext in low for ext in FILE_EXTS) or any(k in low for k in ("geo", "barrio", "postal", "ign", "manifest", "map"))):
            continue
        meta, text = get_text(sess, url, MAX_FOLLOWUP_BYTES)
        row = dict(meta)
        if text:
            row["contextos_metodologicos"] = contexts(text, radius=260, max_hits=60)
            if "json" in str(meta.get("content_type", "")).lower() or any(ext in low for ext in (".json", ".geojson", ".topojson")):
                try:
                    obj = json.loads(text)
                    row["entradas_metodologicas_json"] = keyword_entries_from_json(obj)
                except Exception:
                    pass
        followups.append(row)
    out["recursos_seguidos"] = followups

    out["navegador"] = audit_playwright()

    # Resumen mecánico, sin convertir indicios en afirmaciones no verificadas.
    joined = json.dumps(out, ensure_ascii=False).lower()
    out["senales"] = {
        "manifest_accesible": bool(manifest_text),
        "menciona_barrio": "barrio" in joined,
        "menciona_codigo_postal": ("codigo postal" in joined or "código postal" in joined or "postal" in joined),
        "menciona_ign": ("instituto geográfico" in joined or "instituto geografico" in joined or '"ign"' in joined),
        "menciona_geocodificacion": "geocod" in joined,
        "menciona_centroide": ("centroid" in joined or "centroide" in joined),
        "menciona_geojson": "geojson" in joined,
        "menciona_barrio_caba": "barrio_caba" in joined,
        "menciona_mobile_slices_v2": "mobile-slices-v2" in joined,
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out["senales"], ensure_ascii=False, indent=2))
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
