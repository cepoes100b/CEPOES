#!/usr/bin/env python3
"""Construye y mantiene una red peatonal reproducible para CABA.

Usa el límite comunal versionado por CEPOES, agrega un margen de 1.200 m y
obtiene la red caminable de OpenStreetMap con OSMnx. El GraphML queda solamente
en `_cache/`: no se publica ni se versiona. La red se refresca como máximo cada
28 días. Si un refresco falla y existe una copia válida, conserva la anterior.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import osmnx as ox

BASE = Path(__file__).resolve().parent
GEO = BASE / "deploy" / "site-overlay" / "assets" / "data" / "estructura-productiva" / "comunas.geojson"
CACHE = BASE / "_cache" / "osmnx"
GRAPH = BASE / "_cache" / "caba-walk.graphml"
META = BASE / "_cache" / "caba-walk.meta.json"
OUT = BASE / "diagnostico_red_peatonal.json"
MAX_AGE_DAYS = int(os.environ.get("OSM_GRAPH_MAX_AGE_DAYS", "28"))


def now() -> datetime:
    return datetime.now(timezone.utc)


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


def configure(use_http_cache: bool = True) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    GRAPH.parent.mkdir(parents=True, exist_ok=True)
    ox.settings.use_cache = use_http_cache
    ox.settings.cache_folder = CACHE
    ox.settings.requests_timeout = 300
    ox.settings.overpass_rate_limit = True
    ox.settings.http_user_agent = "CEPOES-data/1.0 (https://cepoes.org)"
    ox.settings.http_referer = "https://cepoes.org/"


def read_meta() -> dict:
    if not META.exists():
        return {}
    try:
        return json.loads(META.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_meta(source: str) -> dict:
    meta = {
        "generado": now().isoformat(timespec="seconds"),
        "fuente": "OpenStreetMap",
        "network_type": "walk",
        "margen_m": 1200,
        "source_mode": source,
        "osmnx_version": ox.__version__,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def graph_age_days(meta: dict) -> float | None:
    raw = meta.get("generado")
    if not raw:
        return None
    try:
        stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return max(0.0, (now() - stamp).total_seconds() / 86400)
    except Exception:
        return None


def graph_valid() -> bool:
    return GRAPH.exists() and GRAPH.stat().st_size > 1_000_000


def build_fresh():
    polygon = boundary_with_margin()
    print("Red peatonal: consultando OSM walk para CABA + margen 1.200 m")
    # En un refresco no se reutiliza la respuesta HTTP anterior: el GraphML sí se
    # conserva como fallback, pero la consulta debe poder incorporar cambios de OSM.
    configure(use_http_cache=False)
    graph = ox.graph.graph_from_polygon(
        polygon,
        network_type="walk",
        simplify=True,
        retain_all=False,
        truncate_by_edge=True,
    )
    if len(graph.nodes) < 20_000 or len(graph.edges) < 40_000:
        raise RuntimeError(f"Red OSM demasiado pequeña: {len(graph.nodes)} nodos / {len(graph.edges)} aristas")
    tmp = GRAPH.with_suffix(".tmp.graphml")
    ox.save_graphml(graph, tmp)
    if tmp.stat().st_size < 1_000_000:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("GraphML OSM nuevo demasiado pequeño")
    tmp.replace(GRAPH)
    write_meta("overpass_fresco")
    configure(use_http_cache=True)
    print(f"GraphML actualizado · {GRAPH.stat().st_size // 1024 // 1024} MB")
    return graph, True, True


def load_or_build():
    configure(use_http_cache=True)
    meta = read_meta()
    age = graph_age_days(meta)

    # Migración de la primera caché V3, creada antes de incorporar metadata.
    if graph_valid() and age is None:
        meta = write_meta("cache_migrada_sin_fecha_previa")
        age = graph_age_days(meta)

    needs_refresh = (not graph_valid()) or age is None or age >= MAX_AGE_DAYS
    if not needs_refresh:
        print(f"Red peatonal: usando GraphML cacheado · edad {age:.1f} días · {GRAPH.stat().st_size // 1024 // 1024} MB")
        return ox.load_graphml(GRAPH), False, False

    try:
        return build_fresh()
    except Exception as exc:
        configure(use_http_cache=True)
        if graph_valid():
            print(f"AVISO: no se pudo refrescar OSM ({type(exc).__name__}: {exc}); se conserva el último GraphML válido")
            return ox.load_graphml(GRAPH), True, False
        raise


def main() -> int:
    graph, refresh_attempted, refresh_success = load_or_build()
    nodes = len(graph.nodes)
    edges = len(graph.edges)
    total_length = sum(float(data.get("length") or 0) for _, _, data in graph.edges(data=True))
    meta = read_meta()
    age = graph_age_days(meta)
    report = {
        "osmnx_version": ox.__version__,
        "network_type": "walk",
        "bidireccional": "walk" in ox.settings.bidirectional_network_types,
        "margen_m": 1200,
        "nodos": nodes,
        "aristas_dirigidas": edges,
        "longitud_aristas_km": round(total_length / 1000, 1),
        "graphml_bytes": GRAPH.stat().st_size if GRAPH.exists() else None,
        "grafo_generado": meta.get("generado"),
        "grafo_edad_dias": round(age, 2) if age is not None else None,
        "refresco_intentado": refresh_attempted,
        "refresco_exitoso": refresh_success,
        "max_edad_dias": MAX_AGE_DAYS,
        "http_cache_archivos": len(list(CACHE.rglob("*.json"))),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if nodes < 20_000 or edges < 40_000:
        raise SystemExit(f"Red peatonal demasiado pequeña: {nodes} nodos / {edges} aristas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
