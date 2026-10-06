"""Regresiones offline: catálogo más nuevo, conservación y marcadores dinámicos."""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import actualizar_personas_mayores as pm
from verificar_personas_mayores import validate_page


ROOT = Path(__file__).resolve().parent
CATALOGUE = (ROOT / "fixtures/defensoria_catalogo_mayores.html").read_text()
NEWS = (ROOT / "fixtures/defensoria_noticia_mayo_2026.html").read_text()


def catalogue(month="Mayo", year=2026):
    return (f'<a href="https://www.calameo.com/defensoriacaba/read/canasta">'
            f'<h2>Canasta de consumo para personas adultas mayores – {month} {year}</h2>'
            '<p>Publicado en Septiembre 2026</p></a>'
            f'<a href="https://www.calameo.com/defensoriacaba/read/ipm">'
            f'<h2>Índice de Precios de Medicamentos (IPM) – {month} {year}</h2></a>')


def source_get(library=CATALOGUE, news=NEWS):
    def get(session, url, **params):
        if url == pm.DEFENSORIA_LIBRARY:
            return SimpleNamespace(text=library)
        if url == pm.DEFENSORIA_SITEMAP:
            return SimpleNamespace(text="<sitemapindex/>")
        if url == pm.KNOWN_BASKET:
            return SimpleNamespace(text=news)
        raise AssertionError(f"Unexpected URL {url}")
    return get


class LibraryTests(unittest.TestCase):
    def test_actual_catalogue_uses_reference_month_not_september_publication(self):
        result = pm.parse_library(CATALOGUE)
        self.assertEqual({r["periodo"] for r in result.values()}, {"2026-08"})
        self.assertTrue(result["canasta"]["url"].endswith("002682399ff9e859bc7e5"))
        self.assertTrue(result["medicamentos"]["url"].endswith("002682399661470affa19"))

    def test_month_with_de_and_uppercase(self):
        result = pm.parse_library(catalogue("AGOSTO de"))
        self.assertEqual(result["canasta"]["periodo"], "2026-08")

    def test_missing_kind_fails(self):
        with self.assertRaisesRegex(pm.BasketSourceError, "medicamentos"):
            pm.parse_library(catalogue().split('<a href="https://www.calameo.com/defensoriacaba/read/ipm">')[0])

    def test_empty_or_changed_catalogue_fails(self):
        with self.assertRaises(pm.BasketSourceError):
            pm.parse_library("<h1>Monitor de Derechos</h1>")

    def test_unrecognized_external_publisher_fails(self):
        with self.assertRaisesRegex(pm.BasketSourceError, "enlace"):
            pm.parse_library(catalogue().replace("/defensoriacaba/", "/another-publisher/"))

    def test_conflicting_same_period_fails(self):
        with self.assertRaisesRegex(pm.BasketSourceError, "dos informes"):
            pm.parse_library(catalogue() + catalogue().replace("read/canasta", "read/otra"))

    def test_methodological_report_cannot_be_used_as_a_monthly_report(self):
        with self.assertRaises(pm.BasketSourceError):
            pm.parse_library('<a href="https://www.calameo.com/defensoriacaba/read/method">'
                             '<h2>Informe de actualización metodológica del Sistema de Canasta de Consumo '
                             'para Personas Adultas Mayores de la Ciudad de Buenos Aires</h2>'
                             '<p>Marzo 2026</p></a>')


class SourceFreshnessTests(unittest.TestCase):
    def test_original_may_news_is_parsed_without_replacing_its_figures(self):
        result = pm.parse_basket(NEWS, pm.KNOWN_BASKET)
        self.assertEqual((result["periodo"], result["owner"], result["renter"], result["meds"]),
                         ("2026-05", 1622654, 2835928, 2.3))

    def test_new_catalogue_blocks_old_interpretable_news(self):
        with patch.object(pm, "get", side_effect=source_get()):
            with self.assertRaisesRegex(pm.BasketSourceError, "más recientes") as caught:
                pm.latest_basket(object(), "2026-05")
        self.assertIn("canasta 2026-08", str(caught.exception))
        self.assertIn("medicamentos 2026-08", str(caught.exception))

    def test_current_catalogue_with_matching_news_is_accepted(self):
        with patch.object(pm, "get", side_effect=source_get(catalogue())):
            self.assertEqual(pm.latest_basket(object(), "2026-05")["periodo"], "2026-05")

    def test_recession_to_an_older_reference_period_fails(self):
        with patch.object(pm, "get", side_effect=source_get(catalogue())):
            with self.assertRaisesRegex(pm.BasketSourceError, "retrocedería"):
                pm.latest_basket(object(), "2026-06")

    def test_unparseable_news_fails(self):
        with patch.object(pm, "get", side_effect=source_get(catalogue(), "<p>Nuevo formato</p>")):
            with self.assertRaisesRegex(pm.BasketSourceError, "sin publicación"):
                pm.latest_basket(object())

    def test_catalogue_network_failure_is_not_ignored(self):
        with patch.object(pm, "get", side_effect=RuntimeError("503")):
            with self.assertRaisesRegex(RuntimeError, "503"):
                pm.latest_basket(object())


class AtomicityAndPageTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(pm.DATA.read_text())
        self.html = pm.PAGE.read_text()

    def test_build_keeps_input_and_propagates_source_error(self):
        previous = deepcopy(self.data)
        ages = {"anios": [2022], "poblacion_65_mas": [18.0], "poblacion_80_mas": [5.2]}
        aging = {"anios": [2022], "valores": [120.0]}
        with patch.object(pm, "get", return_value=SimpleNamespace(text="ignored")), \
             patch.object(pm, "parse_ages", return_value=ages), \
             patch.object(pm, "parse_aging", return_value=aging), \
             patch.object(pm, "latest_basket", side_effect=pm.BasketSourceError("new report")):
            with self.assertRaises(pm.BasketSourceError):
                pm.build(previous, object())
        self.assertEqual(previous, self.data)

    def test_main_returns_failure_before_writing_either_published_file(self):
        with tempfile.TemporaryDirectory() as directory:
            data_path, page_path = Path(directory)/"data.json", Path(directory)/"page.html"
            data_path.write_text(json.dumps(self.data, ensure_ascii=False))
            page_path.write_text(self.html)
            before = (data_path.read_bytes(), page_path.read_bytes())
            output = io.StringIO()
            with patch.object(pm, "DATA", data_path), patch.object(pm, "PAGE", page_path), \
                 patch.object(pm, "build", side_effect=pm.BasketSourceError("new report")), \
                 patch("sys.argv", ["actualizar_personas_mayores.py"]), contextlib.redirect_stdout(output):
                self.assertEqual(pm.main(), 1)
            self.assertEqual((data_path.read_bytes(), page_path.read_bytes()), before)
            self.assertIn("::error::", output.getvalue())
            self.assertNotIn("sin cambios validados", output.getvalue())

    def test_current_page_passes(self):
        validate_page(self.data, self.html)

    def test_updated_figures_pass_without_hardcoded_may_value(self):
        # Values are synthetic test inputs; no published data is changed.
        future = deepcopy(self.data)
        future["indicadores"]["canasta_inquilinos"]["valor"] = 2900000
        future["indicadores"]["poblacion_65_mas"]["valor"] = 17.8
        for key in ("canasta_propietarios", "canasta_inquilinos", "medicamentos"):
            future["indicadores"][key]["periodo"] = "2026-06"
        source = self.html
        for marker, value in pm.page_values(future).items():
            source = pm.replace_id(source, marker, value)
        validate_page(future, source)

    def test_stale_marker_fails_even_if_expected_value_is_elsewhere(self):
        source = pm.replace_id(self.html, "pm-renter", "$9.999.999")
        with self.assertRaisesRegex(AssertionError, "pm-renter"):
            validate_page(self.data, source)

    def test_duplicate_marker_fails(self):
        with self.assertRaisesRegex(AssertionError, "duplicado"):
            validate_page(self.data, self.html+'<span id="pm-owner">$1.622.654</span>')

    def test_matching_html_cannot_mask_wrong_unit_household_or_age_threshold(self):
        cases=[("canasta_propietarios","unidad","dólares","unidad"),
               ("medicamentos","unidad","índice base 100","unidad"),
               ("indice_envejecimiento","unidad","%","unidad"),
               ("canasta_inquilinos","hogar","una persona inquilina","hogar"),
               ("poblacion_65_mas","umbral_edad","60 años y más","umbral")]
        for key,field,value,message in cases:
            with self.subTest(key=key,field=field):
                wrong=deepcopy(self.data)
                wrong["indicadores"][key][field]=value
                with self.assertRaisesRegex(AssertionError,message):
                    validate_page(wrong,self.html)

    def test_matching_html_cannot_mask_invalid_or_mixed_periods(self):
        cases=[{"canasta_propietarios":"2026-08"},
               {"medicamentos":"2026-08"},
               {"poblacion_80_mas":"2023"},
               {key:"2026-13" for key in ("canasta_propietarios","canasta_inquilinos","medicamentos")}]
        for changes in cases:
            with self.subTest(changes=changes):
                wrong=deepcopy(self.data)
                for key,value in changes.items():wrong["indicadores"][key]["periodo"]=value
                with self.assertRaisesRegex(AssertionError,"períodos"):
                    validate_page(wrong,self.html)

    def test_render_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"page.html"
            path.write_text(self.html)
            with patch.object(pm, "PAGE", path):
                self.assertFalse(pm.render_page(self.data))
                self.assertEqual(path.read_text(), self.html)


if __name__ == "__main__":
    unittest.main()
