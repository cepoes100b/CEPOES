import json
import tempfile
import unittest
from pathlib import Path
from generar_lo_nuevo import generate, snapshot


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

    def test_bulletin_is_visible_classified_and_keeps_date(self):
        path = 'publicaciones/boletines/boletin-05-septiembre-2026/index.html'
        self.write(self.site, path, self.page('Edición nueva'))
        entries = generate(self.site, self.old, '2026-10-01')
        self.assertEqual(entries[0]['type'], 'boletin')
        self.assertEqual(entries[0]['event'], 'Nuevo')
        page = (self.site / 'lo-nuevo/index.html').read_text()
        self.assertIn('<span>Boletín</span>', page)
        self.assertIn('<option value="boletin">Boletín</option>', page)
        self.write(self.old, path, self.page('Edición nueva', '<link href="style.css?v=2">'))
        self.write(self.old, 'assets/data/lo-nuevo.json', json.dumps({'entries': entries}))
        self.assertEqual(generate(self.site, self.old, '2026-10-02')[0]['date'], '2026-10-01')

    def test_old_bulletin_missing_from_feed_is_recovered_honestly(self):
        for root in (self.site, self.old):
            self.write(root, 'publicaciones/boletines/edicion-anterior/index.html', self.page())
        entry = generate(self.site, self.old, '2026-10-01')[0]
        self.assertEqual(entry['type'], 'boletin')
        self.assertEqual(entry['event'], 'Incorporado al archivo')

    def test_web_report_classification_preserves_content_date(self):
        path = 'territorio/seguridad/index.html'
        self.write(self.site, path, self.page())
        entries = generate(self.site, self.old, '2026-09-29')
        self.assertEqual(entries[0]['type'], 'herramienta')
        self.write(self.old, path, self.page())
        self.write(self.old, 'assets/data/lo-nuevo.json', json.dumps({'entries': entries}))
        self.write(self.site, path, self.page(extra='<meta name="cepoes:publication" content="report">'))
        entry = generate(self.site, self.old, '2026-10-01')[0]
        self.assertEqual(entry['type'], 'informe')
        self.assertEqual(entry['date'], '2026-09-29')
        self.assertEqual(entry['fingerprint'], entries[0]['fingerprint'])
        self.assertIn('<span>Informe</span>', (self.site / 'lo-nuevo/index.html').read_text())

    def test_more_than_80_updates_do_not_drop_bulletin_or_reset_history(self):
        path = 'publicaciones/boletines/anterior/index.html'
        for root in (self.site, self.old):
            self.write(root, path, self.page())
        self.write(self.old, 'assets/data/lo-nuevo.json', json.dumps({'entries': [
            {'url': '/publicaciones/boletines/anterior/', 'title': 'Edición', 'date': '2026-09-01', 'event': 'Publicado'}]}))
        for i in range(85):
            self.write(self.site, f'territorio/monitor-{i}/index.html', self.page())
        entries = generate(self.site, self.old, '2026-10-01')
        self.assertEqual(len(entries), 86)
        self.assertEqual(entries[-1]['date'], '2026-09-01')
        self.assertEqual(entries[-1]['type'], 'boletin')

    def test_search_index_changes_do_not_update_every_publication(self):
        path = 'publicaciones/notas/historica/index.html'
        page = self.page(extra='<script src="/assets/common-r1.js?v=259"></script>')
        for root, title in [(self.site, 'Nuevo artículo'), (self.old, 'Artículo anterior')]:
            self.write(root, path, page)
            self.write(root, 'assets/common-r1.js', 'fetch("/assets/data/search-index.json?v=258")')
            self.write(root, 'assets/data/search-index.json', json.dumps([{'title': title}]))
        self.assertEqual(snapshot(self.site, self.site / path)['fingerprint'],
                         snapshot(self.old, self.old / path)['fingerprint'])

    def test_shared_controls_and_processing_badges_do_not_update_content(self):
        path = 'observatorio/precios/index.html'
        for root, date, label in [(self.site, '15/10/2026', 'Base procesada:'),
                                  (self.old, '14/10/2026', 'Última actualización:')]:
            body = (f'<div class="meta-row"><span>{label} <b id="data-date">{date}</b></span></div>'
                    f'<section class="cepoes-share"><div><span>Compartir {date}</span></div></section><p>Dato: 12</p>')
            self.write(root, path, self.page(body))
        self.assertEqual(snapshot(self.site, self.site / path)['fingerprint'],
                         snapshot(self.old, self.old / path)['fingerprint'])

    def test_spanish_generation_timestamp_is_not_a_data_update(self):
        path = 'territorio/monitor/index.html'
        for root, date in [(self.site, '2026-10-15'), (self.old, '2026-10-14')]:
            self.write(root, path, self.page(extra='<script src="/assets/monitor.js"></script>'))
            self.write(root, 'assets/monitor.js', 'fetch("/assets/data/monitor.json")')
            self.write(root, 'assets/data/monitor.json', json.dumps({'total': 12, 'generado': date}))
        self.assertEqual(snapshot(self.site, self.site / path)['fingerprint'],
                         snapshot(self.old, self.old / path)['fingerprint'])

    def test_repair_mass_batch_recovers_metadata_without_inventing_dates(self):
        entries = []
        for i in range(110):
            url = f'/territorio/monitor-{i}/'
            extra = '<meta content="2026-09-20T10:00:00-03:00" property="article:published_time">' if i == 0 else ''
            for root in (self.site, self.old):
                self.write(root, url.lstrip('/') + 'index.html', self.page(extra=extra))
            entries.append({'url': url, 'title': 'Una nota', 'date': '2026-10-14', 'event': 'Actualizado'})
        self.write(self.old, 'assets/data/lo-nuevo.json', json.dumps({'version': 1, 'entries': entries}))
        result = generate(self.site, self.old, '2026-10-15')
        recovered = next(e for e in result if e['url'] == '/territorio/monitor-0/')
        unknown = next(e for e in result if e['url'] == '/territorio/monitor-1/')
        self.assertEqual(recovered['date'], '2026-09-20')
        self.assertEqual(recovered['event'], 'Fecha editorial')
        self.assertIsNone(unknown['date'])
        self.assertEqual(unknown['legacy_detected_at'], '2026-10-14')
        rendered = (self.site / 'lo-nuevo/index.html').read_text()
        self.assertIn('Sin fecha editorial verificada', rendered)
        self.assertNotIn('<time datetime="2026-10-15">', rendered)

    def test_migration_does_not_mask_a_real_content_change(self):
        path = 'publicaciones/notas/nueva-cifra/index.html'
        self.write(self.old, path, self.page('Dato: 10'))
        self.write(self.site, path, self.page('Dato: 12'))
        entries = [{'url': '/' + path.removesuffix('index.html'), 'title': 'Una nota', 'date': '2026-10-14', 'event': 'Actualizado'}]
        entries += [{'url': f'/territorio/monitor-{i}/', 'title': 'Monitor', 'date': '2026-10-14', 'event': 'Actualizado'} for i in range(110)]
        self.write(self.old, 'assets/data/lo-nuevo.json', json.dumps({'version': 1, 'entries': entries}))
        result = generate(self.site, self.old, '2026-10-15')
        self.assertEqual(result[0]['date'], '2026-10-15')
        self.assertEqual(result[0]['event'], 'Actualizado')

if __name__ == '__main__':
    unittest.main()

