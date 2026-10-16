#!/usr/bin/env python3
"""Normaliza SUACI oficial. Agregados sin identificadores de contacto ni género."""
import argparse,calendar,collections,csv,datetime,hashlib,json,os,re,tempfile,unicodedata
from zoneinfo import ZoneInfo
from pathlib import Path
CATALOG='https://data.buenosaires.gob.ar/dataset/sistema-unico-atencion-ciudadana'
CONFIG=Path(__file__).resolve().parents[1]/'config/limpieza-prestaciones.json'
def norm(s):return ''.join(c for c in unicodedata.normalize('NFD',s.strip().lower()) if unicodedata.category(c)!='Mn')
def geometry(path):
 names={'agronomia':'Agronomía','boca':'La Boca','paternal':'La Paternal','nunez':'Núñez','villa gral. mitre':'Villa General Mitre'}
 features=[]
 for f in json.loads(path.read_text())['features']:
  props=f['properties'];g=f['geometry'];rings=g['coordinates'] if g['type']=='Polygon' else [r for p in g['coordinates'] for r in p];reduced=[]
  for ring in rings:
   keep=ring[::6]
   if keep[-1]!=keep[0]:keep.append(keep[0])
   reduced.append([[round(x,6),round(y,6)] for x,y,*_ in keep])
  name=names.get(norm(props['nombre']),props['nombre'].title())
  features.append({'name':name,'comuna':str(props['comuna']),'rings':reduced})
 if len(features)!=48 or len({f['comuna'] for f in features})!=15:raise ValueError('Límites incompletos')
 return features

def generate(files,geo_path):
 mapping=json.loads(CONFIG.read_text())['groups'];types={norm(k):v for k,v in mapping.items()};features=geometry(geo_path);lookup={norm(f['name']):f for f in features}
 for alias,canonical in {'boca':'la boca','paternal':'la paternal','villa gral. mitre':'villa general mitre'}.items():lookup[alias]=lookup[canonical]
 raw_types=collections.Counter();counts=collections.Counter();streets=collections.Counter();seen={};selected_dates=[];all_dates=[];unknown=collections.Counter();missing=conflicts=duplicates=without_street=0;sources=[]
 for path in files:
  with path.open('rb') as raw_file:digest=hashlib.file_digest(raw_file,'sha256').hexdigest()
  meta=path.with_suffix('.json')
  if meta.exists() and json.loads(meta.read_text())['sha256']!=digest:raise ValueError('Huella CSV inconsistente')
  sources.append({'year':int(re.search(r'(20\d\d)',path.name)[1]),'sha256':digest,'bytes':path.stat().st_size})
  with path.open(encoding='utf-8-sig',newline='') as f:
   reader=csv.DictReader(f);required={'nro_solicitud','prestacion','fecha_ingreso','comuna','barrio','calle','altura','categoria','tipo'}
   if not required.issubset(reader.fieldnames or []):raise ValueError(f'Cambió el esquema: {path.name}')
   for row in reader:
    if None in row or row.get('estado_general') is None:raise ValueError('Fila truncada o mal formada')
    date=datetime.date.fromisoformat(row['fecha_ingreso'][:10]);all_dates.append(date)
    t=norm(row['prestacion'])
    if row['categoria']!='HIGIENE':continue
    if t not in types:unknown[t]+=1;continue
    ident=row['nro_solicitud'];payload=tuple(row.get(k,'') for k in ['prestacion','tipo','fecha_ingreso','barrio','comuna','calle','altura'])
    if not ident:raise ValueError('Contacto sin identificador')
    if ident in seen:
     if seen[ident]!=payload:raise ValueError('Contacto repetido con atributos diferentes')
     duplicates+=1;continue
    seen[ident]=payload;raw_types[row['prestacion']]+=1;b=row['barrio'];bn=norm(b);feature=lookup.get(bn)
    if bn and not feature:raise ValueError(f'Barrio desconocido: {b}')
    b=feature['name'] if feature else '';c=feature['comuna'] if feature else str(row['comuna']).strip()
    if c and c not in map(str,range(1,16)):raise ValueError('Comuna desconocida')
    conflicts+=bool(feature and str(row['comuna']).strip()!=c);missing+=not bool(b)
    selected_dates.append(date);counts[(b,c,date.strftime('%Y-%m'),types[t],row['tipo'].strip() or 'Sin tipo informado')]+=1
 if unknown:raise ValueError('Prestaciones nuevas por revisar: '+str(dict(unknown)))
 if not selected_dates:raise ValueError('Sin registros de higiene')
 first=min(all_dates);last=max(all_dates);today=datetime.datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date()
 if last>today:raise ValueError('Fechas futuras')
 all_months=[];cursor=first.replace(day=1)
 while cursor<=last:
  all_months.append(cursor.strftime('%Y-%m'));cursor=(cursor.replace(day=28)+datetime.timedelta(days=4)).replace(day=1)
 return {'schema':2,'sourceKind':'official','source':CATALOG,'primarySource':CATALOG,'sources':sources,'periodStart':first.isoformat(),'periodEnd':last.isoformat(),'months':all_months,'lastMonthPartial':last.day<calendar.monthrange(last.year,last.month)[1],'total':len(seen),'missingBarrio':missing,'comunaConflictsResolvedFromBarrio':conflicts,'duplicatesRemoved':duplicates,'sourceTypes':dict(sorted(raw_types.items())),'types':sorted(set(mapping.values())),'contactKinds':sorted({k[4] for k in counts}),'counts':[list(k)+[v] for k,v in sorted(counts.items())],'features':features}

def validate(d,previous=None):
 if d['total']!=sum(r[5] for r in d['counts']):raise ValueError('Suma inconsistente')
 if len(d['features'])!=48 or len({f['comuna'] for f in d['features']})!=15:raise ValueError('Cobertura incompleta')
 if len({r[0] for r in d['counts'] if r[0]})!=48:raise ValueError('Faltan barrios con registros')
 if previous and previous.get('sourceKind')=='official':
  if d['periodEnd']<previous['periodEnd']:raise ValueError('Retroceso de corte')
  old=collections.Counter();new=collections.Counter()
  for r in previous['counts']:old[r[2]]+=r[5]
  for r in d['counts']:new[r[2]]+=r[5]
  for m,n in old.items():
   if new[m]<n:raise ValueError(f'Retroceso en {m}: revisión necesaria')

def atomic_write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as f:
  f.write(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n');tmp=f.name
 os.replace(tmp,path)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--geometry',type=Path,default=Path('badata/barrios.geojson'));p.add_argument('--output',type=Path,default=Path('deploy/site-overlay/assets/data/limpieza-urbana.json'));a=p.parse_args()
 files=sorted(a.directory.glob('suaci-20??.csv'))
 if not files:raise SystemExit('Faltan CSV oficiales completos')
 # El descargador genera manifiestos; en pruebas locales se exige al menos un salto de línea final.
 for file in files:
  with file.open('rb') as f:f.seek(-1,2);last=f.read(1)
  if last!=b'\n':raise SystemExit('Descarga sin completar: '+file.name)
 d=generate(files,a.geometry);previous=json.loads(a.output.read_text()) if a.output.exists() else None;validate(d,previous)
 if previous and {k:v for k,v in previous.items() if k not in ['retrieved','dataUpdatedAt']}==d:print('Sin cambios');raise SystemExit(0)
 d['retrieved']=datetime.datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date().isoformat();d['dataUpdatedAt']=datetime.datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date().isoformat();atomic_write(a.output,d)
 print(json.dumps({k:d[k] for k in ['total','periodStart','periodEnd','missingBarrio','comunaConflictsResolvedFromBarrio','duplicatesRemoved']},ensure_ascii=False))
