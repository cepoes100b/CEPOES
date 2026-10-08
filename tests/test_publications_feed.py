import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.generar_publications_feed import generate

class PublicationsFeedTest(unittest.TestCase):
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
