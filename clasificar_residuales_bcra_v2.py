#!/usr/bin/env python3
"""Wrapper para payloads JSON anidados del registro de fideicomisos BCRA."""
from __future__ import annotations

import requests

import clasificar_residuales_bcra as base


def encontrar_listas_codigo(obj, ruta="$", out=None):
    if out is None:
        out = []
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict) and "codigo" in obj[0]:
            out.append((ruta, obj))
        for i, v in enumerate(obj[:10]):
            encontrar_listas_codigo(v, f"{ruta}[{i}]", out)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            encontrar_listas_codigo(v, f"{ruta}.{k}", out)
    return out


def lista_codigo_json_recursiva(url: str, minimo: int):
    r = requests.get(url, headers=base.HEADERS, timeout=60)
    r.raise_for_status()
    obj = r.json()
    candidatos = encontrar_listas_codigo(obj)
    if not candidatos:
        raise RuntimeError(f"No se encontró una colección con campo codigo: {url}")
    ruta, filas = max(candidatos, key=lambda x: len(x[1]))
    codigos = {
        base.codigo5(f["codigo"])
        for f in filas
        if isinstance(f, dict) and "codigo" in f and str(f["codigo"]).strip().isdigit()
    }
    if len(codigos) < minimo:
        raise RuntimeError(f"Registro JSON corto: {len(codigos)} < {minimo}: {url}")
    return codigos, {
        "url": url,
        "metodo": "endpoint_json_busqueda_recursiva_campo_codigo",
        "ruta_lista": ruta,
        "filas": len(filas),
        "codigos_unicos": len(codigos),
    }


base.lista_codigo_json = lista_codigo_json_recursiva

if __name__ == "__main__":
    raise SystemExit(base.main())
