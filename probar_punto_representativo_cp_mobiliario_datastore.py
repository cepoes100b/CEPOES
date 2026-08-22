#!/usr/bin/env python3
"""Adaptador DataStore para la prueba de punto representativo por CP.

BA Data muestra en la vista previa de Mobiliario Urbano un esquema actualizado con
long/lat/barrio/codigo_postal, mientras los archivos descargables hoy devuelven un
esquema legado. Este adaptador busca el recurso DataStore público que alimenta la
vista previa, valida explícitamente esos campos y luego reutiliza sin cambios la
prueba espacial/estadística de `probar_punto_representativo_cp_mobiliario.py`.
"""
from __future__ import annotations

from collections import Counter, defaultdict

import requests

import probar_punto_representativo_cp_mobiliario as base

APIS = [
    "https://data.buenosaires.gob.ar/api/3/action/datastore_search",
    "https://data.buenosaires.gob.ar/api/action/datastore_search",
]
RESOURCES = ["juqdkmgo-1441-resource-xlsx", "juqdkmgo-1441-resource"]


def _request(api, resource, limit, offset=0):
    r = requests.get(
        api,
        params={"resource_id": resource, "limit": limit, "offset": offset},
        headers=base.UA,
        timeout=90,
    )
    r.raise_for_status()
    obj = r.json()
    if not obj.get("success") or not isinstance(obj.get("result"), dict):
        raise RuntimeError(f"Respuesta CKAN no exitosa: {str(obj)[:500]}")
    return r, obj["result"]


def _elegir_fuente():
    intentos = []
    for api in APIS:
        for resource in RESOURCES:
            try:
                r, result = _request(api, resource, 5)
                records = result.get("records") or []
                fields = {base.norm(x.get("id")).replace(" ", "_").lower() for x in (result.get("fields") or []) if isinstance(x, dict)}
                if records:
                    fields |= {base.norm(k).replace(" ", "_").lower() for k in records[0]}
                ok = {"long", "lat", "codigo_postal"}.issubset(fields)
                intentos.append({"api": api, "resource_id": resource, "status": r.status_code, "fields": sorted(fields), "compatible": ok})
                if ok:
                    return api, resource, result, intentos
            except Exception as exc:
                intentos.append({"api": api, "resource_id": resource, "error": f"{type(exc).__name__}: {exc}"})
    raise RuntimeError(f"No se encontró DataStore compatible para Mobiliario: {intentos}")


def cargar_mobiliario_datastore():
    api, resource, first, intentos = _elegir_fuente()
    total = int(first.get("total") or 0)
    limit = 50000
    offset = 0
    puntos = defaultdict(list)
    barrios_fuente = defaultdict(Counter)
    filas = validas = fuera_bbox = 0
    xmin, xmax, ymin, ymax = -58.56, -58.32, -34.72, -34.51
    field_names = None

    while True:
        _, result = _request(api, resource, limit, offset)
        records = result.get("records") or []
        if field_names is None:
            field_names = [x.get("id") for x in (result.get("fields") or []) if isinstance(x, dict)]
        for row in records:
            filas += 1
            normalized = {base.norm(k).replace(" ", "_").lower(): v for k, v in row.items()}
            cp = base.cp4(normalized.get("codigo_postal"))
            lon = base.num(normalized.get("long")); lat = base.num(normalized.get("lat"))
            if cp is None or lon is None or lat is None:
                continue
            if not (xmin <= lon <= xmax and ymin <= lat <= ymax):
                fuera_bbox += 1
                continue
            puntos[cp].append((lon, lat))
            if normalized.get("barrio"):
                barrios_fuente[cp][base.norm(normalized["barrio"])] += 1
            validas += 1
        offset += len(records)
        if not records or (total and offset >= total) or len(records) < limit:
            break
        if offset > 500000:
            raise RuntimeError("DataStore excede 500.000 filas; se aborta por seguridad")

    meta = {
        "pagina": base.MOB_PAGE,
        "metodo": "CKAN DataStore público que alimenta la vista previa",
        "api": api,
        "resource_id": resource,
        "total_declarado": total,
        "campos": field_names,
        "filas_leidas": filas,
        "filas_cp_coord_validas": validas,
        "filas_coord_fuera_bbox_caba": fuera_bbox,
        "cp_distintos": len(puntos),
        "intentos_descubrimiento": intentos,
    }
    if validas < 100 or len(puntos) < 20:
        raise RuntimeError(f"Cobertura DataStore insuficiente: {meta}")
    return puntos, barrios_fuente, meta


base.cargar_mobiliario = cargar_mobiliario_datastore

if __name__ == "__main__":
    base.main()
