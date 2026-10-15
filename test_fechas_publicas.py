"""Regression: a dataset's processing timestamp is not an editorial update."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("public_site", Path(__file__).parent / "deploy/preparar_sitio_publico.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicDatesTests(unittest.TestCase):
    def test_processing_date_does_not_change_indicator_period(self):
        source = ('<span>Última actualización: <b id="data-date">13 de octubre de 2026</b></span>'
                  '<p>IPC: septiembre de 2026. Fuente actualizada el 10/10/2026.</p>')
        result = module.normalize_data_timestamp(source, "/observatorio/precios/index.html")
        self.assertIn('Base procesada:', result)
        self.assertIn('13 de octubre de 2026', result)
        self.assertIn('IPC: septiembre de 2026. Fuente actualizada el 10/10/2026.', result)
        self.assertIn('data-date-role="processing"', result)
        self.assertEqual(result, module.normalize_data_timestamp(result, "/observatorio/precios/index.html"))

    def test_shared_processing_day_is_valid_for_different_periods(self):
        for path, period in [("/observatorio/trabajo/index.html", "II trimestre de 2026"),
                             ("/territorio/comuna-4/index.html", "Censo 2022")]:
            source = f'<span>Última actualización: <b id="data-date">13/10/2026</b></span><p>{period}</p>'
            result = module.normalize_data_timestamp(source, path)
            self.assertIn(period, result)
            self.assertIn('13/10/2026', result)
            self.assertNotIn('Última actualización:', result)

    def test_editorial_and_source_dates_are_preserved(self):
        publication = ('<meta property="article:published_time" content="2026-10-01">'
                       '<meta property="article:modified_time" content="2026-10-02">'
                       '<span>Última actualización: <b id="data-date">2/10/2026</b></span>')
        self.assertEqual(publication, module.normalize_data_timestamp(publication, "/publicaciones/informe/index.html"))
        source_note = '<p>Última actualización: agosto de 2025, según el RNTR.</p>'
        self.assertEqual(source_note, module.normalize_data_timestamp(source_note, "/territorio/tierras-y-soberania/index.html"))

    def test_html_entities_and_attribute_order(self):
        source = "<span>Última actualizaci&oacute;n: <time class='stamp' id='data-date'>13/10/2026</time></span>"
        result = module.normalize_data_timestamp(source, "/presupuesto/index.html")
        self.assertIn('Base procesada:', result)
        self.assertIn("class='stamp' id='data-date'", result)


if __name__ == '__main__':
    unittest.main()
