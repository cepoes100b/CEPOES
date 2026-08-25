#!/usr/bin/env python3
"""Genera indicadores agregados de proximidad a la red deportiva de CABA.

Metodología:
- población y geometría: radios censales 2022 con población total (CA3),
  dataset abierto de CONICET basado en cartografía y Redatam de INDEC;
- oferta: puntos ya normalizados por CEPOES en deporte-salud.json;
- proximidad: buffers euclidianos de 800 y 1.000 metros en CRS métrico;
- población cubierta: prorrateo por proporción del área del radio intersectada por
  el buffer, suponiendo distribución uniforme de la población dentro de cada radio.

Solo se publica el agregado Ciudad/comuna; no se replica la cartografía censal.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import Point
from shapely.ops import unary_union

BASE = Path(__file__).resolve().parent
SPORT = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-salud.json"
OUT = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-accesibilidad.json"
TMP = BASE / "_tmp_radios_2022.gpkg"

RADIOS_URL = "https://datosdeinvestigacion.conicet.gov.ar/bitstream/handle/11336/284095/radios_2022_conDatos_1habHa.gpkg?isAllowed=y&sequence=2"
RADIOS_PAGE = "https://datosdeinvestigacion.conicet.gov.ar/handle/11336/284095"
DISTANCES = (800, 1000)


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Falta {path.relative_to(BASE)}")
    return json.loads(path.read_text(encoding="utf-8"))


def download_radios() -> None:
    with requests.get(RADIOS_URL, stream=True, timeout=180, headers={"User-Agent": "CEPOES-data/1.0"}) as r:
        r.raise_for_status()
        with TMP.open("wb") as fh:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    fh.write(chunk)
    if TMP.stat().st_size < 10_000_000:
        raise SystemExit(f"Descarga de radios inesperadamente pequeña: {TMP.stat().st_size} bytes")


def read_caba() -> gpd.GeoDataFrame:
    download_radios()
    layer = gpd.list_layers(TMP).iloc[0]["name"]
    gdf = gpd.read_file(TMP, layer=layer)
    needed = {"NOMPROV", "NOMDEPTO", "CRO", "CA3", "geometry"}
    missing = needed - set(gdf.columns)
    if missing:
        raise SystemExit(f"Faltan columnas en radios 2022: {sorted(missing)}")
    mask = gdf["NOMPROV"].astype(str).str.casefold().eq("ciudad autónoma de buenos aires".casefold())
    if not mask.any():
        mask = (
            gdf["NOMPROV"].astype(str).str.contains("Buenos Aires", case=False, na=False)
            & gdf["NOMDEPTO"].astype(str).str.contains("Comuna", case=False, na=False)
        )
    caba = gdf.loc[mask, ["NOMDEPTO", "CRO", "CA3", "geometry"]].copy()
    caba["CA3"] = caba["CA3"].fillna(0).astype(float)
    if len(caba) < 3000 or caba["CA3"].sum() < 3_000_000:
        raise SystemExit(f"Filtrado CABA inválido: {len(caba)} radios, población {caba['CA3'].sum():.0f}")
    return caba


def sport_points(data: dict, layer: str) -> list[Point]:
    items = ((data.get("capas") or {}).get(layer) or {}).get("items") or []
    pts: list[Point] = []
    seen: set[tuple[float, float]] = set()
    for item in items:
        coord = item.get("coord")
        if not isinstance(coord, list) or len(coord) != 2:
            continue
        try:
            lon, lat = float(coord[0]), float(coord[1])
        except (TypeError, ValueError):
            continue
        if not (-58.7 <= lon <= -58.2 and -34.85 <= lat <= -34.45):
            continue
        key = (round(lon, 6), round(lat, 6))
        if key not in seen:
            seen.add(key)
            pts.append(Point(lon, lat))
    return pts


def comuna_id(name: object) -> str | None:
    text = str(name or "")
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    n = int(digits)
    return str(n) if 1 <= n <= 15 else None


def coverage_for(
    radios_metric: gpd.GeoDataFrame,
    points_wgs84: list[Point],
    metric_crs: object,
    distance: int,
) -> tuple[dict, dict]:
    if not points_wgs84:
        raise SystemExit("No hay puntos deportivos georreferenciados")
    points = gpd.GeoSeries(points_wgs84, crs="EPSG:4326").to_crs(metric_crs)
    service = unary_union([geom.buffer(distance) for geom in points])
    area = radios_metric.geometry.area
    covered_area = radios_metric.geometry.intersection(service).area
    frac = (covered_area / area).clip(lower=0, upper=1).fillna(0)
    covered_pop = radios_metric["CA3"] * frac

    total_pop = float(radios_metric["CA3"].sum())
    city_covered = float(covered_pop.sum())
    city = {
        "poblacion_base": int(round(total_pop)),
        "poblacion_cubierta_estimada": int(round(city_covered)),
        "poblacion_fuera_cobertura_estimada": int(round(total_pop - city_covered)),
        "cobertura_pct": round(city_covered / total_pop * 100, 2) if total_pop else None,
    }

    work = radios_metric[["NOMDEPTO", "CA3"]].copy()
    work["covered"] = covered_pop
    comunas = {}
    for name, group in work.groupby("NOMDEPTO", dropna=False):
        cid = comuna_id(name)
        if not cid:
            continue
        pop = float(group["CA3"].sum())
        covered = float(group["covered"].sum())
        comunas[cid] = {
            "poblacion_base": int(round(pop)),
            "poblacion_cubierta_estimada": int(round(covered)),
            "poblacion_fuera_cobertura_estimada": int(round(pop - covered)),
            "cobertura_pct": round(covered / pop * 100, 2) if pop else None,
        }
    if set(comunas) != {str(i) for i in range(1, 16)}:
        raise SystemExit(f"Agregación comunal incompleta: {sorted(comunas)}")
    return city, comunas


def main() -> int:
    sport = load_json(SPORT)
    radios = read_caba()
    metric_crs = radios.estimate_utm_crs()
    if metric_crs is None:
        raise SystemExit("No se pudo estimar un CRS métrico para CABA")
    radios_m = radios.to_crs(metric_crs)

    clubs = sport_points(sport, "clubes")
    polis = sport_points(sport, "polideportivos")
    network = clubs + [p for p in polis if (round(p.x, 6), round(p.y, 6)) not in {(round(c.x, 6), round(c.y, 6)) for c in clubs}]

    universes = {
        "clubes": {"label": "Clubes y sedes", "points": clubs},
        "polideportivos": {"label": "Polideportivos públicos", "points": polis},
        "red_deportiva": {"label": "Red deportiva registrada", "points": network},
    }

    results = {}
    for key, meta in universes.items():
        distances = {}
        for d in DISTANCES:
            city, comunas = coverage_for(radios_m, meta["points"], metric_crs, d)
            distances[str(d)] = {"ciudad": city, "comunas": comunas}
        results[key] = {
            "label": meta["label"],
            "puntos_georreferenciados": len(meta["points"]),
            "distancias": distances,
        }

    pop_radios = int(round(radios["CA3"].sum()))
    territory_pop = sum(int((v or {}).get("poblacion") or 0) for v in (load_json(BASE / "territorio.json").get("comunas") or {}).values())
    gap = territory_pop - pop_radios

    out = {
        "version": 1,
        "generado": dt.date.today().isoformat(),
        "titulo": "Accesibilidad territorial a la red deportiva de CABA",
        "metodologia": {
            "tipo": "proximidad euclidiana con estimación areal de población",
            "distancias_m": list(DISTANCES),
            "crs_calculo": str(metric_crs),
            "supuesto_intraradio": "La población se distribuye uniformemente dentro de cada radio censal; la población cubierta se prorratea por la proporción del área del radio dentro de cada buffer.",
            "interpretacion": "800 m y 1.000 m son distancias geométricas, no tiempos de caminata ni isócronas sobre red peatonal.",
            "universo": "Radios censales 2022 incluidos en la fuente derivada con densidad superior a 1 habitante por hectárea.",
        },
        "base_poblacional": {
            "radios": len(radios),
            "poblacion_radios": pop_radios,
            "poblacion_territorial_cepoes": territory_pop,
            "diferencia_personas": gap,
            "diferencia_pct": round(abs(gap) / territory_pop * 100, 4) if territory_pop else None,
        },
        "fuentes": [
            {
                "nombre": "CONICET Digital · Argentina (2022) radios censales con datos de cantidad de población y densidad de población",
                "url": RADIOS_PAGE,
                "detalle": "Geometría de radios censales INDEC 2022 y población total obtenida mediante Redatam-INDEC.",
            },
            {
                "nombre": "CEPOES · Deporte y vida saludable",
                "url": "https://cepoes.org/territorio/deporte-salud/",
                "detalle": "Clubes, sedes y polideportivos normalizados desde fuentes oficiales de BA Data.",
            },
        ],
        "cobertura": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"deporte-accesibilidad.json · {OUT.stat().st_size // 1024} KB · {len(radios)} radios · {pop_radios} habitantes")
    for key in ("clubes", "polideportivos", "red_deportiva"):
        vals = out["cobertura"][key]["distancias"]
        print(f"  · {key}: 800 m {vals['800']['ciudad']['cobertura_pct']}% · 1000 m {vals['1000']['ciudad']['cobertura_pct']}%")
    print(f"  · control población vs territorio.json: diferencia {gap} ({out['base_poblacional']['diferencia_pct']}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
