import unittest
from unittest.mock import patch
from deploy.preparar_sitio_publico import latest_home_publications,home_publications_hero,load_json
class HomeEditorialTests(unittest.TestCase):
    def test_current_selection(self):
        items=latest_home_publications()
        self.assertEqual(len(items),3)
        self.assertIn('boletin-05',items[1]['url'])
        self.assertIn('informe-coyuntura-02',items[2]['url'])
    def test_new_report_replaces_previous(self):
        def changed(name):
            data=load_json(name)
            if name=='deploy/reports-registry.json':
                data['reports'].append(dict(data['reports'][0],period='2026-12-01',title='Nueva edición'))
            return data
        with patch('deploy.preparar_sitio_publico.load_json',side_effect=changed):
            self.assertEqual(latest_home_publications()[2]['title'],'Nueva edición')
    def test_static_accessible_links(self):
        hero=home_publications_hero()
        self.assertEqual(hero.count('<article'),3)
        self.assertEqual(hero.count('<h1>'),1)
        self.assertIn('tabindex="0"',hero)
        self.assertNotIn('setInterval',hero)

    def test_budget_feature_and_health_link(self):
        self.assertEqual(latest_home_publications()[0]['url'],'/presupuesto/2027/')
        hero=home_publications_hero()
        self.assertIn('href="/presupuesto/2027/salud/"',hero)
        self.assertIn('Explorar el presupuesto',hero)
    def test_disabled_feature_restores_automatic_selection(self):
        def changed(name):
            data=load_json(name)
            if name.endswith('home-editorial.json'):
                data['featured_publication']['enabled']=False
            return data
        with patch('deploy.preparar_sitio_publico.load_json',side_effect=changed):
            self.assertEqual(latest_home_publications()[0]['label'],'Última nota')
    def test_unregistered_feature_is_rejected(self):
        def changed(name):
            data=load_json(name)
            if name.endswith('home-editorial.json'):
                data['featured_publication']['url']='/borrador/'
            return data
        with patch('deploy.preparar_sitio_publico.load_json',side_effect=changed):
            with self.assertRaises(ValueError): latest_home_publications()
