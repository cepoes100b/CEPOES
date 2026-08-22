#!/usr/bin/env python3
"""Clasifica el agregado por entidad de CENDEU contra registros oficiales BCRA.

Esta herramienta NO vuelve a leer PADRON ni DEUDORES. Consume exclusivamente
`diagnostico_bcra_entidades.json`, un artefacto agregado y sin datos personales.

Para páginas BCRA cuyo HTML inicial no incluye las filas, primero intenta requests
+ BeautifulSoup y luego renderiza con Playwright/Chromium. La clasificación se hace
por código publicado en el registro oficial, nunca por inferencia de nombre/rango.

Importante: deudores y personas en mora NO son aditivos entre entidades. La salida
muestra sus sumas por entidad sólo como diagnóstico; los totales únicos por universo
requieren una futura corrida única sobre microdatos.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

INPUT = Path("diagnostico_bcra_entidades.json")
OUTPUT = Path("diagnostico_clasificacion_acreedores_agregado.json")

FUENTES = {
    "entidad_financiera": "https://www.bcra.gob.ar/sistema-financiero-nomina-de-entidades/?bco=AAA00&tipo=1",
    "enf_emisora_tarjeta": "https://www.bcra.gob.ar/emisoras-tarjetas-credito-compra/",
    "otro_pnfc": "https://www.bcra.gob.ar/proveedores-no-financieros/",
    "pscpp": "https://www.bcra.gob.ar/registro-de-proveedores-de-servicios-de-creditos-entre-particulares-a-traves-de-plataformas/",
    "sgr": "https://www.bcra.gob.ar/sociedades-de-garantia-reciproca/",
    "fgcp": "https://www.bcra.gob.ar/fondos-de-garantia-de-caracter-publico/",
    "fideicomiso_financiero": "https://www.bcra.gob.ar/fideicomisos-financieros/",
}

MINIMOS = {
    "entidad_financiera": 50,
    "enf_emisora_tarjeta": 10,
    "otro_pnfc": 30,
    "pscpp": 1,
    "sgr": 10,
    "fgcp": 5,
    "fideicomiso_financiero": 1,
}

ORDEN = [
    "entidad_financiera",
    "enf_emisora_tarjeta",
    "otro_pnfc",
    "pscpp",
    "sgr",
    "fgcp",
    "fideicomiso_financiero",
]


def codigos_desde_html(html: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    out: set[str] = set()
    for tr in soup.find_all("tr"):
        celdas = tr.find_all(["td", "th"])
        if not celdas:
            continue
        txt = " ".join(celdas[0].stripped_strings)
        m = re.match(r"^\s*(\d{1,5})(?:\s|\(|$)", txt)
        if m:
            out.add(m.group(1).zfill(5))
    return out


def requests_html(url: str) -> str:
    r = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CEPOES-validacion-metodologica/1.0)"
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.text


def render_html(url: str) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(6_000)
        html = page.content()
        browser.close()
    return html


def cargar_registro(categoria: str, url: str) -> dict:
    metodo = "requests"
    error_requests = None
    try:
        html = requests_html(url)
        codigos = codigos_desde_html(html)
    except Exception as exc:
        codigos = set()
        error_requests = repr(exc)

    if len(codigos) < MINIMOS[categoria]:
        metodo = "playwright"
        html = render_html(url)
        codigos = codigos_desde_html(html)

    if len(codigos) < MINIMOS[categoria]:
        raise RuntimeError(
            f"Registro {categoria} inesperadamente corto: {len(codigos)} < "
            f"{MINIMOS[categoria]} ({url})"
        )

    return {
        "url": url,
        "metodo": metodo,
        "cantidad_codigos": len(codigos),
        "codigos": sorted(codigos),
        "error_requests": error_requests,
    }


def clasificar(codigo: str, registros: dict[str, dict]) -> str:
    presentes = [cat for cat in ORDEN if codigo in set(registros[cat]["codigos"])]
    if not presentes:
        return "residual_no_clasificado"
    return presentes[0]


def main() -> int:
    if not INPUT.exists():
        raise SystemExit(f"Falta {INPUT}")
    base = json.loads(INPUT.read_text(encoding="utf-8"))
    entidades = base.get("entidades", [])
    if not entidades:
        raise SystemExit("El agregado de entidades no contiene entidades")

    registros = {}
    for cat, url in FUENTES.items():
        print(f"Leyendo registro oficial: {cat}", flush=True)
        registros[cat] = cargar_registro(cat, url)
        print(
            f"  {registros[cat]['cantidad_codigos']} códigos vía {registros[cat]['metodo']}",
            flush=True,
        )

    # Hace visibles los solapamientos entre registros oficiales.
    solapamientos = []
    sets = {cat: set(registros[cat]["codigos"]) for cat in ORDEN}
    for i, a in enumerate(ORDEN):
        for b in ORDEN[i + 1 :]:
            comunes = sorted(sets[a] & sets[b])
            if comunes:
                solapamientos.append({"a": a, "b": b, "codigos": comunes})

    por_cat = defaultdict(lambda: {
        "entidades": 0,
        "registros_caba": 0,
        "deuda_total_pesos": 0,
        "deuda_mora_pesos": 0,
        "suma_deudores_por_entidad_no_unicos": 0,
        "suma_personas_mora_por_entidad_no_unicas": 0,
    })
    detalle = []
    for e in entidades:
        codigo = str(e["codigo"]).zfill(5)
        cat = clasificar(codigo, registros)
        p = por_cat[cat]
        p["entidades"] += 1
        p["registros_caba"] += int(e.get("registros_caba", 0) or 0)
        p["deuda_total_pesos"] += int(e.get("deuda_total_pesos", 0) or 0)
        p["deuda_mora_pesos"] += int(e.get("deuda_mora_pesos", 0) or 0)
        p["suma_deudores_por_entidad_no_unicos"] += int(e.get("deudores", 0) or 0)
        p["suma_personas_mora_por_entidad_no_unicas"] += int(e.get("personas_mora", 0) or 0)
        detalle.append({**e, "categoria_oficial_auditada": cat})

    for cat, p in por_cat.items():
        deuda = p["deuda_total_pesos"]
        p["tasa_mora_monetaria_pct"] = round(
            p["deuda_mora_pesos"] / deuda * 100, 4
        ) if deuda else 0.0

    detalle.sort(
        key=lambda x: (int(x.get("personas_mora", 0)), int(x.get("deuda_mora_pesos", 0))),
        reverse=True,
    )
    residuales = [x for x in detalle if x["categoria_oficial_auditada"] == "residual_no_clasificado"]

    # Campos aditivos exactos del escenario amplio del artefacto base.
    total_deuda = sum(int(e.get("deuda_total_pesos", 0) or 0) for e in entidades)
    total_mora = sum(int(e.get("deuda_mora_pesos", 0) or 0) for e in entidades)
    objetivo = {"entidad_financiera", "enf_emisora_tarjeta", "otro_pnfc"}
    deuda_obj = sum(por_cat[c]["deuda_total_pesos"] for c in objetivo if c in por_cat)
    mora_obj = sum(por_cat[c]["deuda_mora_pesos"] for c in objetivo if c in por_cat)

    salida = {
        "schema": "cepoes-clasificacion-acreedores-agregado-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "input": {
            "schema": base.get("schema"),
            "generado_utc": base.get("generado_utc"),
            "cantidad_entidades": len(entidades),
        },
        "registros_oficiales_bcra": {
            c: {
                "url": registros[c]["url"],
                "metodo": registros[c]["metodo"],
                "cantidad_codigos": registros[c]["cantidad_codigos"],
            }
            for c in ORDEN
        },
        "solapamientos_registros": solapamientos,
        "por_categoria": dict(sorted(por_cat.items())),
        "escenario_aditivo": {
            "todos_informantes": {
                "deuda_total_pesos": total_deuda,
                "deuda_mora_pesos": total_mora,
                "tasa_mora_monetaria_pct": round(total_mora / total_deuda * 100, 4) if total_deuda else 0,
            },
            "entidades_financieras_mas_pnfc": {
                "categorias": sorted(objetivo),
                "deuda_total_pesos": deuda_obj,
                "deuda_mora_pesos": mora_obj,
                "tasa_mora_monetaria_pct": round(mora_obj / deuda_obj * 100, 4) if deuda_obj else 0,
                "participacion_deuda_total_pct": round(deuda_obj / total_deuda * 100, 4) if total_deuda else 0,
                "participacion_deuda_mora_pct": round(mora_obj / total_mora * 100, 4) if total_mora else 0,
            },
        },
        "advertencia_no_aditividad": (
            "Deudores y personas en mora por entidad no pueden sumarse para obtener personas únicas "
            "del universo: una misma persona puede tener deuda con múltiples informantes. Los campos "
            "monetarios y cantidad de registros sí son aditivos. Los conteos únicos exactos se calcularán "
            "en la próxima corrida integral sobre PADRON+DEUDORES."
        ),
        "residuales_top40_por_mora_entidad": residuales[:40],
        "entidades_clasificadas": detalle,
        "privacidad": {
            "microdatos_leidos": False,
            "identificadores_personales_en_salida": False,
            "filas_personales_en_salida": False,
            "solo_agregado_institucional": True,
        },
    }
    OUTPUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "entidades": len(entidades),
        "categorias": {k: v["entidades"] for k, v in por_cat.items()},
        "escenario_aditivo": salida["escenario_aditivo"],
        "residuales": len(residuales),
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
