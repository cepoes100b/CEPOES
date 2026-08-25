#!/usr/bin/env python3
"""Diagnóstico V3: accesibilidad a oferta deportiva mediante red peatonal OSM.

NO publica resultados. Compara la proximidad euclidiana de la V2 con una
estimación de distancia caminable por red para los mismos radios censales y
universos de oferta.

Supuestos:
- población uniforme dentro de cada radio, igual que en V2;
- cada radio se aproxima con una malla N×N configurable mediante GRID_N;
- cada muestra y equipamiento se conecta al TRAMO peatonal OSM más cercano;
- distancia = acceso perpendicular + recorrido por la red `walk` + acceso final;
- si muestra y equipamiento caen en el mismo tramo físico, se considera también
  el recorrido directo sobre ese tramo, sin obligar a pasar por una esquina;
- 800/1.000 m son metros recorridos estimados, no tiempo real de caminata.
"""
from __future__ import annotations

import heapq
import json
import math
import os
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import numpy as np
import osmnx as ox
from shapely.geometry import LineString, Point, box

from generar_accesibilidad_deportiva import comuna_id, load_json, read_caba, sport_points

BASE = Path(__file__).resolve().parent
GRAPH = BASE / "_cache" / "caba-walk.graphml"
SPORT = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-salud.json"
EUCLIDEAN = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-accesibilidad.json"
DISTANCES = (800, 1000)
GRID_N = int(os.environ.get("GRID_N", "4"))
if GRID_N < 2 or GRID_N > 16:
    raise SystemExit("GRID_N debe estar entre 2 y 16")
OUT = BASE / os.environ.get("OUT_FILE", f"diagnostico_accesibilidad_peatonal_g{GRID_N}.json")
EXTREME_THRESHOLDS = (50, 100, 200, 500)


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
    for idx, row in radios_m.iterrows():
        geom = row.geometry
        pop = float(row["CA3"] or 0)
        cid = comuna_id(row["NOMDEPTO"])
        radio = str(row.get("CRO", idx))
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
                cell = box(
                    minx + ix * dx,
                    miny + iy * dy,
                    minx + (ix + 1) * dx,
                    miny + (iy + 1) * dy,
                )
                inter = geom.intersection(cell)
                if inter.is_empty or inter.area <= 0:
                    continue
                frac = float(inter.area) / radio_area
                local.append((inter.representative_point(), frac))
                radio_weight += frac
        if not local or radio_weight <= 0:
            invalid += 1
            continue
        for point, frac in local:
            samples.append(
                {
                    "comuna": cid,
                    "radio": radio,
                    "x": float(point.x),
                    "y": float(point.y),
                    "poblacion": pop * frac / radio_weight,
                }
            )
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
    """Dijkstra multi-fuente con costo inicial continuo desde equipamientos."""
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


def edge_geometry(graph, u, v, k) -> tuple[LineString, float, object]:
    data = graph.get_edge_data(u, v, k)
    if data is None:
        raise KeyError((u, v, k))
    geom = data.get("geometry")
    if geom is None:
        geom = LineString(
            [
                (float(graph.nodes[u]["x"]), float(graph.nodes[u]["y"])),
                (float(graph.nodes[v]["x"]), float(graph.nodes[v]["y"])),
            ]
        )
    try:
        edge_len = float(data.get("length", geom.length))
    except (TypeError, ValueError):
        edge_len = float(geom.length)
    if not math.isfinite(edge_len) or edge_len < 0:
        edge_len = float(geom.length)
    return geom, edge_len, data.get("osmid", "")


def physical_edge_key(u, v, osmid: object, edge_len: float) -> tuple:
    a, b = sorted((str(u), str(v)))
    # osmid ayuda a distinguir paralelas; longitud redondeada estabiliza GraphML.
    return a, b, str(osmid), round(float(edge_len), 2)


def edge_access(graph, edge_id, x: float, y: float, off_network: float) -> tuple:
    """Devuelve información continua de acceso a una arista.

    (u, v, fuera_red, hasta_u, hasta_v, clave_fisica, posicion_canonica, longitud)
    """
    u, v, k = tuple(edge_id)
    geom, edge_len, osmid = edge_geometry(graph, u, v, k)
    p = Point(float(x), float(y))
    geom_len = float(geom.length)
    if geom_len <= 0:
        key = physical_edge_key(u, v, osmid, edge_len)
        return u, v, float(off_network), 0.0, 0.0, key, 0.0, float(edge_len)

    position = float(geom.project(p))
    first = Point(geom.coords[0])
    up = Point(float(graph.nodes[u]["x"]), float(graph.nodes[u]["y"]))
    vp = Point(float(graph.nodes[v]["x"]), float(graph.nodes[v]["y"]))
    if first.distance(up) <= first.distance(vp):
        geom_to_u = position
    else:
        geom_to_u = geom_len - position
    frac_u = min(1.0, max(0.0, geom_to_u / geom_len))
    along_u = edge_len * frac_u
    along_v = max(0.0, edge_len - along_u)
    key = physical_edge_key(u, v, osmid, edge_len)
    canonical_pos = along_u if str(u) <= str(v) else along_v
    return (
        u,
        v,
        float(off_network),
        float(along_u),
        float(along_v),
        key,
        float(canonical_pos),
        float(edge_len),
    )


def nearest_edge_accesses(graph, xs: np.ndarray, ys: np.ndarray) -> tuple[list[tuple], np.ndarray]:
    edge_ids, off = ox.distance.nearest_edges(graph, X=xs, Y=ys, return_dist=True)
    off_arr = np.asarray(off, dtype=float)
    accesses = [
        edge_access(graph, edge_id, x, y, d)
        for edge_id, x, y, d in zip(edge_ids, xs, ys, off_arr)
    ]
    return accesses, off_arr


def facility_seeds(points_wgs84: list[Point], graph, graph_crs) -> tuple[dict, dict, dict]:
    if not points_wgs84:
        raise SystemExit("Universo deportivo sin puntos georreferenciados")
    gs = gpd.GeoSeries(points_wgs84, crs="EPSG:4326").to_crs(graph_crs)
    xs = gs.x.to_numpy(dtype=float)
    ys = gs.y.to_numpy(dtype=float)
    accesses, off = nearest_edge_accesses(graph, xs, ys)
    seeds: dict = {}
    direct_by_edge: dict = {}
    for u, v, outside, along_u, along_v, key, pos, _ in accesses:
        for node, value in ((u, outside + along_u), (v, outside + along_v)):
            if value < seeds.get(node, math.inf):
                seeds[node] = value
        direct_by_edge.setdefault(key, []).append((float(pos), float(outside)))
    return seeds, direct_by_edge, {
        "puntos_georreferenciados": len(points_wgs84),
        "nodos_semilla_unicos": len(seeds),
        "tramos_destino_unicos": len(direct_by_edge),
        "distancia_fuera_red_equipamiento": stats(off),
    }


def sample_network_distances(accesses: list[tuple], node_dist: dict, direct_by_edge: dict) -> np.ndarray:
    out = np.full(len(accesses), math.inf, dtype=float)
    for i, (u, v, outside, along_u, along_v, key, pos, _) in enumerate(accesses):
        via_u = node_dist.get(u, math.inf) + along_u
        via_v = node_dist.get(v, math.inf) + along_v
        best = min(via_u, via_v)
        # Corrección continua si origen y destino están sobre el mismo tramo físico.
        for facility_pos, facility_off in direct_by_edge.get(key, ()): 
            best = min(best, abs(pos - facility_pos) + facility_off)
        if math.isfinite(best):
            out[i] = outside + best
    return out


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


def extreme_off_network(samples: list[dict], off: np.ndarray) -> dict:
    pop = np.asarray([s["poblacion"] for s in samples], dtype=float)
    total_pop = float(pop.sum())
    comunas = np.asarray([s["comuna"] for s in samples], dtype=object)
    thresholds: dict = {}
    for t in EXTREME_THRESHOLDS:
        mask = off > t
        affected = float(pop[mask].sum())
        by_comuna = {}
        for cid in map(str, range(1, 16)):
            cmask = mask & (comunas == cid)
            cpop = float(pop[cmask].sum())
            if cpop > 0:
                by_comuna[cid] = {
                    "muestras": int(cmask.sum()),
                    "poblacion_ponderada": round(cpop, 1),
                }
        thresholds[str(t)] = {
            "muestras": int(mask.sum()),
            "poblacion_ponderada": round(affected, 1),
            "poblacion_pct": round(affected / total_pop * 100, 4) if total_pop else None,
            "comunas": by_comuna,
        }

    order = np.argsort(-off)[:20]
    top = [
        {
            "comuna": samples[int(i)]["comuna"],
            "radio": samples[int(i)]["radio"],
            "poblacion_ponderada": round(float(samples[int(i)]["poblacion"]), 1),
            "fuera_red_m": round(float(off[int(i)]), 1),
            "x": round(float(samples[int(i)]["x"]), 1),
            "y": round(float(samples[int(i)]["y"]), 1),
        }
        for i in order
    ]
    return {"umbrales": thresholds, "top_20": top}


def main() -> int:
    if not GRAPH.exists() or GRAPH.stat().st_size < 10_000_000:
        raise SystemExit("Falta _cache/caba-walk.graphml; ejecutar explorar_red_peatonal_osm.py")

    sport = load_json(SPORT)
    euclidean = load_json(EUCLIDEAN)
    radios = read_caba()

    graph_wgs = ox.load_graphml(GRAPH)
    graph = ox.project_graph(graph_wgs)
    graph_crs = graph.graph["crs"]

    radios_m = radios.to_crs(graph_crs)
    samples, sampling_diag = sample_radios(radios_m)
    if sampling_diag["diferencia_pct"] is None or sampling_diag["diferencia_pct"] > 0.01:
        raise SystemExit(f"Reconstrucción poblacional inválida: {sampling_diag}")

    sample_x = np.asarray([s["x"] for s in samples], dtype=float)
    sample_y = np.asarray([s["y"] for s in samples], dtype=float)
    sample_accesses, sample_off = nearest_edge_accesses(graph, sample_x, sample_y)

    clubs = sport_points(sport, "clubes")
    polis = sport_points(sport, "polideportivos")
    club_keys = {(round(c.x, 6), round(c.y, 6)) for c in clubs}
    network = clubs + [p for p in polis if (round(p.x, 6), round(p.y, 6)) not in club_keys]
    universes = {"clubes": clubs, "polideportivos": polis, "red_deportiva": network}

    max_threshold = max(DISTANCES)
    results = {}
    for key, points in universes.items():
        seeds, direct_by_edge, seed_diag = facility_seeds(points, graph, graph_crs)
        node_dist = seeded_distances(graph, seeds, cutoff=max_threshold)
        total_distance = sample_network_distances(sample_accesses, node_dist, direct_by_edge)

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
            "muestras_con_distancia_hasta_cutoff": int(np.isfinite(total_distance).sum()),
            "distancia_total_m_hasta_cutoff": stats(reachable),
            "distancias": distances,
        }

    out = {
        "version": 0,
        "estado": "diagnostico_no_publicado",
        "metodologia": {
            "tipo": "distancia peatonal estimada sobre red OpenStreetMap walk",
            "network_type": "walk",
            "conexion_red": "tramo peatonal más cercano con recorrido parcial y atajo directo si origen/destino comparten tramo",
            "distancias_m": list(DISTANCES),
            "muestreo_intraradio": f"malla {GRID_N}x{GRID_N} con población ponderada por superficie intersectada",
            "supuesto_intraradio": "población uniforme dentro de cada radio censal, consistente con V2",
            "formula": "acceso perpendicular muestra→tramo + camino mínimo continuo por red + acceso tramo→equipamiento",
            "interpretacion": "metros de recorrido peatonal estimados; no equivalen a tiempo real de caminata",
        },
        "grafo": {
            "archivo_bytes": GRAPH.stat().st_size,
            "crs_calculo": str(graph_crs),
            "nodos": int(graph.number_of_nodes()),
            "aristas_dirigidas": int(graph.number_of_edges()),
        },
        "muestreo": sampling_diag,
        "distancia_fuera_red_muestras": stats(sample_off),
        "auditoria_fuera_red": extreme_off_network(samples, sample_off),
        "cobertura": results,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{OUT.name} · {OUT.stat().st_size // 1024} KB · {len(samples)} muestras")
    print(
        "fuera de red muestras: "
        f"p50 {out['distancia_fuera_red_muestras'].get('p50_m')} m · "
        f"p95 {out['distancia_fuera_red_muestras'].get('p95_m')} m · "
        f"max {out['distancia_fuera_red_muestras'].get('max_m')} m"
    )
    for t in EXTREME_THRESHOLDS:
        row = out["auditoria_fuera_red"]["umbrales"][str(t)]
        print(f"  >{t} m fuera de red: {row['poblacion_pct']}% población ponderada · {row['muestras']} muestras")
    for key in universes:
        print(f"  · {key}")
        for d in DISTANCES:
            comp = results[key]["distancias"][str(d)]["comparacion_v2"]["ciudad"]
            print(
                f"    {d} m: peatonal {comp['peatonal_pct']}% · "
                f"euclidiana {comp['euclidiana_pct']}% · Δ {comp['diferencia_pp']} pp"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
