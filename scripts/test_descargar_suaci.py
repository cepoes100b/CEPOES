"""Regresiones aisladas: ninguna prueba accede a la red ni a datos reales."""
import hashlib
import http.client
import io
import json
import ssl
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
import descargar_suaci as m
import actualizar_limpieza_urbana as pipeline

BODY=b'nro_solicitud,prestacion\n'+b'1,fixture\n'*20
class Response(io.BytesIO):
 def __init__(self,body=BODY,status=200,**headers):
  super().__init__(body);self.status=status
  self.headers={'Content-Type':'text/csv','Content-Length':str(len(body)),**headers}

class DownloadTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.target=self.root/'suaci-2026.csv';self.meta=self.root/'suaci-2026.json'
  self.target.write_bytes(BODY)
  self.old={'year':2026,'url':m.BASE+'sistema-unico-de-atencion-ciudadana-2026.csv','etag':'"old"','bytes':len(BODY),'sha256':hashlib.sha256(BODY).hexdigest(),'downloadedAt':'2026-10-15'}
  self.meta.write_text(json.dumps(self.old));self.before=self.snapshot()
  self.sleep=patch.object(m.time,'sleep').start();self.addCleanup(patch.stopall)
 def snapshot(self):return {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.root.iterdir()}
 def test_truncated_then_success(self):
  responses=[Response(BODY[:100],**{'Content-Length':str(len(BODY))}),Response(ETag='"new"')]
  with patch.object(m.urllib.request,'urlopen',side_effect=responses) as request:
   result=m.download(2026,self.root)
  self.assertEqual(request.call_count,2);self.assertEqual(result['sha256'],hashlib.sha256(BODY).hexdigest())
  self.assertEqual(request.call_args.args[0].get_header('Accept-encoding'),'identity')
  self.assertEqual(set(self.snapshot()),{'suaci-2026.csv','suaci-2026.json'})
  self.assertTrue(all(r.closed for r in responses))
 def test_exhaustion_keeps_bytes_manifest_dates_and_cleans_temps(self):
  with patch.object(m.urllib.request,'urlopen',side_effect=lambda *a,**k:Response(BODY[:100],**{'Content-Length':str(len(BODY))})) as request:
   with self.assertRaises(m.IncompleteDownload):m.download(2026,self.root)
  self.assertEqual(request.call_count,3);self.assertEqual(self.snapshot(),self.before)
  self.assertEqual([c.args[0] for c in self.sleep.call_args_list],[2,4])
 def test_transport_and_transient_http_recover(self):
  for error in (TimeoutError(),ConnectionResetError(),http.client.IncompleteRead(b'partial',50),urllib.error.URLError(TimeoutError()),urllib.error.HTTPError(m.BASE,503,'unavailable',{},None)):
   with self.subTest(error=type(error).__name__),patch.object(m.urllib.request,'urlopen',side_effect=[error,Response()] ) as request:
    m.download(2026,self.root);self.assertEqual(request.call_count,2)
 def test_transport_exhaustion_preserves_cache(self):
  with patch.object(m.urllib.request,'urlopen',side_effect=TimeoutError()) as request:
   with self.assertRaises(TimeoutError):m.download(2026,self.root)
  self.assertEqual(request.call_count,3);self.assertEqual(self.snapshot(),self.before)
 def test_replacement_happens_only_after_validation(self):
  replace=m.os.replace
  def checked_replace(source,destination):
   if destination==self.target:
    self.assertEqual(self.snapshot()[self.target.name],self.before[self.target.name])
    self.assertEqual(Path(source).read_bytes(),BODY)
   return replace(source,destination)
  with patch.object(m.urllib.request,'urlopen',return_value=Response()),patch.object(m.os,'replace',side_effect=checked_replace):m.download(2026,self.root)
  self.assertEqual(self.target.read_bytes(),BODY);self.assertEqual(len(list(self.root.iterdir())),2)
 def test_midstream_transport_cleans_partial(self):
  response=Response()
  with patch.object(response,'read',side_effect=[BODY[:100],ConnectionResetError()]),patch.object(m.urllib.request,'urlopen',side_effect=[response,Response()]):m.download(2026,self.root)
  self.assertTrue(response.closed);self.assertEqual(len(list(self.root.iterdir())),2)
 def test_304_valid_preserves_dates(self):
  error=urllib.error.HTTPError(m.BASE,304,'unchanged',{},None)
  with patch.object(m.urllib.request,'urlopen',side_effect=error):self.assertEqual(m.download(2026,self.root),self.old)
  self.assertEqual(self.snapshot(),self.before)
 def test_304_without_integrity_is_permanent(self):
  self.target.write_bytes(BODY+b'corrupt')
  with patch.object(m.urllib.request,'urlopen',side_effect=urllib.error.HTTPError(m.BASE,304,'unchanged',{},None)) as request:
   with self.assertRaisesRegex(ValueError,'304 sin'):m.download(2026,self.root)
  self.assertEqual(request.call_count,1);self.assertIsNone(request.call_args.args[0].get_header('If-none-match'))
 def test_permanent_invalid_responses_never_retry(self):
  cases=[Response(status=206),Response(**{'Content-Type':'text/html'}),Response(**{'Content-Encoding':'gzip'}),Response(**{'Content-Range':'bytes 0-99/200'}),Response(**{'Content-Length':'-1'}),Response(b'tiny'),Response(b'x'*200),urllib.error.HTTPError(m.BASE,404,'missing',{},None),urllib.error.URLError(ssl.SSLCertVerificationError('certificate'))]
  for case in cases:
   with self.subTest(case=type(case).__name__):
    with patch.object(m.urllib.request,'urlopen',side_effect=case if isinstance(case,Exception) else None,return_value=case) as request:
     with self.assertRaises(Exception):m.download(2026,self.root)
    self.assertEqual(request.call_count,1);self.assertEqual(self.snapshot(),self.before)
 def test_pipeline_stops_before_generation_on_exhaustion(self):
  # Ejecutar el coordinador real; sólo sustituir su proceso de descarga por
  # el descargador real con transporte simulado y ROOT temporal.
  paths=['deploy/site-overlay/assets/data/limpieza-urbana.json','deploy/site-overlay/assets/data/limpieza-urbana-estado.json','deploy/site-overlay/territorio/limpieza-urbana/index.html']
  for name in paths:
   p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('ultima version 2026-10-15')
  before={name:((self.root/name).read_bytes(),(self.root/name).stat().st_mtime_ns) for name in paths}
  def child(command,**kwargs):
   self.assertTrue(command[1].endswith('descargar_suaci.py'))
   try:m.download(2026,self.root)
   except m.IncompleteDownload:raise subprocess.CalledProcessError(1,command)
  with patch.object(pipeline,'ROOT',self.root),patch.object(sys,'argv',['actualizar_limpieza_urbana.py']),patch.object(pipeline.subprocess,'run',side_effect=child) as run,patch.object(m.urllib.request,'urlopen',side_effect=lambda *a,**k:Response(BODY[:100],**{'Content-Length':str(len(BODY))})):
   with self.assertRaises(subprocess.CalledProcessError):pipeline.main()
  self.assertEqual(run.call_count,1)
  self.assertEqual(before,{name:((self.root/name).read_bytes(),(self.root/name).stat().st_mtime_ns) for name in paths})
  self.assertEqual(self.target.read_bytes(),self.before[self.target.name][0]);self.assertEqual(self.meta.read_bytes(),self.before[self.meta.name][0])

if __name__=='__main__':unittest.main()
