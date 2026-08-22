#!/usr/bin/env python3
import io, json, math, re, unicodedata, urllib.request, zipfile
from collections import Counter, defaultdict
from pathlib import Path
from shapely.geometry import Point, shape

GEONAMES='https://download.geonames.org/export/zip/AR.zip'
BARRIOS='https://cdn.buenosaires.gob.ar/datosabiertos/datasets/barrios/barrios.geojson'
MAPA_SLICE='https://datos.mapadeladeuda.ar/periods/2026-06/slices/barrio_caba/02/default.json'
MAPA_LOOKUP='https://datos.mapadeladeuda.ar/geo/lookup.json'
INPUT=Path('diagnostico/diagnostico_universo_territorial_integral.json')
OUT=Path('diagnostico_geocodificacion_postal_barrios.json')

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'CEPOES-metodologia/2.29'})
    with urllib.request.urlopen(req,timeout=90) as r: return r.read()

def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]+',' ',s).strip()

def corr(xs,ys):
    if not xs or len(xs)!=len(ys): return None
    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
    num=sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    den=(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))**0.5
    return num/den if den else None

def main():
    src=json.loads(INPUT.read_text())
    cp_rows={int(x['clave']):x for x in src['agregado_cp_1000_1499']['filas']}

    gj=json.loads(get(BARRIOS))
    barrios=[]
    for f in gj['features']:
        p=f.get('properties',{})
        name=p.get('BARRIO') or p.get('barrio') or p.get('Barrio')
        barrios.append((norm(name),name,shape(f['geometry'])))
    assert len(barrios)==48

    z=zipfile.ZipFile(io.BytesIO(get(GEONAMES)))
    txt=z.read('AR.txt').decode('utf-8')
    candidates=defaultdict(list)
    geonames_rows=0
    for line in txt.splitlines():
        a=line.split('\t')
        if len(a)<12: continue
        postal=a[1].strip().upper()
        m=re.fullmatch(r'C?(\d{4})',postal)
        if not m: continue
        cp=int(m.group(1))
        if not (1000<=cp<=1499): continue
        try: lat=float(a[9]); lon=float(a[10])
        except: continue
        pt=Point(lon,lat)
        hits=[bn for bn,raw,poly in barrios if poly.covers(pt)]
        if hits:
            candidates[cp].append({'barrio':hits[0],'postal':postal,'place':a[2],'admin1':a[3],'lat':lat,'lon':lon,'accuracy':a[11]})
            geonames_rows+=1

    lookup=json.loads(get(MAPA_LOOKUP))
    # lookup puede ser lista o diccionario/anidado: recorrer recursivamente objetos con geo_id.
    geo_name={}
    def walk(x):
        if isinstance(x,dict):
            if x.get('geo_id') and x.get('nombre') and x.get('level')=='barrio_caba': geo_name[str(x['geo_id'])]=norm(x['nombre'])
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(lookup)
    sl=json.loads(get(MAPA_SLICE)); cols=sl['columns']
    bench={}
    for row in sl['rows']:
        d=dict(zip(cols,row)); bn=geo_name.get(str(d['geo_id']))
        if bn: bench[bn]={'deudores':d['du'],'mora':d['dm'],'deuda':d['mt'],'deuda_mora':d['mm']}
    assert len(bench)==48

    strategies={}
    for strategy in ('modo_geonames','unico_barrio'):
        agg=defaultdict(lambda: {'deudores':0,'mora':0,'deuda':0,'deuda_mora':0,'cps':0})
        assigned=[]; ambiguous=[]; missing=[]
        for cp,r in cp_rows.items():
            cs=candidates.get(cp,[])
            if not cs:
                missing.append(cp); continue
            counts=Counter(c['barrio'] for c in cs)
            if strategy=='unico_barrio':
                if len(counts)!=1:
                    ambiguous.append({'cp':cp,'barrios':dict(counts)}); continue
                bn=next(iter(counts))
            else:
                top=counts.most_common()
                if len(top)>1 and top[0][1]==top[1][1]:
                    ambiguous.append({'cp':cp,'barrios':dict(counts)}); continue
                bn=top[0][0]
            a=agg[bn]; a['deudores']+=r['deudores']; a['mora']+=r['personas_mora']; a['deuda']+=r['deuda_total_pesos']; a['deuda_mora']+=r['deuda_mora_pesos']; a['cps']+=1
            assigned.append(cp)
        rows=[]
        total_ours=sum(v['deudores'] for v in agg.values()); total_b=sum(v['deudores'] for v in bench.values())
        xs=[]; ys=[]; share_abs=[]
        for bn in sorted(bench):
            o=agg.get(bn,{'deudores':0,'mora':0,'deuda':0,'deuda_mora':0,'cps':0}); b=bench[bn]
            xs.append(o['deudores']); ys.append(b['deudores'])
            so=o['deudores']/total_ours if total_ours else 0; sb=b['deudores']/total_b if total_b else 0
            share_abs.append(abs(so-sb))
            rows.append({'barrio':bn,'cepoes':o,'benchmark':b,'dif_deudores':o['deudores']-b['deudores'],'dif_mora':o['mora']-b['mora'],'share_cepoes':round(so,6),'share_benchmark':round(sb,6)})
        strategies[strategy]={
            'cp_asignados':len(assigned),'cp_sin_geonames':len(missing),'cp_ambiguos':len(ambiguous),
            'deudores_asignados':total_ours,'cobertura_deudores_pct':round(100*total_ours/sum(r['deudores'] for r in cp_rows.values()),4),
            'correlacion_deudores_48':round(corr(xs,ys),6) if corr(xs,ys) is not None else None,
            'error_medio_absoluto_share_pp':round(100*sum(share_abs)/48,4),
            'ambiguos':ambiguous[:100],'sin_geonames':missing,'barrios':rows}

    out={
      'schema':'cepoes-geocodificacion-postal-barrios-v1','periodo':'2026-06',
      'hipotesis':'GeoNames postal AR (C+4 digitos) -> punto WGS84 -> poligono oficial de barrio CABA; benchmark Mapa de la Deuda sólo para QA',
      'fuentes':{'geonames':GEONAMES,'barrios_caba':BARRIOS,'benchmark':MAPA_SLICE,'lookup':MAPA_LOOKUP},
      'geonames':{'filas_caba_dentro_poligonos':geonames_rows,'cp_con_al_menos_un_punto':len(candidates)},
      'estrategias':strategies,
      'nota':'Esta prueba no adopta GeoNames ni BA Data como metodología final. Sirve para medir cobertura y similitud espacial. No usa valores de deuda para decidir la asignación CP->barrio.'
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps({k:{x:v[x] for x in ['cp_asignados','cp_sin_geonames','cp_ambiguos','deudores_asignados','cobertura_deudores_pct','correlacion_deudores_48','error_medio_absoluto_share_pp']} for k,v in strategies.items()},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
