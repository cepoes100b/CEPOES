#!/usr/bin/env python3
"""Generate the draft territorial data package, without mutating existing outputs.

Requires Python 3 and GDAL Python bindings (osgeo), already supplied by the OS.
No network access or installation is performed. See README.md for source snapshots.
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import json
import re
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from osgeo import gdal, ogr, osr

gdal.UseExceptions()
osr.UseExceptions()

HERE = Path(__file__).resolve().parent
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
ALIASES = {"montserrat": "monserrat", "boca": "la boca", "paternal": "la paternal",
           "velez sarfield": "velez sarsfield"}
DISPLAY = {"Agronomia": "Agronomía", "Constitucion": "Constitución", "Paternal": "La Paternal",
           "Boca": "La Boca", "Nuñez": "Núñez", "Nunez": "Núñez", "San Nicolas": "San Nicolás",
           "Velez Sarsfield": "Vélez Sarsfield", "Villa Pueyrredon": "Villa Pueyrredón"}


def norm(value):
    s = " ".join("".join(c for c in unicodedata.normalize("NFKD", str(value or "").lower())
                           if not unicodedata.combining(c)).split())
    return ALIASES.get(s, s)


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", norm(value)).strip("-")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")


def read_xlsx(path):
    """Read simple tabular source XLSX using stdlib; keep missing cells as None."""
    with zipfile.ZipFile(path) as z:
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            strings = ["".join(si.itertext()) for si in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        result = []
        for row in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall("s:sheetData/s:row", NS):
            cells = {}
            for cell in row.findall("s:c", NS):
                col = re.match(r"[A-Z]+", cell.attrib["r"]).group()
                index = 0
                for c in col:
                    index = index * 26 + ord(c) - 64
                typ = cell.attrib.get("t")
                raw = cell.find("s:v", NS)
                if typ == "inlineStr":
                    inline = cell.find("s:is", NS)
                    value = "".join(inline.itertext()) if inline is not None else None
                elif raw is None:
                    value = None
                elif typ == "s":
                    value = strings[int(raw.text)]
                elif typ in (None, "n"):
                    value = float(raw.text)
                    value = int(value) if value.is_integer() else value
                else:
                    value = raw.text
                cells[index - 1] = value
            result.append(cells)
        header = result[0]
        return [{name: row.get(i) for i, name in header.items()} for row in result[1:]]


def crs(code):
    s = osr.SpatialReference()
    s.ImportFromEPSG(code)
    s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return s


TO_LOCAL = osr.CoordinateTransformation(crs(4326), crs(9498))
TO_WGS84 = osr.CoordinateTransformation(crs(9498), crs(4326))


def geom(obj):
    return ogr.CreateGeometryFromJson(json.dumps(obj))


def projected(g):
    p = g.Clone()
    p.Transform(TO_LOCAL)
    return p


def round_coordinates(obj):
    if isinstance(obj, list):
        return [round_coordinates(v) for v in obj]
    return round(obj, 7) if isinstance(obj, float) else obj


def geometry_json(g):
    # Keep source precision: rounding tiny inherited slivers can invalidate a union.
    return json.loads(g.ExportToJson())


def point(x, y, projected_input=False):
    if projected_input:
        x, y, _ = TO_WGS84.TransformPoint(float(x), float(y))
    if not (-58.56 < x < -58.30 and -34.73 < y < -34.50):
        raise ValueError(f"Coordinate out of CABA envelope: {x}, {y}")
    return {"type": "Point", "coordinates": [round(x, 7), round(y, 7)]}


def union_all(geometries):
    result = None
    for g in geometries:
        result = g.Clone() if result is None else result.Union(g)
    return result


def area(g):
    if g is None or g.GetDimension() < 2:
        return 0.0
    return projected(g).GetArea()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "output")
    parser.add_argument("--sources", type=Path, default=HERE / "sources.json")
    parser.add_argument("--education-geometry", type=Path, default=HERE / "raw" / "educacion.geojson.gz")
    parser.add_argument("--green-geometry", type=Path, default=HERE / "raw" / "verdes.geojson.gz")
    args = parser.parse_args()
    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mapa-data-build-", dir=destination.parent) as tmp:
        work = Path(tmp)
        candidate = work / "candidate"
        generate(args, candidate)
        # Publish only after the entire package has validated. If replacement fails,
        # restore the former complete package instead of exposing partial products.
        previous = work / "previous"
        if destination.exists():
            generated_paths = {p.relative_to(candidate) for p in candidate.rglob("*") if p.is_file()}
            existing_paths = {p.relative_to(destination) for p in destination.rglob("*") if p.is_file()}
            if existing_paths - generated_paths:
                raise ValueError("Refusing to replace an output directory containing unrelated files")
            destination.rename(previous)
        try:
            candidate.rename(destination)
        except BaseException:
            if previous.exists() and not destination.exists():
                previous.rename(destination)
            raise
    print(f"Complete validated package: {destination}")


def generate(args, out):
    repo = args.repo
    sources = read_json(args.sources)
    source_files = ["badata/barrios.geojson", "badata/establecimientos_educativos.csv", "badata/cesac.csv",
                    "badata/hospitales.xlsx", "badata/espacios_verdes_publicos.xlsx", "estado_territorio.json"]
    input_hashes = {name: sha(repo / name) for name in source_files}
    for name, expected in sources["input_sha256"].items():
        if input_hashes.get(name) != expected:
            raise ValueError(f"Source snapshot changed: {name}. Review and update source metadata before generation.")
    geometry_bytes = gzip.decompress(args.education_geometry.read_bytes())
    if hashlib.sha256(geometry_bytes).hexdigest() != sources["education_geometry_sha256"]:
        raise ValueError("Education geometry snapshot changed without metadata review")
    education_geo = json.loads(geometry_bytes)
    if education_geo.get("crs", {}).get("properties", {}).get("name") != "urn:ogc:def:crs:EPSG::9498":
        raise ValueError("Unexpected education CRS")
    raw_barrios = read_json(repo / "badata/barrios.geojson")
    if raw_barrios.get("crs", {}).get("properties", {}).get("name") != "urn:ogc:def:crs:OGC:1.3:CRS84":
        raise ValueError("Unexpected barrios CRS")
    assert len(raw_barrios["features"]) == 48
    assert {f["properties"]["id"] for f in raw_barrios["features"]} == set(range(1, 49))
    assert {f["properties"]["comuna"] for f in raw_barrios["features"]} == set(range(1, 16))
    territories, by_name, barrios_geoms = [], {}, {}
    communes = collections.defaultdict(list)
    audit = {"verdict": "apto_con_reservas", "source_checked_at": sources["checked_at"],
             "input_sha256": input_hashes, "geometry_source_crs": "EPSG:9498", "output_crs": "OGC:CRS84",
             "area_crs": "EPSG:9498", "topology": {}, "layers": {}, "warnings": []}
    for f in raw_barrios["features"]:
        p, g = f["properties"], geom(f["geometry"])
        assert g.IsValid() and not g.IsEmpty()
        name = DISPLAY.get(p["nombre"], p["nombre"])
        ident = "barrio:" + slug(name)
        center = g.PointOnSurface()
        props = {"id": ident, "source_id": "ba-barrios", "source_feature_id": p["id"],
                 "slug": slug(name), "name": name, "level": "barrio", "comuna": p["comuna"],
                 "area_km2": round(area(g) / 1e6, 6),
                 "center": [round(center.GetX(), 7), round(center.GetY(), 7)],
                 "center_method": "derived_point_on_surface", "area_method": "derived_projected_epsg9498"}
        territories.append({"type": "Feature", "id": ident, "properties": props, "geometry": geometry_json(g)})
        by_name[norm(name)] = props
        barrios_geoms[ident] = g
        communes[p["comuna"]].append(g)
    for number in range(1, 16):
        g = union_all(communes[number])
        assert g.IsValid()
        center = g.PointOnSurface()
        ident = f"comuna:{number}"
        props = {"id": ident, "slug": f"comuna-{number}", "name": f"Comuna {number}", "level": "comuna",
                 "comuna": number, "source_id": "ba-barrios", "area_km2": round(area(g) / 1e6, 6),
                 "center": [round(center.GetX(), 7), round(center.GetY(), 7)],
                 "center_method": "derived_point_on_surface", "geometry_method": "derived_dissolve_barrios",
                 "area_method": "derived_projected_epsg9498"}
        territories.append({"type": "Feature", "id": ident, "properties": props, "geometry": geometry_json(g)})
    overlaps = []
    for i, (aid, a) in enumerate(barrios_geoms.items()):
        for bid, b in list(barrios_geoms.items())[i+1:]:
            if a.Intersects(b):
                overlap = area(a.Intersection(b))
                if overlap > 0.01:
                    overlaps.append({"a": aid, "b": bid, "area_m2": round(overlap, 4)})
    city = union_all(list(barrios_geoms.values()))
    audit["topology"] = {"barrios": 48, "comunas": 15, "valid_barrios": 48, "unique_source_ids": 48,
                         "city_area_km2": round(area(city) / 1e6, 6), "source_overlaps": overlaps,
                         "source_geometry_preserved": True, "polygon_precision": "source_precision",
                         "point_coordinate_decimals": 7,
                         "numerical_validation_tolerances": {"reported_overlap_min_m2": 0.01,
                                                               "commune_dissolve_difference_max_m2": 0.01,
                                                               "serialized_point_to_source_polygon_max_m": 0.05},
                         "overlap_policy": "Preservar y reportar los micro-solapes de origen; no absorberlos como correcciones de límites."}
    for f in territories:
        assert geom(f["geometry"]).IsValid(), f["id"]
    write_json(out / "territories.geojson", {"type": "FeatureCollection", "features": territories})

    def territory(name, comuna):
        b = by_name.get(norm(name))
        if not b or int(comuna) != b["comuna"]:
            raise ValueError(f"Unknown or inconsistent declared territory: {name}, {comuna}")
        return b["id"], f"comuna:{b['comuna']}"

    def feature(ident, name, address, barrio, comuna, category, source, position, method, **extra):
        bid, cid = territory(barrio, comuna)
        p = {"id": ident, "name": str(name or "Sin denominación en la fuente"), "address": str(address or ""),
             "barrio_id": bid, "comuna_id": cid, "category": category, "source_id": source,
             "position_method": method, **extra}
        return {"type": "Feature", "id": ident, "properties": p, "geometry": position}

    layers = {"salud": [], "educacion": [], "verdes": []}
    # CeSAC source coordinates are already WGS84.
    for row in csv.DictReader((repo / "badata/cesac.csv").open(encoding="utf-8-sig")):
        g = ogr.CreateGeometryFromWkt(row["geometry"])
        c = int(re.search(r"\d+", row["comuna"]).group())
        layers["salud"].append(feature("cesac-" + row["id"], row["nombre"], row["direccion"], row["barrio"], c,
                                       "CeSAC", "ba-cesac", point(g.GetX(), g.GetY()), "official_wgs84"))
    # CRS confirmed by the matching official Hospitales GeoJSON snapshot.
    for row in read_xlsx(repo / "badata/hospitales.xlsx"):
        g = ogr.CreateGeometryFromWkt(row["geometry"])
        layers["salud"].append(feature("hospital-" + slug(row["fna"]), row["fna"], row["dir"], row["bar"], row["com"],
                                       "Hospital", "ba-hospitales", point(g.GetX(), g.GetY(), True), "official_reprojected_epsg9498"))
    # A map source is not silently substituted for the official active registry.
    geo_by_key = {}
    for f in education_geo["features"]:
        p = f["properties"]
        if p.get("cue") is None or p.get("anx") is None:
            continue
        key = str(int(p["cue"])) + str(p["anx"]).zfill(2)
        if key in geo_by_key:
            raise ValueError(f"Ambiguous CUE + annex geometry: {key}")
        geo_by_key[key] = f
    exclusions = []
    for row in csv.DictReader((repo / "badata/establecimientos_educativos.csv").open(encoding="utf-8-sig"), delimiter=";"):
        if row["estado_est"] != "1" or row["estado_loc"] != "1":
            exclusions.append(row["cueanexo"])
            continue
        key = row["cueanexo"]
        candidate = geo_by_key.get(key)
        position, method, reason = None, "missing", None
        if candidate is None:
            reason = "sin_cue_anexo_en_geometria"
        else:
            p = candidate["properties"]
            if p.get("cui") is None or str(int(p["cui"])) != row["cui"]:
                reason = "edificio_cui_discrepante"
            elif norm(p["bar"]) != norm(row["barrio"]) or int(p["com"]) != int(row["comuna"]):
                reason = "atributo_territorial_discrepante"
            else:
                position = point(*candidate["geometry"]["coordinates"], projected_input=True)
                method = "official_join_cueanexo_cui_reprojected"
        extra = {"cueanexo": key, "cui": row["cui"], "geometry_source_id": "ba-educacion-geometria"}
        if reason:
            extra["position_missing_reason"] = reason
        layers["educacion"].append(feature("educacion-" + key, row["nombre_est"], row["calle"] + " " + row["num"],
                                           row["barrio"], row["comuna"], row["sector_desc"], "ba-educacion-padron",
                                           position, method, **extra))
    audit["education_registry"] = {"inactive_excluded": exclusions, "geometry_rows": len(education_geo["features"]),
                                     "geometry_unique_cueanexo": len(geo_by_key), "registry_rows": len(layers["educacion"])}
    # Green points locate a source polygon; they are not entrances, centroids or surveyed points.
    invalid_green, truncated_green = [], []
    green_by_id = {}
    if args.green_geometry.exists():
        green_bytes = gzip.decompress(args.green_geometry.read_bytes())
        expected = sources.get("green_geometry_sha256")
        if not expected or hashlib.sha256(green_bytes).hexdigest() != expected:
            raise ValueError("Green GeoJSON snapshot not reviewed in source metadata")
        green_geo = json.loads(green_bytes)
        if green_geo.get("crs", {}).get("properties", {}).get("name") not in ("urn:ogc:def:crs:OGC:1.3:CRS84", "urn:ogc:def:crs:EPSG::4326"):
            raise ValueError("Unexpected green CRS")
        for f in green_geo["features"]:
            key = str(f["properties"]["id"])
            if key in green_by_id:
                raise ValueError(f"Ambiguous green geometry ID: {key}")
            green_by_id[key] = f
    for row in read_xlsx(repo / "badata/espacios_verdes_publicos.xlsx"):
        ident = "verde-" + str(row["id"])
        try:
            g = ogr.CreateGeometryFromWkt(row["geometry"])
        except RuntimeError:
            truncated_green.append(ident)
            g = None
        candidate = green_by_id.get(str(row["id"]))
        if candidate is not None:
            gp = candidate["properties"]
            if norm(gp["barrio"]) == norm(row["barrio"]) and int(gp["comuna"]) == int(row["comuna"]):
                g = geom(candidate["geometry"])
        label = row["nombre"] or ((row["clasificac"] or "Espacio verde").capitalize() + " sin denominación")
        if g is None:
            layers["verdes"].append(feature(ident, label, row["ubicacion"], row["barrio"], row["comuna"],
                                            row["clasificac"], "ba-verdes", None, "missing", source_feature_id=row["id"],
                                            area_m2=row["area"], position_missing_reason="geometria_xlsx_truncada"))
            continue
        valid = g.IsValid()
        if not valid:
            invalid_green.append(ident)
        work = g if valid else g.MakeValid()
        p = work.PointOnSurface()
        assert work.Intersects(p)
        layers["verdes"].append(feature(ident, label, row["ubicacion"], row["barrio"], row["comuna"],
                                        row["clasificac"], "ba-verdes", point(p.GetX(), p.GetY()),
                                        "derived_point_on_surface", source_feature_id=row["id"],
                                        area_m2=row["area"], source_polygon_valid=bool(valid),
                                        geometry_source_id="ba-verdes-geometria" if candidate is not None else "ba-verdes"))
    audit["green_invalid_source_polygons"] = invalid_green
    audit["green_truncated_xlsx_polygons"] = truncated_green
    audit["green_official_geojson_available"] = bool(green_by_id)
    # Spatial discrepancies are retained, never silently snapped or relabelled.
    spatial_issues = []
    summary = {f["id"]: {"id": f["id"], "name": f["properties"]["name"], "level": f["properties"]["level"],
                         "area_km2": f["properties"]["area_km2"], "layers": {}} for f in territories}
    for name, features in layers.items():
        assert len({f["id"] for f in features}) == len(features)
        missing = collections.Counter()
        for f in features:
            p = f["properties"]
            if f["geometry"] is None:
                missing[p["position_missing_reason"]] += 1
            else:
                g = geom(f["geometry"])
                declared = barrios_geoms[p["barrio_id"]]
                if not declared.Intersects(g):
                    distance = projected(declared).Distance(projected(g))
                    p["position_territory_warning"] = True
                    p["distance_to_declared_barrio_m"] = round(distance, 1)
                    spatial_issues.append({"id": f["id"], "layer": name, "declared_barrio_id": p["barrio_id"],
                                           "distance_m": round(distance, 1),
                                           "spatial_barrio_ids": [bid for bid, b in barrios_geoms.items() if b.Intersects(g)]})
            for tid in [p["barrio_id"], p["comuna_id"]]:
                cell = summary[tid]["layers"].setdefault(name, {"count": 0, "mapped": 0, "positions_verified": 0})
                cell["count"] += 1
                cell["mapped"] += f["geometry"] is not None
                cell["positions_verified"] += f["geometry"] is not None and not p.get("position_territory_warning", False)
        for tid, row in summary.items():
            cell = row["layers"].setdefault(name, {"count": 0, "mapped": 0, "positions_verified": 0})
            cell["missing_coordinates"] = cell["count"] - cell["mapped"]
            cell["positions_with_territory_warning"] = cell["mapped"] - cell["positions_verified"]
            cell["comparable"] = name != "verdes"
            cell["records_per_km2"] = round(cell["count"] / row["area_km2"], 3) if cell["comparable"] else None
        features.sort(key=lambda f: f["id"])
        write_json(out / "layers" / (name + ".geojson"), {"type": "FeatureCollection", "features": features})
        audit["layers"][name] = {"count": len(features), "mapped": sum(f["geometry"] is not None for f in features),
                                 "positions_verified": sum(f["geometry"] is not None and not f["properties"].get("position_territory_warning", False) for f in features),
                                 "missing_coordinates": dict(missing),
                                 "barrios_with_records": len({f["properties"]["barrio_id"] for f in features}),
                                 "comunas_with_records": len({f["properties"]["comuna_id"] for f in features}),
                                 "territory_discrepancies": sum(x["layer"] == name for x in spatial_issues)}
        audit["layers"][name]["comparable"] = name != "verdes"
        if name == "verdes":
            audit["layers"][name]["comparison_disabled_reason"] = "41 puntos interiores están fuera del barrio declarado en la fuente. Capa exploratoria: conservar filas, ocultar esos puntos y no publicar tasas ni rankings."
    audit["spatial_discrepancies"] = spatial_issues
    write_json(out / "indicators.json", {"kind": "derived", "indicator": "records_per_km2", "territories": list(summary.values())})
    audit["warnings"] = [
        "El corte de observación no está declarado: actualización del catálogo, recurso y descarga son fechas distintas.",
        "Los micro-solapes originales de límites se documentan y preservan, sin alterar división administrativa.",
        "Educación conserva el padrón activo; se omiten puntos cuando CUE+anexo, CUI o territorio no permiten enlazar con seguridad.",
        "Los puntos verdes son interiores derivados de polígonos, no accesos; el inventario incluye canteros y jardines. Los polígonos inválidos se reparan sólo para obtener el punto representativo.",
        "Las 41 discrepancias entre punto verde y barrio declarado se conservan como advertencias explícitas: ocultar esos puntos en el mapa y no publicar tasas ni rankings verdes.",
        "Densidad de registros no equivale a capacidad, calidad, cobertura poblacional o accesibilidad."
    ]
    write_json(out / "audit.json", audit)
    manifest = {"version": 1, "status": "draft", "checked_at": sources["checked_at"], "data_observed_at": None,
                "crs": "OGC:CRS84", "sources": sources["sources"], "territories": {"url": "territories.geojson", "barrios": 48, "comunas": 15},
                "layers": [{"id": name, "url": f"layers/{name}.geojson", **audit["layers"][name]} for name in layers],
                "indicators": {"url": "indicators.json", "id": "records_per_km2", "label": "Registros por km²",
                               "kind": "derived", "unit": "registros/km²", "denominator": "Superficie administrativa BA Data proyectada a EPSG:9498",
                               "formula": "Registros asignados por barrio/comuna declarados en fuente / superficie administrativa en km²",
                               "includes_unmapped_records": True, "missing_is_zero": False,
                               "recommended_layers": ["salud", "educacion"],
                               "green_ranking_status": "requiere_revision_de_discrepancias_territoriales",
                               "limitations": "Mide densidad de inventario. No mide capacidad, calidad, vacantes, accesibilidad ni cobertura poblacional."},
                "position_methods": {"official_wgs84": "Coordenadas publicadas en WGS84",
                                     "official_reprojected_epsg9498": "Coordenadas oficiales transformadas de EPSG:9498 a WGS84",
                                     "official_join_cueanexo_cui_reprojected": "Coordenadas oficiales enlazadas por CUE+anexo y CUI, con territorio compatible; reproyectadas",
                                     "derived_point_on_surface": "Punto interior derivado del polígono oficial; no representa un acceso",
                                     "missing": "Coordenada no verificable: registro conservado sin punto"},
                "audit_url": "audit.json", "warnings": audit["warnings"], "input_sha256": input_hashes}
    manifest["files"] = [{"path": str(p.relative_to(out)), "bytes": p.stat().st_size, "sha256": sha(p)}
                         for p in sorted(out.rglob("*")) if p.is_file() and p.name != "manifest.json"]
    write_json(out / "manifest.json", manifest)
    print(json.dumps({"output": str(out), "territories": 63, "layers": audit["layers"], "source_overlaps": overlaps,
                      "invalid_green_source_polygons": len(invalid_green)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
