import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('build_public_local',Path(__file__).with_name('build_public_local.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class PublicScopeTest(unittest.TestCase):
    def test_public_resources(self):
        self.assertEqual(module.canonical('/assets/site.css?v=123#x'),'https://cepoes.org/assets/site.css')
        self.assertEqual(module.canonical('/territorio/barrios/almagro/'),'https://cepoes.org/territorio/barrios/almagro/')
        self.assertEqual(module.canonical(module.MARKER),module.ORIGIN+module.MARKER)
    def test_boundaries(self):
        # Deliberately synthetic fixture, assembled like R2's own detector tests.
        for path in ['/privado/','/LOGIN/','/api/events.json','/suscriptores/list.json',
                     '/.env','/.git/config','/.well-known/anything.json','https://other.example/a.json',
                     'http://cepoes.org/','https://' + 'synthetic-user:synthetic-password@cepoes.org/index.html',
                     '/%70rivado/index.html','/%252e%252e/privado/index.html','/assets/%5cprivado.json',
                     '/datos/padron.csv','/datos/deudores.txt','/assets/${token}.json']:
            with self.subTest(path=path): self.assertIsNone(module.canonical(path))
    def test_references_do_not_evaluate_code(self):
        data=b'''<script src="/assets/a.js?v=1"></script><a href="/privado/">Private</a>
            fetch('/api/users.json'); fetch('/assets/data/actual.json'); fetch(`/assets/${x}.json`)
            "https://other.example/external.js"'''
        self.assertEqual(module.references(data,module.ORIGIN+'/'),
                         {module.ORIGIN+'/assets/a.js',module.ORIGIN+'/assets/data/actual.json'})
    def test_local_paths(self):
        self.assertEqual(module.relpath(module.ORIGIN+'/'),'index.html')
        self.assertEqual(module.relpath(module.ORIGIN+'/territorio/'),'territorio/index.html')
        self.assertEqual(module.relpath(module.ORIGIN+'/assets/data.json'),'assets/data.json')

if __name__=='__main__': unittest.main()
