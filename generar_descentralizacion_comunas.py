#!/usr/bin/env python3
"""CEPOES · Descentralización comunal: presupuesto administrado por las Comunas.

IMPORTANTE: diferencia presupuesto *administrado por la entidad/unidad ejecutora
Comuna N* de gasto meramente geocodificado en Desc_Geo=Comuna N.
"""
from __future__ import annotations
import csv, io, json, re, unicodedata, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

CKAN_IDS=("presupuesto-ejecutado","presupuesto-ejecutado-2026")
CKAN_BASE="https://data.buenosaires.gob.ar/api/3/action/package_show?id="
OUT_ROOT=Path("descentralizacion_comunas.json")
OUT_PUBLIC=Path("deploy/site-overlay/assets/data/descentralizacion-comunas.json")
UA="CEPOES-data-pipeline/1.0"
# Censo 2022, mismos totales territoriales ya usados por CEPOES.
POP={1:221001,2:160609,3:193537,4:227024,5:192449,6:201764,7:213262,8:203888,9:167908,10:171896,11:201905,12:235364,13:262330,14:247252,15:195265}


def norm(v):
    s=unicodedata.normalize("NFKD",str(v or "")).encode("ascii","ignore").decode().lower().strip()
    return re.sub(r"[^a-z0-9]+","_",s).strip("_")

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)

def get_bytes(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=180) as r:return r.read()

def package():
    errs=[]
    for pid in CKAN_IDS:
        try:
            x=get_json(CKAN_BASE+pid)
            if x.get("success"):return x["result"]
        except Exception as e: errs.append(f"{pid}: {e}")
    raise RuntimeError("No se pudo resolver dataset presupuesto: "+"; ".join(errs))

def choose_resource(pkg):
    candidates=[]
    for r in pkg.get("resources",[]):
        text=f"{r.get('name','')} {r.get('description','')}".lower()
        fmt=str(r.get("format","")).lower()
        if "2026" not in text or "csv" not in fmt: continue
        q=0
        if "cuarto" in text or re.search(r"\b4(?:to)?\s*trimestre\b", text): q=4
        elif "tercer" in text or re.search(r"\b3(?:er)?\s*trimestre\b", text): q=3
        elif "segundo" in text or re.search(r"\b2(?:do)?\s*trimestre\b", text): q=2
        elif "primer" in text or re.search(r"\b1(?:er)?\s*trimestre\b", text): q=1
        candidates.append((q,r))
    if not candidates: raise RuntimeError("No se encontró CSV de Presupuesto Ejecutado 2026")
    return max(candidates,key=lambda x:x[0])

def decode(raw):
    text=None
    for enc in ("utf-8-sig","utf-8","latin-1"):
        try:text=raw.decode(enc);break
        except UnicodeDecodeError:pass
    if text is None:raise RuntimeError("No se pudo decodificar presupuesto")
    try: delim=csv.Sniffer().sniff(text[:20000],delimiters=",;\t|").delimiter
    except csv.Error:delim="," 
    rd=csv.DictReader(io.StringIO(text),delimiter=delim)
    return list(rd.fieldnames or []), rd

def fnum(v):
    s=str(v or "").strip().replace(" ","")
    if not s:return 0.0
    # CKAN suele exportar decimal con punto; tolerar coma decimal.
    if s.count(",")==1 and "." not in s:s=s.replace(",",".")
    try:return float(s)
    except:return 0.0

def colmap(fields):return {norm(f):f for f in fields}
def find_amount(m,prefixes):
    for p in prefixes:
        for n,o in m.items():
            if p in n:return o
    return None

def commune_number(row,m):
    # Fuente canónica: entidad administrativa y/o unidad ejecutora. NO Desc_Geo.
    for key in ("ent_desc","desc_ent","ue_desc","desc_ue"):
        col=m.get(key)
        if not col:continue
        s=norm(row.get(col))
        mt=re.fullmatch(r"comuna_?(1[0-5]|[1-9])",s)
        if mt:return int(mt.group(1))
    return None

def main():
    pkg=package(); quarter,res=choose_resource(pkg)
    fields,rows=decode(get_bytes(res["url"]));m=colmap(fields)
    vig=find_amount(m,("vigente_trim","vigente"));dev=find_amount(m,("devengado_trim","devengado"));sanc=find_amount(m,("sancion",));defi=find_amount(m,("definitivo_trim","definitivo"))
    if not vig or not dev or not sanc: raise SystemExit(f"Columnas monetarias no reconocidas: {fields}")
    inc=m.get("inciso") or m.get("inc"); incd=m.get("inciso_desc") or m.get("desc_inc") or m.get("inc_desc")
    geod=m.get("geo_desc") or m.get("desc_geo")
    acc={i:{"sancionado":0.0,"vigente":0.0,"definitivo":0.0,"devengado":0.0,"rows":0,"incisos":defaultdict(float)} for i in range(1,16)}
    territorial=defaultdict(lambda:{"vigente":0.0,"devengado":0.0})
    total_vig=total_dev=0.0
    admin_rows=0
    for row in rows:
        v=fnum(row.get(vig));d=fnum(row.get(dev));s=fnum(row.get(sanc));df=fnum(row.get(defi)) if defi else 0.0
        total_vig+=v;total_dev+=d
        if geod:
            mg=re.fullmatch(r"comuna_?(1[0-5]|[1-9])",norm(row.get(geod)))
            if mg:
                g=int(mg.group(1));territorial[g]["vigente"]+=v;territorial[g]["devengado"]+=d
        c=commune_number(row,m)
        if not c:continue
        admin_rows+=1;a=acc[c];a["sancionado"]+=s;a["vigente"]+=v;a["definitivo"]+=df;a["devengado"]+=d;a["rows"]+=1
        label=str(row.get(incd) or row.get(inc) or "Sin clasificar").strip();a["incisos"][label]+=v
    if admin_rows==0: raise SystemExit("No se identificaron filas administradas por Comunas. No se usará Desc_Geo como sustituto.")
    missing=[c for c in range(1,16) if acc[c]["rows"]==0]
    if missing: raise SystemExit(f"Faltan entidades/unidades ejecutoras comunales: {missing}")
    sum_communes=sum(x["vigente"] for x in acc.values())
    out_comm=[]
    for c in range(1,16):
        a=acc[c]; pop=POP[c]
        out_comm.append({
            "comuna":c,"poblacion_censo_2022":pop,
            "administrado":{"sancionado":round(a["sancionado"],2),"vigente":round(a["vigente"],2),"definitivo":round(a["definitivo"],2),"devengado":round(a["devengado"],2),"ejecucion_pct":round(a["devengado"]/a["vigente"]*100,2) if a["vigente"] else None,"vigente_por_habitante":round(a["vigente"]/pop,2),"participacion_comunas_pct":round(a["vigente"]/sum_communes*100,2) if sum_communes else None,"composicion_vigente":dict(sorted((k,round(v,2)) for k,v in a["incisos"].items()))},
            "gasto_localizado":{"vigente":round(territorial[c]["vigente"],2),"devengado":round(territorial[c]["devengado"],2)},
        })
    per=[x["administrado"]["vigente_por_habitante"] for x in out_comm]
    output={
        "schema":"cepoes-descentralizacion-comunas-v1","status":"VALIDADO","generated_at":datetime.now(timezone.utc).isoformat(),"year":2026,"quarter":quarter,
        "headline":{"presupuesto_administrado_comunas_vigente":round(sum_communes,2),"participacion_presupuesto_gcba_pct":round(sum_communes/total_vig*100,4) if total_vig else None,"ejecucion_comunas_pct":round(sum(x["administrado"]["devengado"] for x in out_comm)/sum_communes*100,2) if sum_communes else None,"brecha_per_capita_max_min":round(max(per)/min(per),2) if min(per)>0 else None},
        "comunas":out_comm,
        "totales_gcba":{"vigente":round(total_vig,2),"devengado":round(total_dev,2)},
        "methodology":{"administrado":"Sólo se considera presupuesto comunal cuando la entidad administrativa o unidad ejecutora se identifica como Comuna 1 a Comuna 15.","territorial":"Desc_Geo/geo_desc se conserva como gasto localizado territorialmente, pero NO se interpreta como presupuesto administrado por la comuna.","poblacion":"Censo 2022; se usa únicamente para indicadores per cápita.","indice_descentralizacion":"Aún no se calcula. Esta V1 construye el componente presupuestario que luego integrará la matriz de cumplimiento de Ley 1.777."},
        "source":{"name":res.get("name"),"url":res.get("url"),"resource_id":res.get("id"),"dataset":pkg.get("name")},
        "quality":{"admin_rows":admin_rows,"fields":fields,"amount_columns":{"sancionado":sanc,"vigente":vig,"definitivo":defi,"devengado":dev}},
    }
    text=json.dumps(output,ensure_ascii=False,separators=(",",":"))
    for p in (OUT_ROOT,OUT_PUBLIC):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding="utf-8")
    print(f"Descentralización · T{quarter} 2026 · 15 comunas · administrado vigente={sum_communes:.0f} · peso GCBA={output['headline']['participacion_presupuesto_gcba_pct']}%")
if __name__=="__main__":main()
