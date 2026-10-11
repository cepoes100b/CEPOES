import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFont
from deploy.compartir_publicaciones import canonical, inject, card, lines, BOLD

class SharingTests(unittest.TestCase):
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
