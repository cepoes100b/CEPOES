import json
import tempfile
import unittest
from pathlib import Path

from generar_catalogo_informes import generate


class CatalogoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.registry = self.root / 'reports.json'
        self.reports = []
        self.write('publicaciones/informes/index.html', '<main><article class="report-row">Anterior</article></main>')
        self.write('publicaciones/index.html', '<main><article class="report-feature" data-publications-latest-report>Anterior</article></main>')

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def add(self, slug, period='2026-09', folder='publicaciones/informes'):
        url = f'/{folder}/{slug}/'
        report = dict(url=url, title=slug, description='Análisis & datos', kind='Informe', period=period,
                      cover='/assets/tapa.svg', pdf=f'{url}informe.pdf')
        self.reports.append(report)
        self.write(f'{folder}/{slug}/index.html', '<main class="web-report"><h1>Informe</h1><a download href="informe.pdf">Descargar informe completo</a></main>')
        self.write(f'{folder}/{slug}/informe.pdf', '%PDF-1.4')
        self.write('assets/tapa.svg', '<svg/>')
        return report

    def build(self):
        self.registry.write_text(json.dumps({'version': 1, 'reports': self.reports}))
        return generate(self.root, self.registry)

    def test_full_archive_latest_five_and_idempotence(self):
        for i in range(7):
            self.add(str(i), f'2026-09-{i+1:02d}')
        reports = self.build()
        archive = (self.root / 'publicaciones/informes/index.html').read_text()
        landing = (self.root / 'publicaciones/index.html').read_text()
        self.assertEqual(archive.count('<article'), 7)
        self.assertEqual(landing.count('<article'), 5)
        self.assertEqual(reports[0]['title'], '6')
        self.assertNotIn('/informes/0/', landing)
        self.assertIn('Análisis &amp; datos', archive)
        self.build()
        self.assertEqual(archive, (self.root / 'publicaciones/informes/index.html').read_text())
        self.assertEqual(landing, (self.root / 'publicaciones/index.html').read_text())

    def test_missing_new_report_blocks_publication(self):
        self.add('registrado')
        self.add('olvidado')
        self.reports.pop()
        with self.assertRaisesRegex(AssertionError, 'Informe fuera del catálogo'):
            self.build()

    def test_monitor_with_report_is_required_and_linked(self):
        report = self.add('tierras', folder='territorio')
        self.write('territorio/tierras/index.html', '<main><h1>Monitor</h1><a href="informe.pdf">Descargar informe completo en PDF</a></main>')
        self.build()
        self.assertIn(report['url'], (self.root / 'publicaciones/informes/index.html').read_text())
        self.add('otro-monitor', folder='territorio')
        self.reports.pop()
        with self.assertRaisesRegex(AssertionError, 'fuera del catálogo'):
            self.build()

    def test_duplicate_private_missing_pdf_and_cover_fail(self):
        report = self.add('uno')
        self.reports.append(report)
        with self.assertRaisesRegex(AssertionError, 'duplicado'):
            self.build()
        self.reports.pop()
        path = self.root / 'publicaciones/informes/uno/index.html'
        original = path.read_text()
        path.write_text('<meta name="robots" content="noindex">' + original)
        with self.assertRaisesRegex(AssertionError, 'privado'):
            self.build()
        path.write_text(original)
        (self.root / 'assets/tapa.svg').unlink()
        with self.assertRaisesRegex(AssertionError, 'Falta cover'):
            self.build()
        self.write('assets/tapa.svg', '<svg/>')
        (self.root / report['pdf'].lstrip('/')).unlink()
        with self.assertRaisesRegex(AssertionError, 'Falta pdf'):
            self.build()

    def test_unpublished_draft_does_not_enter_archive(self):
        self.add('publicado')
        self.write('publicaciones/informes/borrador/index.html', '<meta name="robots" content="noindex"><main class="web-report"><h1>Borrador</h1></main>')
        self.write('privado/informes/otro/index.html', '<main class="web-report"><h1>Privado</h1></main>')
        self.assertEqual(len(self.build()), 1)

    def test_web_monitor_is_listed_without_inventing_pdf_or_cover(self):
        url = '/territorio/seguridad/'
        self.reports.append(dict(url=url, title='Seguridad y derechos', description='Seguimiento territorial',
                                 kind='Informe y monitor', period='2026-10-01', format='web'))
        self.write('territorio/seguridad/index.html', '<meta name="cepoes:publication" content="report"><main><h1>Seguridad y derechos</h1></main>')
        self.build()
        for path in ('publicaciones/informes/index.html', 'publicaciones/index.html'):
            rendered = (self.root / path).read_text()
            self.assertIn(f'href="{url}"', rendered)
            self.assertIn('Ver informe y monitor', rendered)
            self.assertNotIn('download', rendered)
            self.assertNotIn('<img', rendered)

    def test_web_report_requires_registry_and_explicit_source_marker(self):
        self.add('registrado')
        self.write('territorio/seguridad/index.html', '<meta name="cepoes:publication" content="report"><main><h1>Seguridad</h1></main>')
        with self.assertRaisesRegex(AssertionError, 'fuera del catálogo'):
            self.build()
        self.reports.append(dict(url='/territorio/seguridad/', title='Seguridad', description='Seguimiento',
                                 kind='Informe y monitor', period='2026-10-01', format='web'))
        self.write('territorio/seguridad/index.html', '<main><h1>Seguridad</h1></main>')
        with self.assertRaisesRegex(AssertionError, 'Falta declarar'):
            self.build()


if __name__ == '__main__':
    unittest.main()
