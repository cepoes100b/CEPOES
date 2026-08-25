#!/usr/bin/env python3
"""Diagnóstico reproducible de radios censales 2022 con población."""
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
    layer = gpd.list_layers(OUT).iloc[0]["name"]
    gdf = gpd.read_file(OUT, layer=layer)
    print("CAPA", layer, "CRS", gdf.crs, "FILAS", len(gdf))
    print("COLUMNAS", list(gdf.columns))
    mask = gdf["NOMPROV"].astype(str).str.contains("Ciudad Autónoma de Buenos Aires", case=False, na=False)
    if not mask.any():
        mask = gdf["NOMPROV"].astype(str).str.contains("Buenos Aires", case=False, na=False) & gdf["NOMDEPTO"].astype(str).str.contains("Comuna", case=False, na=False)
    caba = gdf.loc[mask].copy()
    print("CABA_RADIOS", len(caba))
    print("CABA_POB_CA3", int(caba["CA3"].sum()))
    por = caba.groupby("NOMDEPTO", dropna=False).agg(radios=("CRO","count"), poblacion=("CA3","sum"), area_ha=("areaHa","sum")).reset_index()
    print("CABA_DEPARTAMENTOS", json.dumps(por.to_dict(orient="records"), ensure_ascii=False))
    print("CABA_BOUNDS", list(map(float, caba.total_bounds)))
    report = {
        "size": OUT.stat().st_size,
        "layer": layer,
        "crs": str(gdf.crs),
        "columns": list(gdf.columns),
        "caba_radios": len(caba),
        "caba_poblacion_ca3": int(caba["CA3"].sum()),
        "departamentos": por.to_dict(orient="records"),
        "bounds": list(map(float, caba.total_bounds)),
    }
    Path("diagnostico_radios_2022.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
