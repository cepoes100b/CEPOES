import importlib.util
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('monitor',str(Path(__file__).with_name('monitor_tierras.py')))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Reply:
 headers={'Content-Type':'text/html'}
 def __init__(self,body):self.body=body
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,n):return self.body
def valid(req,**kwargs):
 return Reply((b'%PDF-'+b'x'*120) if req.full_url.endswith('.pdf') else b'<html>'+b'x'*120+b'</html>')
with tempfile.TemporaryDirectory() as folder:
 with patch.object(m.urllib.request,'urlopen',side_effect=valid):
  assert m.run(folder)==0
  first=json.loads((Path(folder)/'estado.json').read_text())
  assert all(x['estado']=='primera_captura' for x in first.values())
  assert m.run(folder)==0
  second=json.loads((Path(folder)/'estado.json').read_text())
  assert all(x['estado']=='sin_cambios' for x in second.values())
  assert first['rntr_departamentos']['modificado']==second['rntr_departamentos']['modificado']
 with patch.object(m.urllib.request,'urlopen',side_effect=OSError):
  assert m.run(folder)==1
  third=json.loads((Path(folder)/'estado.json').read_text())
  assert third['rntr_departamentos']['sha256']==second['rntr_departamentos']['sha256']
  assert (Path(folder)/third['rntr_departamentos']['documento']).exists()
print('Primera captura, consulta sin cambios y preservación ante error: correctas')
