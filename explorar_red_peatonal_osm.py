#!/usr/bin/env python3
"""Prueba aislada de una red peatonal reproducible para CABA.

No publica resultados. Usa el límite comunal ya versionado por CEPOES, agrega un
margen de 1.200 m y obtiene la red caminable de OpenStreetMap con OSMnx. Guarda
el grafo y respuestas HTTP bajo `_cache/` para que futuras corridas no vuelvan a
consultar Overpass si el cache de GitHub Actions está disponible.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import osmnx as ox

BASE = Path(__file__).resolve().parent
GEO = BASE / "deploy" / "site-overlay" / "assets" / "data" / "estructura-productiva" / "comunas.geojson"
CACHE = BASE / "_cache" / "osmnx"
GRAPH = BASE / "_cache" / "caba-walk.graphml"
OUT = BASE / "diagnostico_red_peatonal.json"


def boundary_with_margin() -> object:
    gdf = gpd.read_file(GEO)
    if len(gdf) != 15:
        raise SystemExit(f"GeoJSON comunal inesperado: {len(gdf)} features")
    metric_crs = gdf.estimate_utm_crs()
    if metric_crs is None:
        raise SystemExit("No se pudo estimar CRS métrico")
    metric = gdf.to_crs(metric_crs)
    merged = metric.geometry.union_all().buffer(1200)
    return gpd.GeoSeries([merged], crs=metric_crs).to_crs("EPSG:4326").iloc[0]


def configure() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    GRAPH.parent.mkdir(parents=True, exist_ok=True)
    ox.settings.use_cache = True
    ox.settings.cache_folder = CACHE
    ox.settings.requests_timeout = 300
    ox.settings.overpass_rate_limit = True
    ox.settings.http_user_agent = "CEPOES-data/1.0 (https://cepoes.org)"
    ox.settings.http_referer = "https://cepoes.org/"


def load_or_build():
    if GRAPH.exists() and GRAPH.stat().st_size > 1_000_000:
        print(f"Red peatonal: usando GraphML cacheado · {GRAPH.stat().st_size // 1024 // 1024} MB")
        return ox.load_graphml(GRAPH)
    polygon = boundary_with_margin()
    print("Red peatonal: descargando OSM walk para CABA + margen 1.200 m")
    graph = ox.graph.graph_from_polygon(
        polygon,
        network_type="walk",
        simplify=True,
        retain_all=False,
        truncate_by_edge=True,
    )
    ox.save_graphml(graph, GRAPH)
    print(f"GraphML guardado · {GRAPH.stat().st_size // 1024 // 1024} MB")
    return graph


def main() -> int:
    configure()
    graph = load_or_build()
    nodes = len(graph.nodes)
    edges = len(graph.edges)
    total_length = sum(float(data.get("length") or 0) for _, _, data in graph.edges(data=True))
    report = {
        "osmnx_version": ox.__version__,
        "network_type": "walk",
        "bidireccional": "walk" in ox.settings.bidirectional_network_types,
        "margen_m": 1200,
        "nodos": nodes,
        "aristas_dirigidas": edges,
        "longitud_aristas_km": round(total_length / 1000, 1),
        "graphml_bytes": GRAPH.stat().st_size if GRAPH.exists() else None,
        "http_cache_archivos": len(list(CACHE.rglob("*.json"))),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if nodes < 20_000 or edges < 40_000:
        raise SystemExit(f"Red peatonal demasiado pequeña: {nodes} nodos / {edges} aristas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
