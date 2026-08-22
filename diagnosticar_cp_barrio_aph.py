#!/usr/bin/env python3
"""Diagnóstico liviano CP tradicional -> barrio usando APH 2018 de BA Data.

El recurso oficial aporta en una misma fila código postal, barrio, CPA y coordenadas.
No se descarga cartografía ni microdatos BCRA: se cruza la distribución CP->barrio
con el agregado por CP ya calculado y con los 48 agregados públicos de Mapa de la
Deuda usados exclusivamente como benchmark de QA.
"""
from __future__ import annotations

import csv
import io
import json
import math
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import requests

INPUT = Path("diagnostico_universo_territorial_integral.json")
OUTPUT = Path("diagnostico_cp_barrio_aph.json")
APH_PAGE = "https://data.buenosaires.gob.ar/dataset/areas-proteccion-historica/resource/juqdkmgo-94-resource"
APH_URL = APH_PAGE + "/download"
LOOKUP_URL = "https://datos.mapadeladeuda.ar/geo/lookup.json"
SLICE_URL = "https://datos.mapadeladeuda.ar/periods/2026-06/slices/barrio_caba/02/default.json"


def get(url, timeout=120):
    r = requests.get(url, headers={"User-Agent":"CEPOES-validacion-territorial/1.0"}, timeout=timeout)
    r.raise_for_status()
    return r


def norm(s):
    x = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode("ascii").upper()
    return " ".join(x.replace("-"," ").split())


def nfloat(v):
    if v is None: return None
    s=str(v).strip()
    if not s: return None
    if "," in s and "." not in s: s=s.replace(",",".")
    try: return float(s)
    except ValueError: return None


def cp4(v):
    n=nfloat(v)
    if n is None: return None
    i=int(round(n))
    return i if 1000 <= i <= 1499 else None


def cargar_lookup_benchmark():
    lookup=get(LOOKUP_URL).json()
    barrios={}
    for f in lookup.get("features",[]):
        if f.get("level")=="barrio_caba" and str(f.get("scope"))=="02":
            barrios[norm(f["nombre"])]=str(f["geo_id"])
    if len(barrios)!=48: raise RuntimeError(f"Lookup: {len(barrios)} barrios")
    sl=get(SLICE_URL).json(); cols=sl["columns"]; aliases=sl.get("aliases",{})
    bench={}
    for raw in sl["rows"]:
        d=raw if isinstance(raw,dict) else dict(zip(cols,raw))
        gid=str(d["geo_id"])
        bench[gid]={aliases.get(k,k):v for k,v in d.items() if k!="geo_id"}
    if len(bench)!=48: raise RuntimeError(f"Benchmark: {len(bench)} barrios")
    return barrios,bench


def cargar_aph(barrios):
    r=get(APH_URL,180); raw=r.content
    if len(raw)<1000: raise RuntimeError(f"APH muy pequeño: {len(raw)}")
    text=None; enc=None
    for e in ("utf-8-sig","utf-8","cp1252","latin1"):
        try: text=raw.decode(e); enc=e; break
        except UnicodeDecodeError: pass
    if text is None: raise RuntimeError("No se pudo decodificar APH")
    first=next((x for x in text.splitlines() if x.strip()),"")
    delim=max((";",",","\t"),key=lambda d:first.count(d))
    rd=csv.DictReader(io.StringIO(text),delimiter=delim)
    fields={norm(x).replace(" ","_").lower():x for x in (rd.fieldnames or []) if x}
    def col(*names):
        for n in names:
            if n in fields:return fields[n]
        return None
    ccp=col("codigo_postal","cod_postal","cp"); cb=col("barrio")
    clat=col("latitud","lat"); clon=col("longitud","lon","long")
    ccpa=col("codigo_postal_argentino","cpa")
    if not ccp or not cb: raise RuntimeError(f"APH sin CP/barrio. Campos={sorted(fields)}")
    counts=defaultdict(Counter); valid=unknown=rows=coords=0
    examples_unknown=Counter()
    for row in rd:
        rows+=1; cp=cp4(row.get(ccp)); bn=norm(row.get(cb) or "")
        if cp is None or not bn: continue
        gid=barrios.get(bn)
        if not gid:
            unknown+=1; examples_unknown[bn]+=1; continue
        valid+=1; counts[cp][gid]+=1
        if clat and clon and nfloat(row.get(clat)) is not None and nfloat(row.get(clon)) is not None: coords+=1
    meta={
      "pagina":APH_PAGE,"url_descarga":APH_URL,"url_final":r.url,"bytes":len(raw),"encoding":enc,"delimitador":delim,
      "campos":rd.fieldnames,"columnas":{"cp":ccp,"barrio":cb,"cpa":ccpa,"lat":clat,"lon":clon},
      "filas_leidas":rows,"filas_cp_barrio_validas":valid,"filas_con_coord":coords,"filas_barrio_no_reconocido":unknown,
      "cp_distintos":len(counts),"barrios_no_reconocidos_top":examples_unknown.most_common(10)
    }
    if valid<1000 or len(counts)<30: raise RuntimeError(f"APH cobertura insuficiente: {meta}")
    return counts,meta


def pearson(a,b):
    if len(a)<2:return None
    ma=statistics.fmean(a);mb=statistics.fmean(b)
    num=sum((x-ma)*(y-mb) for x,y in zip(a,b));da=math.sqrt(sum((x-ma)**2 for x in a));db=math.sqrt(sum((y-mb)**2 for y in b))
    return num/(da*db) if da and db else None


def compare(agg,bench):
    pairs={"deudores":("deudores","deudores_unicos_total",1),"mora":("personas_mora","deudores_unicos_mora",1),"deuda":("deuda_total_pesos","monto_total",1/1000),"deuda_mora":("deuda_mora_pesos","monto_mora",1/1000)}
    out={}
    gids=sorted(bench)
    for label,(of,bf,scale) in pairs.items():
        xs=[float(agg.get(g,{}).get(of,0))*scale for g in gids];ys=[float(bench[g].get(bf,0) or 0) for g in gids]
        sx=sum(xs);sy=sum(ys);fac=sy/sx if sx else 0
        raw=sum(abs(x-y) for x,y in zip(xs,ys))/sy*100 if sy else None
        normw=sum(abs(x*fac-y) for x,y in zip(xs,ys))/sy*100 if sy else None
        cor=pearson(xs,ys)
        out[label]={"total_asignado":round(sx,3),"benchmark_total":round(sy,3),"wape_raw_pct":round(raw,3) if raw is not None else None,"wape_distribucion_normalizada_pct":round(normw,3) if normw is not None else None,"correlacion_pearson":round(cor,4) if cor is not None else None}
    return out


def main():
    src=json.loads(INPUT.read_text(encoding="utf-8")); cp_rows={int(r["clave"]):r for r in src["agregado_cp_1000_1499"]["filas"]}
    barrios,bench=cargar_lookup_benchmark(); counts,meta=cargar_aph(barrios)
    methods={"moda_aph":{},"fraccional_aph":{}}
    ambiguous=[]
    for cp,c in counts.items():
        if len(c)>1: ambiguous.append({"cp":cp,"barrios":dict(c)})
        methods["moda_aph"][cp]=sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))[0][0]
        methods["fraccional_aph"][cp]={g:n/sum(c.values()) for g,n in c.items()}
    results={};total=sum(r["deudores"] for r in cp_rows.values())
    for method,mapping in methods.items():
        agg=defaultdict(lambda:defaultdict(float));covered=[]
        for cp,r in cp_rows.items():
            if cp not in mapping:continue
            covered.append(cp)
            weights={mapping[cp]:1.0} if method=="moda_aph" else mapping[cp]
            for gid,w in weights.items():
                for f in ("deudores","personas_mora","deuda_total_pesos","deuda_mora_pesos","registros"):
                    agg[gid][f]+=float(r.get(f,0) or 0)*w
        cov=sum(cp_rows[c]["deudores"] for c in covered)
        results[method]={"cp_asignados":len(covered),"cp_sin_aph":sorted(set(cp_rows)-set(covered)),"cobertura_deudores_pct":round(cov/total*100,4) if total else 0,"barrios_con_datos":len(agg),"comparacion_48":compare(dict(agg),bench)}
    out={"schema":"cepoes-cp-barrio-aph-v1","periodo":"2026-06","fuente_aph":meta,"controles":{"cp_bcra":len(cp_rows),"cp_aph":len(counts),"cp_ambiguos_multiples_barrios":len(ambiguous),"ambiguos":ambiguous},"resultados":results,"privacidad":{"microdatos_bcra_arca_leidos":False,"identificadores_personales_leidos":False,"solo_agregados_y_registro_publico":True}}
    OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"fuente":meta,"ambiguos":len(ambiguous),"resultados":results},ensure_ascii=False,indent=2))
    if max(x["cp_asignados"] for x in results.values())<30:raise SystemExit("Cobertura CP insuficiente")

if __name__=="__main__":main()
