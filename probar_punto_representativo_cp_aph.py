#!/usr/bin/env python3
"""Prueba de punto representativo por CP usando coordenadas públicas APH.

Reutiliza el motor espacial/estadístico de la prueba de Mobiliario, pero sustituye
la fuente de puntos por el recurso APH que ya fue validado en una corrida anterior.
No lee microdatos BCRA/ARCA: consume sólo el agregado por CP de la corrida integral.
"""
from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

import requests

import probar_punto_representativo_cp_mobiliario as base

APH_PAGE = "https://data.buenosaires.gob.ar/dataset/areas-proteccion-historica/resource/juqdkmgo-94-resource"
APH_URL = APH_PAGE + "/download"
OUT = Path("diagnostico_punto_representativo_cp_aph.json")


def cargar_aph_puntos():
    r = requests.get(APH_URL, headers=base.UA, timeout=180, allow_redirects=True)
    r.raise_for_status()
    raw = r.content
    if len(raw) < 1000:
        raise RuntimeError(f"APH demasiado pequeño: {len(raw)} bytes")

    text = None; encoding = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            text = raw.decode(enc); encoding = enc; break
        except UnicodeDecodeError:
            pass
    if text is None:
        raise RuntimeError("No se pudo decodificar APH")

    first = next((x for x in text.splitlines() if x.strip()), "")
    delim = max((";", ",", "\t", "|"), key=lambda d: first.count(d))
    rd = csv.DictReader(io.StringIO(text), delimiter=delim)
    fields = {base.norm(x).replace(" ", "_").lower(): x for x in (rd.fieldnames or []) if x}

    def col(*names):
        for n in names:
            if n in fields:
                return fields[n]
        return None

    ccp = col("codigo_postal", "cod_postal", "cp")
    cb = col("barrio")
    clat = col("latitud", "lat")
    clon = col("longitud", "lon", "long")
    ccpa = col("codigo_postal_argentino", "cpa")
    if not ccp or not clat or not clon:
        raise RuntimeError(f"APH sin CP/lat/lon. Campos={sorted(fields)}")

    puntos = defaultdict(list)
    barrios_fuente = defaultdict(Counter)
    filas = validas = fuera_bbox = 0
    xmin, xmax, ymin, ymax = -58.56, -58.32, -34.72, -34.51

    for row in rd:
        filas += 1
        cp = base.cp4(row.get(ccp))
        lon = base.num(row.get(clon)); lat = base.num(row.get(clat))
        if cp is None or lon is None or lat is None:
            continue
        if not (xmin <= lon <= xmax and ymin <= lat <= ymax):
            fuera_bbox += 1
            continue
        puntos[cp].append((lon, lat))
        if cb and row.get(cb):
            barrios_fuente[cp][base.norm(row.get(cb))] += 1
        validas += 1

    meta = {
        "pagina": APH_PAGE,
        "url_descarga": APH_URL,
        "url_final": r.url,
        "bytes": len(raw),
        "encoding": encoding,
        "delimitador": delim,
        "campos": rd.fieldnames,
        "columnas": {"cp": ccp, "barrio": cb, "lat": clat, "lon": clon, "cpa": ccpa},
        "filas_leidas": filas,
        "filas_cp_coord_validas": validas,
        "filas_coord_fuera_bbox_caba": fuera_bbox,
        "cp_distintos": len(puntos),
    }
    if validas < 100000 or len(puntos) < 100:
        raise RuntimeError(f"Cobertura APH inesperadamente baja: {meta}")
    return puntos, barrios_fuente, meta


base.cargar_mobiliario = cargar_aph_puntos
base.OUTPUT = OUT

if __name__ == "__main__":
    base.main()
    obj = json.loads(OUT.read_text(encoding="utf-8"))
    obj["schema"] = "cepoes-punto-representativo-cp-aph-v1"
    obj["fuente_aph"] = obj.pop("fuente_mobiliario")
    obj["controles"]["cp_aph"] = obj["controles"].pop("cp_mobiliario")
    obj["controles"]["cp_aph_multibarrio"] = obj["controles"].pop("cp_mobiliario_multibarrio")
    obj["advertencia"] = (
        "APH es un inventario especializado y no un padrón representativo de domicilios. "
        "Este ensayo prueba únicamente si una regla CP -> punto representativo -> barrio "
        "es compatible con el patrón territorial de Mapa de la Deuda."
    )
    OUT.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"fuente_aph": obj["fuente_aph"], "controles": obj["controles"], "resultados": obj["resultados"]}, ensure_ascii=False, indent=2))
