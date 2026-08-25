#!/usr/bin/env python3
"""Diagnóstico V3: accesibilidad a oferta deportiva mediante red peatonal OSM.

Este script NO publica resultados. Compara la proximidad euclidiana de la V2 con
una estimación de distancia caminable por red para los mismos radios censales y
universos de oferta.

Supuestos principales:
- población uniforme dentro de cada radio, igual que en V2;
- cada radio se aproxima con una malla 4x4: cada intersección no vacía aporta un
  punto representativo y una fracción de población proporcional a su superficie;
- distancia caminable estimada = acceso desde la muestra al nodo OSM más cercano
  + camino mínimo por la red `walk` + acceso del nodo OSM al equipamiento;
- los umbrales 800/1.000 m representan metros recorridos estimados, no tiempo real.
"""
from __future__ import annotations

import heapq
import json
import math
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import numpy as np
import osmnx as ox
from scipy.spatial import cKDTree
from shapely.geometry import Point, box

from generar_accesibilidad_deportiva import comuna_id, load_json, read_caba, sport_points

BASE = Path(__file__).resolve().parent
GRAPH = BASE / "_cache" / "caba-walk.graphml"
SPORT = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-salud.json"
EUCLIDEAN = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-accesibilidad.json"
OUT = BASE / "diagnostico_accesibilidad_peatonal.json"
DISTANCES = (800, 1000)
GRID_N = 4


def percentile(values: np.ndarray, q: float) -> float | None:
    if values.size == 0:
        return None
    return round(float(np.percentile(values, q)), 1)


def stats(values: Iterable[float]) -> dict:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"n": 0}
    return {
        "n": int(arr.size),
        "p50_m": percentile(arr, 50),
        "p95_m": percentile(arr, 95),
        "p99_m": percentile(arr, 99),
        "max_m": round(float(arr.max()), 1),
    }


def sample_radios(radios_m: gpd.GeoDataFrame) -> tuple[list[dict], dict]:
    samples: list[dict] = []
    invalid = 0
    for _, row in radios_m.iterrows():
        geom = row.geometry
        pop = float(row["CA3"] or 0)
        cid = comuna_id(row["NOMDEPTO"])
        if cid is None or geom is None or geom.is_empty or geom.area <= 0:
            invalid += 1
            continue
        minx, miny, maxx, maxy = geom.bounds
        dx = (maxx - minx) / GRID_N
        dy = (maxy - miny) / GRID_N
        if dx <= 0 or dy <= 0:
            invalid += 1
            continue
        radio_area = float(geom.area)
        radio_weight = 0.0
        local: list[tuple[Point, float]] = []
        for ix in range(GRID_N):
            for iy in range(GRID_N):
                cell = box(minx + ix * dx, miny + iy * dy, minx + (ix + 1) * dx, miny + (iy + 1) * dy)
                inter = geom.intersection(cell)
                if inter.is_empty or inter.area <= 0:
                    continue
                frac = float(inter.area) / radio_area
                local.append((inter.representative_point(), frac))
                radio_weight += frac
        # Renormalizar solo por error numérico; la malla cubre todo el bbox.
        if not local or radio_weight <= 0:
            invalid += 1
            continue
        for point, frac in local:
            samples.append({
                "comuna": cid,
                "x": float(point.x),
                "y": float(point.y),
                "poblacion": pop * frac / radio_weight,
            })
    pop_samples = sum(s["poblacion"] for s in samples)
    pop_radios = float(radios_m["CA3"].sum())
    return samples, {
        "grid": f"{GRID_N}x{GRID_N}",
        "muestras": len(samples),
        "radios_descartados": invalid,
        "poblacion_radios": int(round(pop_radios)),
        "poblacion_reconstruida": int(round(pop_samples)),
        "diferencia_pct": round(abs(pop_samples - pop_radios) / pop_radios * 100, 6) if pop_radios else None,
    }


def node_index(graph) -> tuple[list, np.ndarray, cKDTree]:
    nodes = ox.graph_to_gdfs(graph, edges=False)
    ids = list(nodes.index)
    xy = np.column_stack((nodes["x"].astype(float).to_numpy(), nodes["y"].astype(float).to_numpy()))
    return ids, xy, cKDTree(xy)


def nearest_nodes(tree: cKDTree, ids: list, xs: np.ndarray, ys: np.ndarray) -> tuple[np.ndarray, list]:
    dist, idx = tree.query(np.column_stack((xs, ys)), k=1)
    return np.asarray(dist, dtype=float), [ids[int(i)] for i in np.asarray(idx)]


def min_edge_length(keydict: dict) -> float | None:
    best: float | None = None
    for data in keydict.values():
        try:
            length = float(data.get("length", math.inf))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(length) or length < 0:
            continue
        if best is None or length < best:
            best = length
    return best


def seeded_distances(graph, seeds: dict, cutoff: float) -> dict:
    """Dijkstra multi-fuente con costo inicial por snap del equipamiento."""
    dist = {node: float(value) for node, value in seeds.items() if value <= cutoff}
    heap = [(value, node) for node, value in dist.items()]
    heapq.heapify(heap)
    while heap:
        current, node = heapq.heappop(heap)
        if current != dist.get(node):
            continue
        if current > cutoff:
            continue
        for nbr, keydict in graph[node].items():
            edge = min_edge_length(keydict)
            if edge is None:
                continue
            new = current + edge
            if new > cutoff:
                continue
            if new < dist.get(nbr, math.inf):
                dist[nbr] = new
                heapq.heappush(heap, (new, nbr))
    return dist


def facility_seeds(points_wgs84: list[Point], graph_crs, tree: cKDTree, ids: list) -> tuple[dict, dict]:
    if not points_wgs84:
        raise SystemExit("Universo deportivo sin puntos georreferenciados")
    gs = gpd.GeoSeries(points_wgs84, crs="EPSG:4326").to_crs(graph_crs)
    xs = gs.x.to_numpy(dtype=float)
    ys = gs.y.to_numpy(dtype=float)
    snap, nodes = nearest_nodes(tree, ids, xs, ys)
    seeds: dict = {}
    for node, d in zip(nodes, snap):
        val = float(d)
        if val < seeds.get(node, math.inf):
            seeds[node] = val
    return seeds, {
        "puntos_georreferenciados": len(points_wgs84),
        "nodos_destino_unicos": len(seeds),
        "snap_equipamiento": stats(snap),
    }


def aggregate(samples: list[dict], total_distance: np.ndarray, threshold: int) -> tuple[dict, dict]:
    pop = np.asarray([s["poblacion"] for s in samples], dtype=float)
    covered = np.isfinite(total_distance) & (total_distance <= threshold)
    total_pop = float(pop.sum())
    cov_pop = float(pop[covered].sum())
    city = {
        "poblacion_base": int(round(total_pop)),
        "poblacion_cubierta_estimada": int(round(cov_pop)),
        "poblacion_fuera_cobertura_estimada": int(round(total_pop - cov_pop)),
        "cobertura_pct": round(cov_pop / total_pop * 100, 2) if total_pop else None,
    }
    comunas: dict = {}
    sample_comunas = np.asarray([s["comuna"] for s in samples], dtype=object)
    for cid in map(str, range(1, 16)):
        mask = sample_comunas == cid
        base = float(pop[mask].sum())
        cov = float(pop[mask & covered].sum())
        comunas[cid] = {
            "poblacion_base": int(round(base)),
            "poblacion_cubierta_estimada": int(round(cov)),
            "poblacion_fuera_cobertura_estimada": int(round(base - cov)),
            "cobertura_pct": round(cov / base * 100, 2) if base else None,
        }
    return city, comunas


def compare_euclidean(euclidean: dict, key: str, distance: int, network_city: dict, network_comunas: dict) -> dict:
    old = euclidean["cobertura"][key]["distancias"][str(distance)]
    city_old = float(old["ciudad"]["cobertura_pct"])
    city_new = float(network_city["cobertura_pct"])
    communes = {}
    for cid in map(str, range(1, 16)):
        e = float(old["comunas"][cid]["cobertura_pct"])
        n = float(network_comunas[cid]["cobertura_pct"])
        communes[cid] = {
            "euclidiana_pct": e,
            "peatonal_pct": n,
            "diferencia_pp": round(n - e, 2),
        }
    return {
        "ciudad": {
            "euclidiana_pct": city_old,
            "peatonal_pct": city_new,
            "diferencia_pp": round(city_new - city_old, 2),
        },
        "comunas": communes,
    }


def main() -> int:
    if not GRAPH.exists() or GRAPH.stat().st_size < 10_000_000:
        raise SystemExit("Falta _cache/caba-walk.graphml; ejecutar explorar_red_peatonal_osm.py")

    sport = load_json(SPORT)
    euclidean = load_json(EUCLIDEAN)
    radios = read_caba()

    graph_wgs = ox.load_graphml(GRAPH)
    graph = ox.project_graph(graph_wgs)
    graph_crs = graph.graph["crs"]
    ids, _, tree = node_index(graph)

    radios_m = radios.to_crs(graph_crs)
    samples, sampling_diag = sample_radios(radios_m)
    if sampling_diag["diferencia_pct"] is None or sampling_diag["diferencia_pct"] > 0.01:
        raise SystemExit(f"Reconstrucción poblacional inválida: {sampling_diag}")

    sample_x = np.asarray([s["x"] for s in samples], dtype=float)
    sample_y = np.asarray([s["y"] for s in samples], dtype=float)
    sample_snap, sample_nodes = nearest_nodes(tree, ids, sample_x, sample_y)

    clubs = sport_points(sport, "clubes")
    polis = sport_points(sport, "polideportivos")
    club_keys = {(round(c.x, 6), round(c.y, 6)) for c in clubs}
    network = clubs + [p for p in polis if (round(p.x, 6), round(p.y, 6)) not in club_keys]
    universes = {
        "clubes": clubs,
        "polideportivos": polis,
        "red_deportiva": network,
    }

    max_threshold = max(DISTANCES)
    results = {}
    for key, points in universes.items():
        seeds, seed_diag = facility_seeds(points, graph_crs, tree, ids)
        node_dist = seeded_distances(graph, seeds, cutoff=max_threshold)
        graph_distance = np.asarray([node_dist.get(node, math.inf) for node in sample_nodes], dtype=float)
        total_distance = graph_distance + sample_snap

        distances = {}
        for d in DISTANCES:
            city, comunas = aggregate(samples, total_distance, d)
            distances[str(d)] = {
                "ciudad": city,
                "comunas": comunas,
                "comparacion_v2": compare_euclidean(euclidean, key, d, city, comunas),
            }
        reachable = total_distance[np.isfinite(total_distance)]
        results[key] = {
            **seed_diag,
            "muestras_con_distancia_hasta_1000m": int(np.isfinite(total_distance).sum()),
            "distancia_total_m_hasta_cutoff": stats(reachable),
            "distancias": distances,
        }

    out = {
        "version": 0,
        "estado": "diagnostico_no_publicado",
        "metodologia": {
            "tipo": "distancia peatonal estimada sobre red OpenStreetMap walk",
            "network_type": "walk",
            "distancias_m": list(DISTANCES),
            "muestreo_intraradio": f"malla {GRID_N}x{GRID_N} con población ponderada por superficie intersectada",
            "supuesto_intraradio": "población uniforme dentro de cada radio censal, consistente con V2",
            "formula": "snap muestra→red + camino mínimo por red + snap red→equipamiento",
            "interpretacion": "metros de recorrido peatonal estimados; no equivalen a tiempo real de caminata",
        },
        "grafo": {
            "archivo_bytes": GRAPH.stat().st_size,
            "crs_calculo": str(graph_crs),
            "nodos": int(graph.number_of_nodes()),
            "aristas_dirigidas": int(graph.number_of_edges()),
        },
        "muestreo": sampling_diag,
        "snap_muestras": stats(sample_snap),
        "cobertura": results,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{OUT.name} · {OUT.stat().st_size // 1024} KB · {len(samples)} muestras")
    print(f"snap muestras: p50 {out['snap_muestras'].get('p50_m')} m · p95 {out['snap_muestras'].get('p95_m')} m · max {out['snap_muestras'].get('max_m')} m")
    for key in universes:
        print(f"  · {key}")
        for d in DISTANCES:
            comp = results[key]["distancias"][str(d)]["comparacion_v2"]["ciudad"]
            print(f"    {d} m: peatonal {comp['peatonal_pct']}% · euclidiana {comp['euclidiana_pct']}% · Δ {comp['diferencia_pp']} pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
