#!/usr/bin/env python3
"""Corrección fail-closed del experimento GeoNames v1.

El ZIP AR.zip incluye `AR.txt` y `readme.txt`; la primera versión elegía el primer
.txt y podía leer el README. Este wrapper reemplaza exclusivamente el cargador de
GeoNames, exige `AR.txt` y valida cobertura real antes de aceptar el resultado.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict

import probar_geolocalizacion_cp_mapadeladeuda as base


def cargar_geonames_corregido(caba_bbox):
    data = base.get(base.GEONAMES_URL).content
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        exactos = [n for n in names if n.lower().endswith("/ar.txt") or n.lower() == "ar.txt"]
        if len(exactos) != 1:
            raise RuntimeError(f"GeoNames AR.zip: se esperaba un único AR.txt; encontrados={exactos}; archivos={names}")
        archivo = exactos[0]
        text = z.read(archivo).decode("utf-8", errors="replace")

    west, south, east, north = caba_bbox
    por_cp = defaultdict(list)
    leidas = rango = bbox = 0
    admin1 = defaultdict(int)
    for row in csv.reader(io.StringIO(text), delimiter="\t"):
        if len(row) < 12:
            continue
        leidas += 1
        cp_s = row[1].strip()
        if len(cp_s) != 4 or not cp_s.isdigit():
            continue
        cp = int(cp_s)
        if not 1000 <= cp <= 1499:
            continue
        rango += 1
        try:
            lat = float(row[9]); lon = float(row[10])
        except ValueError:
            continue
        admin1[row[3]] += 1
        if not (west <= lon <= east and south <= lat <= north):
            continue
        bbox += 1
        try:
            accuracy = int(row[11]) if row[11].strip() else 0
        except ValueError:
            accuracy = 0
        por_cp[cp].append({
            "place": row[2], "admin1": row[3], "lat": lat, "lon": lon, "accuracy": accuracy,
        })

    meta = {
        "url": base.GEONAMES_URL,
        "archivo_zip_leido": archivo,
        "bytes_zip": len(data),
        "filas_leidas": leidas,
        "filas_cp_1000_1499": rango,
        "filas_dentro_bbox_caba": bbox,
        "cp_con_observaciones_caba": len(por_cp),
        "admin1_top_cp_rango": sorted(admin1.items(), key=lambda kv: (-kv[1], kv[0]))[:10],
    }
    if leidas < 10_000 or rango < 100 or len(por_cp) < 50:
        raise RuntimeError(f"GeoNames AR.txt produjo cobertura inesperadamente baja: {meta}")
    return dict(por_cp), meta


base.cargar_geonames = cargar_geonames_corregido
rc = base.main()

# Fail closed: una ejecución técnicamente exitosa pero sin cobertura territorial no
# debe volver a quedar verde.
out = json.load(open(base.OUTPUT, encoding="utf-8"))
max_cp = max(r["cp_asignados"] for r in out["resultados"].values())
max_cov = max(r["cobertura_deudores_pct"] for r in out["resultados"].values())
max_barrios = max(r["barrios_con_datos"] for r in out["resultados"].values())
if max_cp < 50 or max_cov < 50 or max_barrios < 20:
    raise SystemExit(f"Cobertura territorial insuficiente: CP={max_cp}, deudores={max_cov}%, barrios={max_barrios}")
raise SystemExit(rc)
