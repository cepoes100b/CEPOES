#!/usr/bin/env python3
"""Clasifica los 30 informantes residuales del agregado CENDEU.

No lee PADRON ni DEUDORES. Consume el artefacto agregado por entidad ya calculado
y consulta exclusivamente registros institucionales públicos del BCRA.

Clasificaciones documentadas:
- fideicomiso_financiero: endpoint público vigente BCRA;
- sgr: registro público de Sociedades de Garantía Recíproca;
- fgcp: registro público de Fondos de Garantía de Carácter Público;
- pscpp: registro público de proveedores de crédito entre particulares vía plataformas.

No se equipara automáticamente `fideicomiso_financiero` con `Mercado Secundario`.
La salida ofrece escenarios de sensibilidad separados; esa equivalencia requiere
evidencia metodológica adicional del productor de Mapa de la Deuda.
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
OUTPUT = Path("diagnostico_residuales_bcra.json")

URL_FIDEICOMISOS = "https://www.bcra.gob.ar/api/endpoints/fideicomisos-financieros.php?lang=es"
URL_SGR = "https://www.bcra.gob.ar/en/mutual-guarantee-companies/"
URL_FGCP = "https://www.bcra.gob.ar/fondos-de-garantia-de-caracter-publico/"
URL_PSCPP = "https://www.bcra.gob.ar/registro-de-proveedores-de-servicios-de-creditos-entre-particulares-a-traves-de-plataformas/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CEPOES-validacion-metodologica/1.0)",
    "Accept": "application/json,text/html,*/*",
}


def codigo5(v) -> str:
    s = str(v).strip()
    if not s.isdigit():
        raise ValueError(f"Código no numérico: {v!r}")
    return s.zfill(5)


def lista_codigo_json(url: str, minimo: int) -> tuple[set[str], dict]:
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    obj = r.json()
    candidatos = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "codigo" in v[0]:
                candidatos.append((k, v))
    elif isinstance(obj, list) and obj and isinstance(obj[0], dict) and "codigo" in obj[0]:
        candidatos.append(("$", obj))
    if not candidatos:
        raise RuntimeError(f"No se encontró una lista institucional con campo codigo: {url}")
    key, filas = max(candidatos, key=lambda kv: len(kv[1]))
    codigos = {codigo5(f["codigo"]) for f in filas if isinstance(f, dict) and "codigo" in f}
    if len(codigos) < minimo:
        raise RuntimeError(f"Registro JSON corto: {len(codigos)} < {minimo}: {url}")
    return codigos, {
        "url": url,
        "metodo": "endpoint_json_campo_codigo",
        "ruta_lista": f"$.{key}" if key != "$" else "$",
        "filas": len(filas),
        "codigos_unicos": len(codigos),
    }


def codigos_tabla_html(url: str, prefijo: str, minimo: int) -> tuple[set[str], dict]:
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    codigos = set()
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        primero = " ".join(tds[0].stripped_strings)
        m = re.search(r"\b(\d{5})\b", primero)
        if m and m.group(1).startswith(prefijo):
            codigos.add(m.group(1))
    if len(codigos) < minimo:
        # Fallback conservador: sólo líneas visibles que empiezan con el prefijo
        # esperado y un código de cinco dígitos. No se aceptan otros números de la página.
        texto = soup.get_text("\n")
        for line in texto.splitlines():
            m = re.match(rf"^\s*({re.escape(prefijo)}\d{{{5-len(prefijo)}}})\b", line)
            if m:
                codigos.add(m.group(1))
    if len(codigos) < minimo:
        raise RuntimeError(f"Registro HTML corto: {len(codigos)} < {minimo}: {url}")
    return codigos, {
        "url": url,
        "metodo": "primera_columna_tabla_html_codigo_5_digitos",
        "codigos_unicos": len(codigos),
    }


def agregado(entidades: list[dict]) -> dict:
    deuda = sum(int(e.get("deuda_total_pesos", 0) or 0) for e in entidades)
    mora = sum(int(e.get("deuda_mora_pesos", 0) or 0) for e in entidades)
    registros = sum(int(e.get("registros_caba", 0) or 0) for e in entidades)
    return {
        "entidades": len(entidades),
        "registros_caba": registros,
        "deuda_total_pesos": deuda,
        "deuda_mora_pesos": mora,
        "tasa_mora_monetaria_pct": round(mora / deuda * 100, 4) if deuda else 0.0,
        "suma_deudores_por_entidad_no_unicos": sum(int(e.get("deudores", 0) or 0) for e in entidades),
        "suma_personas_mora_por_entidad_no_unicas": sum(int(e.get("personas_mora", 0) or 0) for e in entidades),
    }


def main() -> int:
    base = json.loads(INPUT.read_text(encoding="utf-8"))
    entidades = base.get("entidades", [])
    if len(entidades) < 400:
        raise SystemExit(f"Agregado inesperadamente corto: {len(entidades)}")

    # EEFF + PNFC vigentes, idéntica lógica al clasificador API anterior, para aislar residuales.
    api = {
        "eeff": ("https://www.bcra.gob.ar/api/endpoints/nomina-entidades.php?action=nomina_AAA00&lang=es", "entidades", 60),
        "emisoras": ("https://www.bcra.gob.ar/api/endpoints/emisoras-tarjetas-credito.php", "data", 80),
        "opnfc": ("https://www.bcra.gob.ar/api/endpoints/proveedores-no-financieros.php?lang=es", "data", 400),
    }
    principales = {}
    for name, (url, key, minimo) in api.items():
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        filas = r.json().get(key, [])
        principales[name] = {codigo5(f["codigo"]) for f in filas if isinstance(f, dict) and "codigo" in f}
        if len(principales[name]) < minimo:
            raise RuntimeError(f"Registro principal {name} corto: {len(principales[name])}")
    universo_principal = principales["eeff"] | principales["emisoras"] | principales["opnfc"]
    residuales = [e for e in entidades if codigo5(e["codigo"]) not in universo_principal]

    fideicomisos, meta_ff = lista_codigo_json(URL_FIDEICOMISOS, minimo=10)
    sgr, meta_sgr = codigos_tabla_html(URL_SGR, prefijo="50", minimo=30)
    fgcp, meta_fgcp = codigos_tabla_html(URL_FGCP, prefijo="51", minimo=10)
    pscpp, meta_pscpp = codigos_tabla_html(URL_PSCPP, prefijo="40", minimo=5)

    sets = {
        "fideicomiso_financiero": fideicomisos,
        "sgr": sgr,
        "fgcp": fgcp,
        "pscpp": pscpp,
    }
    por_categoria = defaultdict(list)
    detalle = []
    for e in residuales:
        codigo = codigo5(e["codigo"])
        hits = [cat for cat, cods in sets.items() if codigo in cods]
        if not hits:
            cat = "residual_no_clasificado"
        elif len(hits) == 1:
            cat = hits[0]
        else:
            cat = "solapamiento_" + "_".join(sorted(hits))
        item = {**e, "categoria_residual_oficial": cat, "coincidencias_registros": hits}
        por_categoria[cat].append(item)
        detalle.append(item)

    resumen_cat = {k: agregado(v) for k, v in sorted(por_categoria.items())}
    todos = agregado(entidades)
    principales_ent = [e for e in entidades if codigo5(e["codigo"]) in universo_principal]
    principal = agregado(principales_ent)

    # Escenarios aditivos de sensibilidad. No implican que todos los FF sean
    # necesariamente el “Mercado Secundario” de Mapa de la Deuda.
    def excluir(categorias: set[str]) -> dict:
        excl_codes = set().union(*(sets[c] for c in categorias)) if categorias else set()
        incluidos = [e for e in entidades if codigo5(e["codigo"]) not in excl_codes]
        return agregado(incluidos)

    escenarios = {
        "todos_informantes": todos,
        "solo_eeff_mas_pnfc": principal,
        "excluir_sgr_fgcp": excluir({"sgr", "fgcp"}),
        "excluir_sgr_fgcp_y_todos_los_fideicomisos": excluir({"sgr", "fgcp", "fideicomiso_financiero"}),
        "excluir_sgr_fgcp_fideicomisos_y_pscpp": excluir({"sgr", "fgcp", "fideicomiso_financiero", "pscpp"}),
    }

    salida = {
        "schema": "cepoes-bcra-residuales-oficiales-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "input": {"cantidad_entidades": len(entidades), "residuales_fuera_eeff_pnfc": len(residuales)},
        "fuentes_oficiales": {
            "fideicomiso_financiero": meta_ff,
            "sgr": meta_sgr,
            "fgcp": meta_fgcp,
            "pscpp": meta_pscpp,
        },
        "por_categoria_residual": resumen_cat,
        "detalle_residuales": sorted(detalle, key=lambda x: int(x.get("personas_mora", 0) or 0), reverse=True),
        "escenarios_aditivos_sensibilidad": escenarios,
        "advertencias": {
            "mercado_secundario_no_equivalente_automaticamente_a_fideicomiso": True,
            "conteos_personas_no_aditivos": True,
            "nota": "Los montos y registros son aditivos. Los deudores/morosos únicos del universo final requieren una corrida integral sobre microdatos una vez documentada la exclusión exacta de Mercado Secundario.",
        },
        "privacidad": {
            "microdatos_personales_leidos": False,
            "identificadores_personales_en_salida": False,
            "solo_entidades_y_agregados": True,
        },
    }
    OUTPUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "fuentes": {k: v["codigos_unicos"] for k, v in salida["fuentes_oficiales"].items()},
        "residuales": len(residuales),
        "categorias": {k: v["entidades"] for k, v in resumen_cat.items()},
        "escenarios": escenarios,
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
