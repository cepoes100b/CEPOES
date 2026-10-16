import json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.generar_publications_feed import generate

class PublicationsFeedTest(unittest.TestCase):
 def test_generated_dates_are_accepted_unchanged_by_dispatch_validator(self):
  # Public regression observed on 2026-10-15; all other pages are local fixtures.
  undated=dict(key='/territorio/seguridad-barrios-populares/',url='/territorio/seguridad-barrios-populares/',kind='informe',title='Seguridad y derechos en los barrios populares',summary='Rechazamos Tormenta Negra como política de seguridad y seguimos sus operativos, resultados, denuncias y efectos sobre los barrios populares de CABA.',date=None)
  expected=[undated]+[dict(key=f'/publicaciones/informes/{name}/',url=f'/publicaciones/informes/{name}/',kind='informe',title='Informe de prueba',summary='Resumen de prueba',date=date) for name,date in [('mes','2026-09'),('dia','2026-10-15')]]
  for version in (1,2):
   with self.subTest(registry_version=version),tempfile.TemporaryDirectory() as tmp:
    site=Path(tmp);(site/'assets/data').mkdir(parents=True)
    entries=[]
    for item in expected:
     page=site/item['url'].lstrip('/')/'index.html';page.parent.mkdir(parents=True,exist_ok=True);page.write_text('<main><h1>Informe</h1></main>',encoding='utf-8')
     entries.append(dict(url=item['url'],type=item['kind'],title=item['title'],description=item['summary'],date=item['date']))
    (site/'assets/data/lo-nuevo.json').write_text(json.dumps(dict(version=version,entries=entries)),encoding='utf-8')
    generated=generate(site)  # Real producer, including bulletin extraction; no mocks.
    serialized=(site/'assets/data/newsletter-publications.json').read_text(encoding='utf-8')
    self.assertEqual(json.loads(serialized),generated)
    self.assertEqual(generated,dict(version=1,publications=sorted(expected,key=lambda p:p['key'])))
    # Import only the pure consumer, never index.ts or any remote service.
    consumer=subprocess.run(['node','--input-type=module','-e',"import {readFileSync} from 'node:fs'; import {validatePublication} from './supabase/functions/newsletter-dispatch/logic.js'; const feed=JSON.parse(readFileSync(0,'utf8')); process.stdout.write(JSON.stringify(feed.publications.map(validatePublication)));"],input=serialized,text=True,capture_output=True,cwd=Path(__file__).resolve().parents[1],timeout=15)
    self.assertEqual(consumer.returncode,0,consumer.stderr)
    self.assertEqual(json.loads(consumer.stdout),generated['publications'])

 def test_registry_v2_accepts_unknown_and_month_only_dates(self):
  with tempfile.TemporaryDirectory() as tmp:
   site=Path(tmp);(site/'assets/data').mkdir(parents=True)
   entries=[]
   for name,date in [('sin-fecha',None),('edicion','2026-09')]:
    url=f'/publicaciones/informes/{name}/';page=site/url.lstrip('/')/'index.html';page.parent.mkdir(parents=True,exist_ok=True);page.write_text('<main><h1>Informe</h1></main>')
    entries.append(dict(url=url,type='informe',title='Informe',description='Resumen',date=date,event='Fecha por verificar' if date is None else 'Edición'))
   (site/'assets/data/lo-nuevo.json').write_text(json.dumps(dict(version=2,entries=entries)))
   with patch('scripts.generar_publications_feed.editions',return_value=[]):result=generate(site)
   self.assertEqual(len(result['publications']),2)
   self.assertIsNone(next(p['date'] for p in result['publications'] if 'sin-fecha' in p['url']))
   self.assertEqual(next(p['date'] for p in result['publications'] if 'edicion' in p['url']),'2026-09')

 def test_editorial_new_pages_only_and_stable_identity(self):
  with tempfile.TemporaryDirectory() as tmp:
   site=Path(tmp);(site/'assets/data').mkdir(parents=True)
   entries=[]
   for url,kind,meta in [('/publicaciones/informes/','informe',''),('/publicaciones/informes/nuevo/','informe',''),('/publicaciones/notas/nueva/','analisis',''),('/prensa/aviso/','prensa','<meta name="cepoes:publication" content="notice">'),('/datos/indicador/','datos',''),('/territorio/mapa/','herramienta',''),('/publicaciones/notas/borrador/','analisis','<meta name="robots" content="noindex">')]:
    page=site/url.lstrip('/')/'index.html';page.parent.mkdir(parents=True,exist_ok=True);page.write_text(meta+'<main><h1>Título</h1></main>')
    entries.append(dict(url=url,type=kind,title='Título',description='Resumen',date='2026-10-08',event='Nuevo'))
   (site/'assets/data/lo-nuevo.json').write_text(json.dumps(dict(version=1,entries=entries)))
   with patch('scripts.generar_publications_feed.editions',return_value=[]):first=generate(site)
   self.assertEqual({p['key'] for p in first['publications']},{'/publicaciones/informes/nuevo/','/publicaciones/notas/nueva/','/prensa/aviso/'})
   self.assertEqual(next(p for p in first['publications'] if p['url']=='/prensa/aviso/')['kind'],'aviso')
   entries[1]['title']='Título corregido';entries[1]['event']='Actualizado'
   (site/'assets/data/lo-nuevo.json').write_text(json.dumps(dict(version=1,entries=entries)))
   with patch('scripts.generar_publications_feed.editions',return_value=[]):second=generate(site)
   self.assertEqual([p['key'] for p in first['publications']],[p['key'] for p in second['publications']])

if __name__=='__main__':unittest.main()

