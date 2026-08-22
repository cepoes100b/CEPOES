#!/usr/bin/env python3
"""Identifica el esquema mínimo de los endpoints que alimentan registros BCRA.

No lee microdatos. Sólo conserva metadatos de respuesta y, por nombre de campo,
la cantidad de valores de exactamente cinco dígitos. No guarda CUIT, domicilios,
teléfonos ni otros campos registrales.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

SOURCES = {
    "entidad_financiera": {
        "page": "https://www.bcra.gob.ar/sistema-financiero-nomina-de-entidades/?bco=AAA00&tipo=1",
        "endpoint_contains": "/api/endpoints/nomina-entidades.php",
    },
    "enf_emisora_tarjeta": {
        "page": "https://www.bcra.gob.ar/emisoras-tarjetas-credito-compra/",
        "endpoint_contains": "/api/endpoints/emisoras-tarjetas-credito.php",
    },
    "otro_pnfc": {
        "page": "https://www.bcra.gob.ar/proveedores-no-financieros/",
        "endpoint_contains": "/api/endpoints/proveedores-no-financieros.php",
    },
}

OUT = Path("diagnostico_esquema_registros_bcra_api.json")
CODE5 = re.compile(r"^\d{5}$")


def scan(obj, path="$", by_key=None, samples=None):
    if by_key is None:
        by_key = defaultdict(set)
    if samples is None:
        samples = defaultdict(list)
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if isinstance(v, (str, int)):
                s = str(v).strip()
                if CODE5.fullmatch(s):
                    by_key[str(k)].add(s)
                    if len(samples[str(k)]) < 10:
                        samples[str(k)].append(s)
            scan(v, p, by_key, samples)
    elif isinstance(obj, list):
        for v in obj:
            scan(v, path + "[]", by_key, samples)
    return by_key, samples


def shape(obj):
    if isinstance(obj, dict):
        return {"type": "dict", "keys": sorted(map(str, obj.keys()))[:100]}
    if isinstance(obj, list):
        first = obj[0] if obj else None
        return {
            "type": "list",
            "length": len(obj),
            "first_type": type(first).__name__ if first is not None else None,
            "first_keys": sorted(map(str, first.keys()))[:100] if isinstance(first, dict) else None,
        }
    return {"type": type(obj).__name__}


def main() -> int:
    out = {
        "schema": "cepoes-bcra-registry-api-shape-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "registros": {},
        "privacidad": {"microdatos_leidos": False, "datos_personales_guardados": False},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 Chrome/151 Safari/537.36")
        for name, cfg in SOURCES.items():
            page = context.new_page()
            result = {"page": cfg["page"], "endpoint_contains": cfg["endpoint_contains"]}
            try:
                with page.expect_response(
                    lambda r, needle=cfg["endpoint_contains"]: needle in r.url,
                    timeout=60_000,
                ) as info:
                    page.goto(cfg["page"], wait_until="domcontentloaded", timeout=60_000)
                resp = info.value
                result["endpoint"] = resp.url
                result["status"] = resp.status
                result["content_type"] = resp.headers.get("content-type", "")
                data = resp.json()
                result["shape"] = shape(data)
                by_key, samples = scan(data)
                result["campos_5_digitos"] = {
                    k: {"cantidad_unicos": len(vals), "muestra": samples[k]}
                    for k, vals in sorted(by_key.items(), key=lambda kv: (-len(kv[1]), kv[0]))
                }
                # El mejor candidato es el campo con más códigos únicos cuyo nombre sugiere código.
                candidates = [
                    (k, vals) for k, vals in by_key.items()
                    if "cod" in k.lower() or "entidad" in k.lower() or "proveedor" in k.lower() or "emis" in k.lower()
                ]
                if not candidates:
                    candidates = list(by_key.items())
                if candidates:
                    k, vals = max(candidates, key=lambda kv: len(kv[1]))
                    result["candidato_codigo"] = {"campo": k, "cantidad_unicos": len(vals)}
                else:
                    result["candidato_codigo"] = None
            except PlaywrightTimeout as exc:
                result["error"] = f"timeout: {exc}"
            except Exception as exc:
                result["error"] = repr(exc)
            out["registros"][name] = result
            print(name, json.dumps({
                "status": result.get("status"),
                "endpoint": result.get("endpoint"),
                "shape": result.get("shape"),
                "candidato_codigo": result.get("candidato_codigo"),
                "error": result.get("error"),
            }, ensure_ascii=False), flush=True)
            page.close()
        browser.close()
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
