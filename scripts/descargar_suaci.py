#!/usr/bin/env python3
"""Descarga anual SUACI con control de tipo, tamaño y reemplazo atómico."""
import argparse,datetime,hashlib,json,os,tempfile,urllib.request
from pathlib import Path
BASE='https://cdn.buenosaires.gob.ar/datosabiertos/datasets/atencion-ciudadana/sistema-unico-atencion-ciudadana/'
CATALOG='https://data.buenosaires.gob.ar/dataset/sistema-unico-atencion-ciudadana'
def download(year,directory):
 url=BASE+f'sistema-unico-de-atencion-ciudadana-{year}.csv'
 directory.mkdir(parents=True,exist_ok=True);target=directory/f'suaci-{year}.csv';meta_path=directory/f'suaci-{year}.json'
 old=json.loads(meta_path.read_text()) if meta_path.exists() else {};headers={'User-Agent':'CEPOES-datos-publicos/1.0'}
 if target.exists() and old.get('etag'):headers['If-None-Match']=old['etag']
 try:r=urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=90)
 except urllib.error.HTTPError as e:
  if e.code==304 and target.exists():return old
  raise
 tmp=None
 try:
  with r:
   if r.status!=200 or 'text/csv' not in r.headers.get('Content-Type','').lower():raise ValueError(f'Respuesta no CSV completa: {year}, {r.status}')
   expected=int(r.headers['Content-Length']) if r.headers.get('Content-Length') else None
   digest=hashlib.sha256();size=0
   with tempfile.NamedTemporaryFile(dir=directory,delete=False) as f:
    tmp=Path(f.name)
    while chunk:=r.read(1024*1024):
     digest.update(chunk);size+=len(chunk);f.write(chunk)
   if expected is not None and size!=expected:raise ValueError('Descarga incompleta')
   if size<100:raise ValueError('CSV vacío')
   with tmp.open('rb') as f:
    if b'nro_solicitud' not in f.readline():raise ValueError('Cabecera SUACI inesperada')
   os.replace(tmp,target);tmp=None
   meta={'year':year,'url':url,'catalog':CATALOG,'etag':r.headers.get('ETag'),'sha256':digest.hexdigest(),'bytes':size,'downloadedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
   meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');return meta
 finally:
  if tmp:tmp.unlink(missing_ok=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path('_cache/suaci'));p.add_argument('--start-year',type=int,default=2025);a=p.parse_args()
 for year in range(a.start_year,datetime.date.today().year+1):
  m=download(year,a.directory);print(year,m['bytes'],m['sha256'])
