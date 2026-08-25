#!/usr/bin/env python3
"""Diagnóstico reproducible de la base de radios censales 2022 con población.

No publica datos. Descarga el dataset abierto de CONICET Digital, inspecciona su
esquema y deja en logs la información necesaria para construir el indicador de
accesibilidad deportiva sin asumir nombres de campos.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import requests

URL = "https://datosdeinvestigacion.conicet.gov.ar/bitstream/handle/11336/284095/radios_2022_conDatos_1habHa.gpkg?isAllowed=y&sequence=2"
OUT = Path("_tmp_radios_2022.gpkg")


def download() -> None:
    with requests.get(URL, stream=True, timeout=180, headers={"User-Agent": "CEPOES-data/1.0"}) as r:
        r.raise_for_status()
        with OUT.open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
    if OUT.stat().st_size < 10_000_000:
        raise SystemExit(f"Descarga inesperadamente pequeña: {OUT.stat().st_size} bytes")


def main() -> int:
    download()
    layers = gpd.list_layers(OUT)
    print("CAPAS", layers.to_dict(orient="records"))
    report = {"size": OUT.stat().st_size, "layers": []}
    for layer in layers["name"].tolist():
        sample = gpd.read_file(OUT, layer=layer, rows=8)
        print(f"\nLAYER {layer}")
        print("CRS", sample.crs)
        print("COLUMNS", list(sample.columns))
        print("DTYPES", {c: str(t) for c, t in sample.dtypes.items()})
        printable = sample.drop(columns="geometry", errors="ignore").head(8).fillna("").astype(str)
        print("SAMPLE", json.dumps(printable.to_dict(orient="records"), ensure_ascii=False))
        report["layers"].append({
            "name": layer,
            "crs": str(sample.crs),
            "columns": list(sample.columns),
            "dtypes": {c: str(t) for c, t in sample.dtypes.items()},
        })
    Path("diagnostico_radios_2022.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
