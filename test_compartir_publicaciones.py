import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
import hashlib
import html
import re
from PIL import Image, ImageDraw, ImageFont
from deploy.compartir_publicaciones import canonical, inject, card, lines, BOLD, meta, place_controls

class SharingTests(unittest.TestCase):
    def test_editorial_correction_refreshes_every_static_share_link(self):
        route = '/educacion/universidad-publica/'
        source = '<html><head><link rel="canonical" href="https://cepoes.org' + route + '"><meta name="description" content="Financiamiento universitario y salarios."><meta property="og:description" content="Posición de CEPOES sobre la universidad."></head><body><h1>Universidad pública</h1></body></html>'
        with tempfile.TemporaryDirectory() as tmp, patch('deploy.compartir_publicaciones.card'):
            site = Path(tmp)
            first = inject(source, route + 'index.html', site, {})
            preview_url = meta(first, 'og:url')
            revision = parse_qs(urlparse(preview_url).query)['share_rev'][0]
            self.assertEqual(meta(first, 'og:description'), 'Financiamiento universitario y salarios.')
            self.assertNotIn('Posición de CEPOES', first)
            self.assertIn('rel="canonical" href="https://cepoes.org' + route + '"', first)
            self.assertIn('data-share-url="' + preview_url + '"', first)
            for platform in ['whatsapp', 'x', 'facebook']:
                href = html.unescape(re.search(r'data-share-platform="' + platform + r'" href="([^"]+)"', first)[1])
                query = parse_qs(urlparse(href).query)
                shared = query['text'][0].split('\n')[-1] if platform == 'whatsapp' else query['url' if platform == 'x' else 'u'][0]
                self.assertEqual(parse_qs(urlparse(shared).query)['share_rev'], [revision])
            self.assertEqual(preview_url, meta(inject(first, route + 'index.html', site, {}), 'og:url'))
            corrected = inject(first.replace('Financiamiento universitario y salarios.', 'Recursos, becas y salarios.'), route + 'index.html', site, {})
            self.assertNotEqual(preview_url, meta(corrected, 'og:url'))
            self.assertNotEqual(meta(first, 'og:image'), meta(corrected, 'og:image'))

    def test_self_referential_share_copy_is_rejected_before_generation(self):
        with tempfile.TemporaryDirectory() as tmp, patch('deploy.compartir_publicaciones.card') as draw:
            for phrase in ['Posición de CEPOES sobre educación', 'La lectura de CEPOES es clara', 'La exigencia de CEPOES', 'Nuestra posición sobre educación']:
                source = '<html><head><meta name="description" content="' + phrase + '"></head><body><h1>Educación</h1></body></html>'
                with self.subTest(phrase=phrase), self.assertRaisesRegex(ValueError, 'sin autorreferencias'):
                    inject(source, '/educacion/index.html', Path(tmp), {})
            source = '<html><head></head><body><h1>Educación</h1></body></html>'
            with self.assertRaisesRegex(ValueError, 'sin autorreferencias'):
                inject(source, '/educacion/index.html', Path(tmp), {'/educacion/': {'description': 'Posición de CEPOES sobre educación'}})
            self.assertFalse(draw.called)
            allowed = source.replace('</head>', '<meta name="description" content="La posición del CIN y las estimaciones de CEPA."></head>')
            self.assertEqual(meta(inject(allowed, '/educacion/index.html', Path(tmp), {}), 'og:description'), 'La posición del CIN y las estimaciones de CEPA.')

    def test_home_cards_are_idempotent_when_featured_heading_changes(self):
        source = '<html><head><title>CEPOES | Centro de Estudios</title></head><body><h1>Informe destacado</h1></body></html>'
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            first = inject(source, '/index.html', site, {})
            images = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in site.rglob('*.png')}
            self.assertEqual(len(images), 3)
            self.assertEqual(first, inject(first, '/index.html', site, {}))
            second = inject(first.replace('<h1>Informe destacado</h1>', '<h1>Otro artículo</h1>'), '/index.html', site, {})
            self.assertEqual(meta(first, 'og:image'), meta(second, 'og:image'))
            self.assertEqual(images, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in site.rglob('*.png')})

    def test_home_uses_institutional_identity_not_featured_h1(self):
        title = 'CEPOES | Centro de Estudios & Observatorio'
        source = '<html><head><title>CEPOES | Centro de Estudios &amp; Observatorio</title></head><body><h1>Salud mental en la Ciudad de Buenos Aires</h1></body></html>'
        with tempfile.TemporaryDirectory() as tmp, patch('deploy.compartir_publicaciones.card') as draw:
            first = inject(source, '/index.html', Path(tmp), {})
            self.assertEqual(first, inject(first, '/index.html', Path(tmp), {}))
            for key in ['og:title', 'twitter:title', 'og:image:alt', 'twitter:image:alt']:
                self.assertEqual(meta(first, key), title)
            self.assertIn('data-share-title="' + html.escape(title, quote=True) + '"', first)
            self.assertEqual(urlparse(meta(first, 'og:url')).path, '/')
            self.assertRegex(parse_qs(urlparse(meta(first, 'og:url')).query)['share_rev'][0], r'^[a-f0-9]{12}$')
            for platform in ['whatsapp', 'x']:
                href = re.search(r'data-share-platform="' + platform + r'" href="([^"]+)"', first)[1]
                query = parse_qs(urlparse(html.unescape(href)).query)
                self.assertEqual(query['text'][0].split('\n')[0], title)
            for call in draw.call_args_list:
                self.assertEqual(call.args[1], title)
            self.assertIn('<h1>Salud mental en la Ciudad de Buenos Aires</h1>', first)

    def test_article_and_registered_report_keep_their_titles(self):
        source = '<html><head><title>Sección | CEPOES</title></head><body><h1>Título de artículo</h1></body></html>'
        route = '/publicaciones/informes/salud-mental/'
        report = {'title': 'Salud mental en la Ciudad de Buenos Aires', 'description': 'Descripción registrada', 'kind': 'Informe especial'}
        with tempfile.TemporaryDirectory() as tmp, patch('deploy.compartir_publicaciones.card') as draw:
            article = inject(source, '/publicaciones/notas/ejemplo/index.html', Path(tmp), {})
            self.assertEqual(meta(article, 'og:title'), 'Título de artículo')
            first = inject(source, route + 'index.html', Path(tmp), {route: report})
            self.assertEqual(first, inject(first, route + 'index.html', Path(tmp), {route: report}))
            self.assertEqual(meta(first, 'og:title'), report['title'])
            self.assertEqual(meta(first, 'twitter:title'), report['title'])
            self.assertEqual(meta(first, 'og:description'), report['description'])
            self.assertEqual(urlparse(meta(first, 'og:url')).path, route)
            self.assertRegex(parse_qs(urlparse(meta(first, 'og:url')).query)['share_rev'][0], r'^[a-f0-9]{12}$')
            for call in draw.call_args_list[3:]:
                self.assertEqual(call.args[1], report['title'])

    def test_private_and_aliases_are_excluded(self):
        for route in ['/privado/index.html', '/prensa/admin/index.html', '/newsletter/index.html', '/legislativa/index.html', '/publicaciones/lectura.html']:
            self.assertIsNone(canonical('<html></html>', route))
        for source in ['<meta name="robots" content="noindex">', '<link rel="canonical" href="https://cepoes.org/otra/">', '<meta http-equiv="refresh" content="0; url=/">']:
            self.assertIsNone(canonical(source, '/index.html'))
        self.assertEqual(canonical('<link rel="canonical" href="https://cepoes.org/territorio/">', '/territorio/index.html'), '/territorio/')

    def test_cards_have_real_png_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            for size in [(1200, 630), (1080, 1350), (1080, 1920)]:
                target = Path(tmp)/f'{size[1]}.png'
                card(target, 'Salud mental en la Ciudad de Buenos Aires', 'Descripción de prueba', 'Informe especial', size)
                with Image.open(target) as im:
                    self.assertEqual(im.size, size)
                    self.assertEqual(im.format, 'PNG')

    def test_rebuild_is_idempotent_and_escapes_content(self):
        with tempfile.TemporaryDirectory() as tmp, patch('deploy.compartir_publicaciones.card'):
            site = Path(tmp)
            source = '<html><head><meta property="og:image" content="old"><title>Título &amp; prueba</title></head><body><h1>Título &amp; prueba</h1><footer class="footer"></footer></body></html>'
            first = inject(source, '/index.html', site, {})
            second = inject(first, '/index.html', site, {})
            self.assertEqual(first, second)
            self.assertEqual(first.count('property="og:image"'), 1)
            self.assertEqual(first.count('class="cepoes-share"'), 1)
            self.assertIn('content="Título &amp; prueba"', first)
            self.assertIn('summary_large_image', first)
            self.assertNotIn('content="old"', first)
            self.assertIn('data-share-close', first)
            self.assertIn('Compartir en WhatsApp', first)
            self.assertIn('utm_source%3Dwhatsapp', first)

    def test_image_panel_includes_download_copy_and_link_without_js(self):
        with tempfile.TemporaryDirectory() as tmp, patch('deploy.compartir_publicaciones.card'):
            source = '<html><head><title>Informe</title></head><body><h1>Informe</h1></body></html>'
            result = inject(source, '/publicaciones/index.html', Path(tmp), {})
            for selector in ['data-media-file', 'data-media-caption', 'data-media-download', 'data-media-link', 'data-media-close']:
                self.assertIn(selector, result)
            self.assertIn('share-media-dialog', result)
            self.assertIn('-enlace.png" download data-media-download', result)
            self.assertEqual(result, inject(result, '/publicaciones/index.html', Path(tmp), {}))

    def test_controls_follow_content_title_and_ignore_script_and_navigation(self):
        source = '<html><head><script>const fake="<h1>Falso</h1>";</script></head><body><nav><h1>Marca</h1></nav><main><h1>Informe</h1><p>Texto</p></main><footer>Pie</footer></body></html>'
        block = '<section class="cepoes-share">Controles</section>'
        result = place_controls(source, block, '/informe/')
        self.assertIn('<h1>Informe</h1><section class="cepoes-share" data-share-placement="title">', result)
        self.assertLess(result.index('Controles'), result.index('<p>Texto'))

    def test_home_and_dynamic_articles_keep_controls_outside_cards_and_loader(self):
        block = '<section class="cepoes-share">Controles</section>'
        home = '<html><body><nav>Menú</nav><header><article><h1>Nota</h1></article></header></body></html>'
        self.assertIn('</nav>' + block + '<header>', place_controls(home, block, '/'))
        article = '<html><body><nav>Menú</nav><main id="article"></main></body></html>'
        self.assertIn('</nav>' + block + '<main', place_controls(article, block, '/prensa/nota/'))

    def test_long_title_does_not_truncate(self):
        draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
        title = 'Una palabraextremadamentelargaperocompletayconservada sobre los barrios'
        wrapped = lines(draw, title, ImageFont.truetype(str(BOLD), 38), 300)
        self.assertEqual(''.join(wrapped).replace(' ', ''), title.replace(' ', ''))

    def test_unbranded_monitor_retains_exception(self):
        with tempfile.TemporaryDirectory() as tmp, patch('deploy.compartir_publicaciones.card') as draw:
            source = '<html><head><title>Seguridad y derechos</title></head><body></body></html>'
            inject(source, '/territorio/seguridad-barrios-populares/index.html', Path(tmp), {})
            self.assertEqual(draw.call_count, 3)
            for call in draw.call_args_list: self.assertFalse(call.args[7])

if __name__ == '__main__': unittest.main()



