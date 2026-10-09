"""Offline regression tests against reviewed official public snapshots."""
import collections
import csv
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from osgeo import ogr
import generar_mapa_territorial as G

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("CEPOES_MAP_DATA_OUTPUT", str(HERE / "output")))
REPO = Path(os.environ.get("CEPOES_REPO", str(next((p for p in HERE.parents if (p / "badata/barrios.geojson").exists()), HERE.parent / "mapa-territorial-2"))))


class TerritorialData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = G.read_json(OUT / "manifest.json")
        cls.audit = G.read_json(OUT / "audit.json")
        cls.territories = G.read_json(OUT / "territories.geojson")["features"]
        cls.layers = {name: G.read_json(OUT / "layers" / (name + ".geojson"))["features"]
                      for name in ["salud", "educacion", "verdes"]}
        cls.indicators = G.read_json(OUT / "indicators.json")["territories"]

    def test_territorial_coverage_and_unique_ids(self):
        self.assertEqual(collections.Counter(f["properties"]["level"] for f in self.territories), {"barrio": 48, "comuna": 15})
        self.assertEqual(len({f["id"] for f in self.territories}), 63)
        self.assertEqual({f["properties"]["source_feature_id"] for f in self.territories if f["properties"]["level"] == "barrio"}, set(range(1, 49)))
        for f in self.territories:
            self.assertTrue(G.geom(f["geometry"]).IsValid(), f["id"])
            self.assertGreater(f["properties"]["area_km2"], 0)

    def test_communes_are_dissolved_from_same_barrios(self):
        for commune in [f for f in self.territories if f["properties"]["level"] == "comuna"]:
            number = commune["properties"]["comuna"]
            children = [G.geom(f["geometry"]) for f in self.territories if f["properties"]["level"] == "barrio" and f["properties"]["comuna"] == number]
            difference = G.geom(commune["geometry"]).SymDifference(G.union_all(children))
            self.assertLess(G.area(difference), 0.01)

    def test_counts_and_coordinate_completeness(self):
        self.assertEqual({k: len(v) for k, v in self.layers.items()}, {"salud": 86, "educacion": 2732, "verdes": 2176})
        self.assertEqual({k: sum(f["geometry"] is not None for f in v) for k, v in self.layers.items()}, {"salud": 86, "educacion": 2672, "verdes": 2176})
        self.assertEqual(self.audit["layers"]["educacion"]["missing_coordinates"], {"sin_cue_anexo_en_geometria": 39, "edificio_cui_discrepante": 18, "atributo_territorial_discrepante": 3})
        self.assertEqual(self.audit["layers"]["verdes"]["positions_verified"], 2135)
        self.assertFalse(self.audit["layers"]["verdes"]["comparable"])

    def test_feature_contract_and_coordinates(self):
        ids = {f["id"] for f in self.territories}
        sources = {s["id"] for s in self.manifest["sources"]}
        for name, features in self.layers.items():
            self.assertEqual(len({f["id"] for f in features}), len(features))
            for f in features:
                p = f["properties"]
                self.assertEqual(f["id"], p["id"])
                for key in ["name", "address", "barrio_id", "comuna_id", "category", "source_id", "position_method"]:
                    self.assertIn(key, p)
                self.assertIn(p["barrio_id"], ids)
                self.assertIn(p["comuna_id"], ids)
                self.assertIn(p["source_id"], sources)
                if f["geometry"]:
                    self.assertEqual(f["geometry"]["type"], "Point")
                    x, y = f["geometry"]["coordinates"]
                    self.assertTrue(-58.56 < x < -58.30 and -34.73 < y < -34.50)
                else:
                    self.assertEqual(p["position_method"], "missing")
                    self.assertIn("position_missing_reason", p)

    def test_health_and_education_points_match_declared_barrios(self):
        barrios = {f["id"]: G.geom(f["geometry"]) for f in self.territories if f["properties"]["level"] == "barrio"}
        for name in ["salud", "educacion"]:
            for f in self.layers[name]:
                if f["geometry"]:
                    self.assertTrue(barrios[f["properties"]["barrio_id"]].Intersects(G.geom(f["geometry"])), f["id"])

    def test_green_points_inside_source_polygons(self):
        raw = json.loads(gzip.decompress((HERE / "raw/verdes.geojson.gz").read_bytes()))
        source = {f["properties"]["id"]: f for f in raw["features"]}
        for f in self.layers["verdes"]:
            polygon = G.geom(source[f["properties"]["source_feature_id"]]["geometry"])
            if not f["properties"]["source_polygon_valid"]:
                polygon = polygon.MakeValid()
            point = G.geom(f["geometry"])
            self.assertLessEqual(G.projected(polygon).Distance(G.projected(point)), 0.05, f["id"])
            self.assertEqual(f["properties"]["position_method"], "derived_point_on_surface")
        self.assertEqual(len(self.audit["green_truncated_xlsx_polygons"]), 69)
        self.assertEqual(len(self.audit["green_invalid_source_polygons"]), 25)

    def test_indicators_reconcile_and_keep_missing_records(self):
        for name, features in self.layers.items():
            for level in ["barrio", "comuna"]:
                rows = [r for r in self.indicators if r["level"] == level]
                self.assertEqual(sum(r["layers"][name]["count"] for r in rows), len(features))
                for r in rows:
                    c = r["layers"][name]
                    self.assertEqual(c["count"] - c["mapped"], c["missing_coordinates"])
                    self.assertEqual(c["mapped"] - c["positions_verified"], c["positions_with_territory_warning"])
                    if name == "verdes":
                        self.assertFalse(c["comparable"])
                        self.assertIsNone(c["records_per_km2"])
                    else:
                        self.assertEqual(c["records_per_km2"], round(c["count"] / r["area_km2"], 3))

    def test_source_traceability_no_fabricated_cutoff(self):
        for s in self.manifest["sources"]:
            self.assertEqual(s["license"], "CC-BY-2.5-AR")
            self.assertTrue(s["url"].startswith("https://data.buenosaires.gob.ar/"))
            self.assertIsNone(s["data_observed_at"])
        self.assertEqual(self.manifest["indicators"]["recommended_layers"], ["salud", "educacion"])

    def test_payload_hashes(self):
        for f in self.manifest["files"]:
            path = OUT / f["path"]
            self.assertEqual(path.stat().st_size, f["bytes"])
            self.assertEqual(G.sha(path), f["sha256"])

    def test_reproducible_generation(self):
        with tempfile.TemporaryDirectory(prefix="mapa-data-qa-", dir=HERE) as tmp:
            subprocess.run([sys.executable, str(HERE / "generar_mapa_territorial.py"), "--repo", str(REPO), "--output", tmp],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for file in OUT.rglob("*"):
                if file.is_file():
                    self.assertEqual(file.read_bytes(), (Path(tmp) / file.relative_to(OUT)).read_bytes(), str(file))

    def test_changed_source_preserves_last_valid_package(self):
        with tempfile.TemporaryDirectory(prefix="mapa-data-failure-qa-", dir=HERE) as tmp:
            tmp = Path(tmp)
            destination = tmp / "data"
            shutil.copytree(OUT, destination)
            sources = G.read_json(HERE / "sources.json")
            sources["green_geometry_sha256"] = "0" * 64
            G.write_json(tmp / "changed-sources.json", sources)
            result = subprocess.run([sys.executable, str(HERE / "generar_mapa_territorial.py"), "--repo", str(REPO),
                                     "--output", str(destination), "--sources", str(tmp / "changed-sources.json")],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.assertNotEqual(result.returncode, 0)
            for file in OUT.rglob("*"):
                if file.is_file():
                    self.assertEqual(file.read_bytes(), (destination / file.relative_to(OUT)).read_bytes(), str(file))


if __name__ == "__main__":
    unittest.main(verbosity=2)
