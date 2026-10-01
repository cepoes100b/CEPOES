import json
import tempfile
import unittest
from pathlib import Path
from generar_lo_nuevo import generate


TEMPLATE = '''<aside class="new-summary">Viejo</aside><label>Tema<select id="new-topic"></select></label><select id="new-type"></select><div class="new-list" id="new-list"></div><div class="new-empty"></div>'''


class NovedadesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = Path(self.tmp.name) / 'site'
        self.old = Path(self.tmp.name) / 'old'
        self.write(self.site, 'lo-nuevo/index.html', TEMPLATE)

    def write(self, root, path, text):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding='utf-8')

    def page(self, text='Contenido', extra=''):
        return f'<head><meta name="description" content="Descripción">{extra}</head><main><h1>Una nota</h1><p>{text}</p></main>'

    def test_new_page_and_escaping(self):
        self.write(self.site, 'publicaciones/notas/nueva/index.html', self.page('Dato', '<meta name="robots" content="index">'))
        entries = generate(self.site, self.old, '2026-09-29')
        self.assertEqual(entries[0]['event'], 'Nuevo')
        self.assertEqual(entries[0]['date'], '2026-09-29')
        self.assertEqual(entries[0]['type'], 'analisis')
        self.assertIn(entries[0]['url'], (self.site / 'lo-nuevo/index.html').read_text())

    def test_unchanged_deployment_keeps_date(self):
        path = 'territorio/monitor/index.html'
        self.write(self.site, path, self.page())
        entries = generate(self.site, self.old, '2026-09-29')
        self.write(self.old, path, self.page(extra='<link href="estilo.css?v=8">'))
        self.write(self.old, 'assets/data/lo-nuevo.json', json.dumps({'entries': entries}))
        again = generate(self.site, self.old, '2026-09-30')
        self.assertEqual(again[0]['date'], '2026-09-29')

    def test_changed_data_updates_page_but_processing_date_does_not(self):
        path = 'territorio/monitor/index.html'
        page = self.page(extra='<script src="/assets/monitor.js?v=1"></script>')
        for root, value, date in [(self.site, 12, '2026-09-29'), (self.old, 10, '2026-09-28')]:
            self.write(root, path, page)
            self.write(root, 'assets/monitor.js', 'fetch("/assets/data/monitor.json")')
            self.write(root, 'assets/data/monitor.json', json.dumps({'total': value, 'generated_at': date}))
        entries = generate(self.site, self.old, '2026-09-29')
        self.assertEqual(entries[0]['event'], 'Actualizado')
        self.write(self.old, 'assets/data/lo-nuevo.json', json.dumps({'entries': entries}))
        self.write(self.old, 'assets/data/monitor.json', json.dumps({'total': 12, 'generated_at': '2026-09-28'}))
        again = generate(self.site, self.old, '2026-09-30')
        self.assertEqual(again[0]['date'], '2026-09-29')

    def test_private_noindex_and_removed_pages_excluded(self):
        self.write(self.site, 'privado/index.html', self.page())
        self.write(self.site, 'publicaciones/borradores/prueba/index.html', self.page())
        self.write(self.site, 'publicaciones/notas/oculta/index.html', self.page(extra='<meta name="robots" content="noindex">'))
        self.write(self.old, 'assets/data/lo-nuevo.json', json.dumps({'entries': [{'url': '/prensa/eliminada/', 'date': '2026-09-29', 'title': 'Eliminada'}]}))
        self.assertEqual(generate(self.site, self.old, '2026-09-29'), [])

    def test_existing_publication_with_declared_date(self):
        page = self.page(extra='<script type="application/ld+json">{"datePublished":"2026-09-26"}</script>')
        for root in (self.site, self.old):
            self.write(root, 'publicaciones/notas/nota/index.html', page)
        entry = generate(self.site, self.old, '2026-09-29')[0]
        self.assertEqual(entry['date'], '2026-09-26')
        self.assertEqual(entry['event'], 'Publicado')


    def test_legacy_route_is_emitted_as_canonical(self):
        self.write(self.site, 'territorio/presupuesto/index.html', self.page())
        entries = generate(self.site, self.old, '2026-09-29')
        rendered = (self.site / 'lo-nuevo/index.html').read_text(encoding='utf-8')
        self.assertEqual(entries[0]['url'], '/presupuesto/territorio/')
        self.assertIn('href="/presupuesto/territorio/"', rendered)
        self.assertNotIn('href="/territorio/presupuesto/"', rendered)

if __name__ == '__main__':
    unittest.main()

