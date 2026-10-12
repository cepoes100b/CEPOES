import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
import hashlib
import html
import re
from PIL import Image, ImageDraw, ImageFont
from deploy.compartir_publicaciones import canonical, inject, card, lines, BOLD, meta

class SharingTests(unittest.TestCase):
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
            self.assertEqual(meta(first, 'og:url'), 'https://cepoes.org/')
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
            self.assertEqual(meta(first, 'og:url'), 'https://cepoes.org' + route)
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

