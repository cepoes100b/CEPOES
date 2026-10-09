import json,re,unittest,tempfile
from pathlib import Path
from deploy.preparar_sitio_publico import inject_octubre_rosa_bridge
from generar_lo_nuevo import generate,kind
ROOT=Path(__file__).parent
class OctubreRosaTest(unittest.TestCase):
 def test_agenda_source_and_static_fallback(self):
  d=json.loads((ROOT/'deploy/site-overlay/assets/data/octubre-rosa-2026.json').read_text())
  h=(ROOT/'deploy/site-overlay/salud/octubre-rosa/index.html').read_text()
  self.assertEqual(len(d['campaigns']),7)
  for c in d['campaigns']:
   self.assertLessEqual(c['start'],c['end']);self.assertIn(c['source'],h)
   self.assertIn('data-barrio="'+c['barrio']+'"',h)
   self.assertIn('data-start="'+c['start']+'"',h)
   self.assertIn(c['address'],h)
  self.assertFalse(next(c for c in d['campaigns'] if c['id']=='rojas')['free'])
  self.assertFalse(next(c for c in d['campaigns'] if c['id']=='zubizarreta')['walkin'])
 def test_bridge_preserves_editorial_and_is_idempotent(self):
  original='<body><header class="hero home-publications-hero">'+''.join('<article>Tarjeta '+str(i)+'</article>' for i in range(3))+'</header><main>Presupuesto</main><footer class="footer"></footer></body>'
  once=inject_octubre_rosa_bridge(original,'/index.html',today='2026-10-09')
  self.assertEqual(once,inject_octubre_rosa_bridge(once,'/index.html',today='2026-10-09'))
  self.assertEqual(once.count('<article>'),3)
  self.assertIn('Presupuesto',once)
  self.assertEqual(once.count('id="octubre-rosa-bridge"'),1)
  self.assertEqual(original,inject_octubre_rosa_bridge(original,'/presupuesto/2027/index.html'))
 def test_home_campaign_is_seasonal(self):
  source='<html><head></head><body><header class="home-publications-hero">Tres notas</header><footer class="footer"></footer></body></html>'
  for date in ['2026-09-30','2026-11-01','2027-10-09']:
   self.assertIn('id="octubre-rosa-bridge" hidden',inject_octubre_rosa_bridge(source,'/index.html',today=date))
  self.assertNotIn('id="octubre-rosa-bridge" hidden',inject_octubre_rosa_bridge(source,'/index.html',today='2026-10-31'))
 def test_special_enters_news_once_with_declared_date(self):
  with tempfile.TemporaryDirectory() as t:
   site=Path(t)/'site';old=Path(t)/'old';(site/'lo-nuevo').mkdir(parents=True);(site/'salud/octubre-rosa').mkdir(parents=True)
   template='<aside class="new-summary"></aside><select id="new-type"></select><select id="new-topic"></select><div class="new-list" id="new-list"></div><div class="new-empty"></div>'
   (site/'lo-nuevo/index.html').write_text(template)
   (site/'salud/octubre-rosa/index.html').write_text((ROOT/'deploy/site-overlay/salud/octubre-rosa/index.html').read_text())
   entries=generate(site,old,today='2026-10-09')
   self.assertEqual(len(entries),1);self.assertEqual(entries[0]['type'],'especial');self.assertEqual(entries[0]['date'],'2026-10-09')
if __name__=='__main__':unittest.main()
