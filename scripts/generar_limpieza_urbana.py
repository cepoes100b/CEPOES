#!/usr/bin/env python3
"""Agrega una copia verificada del derivado SUACI de LA NACION; no descarga ni publica."""
import argparse, collections, datetime, hashlib, json, unicodedata
from pathlib import Path
SOURCE='https://especialess3.lanacion.com.ar/interactivos/26/08/mapa-basura-caba/reclamos-compact.json'
def norm(s):
 s=''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn')
 return {'boca':'la boca','paternal':'la paternal','villa gral. mitre':'villa general mitre'}.get(s,s)
def generate(source,geometry,output):
 raw=source.read_bytes();d=json.loads(raw);ds=d['dictionaries'];rows=d['points']
 assert d['type']=='ln-claims-compact-v2'
 assert d['columns']==['lng','lat','analysis_lng','analysis_lat','fecha','cuadra','barrio','comuna','prestacion']
 counts=collections.Counter();streets=collections.Counter();dates=[];missing=0
 for r in rows:
  assert len(r)==9
  date=ds['fechas'][r[4]];datetime.date.fromisoformat(date);dates.append(date)
  assert '2025-05-01'<=date<='2026-04-30'
  b=ds['barrios'][r[6]];c=ds['comunas'][r[7]].replace('COMUNA ','');t=ds['prestaciones'][r[8]];q=ds['cuadras'][r[5]]
  counts[(b,c,date[:7],t)]+=1;streets[(b,c,q)]+=1
  missing+=not bool(b)
 assert len(rows)==276240, 'Cambió la fuente: revisar antes de regenerar'
 geo=json.loads(geometry.read_text());features=[]
 for f in geo['features']:
  props=f['properties'];g=f['geometry'];rings=g['coordinates'] if g['type']=='Polygon' else [ring for poly in g['coordinates'] for ring in poly]
  # Retener vértices originales: simplificación sólo para el mapa de comparación por barrio.
  reduced=[]
  for ring in rings:
   keep=ring[::6]
   if keep[-1]!=keep[0]:keep.append(keep[0])
   reduced.append([[round(x,6),round(y,6)] for x,y,*_ in keep])
  match=next((b for b in ds['barrios'] if norm(b)==norm(props['nombre'])),None)
  assert match, props['nombre']
  features.append({'name':match,'comuna':str(props['comuna']),'rings':reduced})
 assert len(features)==48 and len({f['comuna'] for f in features})==15
 top=[]
 for b in ds['barrios']:
  top.extend([list(k)+[v] for k,v in sorted(((k,v) for k,v in streets.items() if k[0]==b and k[2]),key=lambda x:(-x[1],x[0]))[:20]])
 result={'schema':1,'source':SOURCE,'primarySource':'https://data.buenosaires.gob.ar/dataset/sistema-unico-atencion-ciudadana','sourceSha256':hashlib.sha256(raw).hexdigest(),'periodStart':min(dates),'periodEnd':max(dates),'retrieved':'2026-10-16','total':len(rows),'articleTotal':276473,'difference':233,'missingBarrio':missing,'types':ds['prestaciones'],'counts':[list(k)+[v] for k,v in sorted(counts.items())],'topStreets':top,'features':features}
 assert sum(x[-1] for x in result['counts'])==result['total']
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
 print(json.dumps({k:result[k] for k in ['total','difference','missingBarrio','periodStart','periodEnd','sourceSha256']},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--geometry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();generate(a.source,a.geometry,a.output)
