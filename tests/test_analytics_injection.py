import unittest
from deploy.preparar_sitio_publico import inject_analytics

class AnalyticsInjectionTests(unittest.TestCase):
    def test_public_and_idempotent(self):
        source = '<html><head></head><body></body></html>'
        result = inject_analytics(source, '/index.html')
        self.assertIn('G-Z6E4BNZXMG', result)
        self.assertEqual(result.count('analytics-cepoes.js'), 1)
        self.assertEqual(inject_analytics(result, '/index.html'), result)

    def test_private_and_auth_excluded(self):
        source = '<html><head></head><body></body></html>'
        for path in ['/privado/index.html', '/suscripcion/index.html', '/newsletter/confirmar/index.html', '/admin/index.html']:
            self.assertEqual(inject_analytics(source, path), source)

if __name__ == '__main__':
    unittest.main()
