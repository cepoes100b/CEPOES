"""Regresión del recurso publicado; no modifica ni descarga datos."""
import re
import hashlib
import shutil
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

    def test_real_build_uses_content_hash_and_deployment_accepts_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            asset = site / 'assets/salud-mental.css'
            asset.parent.mkdir(parents=True)
            shutil.copy2(OVERLAY / 'assets/salud-mental.css', asset)
            page = site / 'observatorio/salud-mental/index.html'
            page.parent.mkdir(parents=True)
            page.write_text((OVERLAY / 'observatorio/salud-mental/index.html').read_text())
            normalize_html(page, site)
            revision = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
            first = page.read_text()
            self.assertIn('/assets/salud-mental.css?v=' + revision, first)
            normalize_html(page, site)
            self.assertEqual(first, page.read_text())
            # Execute the actual deployment assertions, including their failure
            # on stale URLs and on reintroduction of the inline-span bug.
            validator = (ROOT / 'validar_sitio_despliegue.py').read_text()
            start = validator.index('sm_css_revision=')
            end = validator.index("assert '/assets/data/salud-mental.json'", start)
            shutil.copy2(OVERLAY / 'assets/salud-mental.js', asset.with_suffix('.js'))
            checks = validator[start:end]
            context = {'root': site, 'salud_mental': first, 'hashlib': hashlib, 're': re}
            exec(checks, context)
            for stale in ['2', '3', '000000000000']:
                with self.subTest(stale=stale), self.assertRaises(AssertionError):
                    exec(checks, {**context, 'salud_mental': first.replace(revision, stale)})
            asset.write_text(asset.read_text().replace('.sm-jur-fill{display:block;', '.sm-jur-fill{', 1))
            changed = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
            with self.assertRaisesRegex(AssertionError, 'sin caja de relleno'):
                exec(checks, {**context, 'salud_mental': first.replace(revision, changed)})

    def test_fill_has_a_block_box(self):
        css = (OVERLAY / 'assets/salud-mental.css').read_text()
        fill = re.search(r'\.sm-jur-fill\{([^}]+)\}', css)[1]
        self.assertIn('display:block;', fill)
        self.assertIn('height:100%;', fill)


if __name__ == '__main__':
    unittest.main()
