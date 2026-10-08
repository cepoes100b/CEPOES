import unittest
from pathlib import Path
from scripts.generar_newsletter_feed import editions

class EditorialTest(unittest.TestCase):
    def test_approved_publication_excerpts(self):
        site=Path(__file__).resolve().parents[1]/'deploy/site-overlay'
        data=next(e for e in editions(site) if e['edition']==5)['email_content']
        self.assertEqual(data['date'],'Septiembre 2026')
        self.assertEqual(len(data['sections']),4)
        self.assertIn('7,6 puntos',data['sections'][2]['body'])
        self.assertIn('zona sur',data['sections'][2]['body'])
        self.assertIn('diez trimestres',data['sections'][3]['body'])
        self.assertTrue(all(len(s['body'])<=900 and s['body'].endswith('.') for s in data['sections']))
        self.assertEqual(data['metrics'][0]['value'],'+0,3%')

if __name__=='__main__': unittest.main()
