"""Pruebas offline del transporte; las muestras sintéticas nunca se publican."""
import contextlib
import csv
import http.client
import io
import json
import os
import runpy
import ssl
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import actualizar_salud_mental as sm


ROOT = Path(__file__).resolve().parent
DEIS_CSV = "https://datos.salud.gob.ar/dataset/test-defunciones-2005-2024.csv"


def csv_bytes(fields, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fields)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def source_fixtures():
    """Sólo infraestructura: formato y checkpoints ya exigidos por el productor."""
    fields = ["anio", "codigo_delito_snic_id", "cantidad_victimas", "tasa_victimas"]
    national = [
        dict(zip(fields, [year, "31", count, 11.84]))
        for year, count in sm.EXPECTED_ARG.items()
    ]
    prov_fields = fields + ["provincia_id", "provincia_nombre"]
    provinces = [
        dict(zip(prov_fields, [year, "31", 171, 7.97, "02", "CABA"]))
        for year in range(2016, 2025)
    ]
    provinces += [
        dict(zip(prov_fields, [2025, "31", 236, 7.97, "02", "CABA"])),
        dict(zip(prov_fields, [2025, "31", 4973, 1.0, "06", "Buenos Aires"])),
    ]
    provinces += [
        dict(zip(prov_fields, [2025, "31", 0, 0, f"test-{i}", f"Jurisdicción de prueba {i}"]))
        for i in range(22)
    ]
    return {
        sm.SNIC_PAIS_URL: csv_bytes(fields, national),
        sm.SNIC_PROVINCIAS_URL: csv_bytes(prov_fields, provinces),
        sm.DEIS_CKAN: json.dumps({
            "success": True,
            "result": {"resources": [{
                "name": "Defunciones 2005-2024", "format": "CSV", "url": DEIS_CSV,
            }]},
        }).encode(),
        DEIS_CSV: b"anio,causa,cantidad\n2005,X60,1\n2023,X60,3488\n2024,X60,3614\n",
    }


class TransportTests(unittest.TestCase):
    def setUp(self):
        # Defensa adicional: una regresión nunca debe convertir estos tests en una descarga.
        self.no_network = patch("socket.socket.connect", side_effect=AssertionError("Test offline"))
        self.no_network.start()
        self.addCleanup(self.no_network.stop)

    def test_success_requires_certificate_and_hostname(self):
        opener = MagicMock()
        opener.open.return_value = io.BytesIO(b"respuesta verificada")
        with patch.object(sm.urllib.request, "build_opener", return_value=opener) as factory:
            self.assertEqual(sm.request_bytes(sm.DEIS_CKAN, 60), b"respuesta verificada")
        handlers = factory.call_args.args
        https = next(h for h in handlers if isinstance(h, urllib.request.HTTPSHandler))
        self.assertEqual(https._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(https._context.check_hostname)
        self.assertTrue(any(isinstance(h, sm.HTTPSOnlyRedirectHandler) for h in handlers))
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(opener.open.call_args.kwargs, {"timeout": 60})

    def test_certificate_and_transport_failures_never_retry(self):
        errors = [
            urllib.error.URLError(ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED")),
            ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED"),
            urllib.error.URLError("connection failed"),
            TimeoutError("read timed out"),
            OSError("connection reset"),
            http.client.IncompleteRead(b"parcial", 100),
            urllib.error.HTTPError(sm.DEIS_CKAN, 503, "Service unavailable", {}, None),
        ]
        for url in (sm.DEIS_CKAN, sm.SNIC_PAIS_URL, "https://otro.salud.gob.ar/archivo.csv"):
            for error in errors:
                with self.subTest(url=url, error=type(error).__name__):
                    opener = MagicMock()
                    opener.open.side_effect = error
                    with patch.object(sm.urllib.request, "build_opener", return_value=opener):
                        with self.assertRaisesRegex(sm.SourceDownloadError, "Fuente no verificable"):
                            sm.request_bytes(url)
                    self.assertEqual(opener.open.call_count, 1)

    def test_read_failure_is_explicit(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = TimeoutError("read timed out")
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(sm.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(sm.SourceDownloadError):
                sm.request_bytes(sm.DEIS_CKAN)
        self.assertEqual(opener.open.call_count, 1)

    def test_insecure_source_is_rejected_before_network(self):
        with patch.object(sm.urllib.request, "build_opener") as factory:
            for url in ("http://datos.salud.gob.ar/archivo.csv", "file:///tmp/archivo.csv", "ftp://datos.salud.gob.ar/archivo.csv"):
                with self.subTest(url=url), self.assertRaises(sm.SourceDownloadError):
                    sm.request_bytes(url)
        factory.assert_not_called()

    def test_redirect_cannot_downgrade_to_http(self):
        handler = sm.HTTPSOnlyRedirectHandler()
        req = urllib.request.Request(sm.DEIS_CKAN)
        with self.assertRaises(sm.SourceDownloadError):
            handler.redirect_request(req, None, 302, "Found", {}, "http://datos.salud.gob.ar/archivo.csv")
        redirected = handler.redirect_request(req, None, 302, "Found", {}, DEIS_CSV)
        self.assertEqual(redirected.full_url, DEIS_CSV)

    def test_workflow_uses_direct_generator_without_tls_override(self):
        workflow = (ROOT / ".github/workflows/salud-mental.yml").read_text()
        self.assertIn("run: python actualizar_salud_mental.py", workflow)
        self.assertIn("run: python -m unittest test_salud_mental_tls.py", workflow)
        self.assertIn("run: python verificar_salud_mental.py", workflow)
        self.assertNotIn("_create_unverified_context", workflow)
        self.assertNotIn("urllib.request.urlopen =", workflow)
        source = (ROOT / "actualizar_salud_mental.py").read_text()
        self.assertNotIn("_create_unverified_context", source)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out_root = self.root / "salud_mental.json"
        self.out_public = self.root / "public/salud-mental.json"
        self.out_public.parent.mkdir()
        self.previous = {
            "schema": "cepoes-salud-mental-v3",
            "contraste_deis": {
                "estado": "ULTIMO_DATO_VALIDADO",
                "serie_nacional": [{"anio": 2023, "defunciones": 3488}, {"anio": 2024, "defunciones": 3614}],
            },
        }
        self.out_root.write_text(json.dumps(self.previous, indent=2))
        self.out_public.write_text(json.dumps(self.previous, separators=(",", ":")))
        self.original_root = self.out_root.read_bytes()
        self.original_public = self.out_public.read_bytes()
        self.cesac = self.root / "cesac.csv"
        self.cesac.write_bytes(csv_bytes(["id", "nombre", "especialidades"], [
            {"id": str(i), "nombre": f"Centro de prueba {i}", "especialidades": "Psicología"}
            for i in range(43)
        ]))
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in [("OUT_ROOT", self.out_root), ("OUT_PUBLIC", self.out_public), ("CESAC_CSV", self.cesac)]:
            self.stack.enter_context(patch.object(sm, name, value))
        self.stack.enter_context(patch("socket.socket.connect", side_effect=AssertionError("Test offline")))

    def run_pipeline(self, failed_url=None, error=None):
        payloads = source_fixtures()
        calls = []

        def open_request(req, timeout):
            calls.append(req.full_url)
            if req.full_url == failed_url:
                raise error
            return io.BytesIO(payloads[req.full_url])

        opener = MagicMock()
        opener.open.side_effect = open_request
        with patch.object(sm.urllib.request, "build_opener", return_value=opener):
            with contextlib.redirect_stdout(io.StringIO()):
                sm.main()
        return calls

    def test_success_passes_existing_verifier_and_writes_same_payload(self):
        self.assertEqual(len(self.run_pipeline()), 4)
        self.assertEqual(self.out_root.read_bytes(), self.out_public.read_bytes())
        result = json.loads(self.out_root.read_text())
        self.assertEqual(result["contraste_deis"]["estado"], "ACTUALIZADO")
        before = Path.cwd()
        try:
            os.chdir(self.root)
            with contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(ROOT / "verificar_salud_mental.py"), run_name="__main__")
        finally:
            os.chdir(before)

    def test_all_source_failures_preserve_both_files_byte_for_byte(self):
        for url in source_fixtures():
            for error in (
                urllib.error.URLError(ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED")),
                urllib.error.URLError("connection failed"),
                TimeoutError("read timed out"),
                http.client.IncompleteRead(b"parcial", 100),
            ):
                with self.subTest(url=url, error=type(error).__name__):
                    with self.assertRaises(sm.SourceDownloadError):
                        self.run_pipeline(url, error)
                    self.assertEqual(self.out_root.read_bytes(), self.original_root)
                    self.assertEqual(self.out_public.read_bytes(), self.original_public)

    def test_tls_failure_cannot_be_absorbed_by_previous_deis_fallback(self):
        with patch.object(sm, "load_deis_national", side_effect=sm.SourceDownloadError("certificado inválido")):
            with self.assertRaises(sm.SourceDownloadError):
                sm.load_deis_with_fallback(self.previous)

    def test_existing_schema_fallback_remains_separate(self):
        with patch.object(sm, "load_deis_national", side_effect=RuntimeError("esquema cambió")):
            with contextlib.redirect_stdout(io.StringIO()):
                deis = sm.load_deis_with_fallback(self.previous)
        self.assertEqual(deis["estado"], "ULTIMO_DATO_VALIDADO")
        self.assertEqual(deis["serie_nacional"], self.previous["contraste_deis"]["serie_nacional"])
        self.assertIn("esquema cambió", deis["error_actualizacion"])


if __name__ == "__main__":
    unittest.main()
