#!/usr/bin/env python3
"""Descarga anual SUACI con control de tipo, tamaño y reemplazo atómico."""
import argparse,datetime,errno,hashlib,http.client,json,os,socket,ssl,tempfile,time,urllib.error,urllib.request
from pathlib import Path
BASE='https://cdn.buenosaires.gob.ar/datosabiertos/datasets/atencion-ciudadana/sistema-unico-atencion-ciudadana/'
CATALOG='https://data.buenosaires.gob.ar/dataset/sistema-unico-atencion-ciudadana'
MAX_ATTEMPTS=3
RETRY_STATUSES={408,429,500,502,503,504}
class IncompleteDownload(ValueError):
 """Respuesta truncada: es seguro reiniciar la descarga completa."""
def recoverable(error):
 if isinstance(error,urllib.error.HTTPError):return error.code in RETRY_STATUSES
 if isinstance(error,urllib.error.URLError):return recoverable(error.reason)
 if isinstance(error,ssl.SSLError):return False
 return isinstance(error,(IncompleteDownload,http.client.IncompleteRead,http.client.RemoteDisconnected,TimeoutError,ConnectionError)) or (isinstance(error,socket.gaierror) and error.errno==socket.EAI_AGAIN) or (isinstance(error,OSError) and error.errno in {errno.ENETUNREACH,errno.EHOSTUNREACH})
def download(year,directory):
 for attempt in range(1,MAX_ATTEMPTS+1):
  try:return download_once(year,directory)
  except Exception as error:
   if not recoverable(error) or attempt==MAX_ATTEMPTS:raise
   # Sólo metadatos; no volcar cuerpos, registros ni URLs de excepciones.
   print(f'SUACI {year}: fallo recuperable {type(error).__name__}; intento {attempt}/{MAX_ATTEMPTS}')
   time.sleep(2**attempt)
def cached_valid(target,old,year,url):
 if not target.is_file() or old.get('year')!=year or old.get('url')!=url or not old.get('etag'):return False
 if target.stat().st_size!=old.get('bytes') or old.get('bytes',0)<100:return False
 with target.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()==old.get('sha256')
def download_once(year,directory):
 url=BASE+f'sistema-unico-de-atencion-ciudadana-{year}.csv'
 directory.mkdir(parents=True,exist_ok=True);target=directory/f'suaci-{year}.csv';meta_path=directory/f'suaci-{year}.json'
 old=json.loads(meta_path.read_text()) if meta_path.exists() else {};headers={'User-Agent':'CEPOES-datos-publicos/1.0','Accept-Encoding':'identity'}
 valid_cache=cached_valid(target,old,year,url)
 if valid_cache:headers['If-None-Match']=old['etag']
 try:r=urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=90)
 except urllib.error.HTTPError as e:
  if e.code==304:
   e.close()
   if valid_cache:return old
   raise ValueError('304 sin CSV y manifiesto íntegros') from e
  e.close();raise
 tmp=None;meta_tmp=None
 try:
  with r:
   if r.status!=200 or 'text/csv' not in r.headers.get('Content-Type','').lower():raise ValueError(f'Respuesta no CSV completa: {year}, {r.status}')
   # urllib no descomprime Content-Encoding: comparar sólo bytes identity.
   if r.headers.get('Content-Encoding','identity').strip().lower()!='identity':raise ValueError('Content-Encoding inesperado')
   if r.headers.get('Content-Range'):raise ValueError('Respuesta parcial con Content-Range')
   length=r.headers.get('Content-Length')
   if length is not None and (not length.isascii() or not length.isdigit()):raise ValueError('Content-Length inválido')
   expected=int(length) if length is not None else None
   digest=hashlib.sha256();size=0
   with tempfile.NamedTemporaryFile(dir=directory,delete=False) as f:
    tmp=Path(f.name)
    while chunk:=r.read(1024*1024):
     digest.update(chunk);size+=len(chunk);f.write(chunk)
   if expected is not None and size!=expected:raise IncompleteDownload(f'Descarga incompleta: esperados={expected}, recibidos={size}')
   if size<100:raise ValueError('CSV vacío')
   with tmp.open('rb') as f:
    if b'nro_solicitud' not in f.readline():raise ValueError('Cabecera SUACI inesperada')
   meta={'year':year,'url':url,'catalog':CATALOG,'etag':r.headers.get('ETag'),'sha256':digest.hexdigest(),'bytes':size,'downloadedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
   # Preparar ambos archivos antes de reemplazar la versión válida.
   with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=directory,delete=False) as f:
    meta_tmp=Path(f.name);f.write(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
   os.replace(tmp,target);tmp=None
   os.replace(meta_tmp,meta_path);meta_tmp=None
   return meta
 finally:
  if tmp:tmp.unlink(missing_ok=True)
  if meta_tmp:meta_tmp.unlink(missing_ok=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path('_cache/suaci'));p.add_argument('--start-year',type=int,default=2025);a=p.parse_args()
 for year in range(a.start_year,datetime.date.today().year+1):
  m=download(year,a.directory);print(year,m['bytes'],m['sha256'])
