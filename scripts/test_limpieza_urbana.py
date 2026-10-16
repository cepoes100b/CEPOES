import csv,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('limpieza',ROOT/'scripts/generar_limpieza_urbana.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestSUACI(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.geo=ROOT/'badata/barrios.geojson';self.features=m.geometry(self.geo)
 def csv(self,rows):
  p=self.root/'suaci-2026.csv'
  with p.open('w',newline='',encoding='utf-8') as f:
   w=csv.DictWriter(f,fieldnames=['nro_solicitud','prestacion','fecha_ingreso','comuna','barrio','calle','altura','categoria','tipo','estado_general']);w.writeheader();w.writerows(rows)
  return p
 def row(self,i,b=None):
  b=b or self.features[0];return dict(nro_solicitud=str(i),prestacion='Lavado de contenedor',fecha_ingreso='2026-01-15',comuna=b['comuna'],barrio=b['name'],calle='PRUEBA',altura='125.0',categoria='HIGIENE',tipo='Queja',estado_general='Cerrado')
 def test_full_coverage_and_no_personal_fields(self):
  rows=[self.row(i,b) for i,b in enumerate(self.features)];d=m.generate([self.csv(rows)],self.geo);m.validate(d)
  self.assertEqual(d['total'],48);self.assertEqual(sum(r[5] for r in d['counts']),48);self.assertEqual(len(d['features']),48);self.assertNotIn('nro_solicitud',json.dumps(d));self.assertNotIn('PRUEBA',json.dumps(d))
 def test_duplicate_and_conflict(self):
  r=self.row(1);d=m.generate([self.csv([r,r])],self.geo);self.assertEqual(d['total'],1);self.assertEqual(d['duplicatesRemoved'],1)
  changed=dict(r,altura='999');self.csv([r,changed])
  with self.assertRaisesRegex(ValueError,'atributos diferentes'):m.generate([self.root/'suaci-2026.csv'],self.geo)
 def test_unknown_type_fails(self):
  r=self.row(1);r['prestacion']='Nueva prestación de contenedor'
  with self.assertRaisesRegex(ValueError,'Prestaciones nuevas'):m.generate([self.csv([r])],self.geo)
 def test_comuna_from_barrio_and_missing_address(self):
  r=self.row(1);r.update(comuna='99',altura='');d=m.generate([self.csv([r])],self.geo);self.assertEqual(d['comunaConflictsResolvedFromBarrio'],1);self.assertNotIn('topStreets',d);self.assertEqual(d['counts'][0][1],self.features[0]['comuna'])
 def test_regression_preserves_previous(self):
  d=m.generate([self.csv([self.row(i,b) for i,b in enumerate(self.features)])],self.geo);m.validate(d);p=dict(d,periodEnd='2026-02-28')
  target=self.root/'valid.json';m.atomic_write(target,p);before=target.read_bytes()
  with self.assertRaisesRegex(ValueError,'Retroceso de corte'):m.validate(d,p)
  self.assertEqual(target.read_bytes(),before)
class TestDownload(unittest.TestCase):
 def test_incomplete_download_does_not_replace_previous(self):
  import io
  from unittest.mock import patch
  spec=importlib.util.spec_from_file_location('download',ROOT/'scripts/descargar_suaci.py');download=importlib.util.module_from_spec(spec);spec.loader.exec_module(download)
  class Response(io.BytesIO):
   status=200
   headers={'Content-Type':'text/csv','Content-Length':'10000'}
  with tempfile.TemporaryDirectory() as tmp:
   directory=Path(tmp);target=directory/'suaci-2026.csv';target.write_bytes(b'ultimo archivo valido')
   with patch.object(download.urllib.request,'urlopen',side_effect=lambda *a,**k:Response(b'nro_solicitud,prestacion\n1,prueba\n')):
    with patch.object(download.time,'sleep'):
     with self.assertRaisesRegex(ValueError,'incompleta'):download.download(2026,directory)
   self.assertEqual(target.read_bytes(),b'ultimo archivo valido')
 def test_html_and_partial_are_rejected(self):
  import io
  from unittest.mock import patch
  spec=importlib.util.spec_from_file_location('download',ROOT/'scripts/descargar_suaci.py');download=importlib.util.module_from_spec(spec);spec.loader.exec_module(download)
  class Response(io.BytesIO):
   status=206
   headers={'Content-Type':'text/csv'}
  with tempfile.TemporaryDirectory() as tmp:
   with patch.object(download.urllib.request,'urlopen',return_value=Response(b'fragmento')):
    with self.assertRaisesRegex(ValueError,'no CSV completa'):download.download(2026,Path(tmp))
class TestContinuity(unittest.TestCase):
 def test_new_gap_requires_review_and_partial_month_is_not_enough(self):
  import collections
  from calidad_limpieza_urbana import quality
  name='Motivo';months=['2026-01','2026-02','2026-03','2026-04','2026-05']
  config={'canonicalPrestations':{name:name},'groups':{name:'Tema'},'natures':{name:'Problemas reportados'}}
  monthly=collections.Counter({(month,name,'Solicitud'):60 for month in months[:3]})
  self.assertEqual(quality(monthly,{name:'2026-03-20'},months,True,config)['discontinuities'],[])
  q=quality(monthly,{name:'2026-03-20'},months,False,config)
  self.assertEqual(len(q['discontinuities']),1);self.assertFalse(q['discontinuities'][0]['reviewed'])
  with self.assertRaisesRegex(ValueError,'Nueva discontinuidad'):m.validate({'quality':q})
 def test_stable_nature_across_official_kind_change(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'suaci-2026.csv';rows=[]
   for i,kind in enumerate(['Solicitud','Queja']):rows.append({'nro_solicitud':str(i),'prestacion':'Recolección de residuos fuera del contenedor','fecha_ingreso':f'{2025+i}-01-15','categoria':'HIGIENE','tipo':kind,'barrio':'FLORES','comuna':'7','calle':'PRUEBA','altura':'1','estado_general':'Cerrado'})
   with path.open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
   d=m.generate([path],ROOT/'badata/barrios.geojson');self.assertEqual({r[6] for r in d['counts']},{'Problemas reportados'});self.assertEqual({r[4] for r in d['counts']},{'Solicitud','Queja'})

# Incluir regresiones de transporte en el control SUACI canónico.
from test_descargar_suaci import DownloadTests

if __name__=='__main__':unittest.main()
