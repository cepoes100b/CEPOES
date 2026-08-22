#!/usr/bin/env python3
"""Clasifica el agregado CENDEU por registros oficiales vigentes del BCRA.

Consume exclusivamente `diagnostico_bcra_entidades.json` (447 informantes ya
agregados, sin microdatos personales) y los endpoints públicos que alimentan las
tablas del sitio BCRA.

Fuentes vigentes descubiertas desde el tráfico público del propio sitio:
- Nómina de entidades financieras: $.entidades, campo codigo.
- Emisoras no financieras de tarjetas: $.data, campo codigo.
- Otros proveedores no financieros de crédito: $.data, campo codigo.

No hay inferencias por nombre ni por rangos de códigos.

Nota de no aditividad: deuda, deuda en mora y registros son aditivos entre
informantes. Los conteos de personas/deudores no lo son porque una persona puede
estar informada por más de una entidad; esos conteos únicos se calcularán en una
única corrida integral posterior sobre PADRON+DEUDORES.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

INPUT = Path("diagnostico_bcra_entidades.json")
OUTPUT = Path("diagnostico_clasificacion_acreedores_agregado.json")

ENDPOINTS = {
    "entidad_financiera": {
        "url": "https://www.bcra.gob.ar/api/endpoints/nomina-entidades.php?action=nomina_AAA00&lang=es",
        "lista": "entidades",
        "minimo": 60,
    },
    "enf_emisora_tarjeta": {
        "url": "https://www.bcra.gob.ar/api/endpoints/emisoras-tarjetas-credito.php",
        "lista": "data",
        "minimo": 80,
    },
    "otro_pnfc": {
        "url": "https://www.bcra.gob.ar/api/endpoints/proveedores-no-financieros.php?lang=es",
        "lista": "data",
        "minimo": 400,
    },
}


def codigo5(x) -> str:
    s = str(x).strip()
    if not s.isdigit():
        raise ValueError(f"Código no numérico: {x!r}")
    return s.zfill(5)


def cargar_registro(cfg: dict) -> tuple[set[str], dict]:
    r = requests.get(
        cfg["url"],
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CEPOES-validacion-metodologica/1.0)",
            "Accept": "application/json,text/plain,*/*",
        },
        timeout=60,
    )
    r.raise_for_status()
    obj = r.json()
    filas = obj.get(cfg["lista"])
    if not isinstance(filas, list):
        raise RuntimeError(f"Respuesta sin lista {cfg['lista']!r}: {cfg['url']}")
    codigos = {codigo5(f["codigo"]) for f in filas if isinstance(f, dict) and "codigo" in f}
    if len(codigos) < cfg["minimo"]:
        raise RuntimeError(
            f"Registro inesperadamente corto: {len(codigos)} < {cfg['minimo']} ({cfg['url']})"
        )
    meta = {
        "url": cfg["url"],
        "ruta_lista": f"$.{cfg['lista']}",
        "filas": len(filas),
        "codigos_unicos": len(codigos),
        "content_type": r.headers.get("content-type", ""),
    }
    return codigos, meta


def nuevo() -> dict:
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

    registros: dict[str, set[str]] = {}
    fuentes = {}
    for categoria, cfg in ENDPOINTS.items():
        codigos, meta = cargar_registro(cfg)
        registros[categoria] = codigos
        fuentes[categoria] = meta
        print(categoria, meta, flush=True)

    solap_eeff_emis = registros["entidad_financiera"] & registros["enf_emisora_tarjeta"]
    solap_eeff_opnfc = registros["entidad_financiera"] & registros["otro_pnfc"]
    solap_pnfc = registros["enf_emisora_tarjeta"] & registros["otro_pnfc"]

    def categoria(codigo: str) -> str:
        eeff = codigo in registros["entidad_financiera"]
        emis = codigo in registros["enf_emisora_tarjeta"]
        opnfc = codigo in registros["otro_pnfc"]
        if eeff:
            # Si apareciera un solapamiento inesperado, se conserva EEFF y se hace
            # visible mediante controles; no se duplica el monto.
            return "entidad_financiera"
        if emis and opnfc:
            return "pnfc_ambos_registros"
        if emis:
            return "enf_emisora_tarjeta"
        if opnfc:
            return "otro_pnfc"
        return "residual_fuera_eeff_pnfc"

    por_cat = defaultdict(nuevo)
    detalle = []
    for e in entidades:
        codigo = codigo5(e.get("codigo", ""))
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
        d = p["deuda_total_pesos"]
        p["tasa_mora_monetaria_pct"] = round(p["deuda_mora_pesos"] / d * 100, 4) if d else 0.0

    objetivo = {"entidad_financiera", "enf_emisora_tarjeta", "otro_pnfc", "pnfc_ambos_registros"}
    total_deuda = sum(int(e.get("deuda_total_pesos", 0) or 0) for e in entidades)
    total_mora = sum(int(e.get("deuda_mora_pesos", 0) or 0) for e in entidades)
    total_registros = sum(int(e.get("registros_caba", 0) or 0) for e in entidades)
    deuda_obj = sum(por_cat[c]["deuda_total_pesos"] for c in objetivo if c in por_cat)
    mora_obj = sum(por_cat[c]["deuda_mora_pesos"] for c in objetivo if c in por_cat)
    reg_obj = sum(por_cat[c]["registros_caba"] for c in objetivo if c in por_cat)

    detalle.sort(
        key=lambda x: (int(x.get("personas_mora", 0) or 0), int(x.get("deuda_mora_pesos", 0) or 0)),
        reverse=True,
    )
    residuales = [x for x in detalle if x["categoria_oficial_auditada"] == "residual_fuera_eeff_pnfc"]

    salida = {
        "schema": "cepoes-clasificacion-acreedores-agregado-api-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "input": {
            "schema": base.get("schema"),
            "generado_utc": base.get("generado_utc"),
            "cantidad_entidades": len(entidades),
        },
        "fuentes_oficiales_bcra": fuentes,
        "controles_solapamiento": {
            "eeff_emisoras": sorted(solap_eeff_emis),
            "eeff_opnfc": sorted(solap_eeff_opnfc),
            "emisoras_opnfc": sorted(solap_pnfc),
            "cantidad_emisoras_opnfc": len(solap_pnfc),
        },
        "por_categoria": dict(sorted(por_cat.items())),
        "escenario_aditivo": {
            "todos_informantes": {
                "registros_caba": total_registros,
                "deuda_total_pesos": total_deuda,
                "deuda_mora_pesos": total_mora,
                "tasa_mora_monetaria_pct": round(total_mora / total_deuda * 100, 4) if total_deuda else 0.0,
            },
            "eeff_mas_pnfc_vigentes": {
                "categorias": sorted(objetivo),
                "registros_caba": reg_obj,
                "deuda_total_pesos": deuda_obj,
                "deuda_mora_pesos": mora_obj,
                "tasa_mora_monetaria_pct": round(mora_obj / deuda_obj * 100, 4) if deuda_obj else 0.0,
                "participacion_registros_pct": round(reg_obj / total_registros * 100, 4) if total_registros else 0.0,
                "participacion_deuda_total_pct": round(deuda_obj / total_deuda * 100, 4) if total_deuda else 0.0,
                "participacion_deuda_mora_pct": round(mora_obj / total_mora * 100, 4) if total_mora else 0.0,
            },
        },
        "advertencia_no_aditividad": (
            "Deudores y personas en mora por entidad no son aditivos porque una misma persona puede "
            "estar informada por múltiples entidades. Los conteos únicos exactos del universo EEFF+PNFC "
            "se calcularán en una única corrida integral posterior sobre PADRON+DEUDORES."
        ),
        "residuales_top60_por_personas_mora_entidad": residuales[:60],
        "entidades_clasificadas": detalle,
        "privacidad": {
            "microdatos_personales_leidos": False,
            "identificadores_personales_en_salida": False,
            "solo_agregados_institucionales": True,
        },
    }
    OUTPUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "registros_oficiales": {k: len(v) for k, v in registros.items()},
        "solapamiento_emisoras_opnfc": len(solap_pnfc),
        "categorias_cendeu": {k: v["entidades"] for k, v in por_cat.items()},
        "escenario_aditivo": salida["escenario_aditivo"],
        "residuales": len(residuales),
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
