import re
import unittest
from deploy.preparar_sitio_publico import ROOT, ensure_site_fonts


class SiteFontsTests(unittest.TestCase):
    def test_reports_load_shell_fonts_once_and_preserve_body(self):
        for route in (
            'publicaciones/informes/salud-mental-caba',
            'territorio/seguridad-barrios-populares',
            'publicaciones/notas/tormenta-negra-seguridad-territorio',
        ):
            with self.subTest(route=route):
                source = (ROOT / 'deploy/site-overlay' / route / 'index.html').read_text()
                fixed = ensure_site_fonts(source)
                self.assertIn('family=Poppins:', fixed)
                self.assertIn('family=Inter:', fixed)
                self.assertEqual(fixed, ensure_site_fonts(fixed))
                self.assertEqual(source.split('</head>', 1)[1], fixed.split('</head>', 1)[1])

    def test_existing_complete_font_links_are_preserved(self):
        source = '<head><link href="/assets/site.css?v=1" rel="stylesheet"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400&amp;family=Poppins:wght@800"></head>'
        self.assertEqual(source, ensure_site_fonts(source))

    def test_partial_fonts_and_existing_preconnect(self):
        source = '<head><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="/assets/site.css" rel="stylesheet"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@800"></head>'
        fixed = ensure_site_fonts(source)
        self.assertIn('family=Inter:', fixed)
        self.assertEqual(len(re.findall(r'href="https://fonts.gstatic.com"', fixed)), 1)
        self.assertEqual(fixed, ensure_site_fonts(fixed))

    def test_standalone_documents_are_untouched(self):
        source = '<head><link href="report.css" rel="stylesheet"></head><body>Informe</body>'
        self.assertEqual(source, ensure_site_fonts(source))


if __name__ == '__main__':
    unittest.main()
