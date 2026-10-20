import json
import tempfile
import unittest
from pathlib import Path
from deploy.ejes_publicos import registry, axis_grid, prepare, context_links, audit
from deploy.preparar_sitio_publico import mark_latest_axis, territory_subnav

class EjesTest(unittest.TestCase):
    def test_shared_taxonomy_matches_all_nine_axes(self):
        taxonomy = json.loads(Path('deploy/site-overlay/assets/data/taxonomia.json').read_text())
        self.assertEqual({x['slug'] for x in taxonomy['temas']}, {x['id'] for x in registry()['themes']})
        self.assertEqual(len(taxonomy['temas']), 9)

    def test_all_reports_have_an_axis(self):
        routes = {x['url'] for g in registry()['groups'] for x in g['links']}
        reports = json.loads(Path('deploy/reports-registry.json').read_text())['reports']
        self.assertTrue(all(r['url'] in routes for r in reports))

    def test_health_has_distinct_mental_health_products_and_sport(self):
        grid = axis_grid('salud')
        for route in ['/observatorio/salud-mental/', '/publicaciones/informes/salud-mental-caba/', '/publicaciones/notas/prevenir-es-garantizar-ayuda-a-tiempo/', '/territorio/deporte-salud/', '/legislatura/seguimiento/analgesia-peridural/']:
            self.assertIn('href="' + route + '"', grid)
        self.assertNotIn('editorial-feature', grid)

    def test_content_can_belong_to_multiple_axes(self):
        source = '<html><body><main><h1>Deporte y salud</h1></main></body></html>'
        result = context_links(source, '/territorio/deporte-salud/')
        self.assertIn('href="/salud/"', result)
        self.assertIn('href="/territorio/"', result)
        self.assertEqual(result, context_links(result, '/territorio/deporte-salud/'))

    def test_axes_catalogs_are_idempotent(self):
        for axis in ['salud', 'educacion', 'temas']:
            source = Path('deploy/site-overlay', axis, 'index.html').read_text()
            result = prepare(source, '/' + axis + '/index.html')
            self.assertEqual(result, prepare(result, '/' + axis + '/index.html'))

    def test_territory_catalog_is_visible_and_keeps_map_and_communes(self):
        source = '<html><body><header class="page-hero"><h1>Territorio</h1></header><section id="mapa"><svg id="map"/></section><section id="comunas">15 comunas</section></body></html>'
        result = prepare(source, '/territorio/index.html')
        self.assertEqual(result, prepare(result, '/territorio/index.html'))
        self.assertLess(result.index('id="territorio-catalogo"'), result.index('id="mapa"'))
        self.assertIn('<svg id="map"/>', result)
        self.assertIn('id="comunas">15 comunas', result)
        self.assertNotIn('<details', territory_subnav('territorio/index.html'))

    def test_single_new_badge_uses_newest_of_all_card_links(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for route, date in [('one', '2026-01-01'), ('two', '2026-11-01'), ('three', '2026-02-01')]:
                path = root / route / 'index.html'; path.parent.mkdir()
                path.write_text(f'<meta content="{date}" property="article:published_time">')
            source = '<article class="ia-topic-card axis-topic-card"><a href="/one/">Uno</a><a href="/two/">Dos</a></article><article class="ia-topic-card"><a href="/three/">Tres</a></article>'
            result = mark_latest_axis(source, root)
            self.assertEqual(result.count('class="axis-new"'), 1)
            self.assertLess(result.index('class="axis-new"'), result.index('href="/one/"'))
            self.assertEqual(result, mark_latest_axis(result, root))

    def test_missing_destination_blocks_audit(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(AssertionError, 'Destino de eje ausente'):
                audit(Path(d))

if __name__ == '__main__': unittest.main()
