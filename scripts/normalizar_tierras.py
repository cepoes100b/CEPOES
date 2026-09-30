from pathlib import Path
import json,re,unicodedata,hashlib,argparse
p=argparse.ArgumentParser();p.add_argument("--texto",required=True);p.add_argument("--pdf",required=True);p.add_argument("--georef",required=True);p.add_argument("--salida",required=True);args=p.parse_args()
def norm(s):return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn').strip()
def number(s):return float(s.replace('.','').replace(',','.'))
provinces=['Buenos Aires','Catamarca','Chaco','Chubut','Cordoba','Corrientes','Entre Rios','Formosa','Jujuy','La Pampa','La Rioja','Mendoza','Misiones','Neuquen','Rio Negro','Salta','San Juan','San Luis','Santa Cruz','Santa Fe','Santiago del Estero','Tierra del Fuego, Ant.Arg e Islas Atl.Sur','Tucuman']
rows=[];prov=None;totals={};bad=[]
for line in Path(args.texto).read_text().splitlines():
 line=line.strip()
 if not line or 'Superficie Rural' in line:continue
 match=re.match(r'^(.*?)\s+([\d.]+,\d\d)(.*)$',line)
 if not match:bad.append(line);continue
 name,area,tail=match.groups();values=re.findall(r'[\d.]+,\d\d',tail)
 if name=='Nacion':totals['nacion']={'rural_ha':number(area),'extranjera_ha':number(values[0]),'pct':number(values[1])};continue
 if name in provinces and name != prov:
  prov=name;totals[prov]={'rural_ha':number(area),'extranjera_ha':number(values[0]),'pct':number(values[1])};continue
 assert prov,(name,line)
 rural=number(area);ha=number(values[0]) if len(values)==2 else None;pct=number(values[-1]) if values else None
 rows.append(dict(provincia=prov,departamento=name,rural_ha=rural,extranjera_ha=ha,pct=pct,estado='sin_superficie_rural' if rural==0 else ('hectareas_sin_informar' if ha is None else 'observado')))
assert not bad,bad
assert len(totals)==24,len(totals)
geo=[json.loads(x) for x in Path(args.georef).read_text().splitlines()][1:]
aliases={'ameghino':'florentino ameghino','gonzalez chaves':'adolfo gonzales chaves','juarez':'benito juarez','matanza':'la matanza','pte peron':'presidente peron','antofagasta':'antofagasta de la sierra','general angel v. penaloza':'general angel vicente penaloza','general juan f. quiroga':'general juan facundo quiroga','general san martin':'libertador general san martin','general jose de san martin':'general jose de san martin','l. gral. san martin':'libertador general san martin'}
index={(norm(g['provincia']['nombre']),norm(g['nombre'])):g for g in geo}
specific={('Buenos Aires','Coronel Rosales'):'Coronel de Marina Leonardo Rosales',('Buenos Aires','General Lamadrid'):'General La Madrid',('Buenos Aires','General Madariaga'):'General Juan Madariaga',('Buenos Aires','Nueve de Julio'):'9 de Julio',('Buenos Aires','Veinticinco de Mayo'):'25 de Mayo',('Chaco','1 de Mayo'):'1° de Mayo',('Chaco','Mayor Jorge Luis Fontana'):'Mayor Luis J. Fontana',('Chaco','Presidente de la Plaza'):'Presidencia de la Plaza',('Jujuy','Manuel Belgrano'):'Dr. Manuel Belgrano',('La Rioja','Coronel Felipe Varela'):'General Felipe Varela',('La Rioja','General Angel V. Penaloza'):'Ángel Vicente Peñaloza',('La Rioja','General Ocampo'):'General Ortiz de Ocampo',('Misiones','General Belgrano'):'General Manuel Belgrano',('Santiago del Estero','Juan F. Ibarra'):'Juan Felipe Ibarra',('Tucuman','Juan B. Alberdi'):'Juan Bautista Alberdi',('Tucuman','San Miguel de Tucuman'):'Capital'}
unmatched=[]
for row in rows:
 pn=norm(row['provincia']);dn=norm(row['departamento'])
 if pn.startswith('tierra del fuego'):pn='tierra del fuego, antartida e islas del atlantico sur'
 g=index.get((pn,dn)) or index.get((pn,norm(specific.get((row['provincia'],row['departamento']),aliases.get(dn,dn)))))
 if not g:unmatched.append((row['provincia'],row['departamento']))
 else:row['id']=g['id']
print('Registros',len(rows),'totales',len(totals),'sobre15',sum(r['pct'] is not None and r['pct']>15 for r in rows),'sin cruce',unmatched)
data={'fuente':'RNTR','fuente_url':'https://www.argentina.gob.ar/sites/default/files/2021/02/extranjerizacion_por_departamento_pdf.pdf','publicacion':'2025-08','sha256_pdf':hashlib.sha256(Path(args.pdf).read_bytes()).hexdigest(),'totales':totals,'registros':rows,'nota':'Las celdas vacías se conservan como null. Porcentajes publicados con dos decimales. Los límites administrativos de Georef pueden diferir del corte registral.'}
assert len(rows)==513, 'Revisar cobertura del nuevo corte antes de publicar'
assert not unmatched, unmatched
seen=set()
for row in rows:
 row['id_georef']=row['id']
 if row['id'] in seen:
  assert row['provincia']=='Corrientes' and row['departamento']=='ituzaingo' and row['rural_ha']==0, 'Nuevo duplicado: revisar fuente'
  row['id']+='-duplicado'
  row['estado']='duplicado_en_fuente'
 seen.add(row['id'])
assert len(seen)==513
assert len({r['id_georef'] for r in rows})==512
Path(args.salida).parent.mkdir(parents=True,exist_ok=True)
Path(args.salida).write_text(json.dumps(data,ensure_ascii=False,indent=2))

