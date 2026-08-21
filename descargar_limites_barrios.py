"""Descarga el GeoJSON oficial de barrios de BA Data para territorialización espacial.

Se usa únicamente como capa de referencia: permite asignar comuna y barrio a
registros oficiales que publican coordenadas pero no campos territoriales (por
ejemplo estaciones Ecobici), y filtrar recursos regionales para conservar sólo
los puntos efectivamente ubicados dentro de CABA.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests

from fuentes_territorio import BA_DATA_API

BASE = Path(__file__).resolve().parent
OUT = BASE / "badata" / "barrios.geojson"
OUT.parent.mkdir(exist_ok=True)


def main() -> int:
    r = requests.get(BA_DATA_API, params={"id": "barrios"}, timeout=(10, 90), headers={"User-Agent": "CEPOES-data-pipeline/1.0 (+https://cepoes.org)"})
    r.raise_for_status()
    payload = r.json()
    if not payload.get("success") or not payload.get("result"):
        raise RuntimeError("BA Data no devolvió el dataset barrios")
    resources = payload["result"].get("resources") or []
    rx = re.compile(r"^Barrios \(GeoJSON\)$", re.I)
    matches = [x for x in resources if rx.search(x.get("name") or "")]
    if not matches:
        raise RuntimeError("No se encontró el recurso Barrios (GeoJSON)")
    matches.sort(key=lambda x: x.get("last_modified") or x.get("created") or "", reverse=True)
    url = matches[0].get("url")
    if not url:
        raise RuntimeError("Recurso Barrios (GeoJSON) sin URL")
    g = requests.get(url, timeout=(10, 90), headers={"User-Agent": "CEPOES-data-pipeline/1.0 (+https://cepoes.org)"})
    g.raise_for_status()
    obj = g.json()
    features = obj.get("features") or []
    if obj.get("type") != "FeatureCollection" or len(features) != 48:
        raise RuntimeError(f"GeoJSON de barrios inesperado: {len(features)} features")
    comunas = {int((f.get("properties") or {}).get("comuna")) for f in features if (f.get("properties") or {}).get("comuna") is not None}
    if comunas != set(range(1, 16)):
        raise RuntimeError(f"GeoJSON no cubre las 15 comunas: {sorted(comunas)}")
    tmp = OUT.with_suffix(".geojson.nuevo")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(OUT)
    print(f"✔ barrios.geojson · {len(features)} barrios · {OUT.stat().st_size//1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
