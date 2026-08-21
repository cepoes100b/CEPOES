"""Ejecuta la Oferta territorial ampliada con controles espaciales.

Además de asegurar IDs únicos, usa el GeoJSON oficial de barrios para completar
comuna/barrio cuando una fuente oficial trae coordenadas pero no esos campos.
Esto resuelve capas como Ecobici. En fuentes de alcance regional, como estaciones
de ferrocarril, conserva exclusivamente los registros ubicados en CABA.
"""
from __future__ import annotations

import json
from pathlib import Path

import generar_oferta_ampliada as E

BASE = Path(__file__).resolve().parent
DIR = BASE / "equipamientos"
BARRIOS = BASE / "badata" / "barrios.geojson"
G = E.G


def unique_ids(path: Path) -> int:
    d = json.loads(path.read_text(encoding="utf-8"))
    used = set(); changed = 0
    for i, item in enumerate(d.get("items") or [], 1):
        base = str(item.get("id") or f"registro-{i}")
        candidate = base; n = 2
        while candidate in used:
            candidate = f"{base}-{n}"; n += 1
        if candidate != item.get("id"):
            item["id"] = candidate; changed += 1
        used.add(candidate)
    if changed:
        path.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return changed


def point_in_ring(x: float, y: float, ring) -> bool:
    inside = False
    if not ring or len(ring) < 3:
        return False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        # Ray casting; un epsilon mínimo evita divisiones por cero en lados horizontales.
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def point_in_polygon(x: float, y: float, polygon) -> bool:
    if not polygon or not point_in_ring(x, y, polygon[0]):
        return False
    # Los anillos siguientes son huecos.
    return not any(point_in_ring(x, y, hole) for hole in polygon[1:])


def geometry_contains(x: float, y: float, geom: dict) -> bool:
    typ = geom.get("type")
    coords = geom.get("coordinates") or []
    if typ == "Polygon":
        return point_in_polygon(x, y, coords)
    if typ == "MultiPolygon":
        return any(point_in_polygon(x, y, poly) for poly in coords)
    return False


def flatten_points(coords):
    if isinstance(coords, (list, tuple)):
        if len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
            yield float(coords[0]), float(coords[1])
        else:
            for part in coords:
                yield from flatten_points(part)


def load_spatial_index():
    if not BARRIOS.exists():
        raise FileNotFoundError("badata/barrios.geojson")
    obj = json.loads(BARRIOS.read_text(encoding="utf-8"))
    features = obj.get("features") or []
    if len(features) != 48:
        raise RuntimeError(f"barrios.geojson tiene {len(features)} barrios; se esperaban 48")
    official, _ = E.official_territory()
    index = []
    for feat in features:
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        pts = list(flatten_points(geom.get("coordinates") or []))
        if not pts:
            continue
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        nombre = G.canonical_barrio(props.get("nombre"), official)
        comuna = G.parse_comuna(props.get("comuna"))
        index.append((min(xs), min(ys), max(xs), max(ys), nombre, comuna, geom))
    if len(index) != 48:
        raise RuntimeError(f"índice espacial incompleto: {len(index)} barrios")
    return index


def locate(coord, index):
    if not coord or len(coord) < 2:
        return None
    try:
        x, y = float(coord[0]), float(coord[1])
    except (TypeError, ValueError):
        return None
    for minx, miny, maxx, maxy, barrio, comuna, geom in index:
        if minx <= x <= maxx and miny <= y <= maxy and geometry_contains(x, y, geom):
            return comuna, barrio
    return None


def valid_comuna(v) -> bool:
    try:
        return 1 <= int(v) <= 15
    except (TypeError, ValueError):
        return False


def configure_layers():
    # La versión vigente del recurso ferroviario publica geometry POINT además de
    # barrio/comuna para estaciones en CABA. El dataset incluye estaciones de un
    # ámbito regional, por eso luego se recorta espacialmente a la Ciudad.
    for cfg in E.LAYERS:
        if cfg["id"] == "ferrocarril":
            cfg["geometry"] = ["geometry"]
        elif cfg["id"] == "subte-bocas":
            # Compatibilidad con versiones que publican lat/long en columnas.
            cfg.setdefault("lat", ["lat", "latitud"])
            cfg.setdefault("lon", ["long", "lon", "longitud"])


def spatialize_layers(index):
    assigned_total = 0
    removed_rail = 0
    for cfg in E.LAYERS:
        p = DIR / f"{cfg['id']}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        items = d.get("items") or []
        assigned = 0
        for item in items:
            if item.get("coord") and (not valid_comuna(item.get("comuna")) or not item.get("barrio")):
                loc = locate(item.get("coord"), index)
                if loc:
                    comuna, barrio = loc
                    if not valid_comuna(item.get("comuna")):
                        item["comuna"] = comuna
                    if not item.get("barrio"):
                        item["barrio"] = barrio
                    assigned += 1
        # El recurso de ferrocarril puede contener estaciones del AMBA. CEPOES es
        # un observatorio de CABA: se conservan sólo estaciones efectivamente
        # territorializadas dentro de alguna de las 15 comunas.
        if cfg["id"] == "ferrocarril":
            before = len(items)
            items = [x for x in items if valid_comuna(x.get("comuna"))]
            removed_rail = before - len(items)
            d["items"] = items
        d["total"] = len(items)
        p.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        if assigned:
            print(f"  · {cfg['id']}: {assigned} registros territorializados por coordenadas")
        assigned_total += assigned
    if removed_rail:
        print(f"  · ferrocarril: {removed_rail} registros fuera de CABA excluidos")
    print(f"  · territorialización espacial completada: {assigned_total} registros")


def refresh_manifests():
    catalog_path = DIR / "catalogo.json"
    index_path = DIR / "index.json"
    if not catalog_path.exists():
        return
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    totals = {}
    for layer in catalog.get("layers") or []:
        fname = layer.get("file")
        p = DIR / str(fname)
        if not fname or not p.exists():
            continue
        try:
            n = len(json.loads(p.read_text(encoding="utf-8")).get("items") or [])
        except Exception:
            continue
        layer["total"] = n
        totals[layer["id"]] = {"url": f"equipamientos/{fname}", "total": n}
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if index_path.exists():
        idx = json.loads(index_path.read_text(encoding="utf-8"))
        idx["archivos"] = totals
        index_path.write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> int:
    configure_layers()
    rc = E.main()
    if rc:
        return rc
    index = load_spatial_index()
    spatialize_layers(index)
    changed = 0
    for cfg in E.LAYERS:
        p = DIR / f"{cfg['id']}.json"
        if p.exists():
            changed += unique_ids(p)
    refresh_manifests()
    print(f"  · IDs duplicados normalizados: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
