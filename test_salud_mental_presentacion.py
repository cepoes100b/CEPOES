"""Regresión del recurso publicado; no modifica ni descarga datos."""
import re
import tempfile
import unittest
from pathlib import Path

from deploy.preparar_sitio_publico import normalize_html

ROOT = Path(__file__).resolve().parent
OVERLAY = ROOT / 'deploy/site-overlay'


class MentalHealthPresentationTests(unittest.TestCase):
    def test_version_survives_normalizer_and_matches_deployment_validator(self):
        for relative in ['observatorio/salud-mental/index.html',
                         'publicaciones/notas/prevenir-es-garantizar-ayuda-a-tiempo/index.html']:
            original = (OVERLAY / relative).read_text()
            expected = '/assets/salud-mental.css?v=3'
            self.assertIn(expected, original)
            with tempfile.TemporaryDirectory() as tmp:
                site = Path(tmp)
                page = site / relative
                page.parent.mkdir(parents=True)
                for incoming in ['', '?v=1', '?v=2', '?v=3']:
                    with self.subTest(page=relative, incoming=incoming):
                        page.write_text(original.replace(expected, '/assets/salud-mental.css' + incoming))
                        for _ in range(2):
                            normalize_html(page, site)
                            refs = re.findall(r'/assets/salud-mental\.css[^"\'<>\s]*', page.read_text())
                            self.assertEqual(refs, [expected])
            self.assertIn(repr(expected), (ROOT / 'validar_sitio_despliegue.py').read_text())

    def test_fill_has_a_block_box(self):
        css = (OVERLAY / 'assets/salud-mental.css').read_text()
        fill = re.search(r'\.sm-jur-fill\{([^}]+)\}', css)[1]
        self.assertIn('display:block;', fill)
        self.assertIn('height:100%;', fill)


if __name__ == '__main__':
    unittest.main()
