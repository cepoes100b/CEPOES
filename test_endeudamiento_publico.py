#!/usr/bin/env python3
"""Contrato offline de agregados públicos; todos los valores son sintéticos.

No guarda copias del agregado real, microdatos, personas ni la matriz CP4-barrio.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from deploy import validar_endeudamiento_publico as public


STAMP = "2020-03-01T12:00:00+00:00"


def summary(deudores, deuda, *, records=False):
    obj = {"deudores": deudores, "personas_mora": deudores / 10,
           "incidencia_mora_pct": 10.0, "deuda_total_pesos": deuda,
           "deuda_mora_pesos": deuda / 10, "tasa_mora_pct": 10.0}
    if records:
        obj["registros_incluidos"] = deudores * 2
    return obj


def period_fixture(period="2020-02"):
    """Agregados ficticios de 48 barrios, con 10 deudores y $10.000 por barrio."""
    return {
        "schema": public.PERIOD_SCHEMA, "generado_utc": STAMP,
        "periodo": period, "padron_fecha": "2020-02-29",
        "titulo": "Endeudamiento por barrio", "fuente": dict(public.SOURCE_FIELDS),
        "caba": {
            "total": summary(500, 500000, records=True),
            "base_territorial_cp4": summary(490, 490000, records=True),
            "base_barrial_con_soporte": summary(480, 480000),
            "cobertura_territorial_cp4_sobre_caba": dict.fromkeys(public.COVERAGE_METRICS, 98.0),
            "cobertura_mapa_sobre_caba": dict.fromkeys(public.COVERAGE_METRICS, 96.0),
        },
        "filtros": {"sexos": list(public.SEXES), "edades": list(public.AGES), "acreedores": list(public.CREDITORS)},
        "barrios": list(public.BARRIOS), "metricas_segmento": list(public.METRICS),
        "metodologia": {
            **public.METHOD_FIXED, "matriz_periodo_calibracion": "2020-01",
            "matriz_estado_validacion": "VALIDADA",
            "soporte_cp4": {"cp4_matriz": 300, "cp4_con_soporte": 280, "cp4_sin_soporte": 20},
        },
        "segmentos": [
            {"filtros": {"sexo": None, "edad": None, "acreedor": None},
             "datos": [[10.0, 1.0, 10000, 1000] for _ in public.BARRIOS]},
            {"filtros": {"sexo": "F", "edad": "26_35", "acreedor": "entidad_financiera"},
             "datos": [[2.0, 0.2, 2000, 200] for _ in public.BARRIOS]},
        ],
    }


def manifest_fixture(periods=("2020-01", "2020-02")):
    return {"schema": public.MANIFEST_SCHEMA, "actualizado_utc": STAMP,
            "ultimo_periodo": periods[-1], "periodos": list(periods),
            "archivos": {p: f"{p}.json" for p in periods}, "fuente": public.SOURCE}


class PublicSchemaTests(unittest.TestCase):
    def assert_bad_period(self, value):
        with self.assertRaises(public.ValidationError):
            public.validate_period(value, "2020-02")

    def assert_bad_manifest(self, value):
        with self.assertRaises(public.ValidationError):
            public.validate_manifest(value)

    def test_synthetic_current_contract(self):
        self.assertEqual(public.validate_manifest(manifest_fixture()), manifest_fixture())
        self.assertEqual(public.validate_period(period_fixture(), "2020-02"), period_fixture())

    def test_rejects_subgroups_above_each_barrio_total(self):
        for metric, extra in enumerate((10, 1, 10000, 1000)):
            with self.subTest(metric=metric):
                obj = period_fixture()
                row = list(obj["segmentos"][0]["datos"][0])
                row[metric] += extra
                obj["segmentos"][1]["datos"][0] = row
                self.assert_bad_period(obj)

    def test_barrio_order_is_preserved_not_reinterpreted(self):
        obj = period_fixture()
        obj["barrios"].reverse()
        public.validate_period(obj, "2020-02")

    def test_rejects_extra_personal_fields_at_every_object_level(self):
        paths = [(), ("fuente",), ("filtros",), ("metodologia",), ("metodologia", "soporte_cp4"),
                 ("caba",), ("caba", "total"), ("caba", "base_territorial_cp4"),
                 ("caba", "base_barrial_con_soporte"), ("caba", "cobertura_mapa_sobre_caba"),
                 ("caba", "cobertura_territorial_cp4_sobre_caba"),
                 ("segmentos", 0), ("segmentos", 0, "filtros")]
        for path in paths:
            for field in ("cuit", "dni", "nombre", "domicilio", "email", "registros", "filas"):
                with self.subTest(path=path, field=field):
                    obj = period_fixture()
                    target = obj
                    for key in path:
                        target = target[key]
                    target[field] = "dato privado ficticio"
                    self.assert_bad_period(obj)

    def test_rejects_manifest_unknown_fields(self):
        for field in ("cuit", "personas", "matriz", "download_url"):
            obj = manifest_fixture()
            obj[field] = "dato ficticio"
            self.assert_bad_manifest(obj)

    def test_rejects_missing_fields_instead_of_defaulting(self):
        for key in period_fixture():
            obj = period_fixture()
            del obj[key]
            self.assert_bad_period(obj)
        for key in manifest_fixture():
            obj = manifest_fixture()
            del obj[key]
            self.assert_bad_manifest(obj)

    def test_rejects_wrong_container_types(self):
        for replacement in (None, [], "dato", 1, True):
            self.assert_bad_period(replacement)
            self.assert_bad_manifest(replacement)
        for key in ("fuente", "caba", "filtros", "metodologia", "barrios", "segmentos", "metricas_segmento"):
            for replacement in (None, {}, "dato", True):
                obj = period_fixture()
                obj[key] = replacement
                self.assert_bad_period(obj)

    def test_rejects_manifest_period_ambiguity(self):
        for periods in ([], ["2020-02", "2020-01"], ["2020-02", "2020-02"],
                        ["2020-13"], ["0000-01"], ["2020-1"], ["２０２０-01"], [None], [{}]):
            obj = manifest_fixture()
            obj["periodos"] = periods
            self.assert_bad_manifest(obj)
        obj = manifest_fixture()
        obj["ultimo_periodo"] = "2020-01"
        self.assert_bad_manifest(obj)

    def test_rejects_external_traversal_and_non_aggregate_paths(self):
        for filename in ("../2020-02.json", "/tmp/2020-02.json", "a/2020-02.json", "./2020-02.json",
                         "2020-02.json/", "2020-02.json\x00", "2020-02.JSON", "2020-01.json",
                         "matriz_cp_barrio.json", "diagnostico_endeudamiento_productivo.json",
                         "https://example.invalid/2020-02.json", "..\\2020-02.json", ["2020-02.json"]):
            obj = manifest_fixture()
            obj["archivos"]["2020-02"] = filename
            self.assert_bad_manifest(obj)
        obj = manifest_fixture()
        obj["archivos"]["2020-03"] = "2020-03.json"
        self.assert_bad_manifest(obj)

    def test_rejects_metadata_payloads_and_invalid_dates(self):
        for key, value in (("schema", "otro"), ("periodo", "2020-01"), ("titulo", "dato privado ficticio"),
                           ("padron_fecha", None), ("padron_fecha", "2020-02-30"),
                           ("padron_fecha", "2020-02-01 dato ficticio"),
                           ("generado_utc", "2020-03-01T10:00:00"),
                           ("generado_utc", "2020-03-01T10:00:00-03:00"),
                           ("generado_utc", "2020-13-01T10:00:00+00:00")):
            obj = period_fixture()
            obj[key] = value
            self.assert_bad_period(obj)
        for key in public.SOURCE_FIELDS:
            obj = period_fixture()
            obj["fuente"][key] = "texto libre no admitido"
            self.assert_bad_period(obj)
        for key in public.METHOD_FIXED:
            obj = period_fixture()
            obj["metodologia"][key] = "texto libre no admitido"
            self.assert_bad_period(obj)

    def test_rejects_invalid_matrix_metadata_without_reading_matrix(self):
        for key, value in (("matriz_periodo_calibracion", "2021-01"), ("matriz_periodo_calibracion", "cp4"),
                           ("matriz_estado_validacion", "PENDIENTE"), ("matriz_estado_validacion", "VALIDADA_CANDIDATA")):
            obj = period_fixture()
            obj["metodologia"][key] = value
            self.assert_bad_period(obj)
        for key, value in (("cp4_matriz", 301), ("cp4_con_soporte", 249),
                           ("cp4_sin_soporte", -1), ("cp4_con_soporte", True), ("cp4_matriz", 300.0)):
            obj = period_fixture()
            obj["metodologia"]["soporte_cp4"][key] = value
            self.assert_bad_period(obj)

    def test_rejects_barrio_duplication_missing_and_personal_names(self):
        for barrios in (list(public.BARRIOS[:-1]), list(public.BARRIOS) + [public.BARRIOS[0]],
                        list(public.BARRIOS[:-1]) + [public.BARRIOS[0]],
                        list(public.BARRIOS[:-1]) + ["Persona ficticia"],
                        list(public.BARRIOS[:-1]) + [None]):
            obj = period_fixture()
            obj["barrios"] = barrios
            self.assert_bad_period(obj)

    def test_rejects_unknown_filters_metrics_and_order(self):
        for key in ("sexos", "edades", "acreedores"):
            obj = period_fixture()
            obj["filtros"][key].append("dato ficticio")
            self.assert_bad_period(obj)
        obj = period_fixture()
        obj["metricas_segmento"].reverse()
        self.assert_bad_period(obj)
        for key in ("sexo", "edad", "acreedor"):
            for value in ("desconocido", 123, {}, [], True):
                obj = period_fixture()
                obj["segmentos"][1]["filtros"][key] = value
                self.assert_bad_period(obj)

    def test_rejects_empty_duplicate_and_missing_total_segments(self):
        for segments in ([], {}, [period_fixture()["segmentos"][1]],
                         [period_fixture()["segmentos"][0]] * 2,
                         [period_fixture()["segmentos"][0]] * 109):
            obj = period_fixture()
            obj["segmentos"] = segments
            self.assert_bad_period(obj)

    def test_rejects_missing_extra_object_and_string_rows(self):
        for rows in ([], [[1, 1, 1, 1]] * 47, [[1, 1, 1, 1]] * 49,
                     [[1, 1, 1]] * 48, [[1, 1, 1, 1, 123]] * 48,
                     [{"cuit": "ficticio"}] * 48, ["1,1,1,1"] * 48, None):
            obj = period_fixture()
            obj["segmentos"][0]["datos"] = rows
            self.assert_bad_period(obj)

    def test_rejects_non_numeric_non_finite_negative_and_boolean_values(self):
        for value in ("1", None, True, False, {}, [], float("nan"), float("inf"), float("-inf"), -0.1, 10 ** 1000):
            for index in range(4):
                obj = period_fixture()
                obj["segmentos"][1]["datos"][0][index] = value
                self.assert_bad_period(obj)
            obj = period_fixture()
            obj["caba"]["total"]["deudores"] = value
            self.assert_bad_period(obj)

    def test_rejects_inconsistent_aggregates(self):
        for path, value in ((("caba", "total", "incidencia_mora_pct"), 11),
                            (("caba", "total", "registros_incluidos"), 1000.1),
                            (("caba", "total", "personas_mora"), 501),
                            (("caba", "cobertura_mapa_sobre_caba", "deudores_pct"), 96.5),
                            (("caba", "cobertura_territorial_cp4_sobre_caba", "deudores_pct"), 101),
                            (("segmentos", 0, "datos", 0, 0), 20),
                            (("segmentos", 0, "datos", 0, 2), 11000),
                            (("segmentos", 1, "datos", 0, 1), 3),
                            (("segmentos", 1, "datos", 0, 3), 2001)):
            obj = period_fixture()
            target = obj
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            self.assert_bad_period(obj)

    def test_rejects_overflow_of_finite_rows(self):
        obj = period_fixture()
        for row in obj["segmentos"][0]["datos"]:
            row[2] = 1e308
        self.assert_bad_period(obj)

    def test_all_documented_filter_combinations_are_supported(self):
        obj = period_fixture()
        total = obj["segmentos"][0]
        obj["segmentos"] = [total]
        for creditor in (None, *public.CREDITORS):
            for sex in (None, *public.SEXES):
                for age in (None, *public.AGES):
                    if (sex, age, creditor) == (None, None, None):
                        continue
                    obj["segmentos"].append({"filtros": {"sexo": sex, "edad": age, "acreedor": creditor},
                                             "datos": [[0, 0, 0, 0] for _ in public.BARRIOS]})
        self.assertEqual(len(obj["segmentos"]), 108)
        public.validate_period(obj, "2020-02")


class PublicFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cepoes-public-debt-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / public.PUBLIC_DIR
        self.directory.mkdir(parents=True)
        self.write("manifest.json", manifest_fixture())
        for period in ("2020-01", "2020-02"):
            self.write(f"{period}.json", period_fixture(period))

    def write(self, filename, obj):
        (self.directory / filename).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def check(self):
        return public.validate_public_aggregates(self.root)

    def assert_rejected(self):
        with self.assertRaises(public.ValidationError):
            self.check()

    def test_reads_exact_referenced_files_and_returns_explicit_staging(self):
        # Estos archivos deliberadamente inválidos no pueden ser abiertos ni copiados.
        for filename in ("matriz_cp_barrio.json", "diagnostico_endeudamiento_productivo.json", "1999-01.json"):
            (self.directory / filename).write_text("ESTE ARCHIVO NO SE DEBE LEER")
        with patch.object(public, "_read_json", wraps=public._read_json) as reader:
            result = self.check()
        self.assertEqual([call.args[1] for call in reader.call_args_list],
                         ["manifest.json", "2020-01.json", "2020-02.json"])
        self.assertEqual(result["staging_paths"], ["datos/endeudamiento/manifest.json", "datos/endeudamiento/2020-02.json"])
        self.assertEqual(result["latest"], period_fixture())

    def test_old_referenced_period_is_also_validated(self):
        obj = period_fixture("2020-01")
        obj["dni"] = "dato ficticio"
        self.write("2020-01.json", obj)
        self.assert_rejected()

    def test_missing_period_file_fails_closed(self):
        (self.directory / "2020-01.json").unlink()
        self.assert_rejected()

    def test_filename_period_mismatch(self):
        self.write("2020-01.json", period_fixture("2020-02"))
        self.assert_rejected()

    def test_timestamp_mismatch(self):
        obj = manifest_fixture()
        obj["actualizado_utc"] = "2020-03-01T13:00:00+00:00"
        self.write("manifest.json", obj)
        self.assert_rejected()

    def test_manifest_symlink_rejected(self):
        source = self.directory / "manifest.json"
        real = self.root / "manifest-real.json"
        source.rename(real)
        source.symlink_to(real)
        self.assert_rejected()

    def test_month_symlink_rejected_even_within_public_directory(self):
        path = self.directory / "2020-02.json"
        path.unlink()
        path.symlink_to("2020-01.json")
        self.assert_rejected()

    def test_public_directory_symlink_rejected(self):
        target = self.root / "real-public"
        self.directory.rename(target)
        self.directory.symlink_to(target, target_is_directory=True)
        self.assert_rejected()

    def test_ancestor_and_root_symlinks_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(public.ValidationError):
            public.validate_public_aggregates(alias)
        with self.assertRaises(public.ValidationError):
            public.validate_public_aggregates(alias / "alias")

    def test_root_traversal_rejected(self):
        with self.assertRaises(public.ValidationError):
            public.validate_public_aggregates(self.root / "a" / "..")

    def test_non_regular_file_rejected_without_waiting(self):
        path = self.directory / "2020-02.json"
        path.unlink()
        os.mkfifo(path)
        self.assert_rejected()

    def test_directory_instead_of_json_rejected(self):
        path = self.directory / "2020-02.json"
        path.unlink()
        path.mkdir()
        self.assert_rejected()

    def test_duplicate_json_keys_rejected_at_every_level(self):
        path = self.directory / "2020-02.json"
        base = json.dumps(period_fixture())
        for original, replacement in (("\"periodo\": \"2020-02\"", "\"periodo\": \"2020-01\", \"periodo\": \"2020-02\""),
                                      ("\"sexo\": null", "\"sexo\": \"F\", \"sexo\": null"),
                                      ("\"deudores\": 500", "\"deudores\": 1, \"deudores\": 500")):
            path.write_text(base.replace(original, replacement, 1))
            self.assert_rejected()
        self.write("2020-02.json", period_fixture())
        path = self.directory / "manifest.json"
        path.write_text(json.dumps(manifest_fixture()).replace("\"2020-02\": \"2020-02.json\"",
                                                             "\"2020-02\": \"otro.json\", \"2020-02\": \"2020-02.json\""))
        self.assert_rejected()

    def test_non_json_encodings_and_non_finite_json_rejected(self):
        path = self.directory / "2020-02.json"
        base = json.dumps(period_fixture())
        for contents in (b"\xff", b"{} trailing", b"[", b"null", b"[]",
                         base.replace("500000", "NaN").encode(),
                         base.replace("500000", "Infinity").encode(),
                         base.replace("500000", "1e9999").encode(),
                         b"[" * 2000 + b"]" * 2000):
            path.write_bytes(contents)
            self.assert_rejected()

    def test_oversized_aggregate_rejected(self):
        (self.directory / "2020-02.json").write_bytes(b" " * (2 * 1024 * 1024 + 1))
        self.assert_rejected()

    def test_cli_staging_paths_are_only_two_paths_after_success(self):
        for option in ("--staging-paths", "--print-paths"):
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = public.main(["--root", str(self.root), option])
            self.assertEqual(status, 0)
            self.assertEqual(output.getvalue(), "datos/endeudamiento/manifest.json\ndatos/endeudamiento/2020-02.json\n")
            self.assertEqual(errors.getvalue(), "")

    def test_cli_failure_has_no_staging_output_or_private_payload_in_error(self):
        obj = period_fixture("2020-01")
        obj["NO MOSTRAR DATO FICTICIO"] = "NO MOSTRAR VALOR FICTICIO"
        self.write("2020-01.json", obj)
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = public.main(["--root", str(self.root), "--staging-paths"])
        self.assertEqual(status, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn("FICTICIO", errors.getvalue())

    def test_cli_runs_as_script_with_success_and_nonzero_failure(self):
        command = [sys.executable, "-B", str(Path(public.__file__)), "--root", str(self.root), "--staging-paths"]
        process = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(len(process.stdout.splitlines()), 2)
        (self.directory / "2020-02.json").unlink()
        process = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(process.stdout, "")


if __name__ == "__main__":
    unittest.main()
