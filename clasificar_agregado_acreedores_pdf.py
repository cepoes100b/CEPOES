#!/usr/bin/env python3
"""Clasificación agregada de acreedores usando registros oficiales BCRA estables.

No lee PADRON ni DEUDORES: consume el artefacto agregado por entidad ya generado.

Fuentes de clasificación:
- Entidades financieras: unión exacta de las nóminas oficiales BCRA de bancos
  públicos (tipo=2), bancos privados (tipo=3) y compañías financieras (tipo=5),
  información actualizada a abril de 2026.
- Empresas no financieras emisoras de tarjetas: PDF registral oficial BCRA.
- Otros proveedores no financieros de crédito: PDF registral oficial BCRA.

Los PDFs se leen como tablas y se extrae exclusivamente la primera columna de cada
fila. No se infiere pertenencia por nombre ni por rango numérico.

Advertencia: deudores/personas en mora NO son aditivos entre entidades. En este paso
sólo se consolidan exactamente magnitudes aditivas (registros y montos). Los conteos
únicos por universo se calcularán en una única corrida integral posterior.
"""
from __future__ import annotations

import io
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import requests

INPUT = Path("diagnostico_bcra_entidades.json")
OUTPUT = Path("diagnostico_clasificacion_acreedores_agregado.json")

URL_EMISORAS = "https://www.bcra.gob.ar/archivos/Pdfs/Informacion_usuario/Emisora_tarjetas.pdf"
URL_OPNFC = "https://www.bcra.gob.ar/archivos/Pdfs/Informacion_usuario/Proveedores_no_financieros.pdf"

URL_PUBLICOS = "https://www.bcra.gob.ar/sistema-financiero-nomina-de-entidades/?bco=AAA10&tipo=2"
URL_PRIVADOS = "https://www.bcra.gob.ar/sistema-financiero-nomina-de-entidades/?bco=AAA20&tipo=3"
URL_COMP_FIN = "https://www.bcra.gob.ar/sistema-financiero-nomina-de-entidades/?bco=AAA30&tipo=5"

PUBLICOS = {
    "00011", "00014", "00020", "00029", "00065", "00083", "00093",
    "00094", "00097", "00268", "00300", "00309", "00311", "00315",
}

PRIVADOS = {
    "00007", "00015", "00016", "00017", "00027", "00034", "00044",
    "00045", "00072", "00086", "00131", "00143", "00147", "00165",
    "00191", "00198", "00247", "00254", "00266", "00269", "00277",
    "00281", "00285", "00299", "00301", "00305", "00310", "00312",
    "00319", "00321", "00322", "00330", "00331", "00332", "00338",
    "00339", "00340", "00341", "00384", "00386", "00389", "00426",
    "00431", "00432", "00435", "00448",
}

COMPANIAS_FINANCIERAS = {
    "44077", "44088", "44092", "44093", "44094", "44095", "44096",
    "44098", "44099", "45030", "45056", "45072", "65203",
}

EEFF = PUBLICOS | PRIVADOS | COMPANIAS_FINANCIERAS
assert len(EEFF) == 73


def descargar(url: str) -> bytes:
    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; CEPOES-validacion-metodologica/1.0)"},
        timeout=90,
    )
    r.raise_for_status()
    data = r.content
    if not data.startswith(b"%PDF"):
        raise RuntimeError(f"La respuesta no es PDF válido: {url} ({len(data)} bytes)")
    return data


def codigos_primera_columna_pdf(data: bytes, minimo: int, etiqueta: str) -> set[str]:
    codigos: set[str] = set()
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            for tabla in page.extract_tables() or []:
                for fila in tabla or []:
                    if not fila or fila[0] is None:
                        continue
                    primero = " ".join(str(fila[0]).replace("\n", " ").split())
                    m = re.match(r"^\s*(\d{5})(?:\s|\(|$)", primero)
                    if m:
                        codigos.add(m.group(1))
    if len(codigos) < minimo:
        raise RuntimeError(
            f"Registro PDF {etiqueta} inesperadamente corto: {len(codigos)} < {minimo}"
        )
    return codigos


def resumen_vacio() -> dict:
    return {
        "entidades": 0,
        "registros_caba": 0,
        "deuda_total_pesos": 0,
        "deuda_mora_pesos": 0,
        "suma_deudores_por_entidad_no_unicos": 0,
        "suma_personas_mora_por_entidad_no_unicas": 0,
    }


def main() -> int:
    if not INPUT.exists():
        raise SystemExit(f"Falta {INPUT}")
    base = json.loads(INPUT.read_text(encoding="utf-8"))
    entidades = base.get("entidades", [])
    if len(entidades) < 400:
        raise SystemExit(f"Agregado inesperadamente corto: {len(entidades)} entidades")

    print("Descargando registro PDF de emisoras...", flush=True)
    emisoras = codigos_primera_columna_pdf(descargar(URL_EMISORAS), 40, "emisoras")
    print(f"  {len(emisoras)} códigos", flush=True)

    print("Descargando registro PDF de otros PNFC...", flush=True)
    opnfc = codigos_primera_columna_pdf(descargar(URL_OPNFC), 250, "otros PNFC")
    print(f"  {len(opnfc)} códigos", flush=True)

    ambos_pnfc = emisoras & opnfc
    print(f"  solapamiento emisoras/OPNFC: {len(ambos_pnfc)} códigos", flush=True)

    por_cat = defaultdict(resumen_vacio)
    detalle = []

    def categoria(codigo: str) -> str:
        if codigo in EEFF:
            return "entidad_financiera"
        if codigo in emisoras and codigo in opnfc:
            return "pnfc_ambos_registros"
        if codigo in emisoras:
            return "enf_emisora_tarjeta"
        if codigo in opnfc:
            return "otro_pnfc"
        return "residual_no_objetivo"

    for e in entidades:
        codigo = str(e.get("codigo", "")).zfill(5)
        cat = categoria(codigo)
        p = por_cat[cat]
        p["entidades"] += 1
        p["registros_caba"] += int(e.get("registros_caba", 0) or 0)
        p["deuda_total_pesos"] += int(e.get("deuda_total_pesos", 0) or 0)
        p["deuda_mora_pesos"] += int(e.get("deuda_mora_pesos", 0) or 0)
        p["suma_deudores_por_entidad_no_unicos"] += int(e.get("deudores", 0) or 0)
        p["suma_personas_mora_por_entidad_no_unicas"] += int(e.get("personas_mora", 0) or 0)
        detalle.append({**e, "categoria_oficial_auditada": cat})

    for p in por_cat.values():
        deuda = p["deuda_total_pesos"]
        p["tasa_mora_monetaria_pct"] = round(
            p["deuda_mora_pesos"] / deuda * 100, 4
        ) if deuda else 0.0

    objetivo = {
        "entidad_financiera",
        "enf_emisora_tarjeta",
        "otro_pnfc",
        "pnfc_ambos_registros",
    }
    total_deuda = sum(int(e.get("deuda_total_pesos", 0) or 0) for e in entidades)
    total_mora = sum(int(e.get("deuda_mora_pesos", 0) or 0) for e in entidades)
    deuda_obj = sum(por_cat[c]["deuda_total_pesos"] for c in objetivo if c in por_cat)
    mora_obj = sum(por_cat[c]["deuda_mora_pesos"] for c in objetivo if c in por_cat)

    detalle.sort(
        key=lambda x: (int(x.get("personas_mora", 0) or 0), int(x.get("deuda_mora_pesos", 0) or 0)),
        reverse=True,
    )
    residuales = [x for x in detalle if x["categoria_oficial_auditada"] == "residual_no_objetivo"]

    salida = {
        "schema": "cepoes-clasificacion-acreedores-agregado-v2",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "input": {
            "schema": base.get("schema"),
            "generado_utc": base.get("generado_utc"),
            "cantidad_entidades": len(entidades),
        },
        "fuentes_oficiales_bcra": {
            "entidades_financieras": {
                "metodo": "union_exacta_nominas_publicos_privados_companias_financieras",
                "cantidad_codigos": len(EEFF),
                "urls": [URL_PUBLICOS, URL_PRIVADOS, URL_COMP_FIN],
                "actualizacion_documentada": "abril 2026",
            },
            "enf_emisoras_tarjetas": {
                "metodo": "primera_columna_tablas_pdf_registral",
                "url": URL_EMISORAS,
                "cantidad_codigos": len(emisoras),
            },
            "otros_pnfc": {
                "metodo": "primera_columna_tablas_pdf_registral",
                "url": URL_OPNFC,
                "cantidad_codigos": len(opnfc),
            },
        },
        "control_solapamiento_pnfc": {
            "cantidad_codigos_en_ambos_registros": len(ambos_pnfc),
            "codigos": sorted(ambos_pnfc),
        },
        "por_categoria": dict(sorted(por_cat.items())),
        "escenario_aditivo": {
            "todos_informantes": {
                "deuda_total_pesos": total_deuda,
                "deuda_mora_pesos": total_mora,
                "tasa_mora_monetaria_pct": round(total_mora / total_deuda * 100, 4) if total_deuda else 0.0,
            },
            "eeff_mas_pnfc": {
                "categorias": sorted(objetivo),
                "deuda_total_pesos": deuda_obj,
                "deuda_mora_pesos": mora_obj,
                "tasa_mora_monetaria_pct": round(mora_obj / deuda_obj * 100, 4) if deuda_obj else 0.0,
                "participacion_deuda_total_pct": round(deuda_obj / total_deuda * 100, 4) if total_deuda else 0.0,
                "participacion_deuda_mora_pct": round(mora_obj / total_mora * 100, 4) if total_mora else 0.0,
            },
        },
        "advertencia_no_aditividad": (
            "Los conteos de deudores y personas en mora por entidad no son aditivos porque una misma "
            "persona puede aparecer en múltiples informantes. En esta fase sólo se consolidan con exactitud "
            "registros y montos. Los conteos únicos por universo se obtendrán en una única corrida integral."
        ),
        "residuales_top50_por_mora_entidad": residuales[:50],
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
        "emisoras": len(emisoras),
        "opnfc": len(opnfc),
        "ambos": len(ambos_pnfc),
        "categorias_en_cendeu": {k: v["entidades"] for k, v in por_cat.items()},
        "escenario_aditivo": salida["escenario_aditivo"],
        "residuales": len(residuales),
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
