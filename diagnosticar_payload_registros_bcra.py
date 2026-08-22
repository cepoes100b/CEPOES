#!/usr/bin/env python3
"""Inspecciona la estructura de los endpoints públicos que alimentan registros BCRA.

No accede a PADRON/CENDEU ni a datos de personas. Las respuestas corresponden a
registros públicos de instituciones. La salida guarda únicamente metadatos de forma
y hasta dos registros institucionales de muestra por endpoint para definir un parser
por campo, evitando inferencias por regex sobre CUIT/domicilios.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

ENDPOINTS = {
    "entidad_financiera": "https://www.bcra.gob.ar/api/endpoints/nomina-entidades.php?action=nomina_AAA00&lang=es",
    "enf_emisora_tarjeta": "https://www.bcra.gob.ar/api/endpoints/emisoras-tarjetas-credito.php",
    "otro_pnfc": "https://www.bcra.gob.ar/api/endpoints/proveedores-no-financieros.php?lang=es",
}

OUT = Path("diagnostico_payload_registros_bcra.json")


def describir(obj, profundidad=0):
    if profundidad > 4:
        return {"tipo": type(obj).__name__, "nota": "profundidad_limitada"}
    if isinstance(obj, dict):
        return {
            "tipo": "dict",
            "cantidad_claves": len(obj),
            "claves": list(obj.keys())[:50],
            "hijos": {str(k): describir(v, profundidad + 1) for k, v in list(obj.items())[:10]},
        }
    if isinstance(obj, list):
        return {
            "tipo": "list",
            "cantidad": len(obj),
            "primer_elemento": describir(obj[0], profundidad + 1) if obj else None,
        }
    return {"tipo": type(obj).__name__, "valor_muestra": obj}


def encontrar_listas_de_dicts(obj, ruta="$", out=None):
    if out is None:
        out = []
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj[: min(len(obj), 20)]):
            out.append({
                "ruta": ruta,
                "cantidad": len(obj),
                "claves_primer_registro": list(obj[0].keys()) if obj else [],
                "muestras": obj[:2],
            })
        for i, v in enumerate(obj[:5]):
            encontrar_listas_de_dicts(v, f"{ruta}[{i}]", out)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            encontrar_listas_de_dicts(v, f"{ruta}.{k}", out)
    return out


def main() -> int:
    salida = {
        "schema": "cepoes-bcra-registry-payload-shape-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "endpoints": {},
        "privacidad": {"microdatos_personales_leidos": False, "solo_registros_institucionales_publicos": True},
    }
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CEPOES-validacion-metodologica/1.0)", "Accept": "application/json,text/plain,*/*"}
    for nombre, url in ENDPOINTS.items():
        r = requests.get(url, headers=headers, timeout=60)
        print(nombre, r.status_code, r.headers.get("content-type"), len(r.content), flush=True)
        r.raise_for_status()
        try:
            obj = r.json()
        except Exception as exc:
            raise RuntimeError(f"{nombre}: respuesta no JSON: {exc}; inicio={r.text[:200]!r}")
        listas = encontrar_listas_de_dicts(obj)
        salida["endpoints"][nombre] = {
            "url": url,
            "status": r.status_code,
            "content_type": r.headers.get("content-type", ""),
            "bytes": len(r.content),
            "estructura": describir(obj),
            "listas_de_registros": listas,
        }
        print("  listas:", [(x["ruta"], x["cantidad"], x["claves_primer_registro"]) for x in listas], flush=True)
    OUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
