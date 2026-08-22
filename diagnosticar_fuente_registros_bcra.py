#!/usr/bin/env python3
"""Descubre endpoints públicos BCRA para categorías residuales de CENDEU.

No lee PADRON ni DEUDORES. Registra sólo URLs, tipos de recurso, status HTTP y
scripts públicos para identificar las fuentes oficiales de clasificación de
fideicomisos financieros, SGR, FGCP y plataformas de crédito entre particulares.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

PAGES = {
    "fideicomiso_financiero": "https://www.bcra.gob.ar/fideicomisos-financieros/",
    "sgr": "https://www.bcra.gob.ar/sociedades-de-garantia-reciproca/",
    "fgcp": "https://www.bcra.gob.ar/fondos-de-garantia-de-caracter-publico/",
    "pscpp": "https://www.bcra.gob.ar/registro-de-proveedores-de-servicios-de-creditos-entre-particulares-a-traves-de-plataformas/",
}

OUT = Path("diagnostico_fuentes_registros_bcra.json")


def same_bcra(url: str) -> bool:
    try:
        return (urlparse(url).hostname or "").endswith("bcra.gob.ar")
    except Exception:
        return False


def main() -> int:
    resultado = {
        "schema": "cepoes-bcra-residual-registry-network-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "paginas": {},
        "privacidad": {"microdatos_leidos": False, "datos_personales_en_salida": False},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/151 Safari/537.36"
        )
        for nombre, url in PAGES.items():
            page = context.new_page()
            reqs, resps, console_errors = [], [], []

            def on_request(req):
                if same_bcra(req.url):
                    reqs.append({"url": req.url, "resource_type": req.resource_type, "method": req.method})

            def on_response(resp):
                if same_bcra(resp.url):
                    resps.append({
                        "url": resp.url,
                        "status": resp.status,
                        "content_type": resp.headers.get("content-type", ""),
                    })

            def on_console(msg):
                if msg.type == "error":
                    console_errors.append(msg.text[:500])

            page.on("request", on_request)
            page.on("response", on_response)
            page.on("console", on_console)
            nav_error = None
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                page.wait_for_timeout(8_000)
            except Exception as exc:
                nav_error = str(exc)[:1000]
            scripts = page.eval_on_selector_all("script[src]", "els => els.map(e => e.src).filter(Boolean)")
            texto = page.locator("body").inner_text(timeout=10_000) if page.locator("body").count() else ""
            resultado["paginas"][nombre] = {
                "url": url,
                "navigation_error": nav_error,
                "title": page.title(),
                "body_text_length": len(texto),
                "scripts": sorted(set(scripts)),
                "requests": reqs,
                "responses": resps,
                "console_errors": console_errors[:20],
            }
            page.close()
        browser.close()

    OUT.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for nombre, d in resultado["paginas"].items():
        print(f"{nombre}: scripts={len(d['scripts'])} req={len(d['requests'])} resp={len(d['responses'])}")
        for r in d["requests"]:
            if r["resource_type"] in ("xhr", "fetch"):
                print("  DYNAMIC", r["method"], r["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
