#!/usr/bin/env python3
"""Diagnóstico del universo CABA según tipo oficial de informante BCRA.

Objetivo:
- descargar en tiempo de ejecución los códigos publicados en registros oficiales BCRA;
- clasificar cada código de entidad de CENDEU sin inferir por nombre;
- medir cuánto cambia el agregado CABA al restringirlo a entidades financieras,
  empresas no financieras emisoras de tarjetas y otros PNFC;
- mantener PSCPP, SGR, FGCP y residuales como categorías diagnósticas separadas.

Privacidad: PADRON y DEUDORES se leen en streaming desde los .7z. La salida
contiene exclusivamente agregados y denominaciones de entidades informantes;
no contiene CUIT/CUIL/CDI de personas, nombres de personas ni filas individuales.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from reconciliar_bcra_entidades import (
    LONG_DEUDORES,
    LONG_PADRON,
    MORA,
    REFERENCIA,
    buscar_interno,
    cargar_maestro,
    monto_u100,
    stream_lineas,
)

SIT_1_5 = {b"1", b"2", b"3", b"4", b"5"}
BIT_CP_INFORMADO = 1
BIT_CP_1000_1499 = 2

FUENTES = {
    "entidad_financiera": {
        "url": "https://www.bcra.gob.ar/sistema-financiero-nomina-de-entidades/?bco=AAA00&tipo=1",
        "minimo": 50,
    },
    "enf_emisora_tarjeta": {
        "url": "https://www.bcra.gob.ar/emisoras-tarjetas-credito-compra/",
        "minimo": 10,
    },
    "otro_pnfc": {
        "url": "https://www.bcra.gob.ar/proveedores-no-financieros/",
        "minimo": 30,
    },
    "pscpp": {
        "url": "https://www.bcra.gob.ar/registro-de-proveedores-de-servicios-de-creditos-entre-particulares-a-traves-de-plataformas/",
        "minimo": 1,
    },
    "sgr": {
        "url": "https://www.bcra.gob.ar/sociedades-de-garantia-reciproca/",
        "minimo": 10,
    },
    "fgcp": {
        "url": "https://www.bcra.gob.ar/fondos-de-garantia-de-caracter-publico/",
        "minimo": 5,
    },
}

CATEGORIAS_OBJETIVO = {
    "entidad_financiera",
    "enf_emisora_tarjeta",
    "otro_pnfc",
}


def extraer_codigos_oficiales(url: str, minimo: int) -> set[str]:
    r = requests.get(
        url,
        headers={"User-Agent": "CEPOES-validacion-metodologica/1.0"},
        timeout=60,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    codigos: set[str] = set()
    for fila in soup.find_all("tr"):
        celdas = fila.find_all(["td", "th"])
        if not celdas:
            continue
        primero = " ".join(celdas[0].stripped_strings)
        m = re.match(r"^\s*(\d{1,5})(?:\s|\(|$)", primero)
        if m:
            codigos.add(m.group(1).zfill(5))
    if len(codigos) < minimo:
        raise RuntimeError(
            f"Registro oficial inesperadamente corto ({len(codigos)} < {minimo}): {url}"
        )
    return codigos


def cargar_registros_oficiales() -> dict[str, set[str]]:
    salida: dict[str, set[str]] = {}
    for categoria, cfg in FUENTES.items():
        codigos = extraer_codigos_oficiales(cfg["url"], cfg["minimo"])
        salida[categoria] = codigos
        print(f"Registro {categoria}: {len(codigos)} códigos", flush=True)
    return salida


def clasificar(codigo: str, registros: dict[str, set[str]]) -> str:
    # Orden deliberado: ENF y otros PNFC se mantienen separados aunque sean
    # parte del universo amplio de proveedores no financieros de crédito.
    for categoria in (
        "entidad_financiera",
        "enf_emisora_tarjeta",
        "otro_pnfc",
        "pscpp",
        "sgr",
        "fgcp",
    ):
        if codigo in registros[categoria]:
            return categoria
    return "residual_no_clasificado"


def nuevo_escenario() -> dict:
    return {
        "ids": set(),
        "mora_ids": set(),
        "deuda_u100": 0,
        "deuda_mora_u100": 0,
        "registros": 0,
    }


def agregar(esc: dict, ident: int, deuda_u100: int, es_mora: bool) -> None:
    esc["ids"].add(ident)
    esc["deuda_u100"] += deuda_u100
    esc["registros"] += 1
    if es_mora:
        esc["mora_ids"].add(ident)
        esc["deuda_mora_u100"] += deuda_u100


def resumir(esc: dict) -> dict:
    deudores = len(esc["ids"])
    mora = len(esc["mora_ids"])
    deuda = esc["deuda_u100"] * 100
    deuda_mora = esc["deuda_mora_u100"] * 100
    return {
        "deudores": deudores,
        "personas_mora": mora,
        "incidencia_mora_pct": round(mora / deudores * 100, 4) if deudores else 0.0,
        "deuda_total_pesos": deuda,
        "deuda_mora_pesos": deuda_mora,
        "tasa_mora_pct": round(deuda_mora / deuda * 100, 4) if deuda else 0.0,
        "registros_incluidos": esc["registros"],
    }


def desv(valor: float, ref: float) -> float | None:
    return round((valor / ref - 1) * 100, 3) if ref else None


def comparar(ind: dict) -> dict:
    return {
        "deudores_pct": desv(ind["deudores"], REFERENCIA["deudores"]),
        "personas_mora_pct": desv(ind["personas_mora"], REFERENCIA["personas_mora"]),
        "incidencia_mora_diferencia_pp": round(
            ind["incidencia_mora_pct"] - REFERENCIA["incidencia_mora_pct"], 4
        ),
        "deuda_total_pct": desv(ind["deuda_total_pesos"], REFERENCIA["deuda_total_pesos"]),
        "deuda_mora_pct": desv(ind["deuda_mora_pesos"], REFERENCIA["deuda_mora_pesos"]),
        "tasa_mora_diferencia_pp": round(
            ind["tasa_mora_pct"] - REFERENCIA["tasa_mora_pct"], 4
        ),
    }


def main() -> int:
    registros = cargar_registros_oficiales()

    # Control de solapamientos: si una página oficial cambia de semántica y un código
    # aparece en dos registros incompatibles, se hace visible en la salida.
    solapamientos = []
    cats = list(registros)
    for i, a in enumerate(cats):
        for b in cats[i + 1 :]:
            comunes = registros[a] & registros[b]
            if comunes:
                solapamientos.append({"a": a, "b": b, "cantidad": len(comunes)})

    carpeta = Path("bcra_deudores")
    padrones = sorted(carpeta.glob("*PADRON.7Z"))
    deudores_arch = sorted(carpeta.glob("*DEUDORES.7Z"))
    if not padrones or not deudores_arch:
        raise SystemExit("Se requieren PADRON.7Z y DEUDORES.7Z")
    padron = padrones[-1]
    deudores = deudores_arch[-1]
    p_int = buscar_interno(padron, "Padron_ARCA.txt")
    d_int = buscar_interno(deudores, "deudores.txt")
    maestro = cargar_maestro(deudores)

    # Universo temporal: sólo identificador + dos bits de calidad/cobertura postal.
    personas: dict[int, int] = {}
    padron_leidos = 0
    print("[1/2] PADRON: universo M/F con provincia 00", flush=True)
    for raw in stream_lineas(padron, p_int):
        if not raw:
            continue
        padron_leidos += 1
        if len(raw) != LONG_PADRON or raw[210:212] != b"00":
            continue
        if raw[199:200].strip().upper() not in (b"M", b"F"):
            continue
        ident_b = raw[0:11].strip()
        if len(ident_b) != 11 or not ident_b.isdigit():
            continue
        cp = raw[200:210].strip()
        bits = 0
        if cp and cp.isdigit() and int(cp) > 0:
            bits |= BIT_CP_INFORMADO
            if len(cp) == 4 and 1000 <= int(cp) <= 1499:
                bits |= BIT_CP_1000_1499
        personas[int(ident_b)] = bits
        if padron_leidos % 10_000_000 == 0:
            print(f"  PADRON {padron_leidos:,}; personas CABA {len(personas):,}", flush=True)

    escenarios = {
        "A_todos_los_informantes_prov00": nuevo_escenario(),
        "B_categorias_objetivo_prov00": nuevo_escenario(),
        "C_categorias_objetivo_cp_informado": nuevo_escenario(),
        "D_categorias_objetivo_cp_1000_1499": nuevo_escenario(),
    }
    por_categoria = defaultdict(nuevo_escenario)
    residual_por_codigo = defaultdict(nuevo_escenario)
    registros_leidos = 0
    montos_invalidos = 0

    print("[2/2] CENDEU: agregando por registro oficial de informante", flush=True)
    for raw in stream_lineas(deudores, d_int):
        if not raw:
            continue
        registros_leidos += 1
        if len(raw) != LONG_DEUDORES or raw[11:13].strip() != b"11":
            continue
        ident_b = raw[13:24].strip()
        if not ident_b.isdigit():
            continue
        ident = int(ident_b)
        bits = personas.get(ident)
        if bits is None:
            continue
        situ = raw[27:29].strip()
        if situ not in SIT_1_5:
            continue
        m7 = monto_u100(raw[29:41])
        m10 = monto_u100(raw[65:77])
        if m7 is None or m10 is None:
            montos_invalidos += 1
            continue
        deuda = m7 + m10
        if deuda <= 0:
            continue

        codigo = raw[0:5].decode("ascii", errors="replace").strip().zfill(5)
        categoria = clasificar(codigo, registros)
        es_mora = situ in MORA

        agregar(escenarios["A_todos_los_informantes_prov00"], ident, deuda, es_mora)
        agregar(por_categoria[categoria], ident, deuda, es_mora)

        if categoria in CATEGORIAS_OBJETIVO:
            agregar(escenarios["B_categorias_objetivo_prov00"], ident, deuda, es_mora)
            if bits & BIT_CP_INFORMADO:
                agregar(escenarios["C_categorias_objetivo_cp_informado"], ident, deuda, es_mora)
            if bits & BIT_CP_1000_1499:
                agregar(escenarios["D_categorias_objetivo_cp_1000_1499"], ident, deuda, es_mora)
        else:
            agregar(residual_por_codigo[codigo], ident, deuda, es_mora)

        if registros_leidos % 10_000_000 == 0:
            print(f"  CENDEU {registros_leidos:,}", flush=True)

    salida_esc = {}
    for nombre, esc in escenarios.items():
        ind = resumir(esc)
        salida_esc[nombre] = {"indicadores": ind, "reconciliacion_v228": comparar(ind)}

    salida_cat = {
        nombre: resumir(esc)
        for nombre, esc in sorted(por_categoria.items())
    }

    residuales = []
    for codigo, esc in residual_por_codigo.items():
        ind = resumir(esc)
        residuales.append({
            "codigo": codigo,
            "denominacion": maestro.get(codigo, ""),
            **ind,
        })
    residuales.sort(key=lambda x: (x["personas_mora"], x["deuda_mora_pesos"]), reverse=True)

    salida = {
        "schema": "cepoes-bcra-universo-acreedores-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "fuentes_microdatos": {"padron": padron.name, "deudores": deudores.name},
        "registros_oficiales_bcra": {
            cat: {"url": FUENTES[cat]["url"], "cantidad_codigos": len(cods)}
            for cat, cods in registros.items()
        },
        "solapamientos_registros": solapamientos,
        "criterios": {
            "persona_operativa": "sexo ARCA M/F y provincia 00",
            "situaciones": [1, 2, 3, 4, 5],
            "mora": [3, 4, 5],
            "deuda": "campo 7 + campo 10; deuda positiva",
            "categorias_objetivo": sorted(CATEGORIAS_OBJETIVO),
            "nota_neobanco": "No se usa neobanco como categoría jurídica BCRA. Si una entidad está registrada como entidad financiera/ENF/PNFC, integra esa categoría oficial; una etiqueta comercial podrá definirse después.",
        },
        "controles": {
            "padron_registros_leidos": padron_leidos,
            "personas_mf_prov00": len(personas),
            "cendeu_registros_leidos": registros_leidos,
            "montos_invalidos": montos_invalidos,
        },
        "escenarios": salida_esc,
        "por_categoria_oficial": salida_cat,
        "residuales_no_objetivo_top30_por_personas_mora": residuales[:30],
        "referencia_v228": REFERENCIA,
        "privacidad": {
            "microdatos_publicados": False,
            "identificadores_personales_en_salida": False,
            "filas_individuales_en_salida": False,
            "microdatos_descomprimidos_en_disco": False,
        },
    }
    Path("diagnostico_universo_acreedores.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "registros_oficiales": salida["registros_oficiales_bcra"],
        "escenarios": salida_esc,
        "por_categoria": salida_cat,
        "top_residuales": residuales[:15],
    }, ensure_ascii=False, indent=2), flush=True)
    print("OK -> diagnostico_universo_acreedores.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
