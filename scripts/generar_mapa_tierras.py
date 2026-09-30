import json,math,argparse,html
p=argparse.ArgumentParser();p.add_argument("--datos",required=True);p.add_argument("--georef",required=True);p.add_argument("--salida",required=True);args=p.parse_args()
from pathlib import Path
from shapely.geometry import shape
rows=json.load(open(args.datos))['registros'];byid={x['id_georef']:x for x in rows if x['estado']!='duplicado_en_fuente'}
geometries=[json.loads(x) for x in open(args.georef)][1:]
def color(p):
 if p is None:return '#d9dfe4'
 if p>30:return '#7f1734'
 if p>15:return '#bd3c53'
 if p>=9:return '#df846e'
 if p>=5:return '#eac29e'
 return '#c9dcd5'
def project(p):return (round((p[0]+75)*22,2),round((-p[1]-20)*22,2))
parts=[]
for g in geometries:
 geom=shape(g['geometria']).simplify(.012,preserve_topology=True)
 polygons=list(geom.geoms) if geom.geom_type=='MultiPolygon' else [geom]
 paths=[]
 for poly in polygons:
  if poly.centroid.y < -60:continue
  for ring in [poly.exterior,*poly.interiors]:
   coords=[project(c) for c in ring.coords]
   paths.append('M'+'L'.join(f'{x},{y}' for x,y in coords)+'Z')
 if not paths:continue
 r=byid.get(g['id']);pct=r['pct'] if r else None
 value='Sin porcentaje informado' if pct is None else str(pct).replace('.',',')+'% · RNTR, agosto 2025'
 parts.append(f'<path data-id="{g["id"]}" d="{"".join(paths)}" fill="{color(pct)}"><title>{g["provincia"]["nombre"]} · {html.escape(g["nombre"])} · {value}</title></path>')
svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 630 815" aria-hidden="true" focusable="false" class="national-map"><g stroke="#344c5e" stroke-width=".45" fill-rule="evenodd">'+''.join(parts)+'</g></svg>'
Path(args.salida).write_text(svg)
print('Paths',len(parts),'SVG bytes',len(svg.encode()))
