#!/usr/bin/env python3
"""Actualiza Personas mayores y conserva el último conjunto validado si una fuente falla."""
from __future__ import annotations
import argparse,json,re,unicodedata
from concurrent.futures import ThreadPoolExecutor,as_completed
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"deploy/site-overlay/assets/data/personas-mayores.json"
PAGE=ROOT/"deploy/site-overlay/observatorio/personas-mayores/index.html"
AGES="https://www.estadisticaciudad.gob.ar/si/demog/principal-indicador?indicador=b11"
AGING="https://www.estadisticaciudad.gob.ar/si/demog/principal-indicador?indicador=b14"
DEFENSORIA_SITEMAP="https://defensoria.org.ar/wp-sitemap.xml"
KNOWN_BASKET="https://defensoria.org.ar/noticias/aumentos-en-el-ipm-y-la-canasta-de-consumo-para-adultos-as-mayores-durante-mayo/"
UA="CEPOES-data-bot/1.0 (+https://cepoes.org/)";TIMEOUT=40
MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}

def norm(s):
    s=unicodedata.normalize("NFD",s or "")
    return re.sub(r"\s+"," ","".join(c for c in s if unicodedata.category(c)!="Mn")).strip().lower()

def get(session,url,**params):
    last=None
    for _ in range(2):
        try:
            r=session.get(url,params=params or None,headers={"User-Agent":UA},timeout=TIMEOUT);r.raise_for_status();return r
        except Exception as exc:last=exc
    raise RuntimeError(f"{url}: {last}")

def text(source):return re.sub(r"\s+"," ",BeautifulSoup(source,"html.parser").get_text(" ",strip=True))

def years_values(fragment):
    years=[int(x) for x in re.findall(r"(?<![\d,.])(?:20|19|18)\d{2}(?![\d,.])",fragment)]
    return years

def parse_ages(source):
    t=text(source);start=norm(t).find("porcentaje de poblacion segun grupos funcionales de edad")
    if start<0:raise ValueError("encabezado b11 ausente")
    t=t[start:];tab=norm(t).rfind("grupo de edad ano")
    if tab>=0:t=t[tab:]
    unit=norm(t).find("unidad de medida")
    if unit>0:t=t[:unit]
    row0=re.search(r"0\s*-\s*14",t)
    years=years_values(t[:row0.start()] if row0 else t)
    def row(label):
        m=re.search(label+r"\s+((?:\d+[,.]\d+\s*){"+str(len(years))+r"})",t,re.I)
        if not m:raise ValueError(f"fila {label} ausente")
        return [float(x.replace(",",".")) for x in re.findall(r"\d+[,.]\d+",m.group(1))]
    return {"anios":years,"poblacion_65_mas":row(r"65\s+y\s+m[aá]s"),"poblacion_80_mas":row(r"80\s+y\s+m[aá]s")}

def parse_aging(source):
    t=text(source);start=norm(t).find("indice de envejecimiento ano")
    if start<0:raise ValueError("encabezado b14 ausente")
    t=t[start:];tab=norm(t).rfind("indice de envejecimiento ano")
    if tab>=0:t=t[tab:]
    unit=norm(t).find("unidad de medida")
    if unit>0:t=t[:unit]
    first_value=re.search(r"(?<!\d)\d{1,3},\d(?!\d)",t)
    years=years_values(t[:first_value.start()] if first_value else t)
    values=[float(x.replace(",",".")) for x in re.findall(r"(?<!\d)\d{1,3},\d(?!\d)",t[first_value.start():] if first_value else "")]
    if len(values)<len(years):raise ValueError("valores b14 incompletos")
    return {"anios":years,"valores":values[:len(years)]}

def period(t):
    n=norm(t)
    for month,num in MONTHS.items():
        m=re.search(rf"\b{month}\s+de\s+(20\d{{2}})\b",n)
        if m:return f"{m.group(1)}-{num:02d}"
    raise ValueError("período no encontrado")

def parse_basket(source,url):
    t=text(source);p=period(t)
    owner=re.search(r"vivienda propia necesit[oó].{0,110}?\$\s*([\d.]+).{0,90}?([\d,]+)%\s+m[aá]s",t,re.I)
    renter=re.search(r"que alquila.{0,110}?\$\s*([\d.]+).{0,90}?([\d,]+)%\s+mayor",t,re.I)
    meds=re.search(r"medicamentos registraron un aumento promedio del\s*([\d,]+)%",t,re.I)
    if not all((owner,renter,meds)):raise ValueError("estructura de canasta no reconocida")
    return {"periodo":p,"owner":int(owner.group(1).replace(".","")),"owner_var":float(owner.group(2).replace(",",".")),"renter":int(renter.group(1).replace(".","")),"renter_var":float(renter.group(2).replace(",",".")),"meds":float(meds.group(1).replace(",",".")),"url":url}

def latest_basket(session):
    urls={KNOWN_BASKET}
    index=BeautifulSoup(get(session,DEFENSORIA_SITEMAP).text,"xml")
    maps=[loc.get_text(strip=True) for loc in index.find_all("loc") if re.search(r"/noticias-sitemap\d*\.xml$",loc.get_text(strip=True))]
    dated=[]
    for sitemap in maps:
        soup=BeautifulSoup(get(session,sitemap).text,"xml")
        for item in soup.find_all("url"):
            loc=item.find("loc");modified=item.find("lastmod")
            if not loc:continue
            url=loc.get_text(strip=True);slug=norm(url)
            if ("canasta" in slug or "indice-de-ipm" in slug or "medicamentos-y" in slug) and "adultos-as-mayores" in slug:
                dated.append((modified.get_text(strip=True) if modified else "",url))
    urls.update(url for _,url in sorted(dated,reverse=True)[:8])
    candidates=[]
    def download(url):
        return url,get(session,url).text
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(download,url) for url in urls]
        for future in as_completed(futures):
            try:
                url,source=future.result();parsed=parse_basket(source,url);candidates.append((parsed["periodo"],parsed))
            except Exception:pass
    if not candidates:raise ValueError("sin publicación de canasta interpretable")
    return max(candidates,key=lambda item:item[0])[1]

def validate(d):
    assert d["schema"]=="cepoes-personas-mayores-v1" and d["status"]=="VALIDADO"
    i=d["indicadores"];assert 10<=i["poblacion_65_mas"]["valor"]<=30;assert 2<=i["poblacion_80_mas"]["valor"]<=12
    assert 50<=i["indice_envejecimiento"]["valor"]<=250
    assert 500_000<=i["canasta_propietarios"]["valor"]<i["canasta_inquilinos"]["valor"]<=15_000_000
    assert all(-10<=i[k]["variacion_mensual"]<=50 for k in ("canasta_propietarios","canasta_inquilinos"))
    assert -10<=i["medicamentos"]["valor"]<=50
    s=d["series"]["estructura_etaria"];assert len(s["anios"])==len(s["poblacion_65_mas"])==len(s["poblacion_80_mas"])

def build(previous,session):
    out=deepcopy(previous);warnings=[]
    try:
        ages=parse_ages(get(session,AGES).text);aging=parse_aging(get(session,AGING).text)
        out["series"]["estructura_etaria"]=ages;out["series"]["indice_envejecimiento"]=aging
        out["indicadores"]["poblacion_65_mas"].update(valor=ages["poblacion_65_mas"][0],periodo=str(ages["anios"][0]))
        out["indicadores"]["poblacion_80_mas"].update(valor=ages["poblacion_80_mas"][0],periodo=str(ages["anios"][0]))
        out["indicadores"]["indice_envejecimiento"].update(valor=aging["valores"][0],periodo=str(aging["anios"][0]))
    except Exception as exc:warnings.append(f"IDECBA: {exc}")
    try:
        b=latest_basket(session);common={"periodo":b["periodo"],"url":b["url"]}
        out["indicadores"]["canasta_propietarios"].update(common,valor=b["owner"],variacion_mensual=b["owner_var"])
        out["indicadores"]["canasta_inquilinos"].update(common,valor=b["renter"],variacion_mensual=b["renter_var"])
        out["indicadores"]["medicamentos"].update(common,valor=b["meds"])
    except Exception as exc:warnings.append(f"Defensoría: {exc}")
    validate(out)
    if any(out[k]!=previous[k] for k in ("indicadores","series")):
        now=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z");out["actualizado"]=now;out["automatizacion"]["ultima_revision_exitosa"]=now
    return out,warnings

def fmt_number(v):return f"{v:,.1f}".replace(",","X").replace(".",",").replace("X",".")
def fmt_money(v):return "$"+f"{int(v):,}".replace(",",".")
def fmt_period(p):
    year,month=map(int,p.split("-"));name=list(MONTHS)[month-1];return f"{name} de {year}"
def replace_id(source,element_id,value):
    pattern=rf'(<[^>]+\bid=["\']{re.escape(element_id)}["\'][^>]*>).*?(</[^>]+>)'
    source,count=re.subn(pattern,lambda m:m.group(1)+value+m.group(2),source,count=1,flags=re.S)
    if count!=1:raise ValueError(f"marcador HTML ausente: {element_id}")
    return source
def render_page(d):
    source=PAGE.read_text(encoding="utf-8");original=source;i=d["indicadores"];p=i["canasta_inquilinos"]["periodo"]
    values={"pm-65":fmt_number(i["poblacion_65_mas"]["valor"])+"%","pm-80":fmt_number(i["poblacion_80_mas"]["valor"])+"%","pm-aging":fmt_number(i["indice_envejecimiento"]["valor"]),"pm-owner":fmt_money(i["canasta_propietarios"]["valor"]),"pm-renter":fmt_money(i["canasta_inquilinos"]["valor"]),"pm-renter-detail":fmt_money(i["canasta_inquilinos"]["valor"]),"pm-medicine":"+"+fmt_number(i["medicamentos"]["valor"])+"%","pm-dem-period":i["poblacion_65_mas"]["periodo"],"pm-cost-period-meta":fmt_period(p),"pm-cost-period-card":fmt_period(p).capitalize()+".","pm-owner-var":"+"+fmt_number(i["canasta_propietarios"]["variacion_mensual"])+"%","pm-renter-var":"+"+fmt_number(i["canasta_inquilinos"]["variacion_mensual"])+"%","pm-renter-var-card":"+"+fmt_number(i["canasta_inquilinos"]["variacion_mensual"])+"%","pm-medicine-period":fmt_period(p)}
    for element_id,value in values.items():source=replace_id(source,element_id,value)
    if source!=original:PAGE.write_text(source,encoding="utf-8");return True
    return False

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--validate-only",action="store_true");args=ap.parse_args()
    previous=json.loads(DATA.read_text(encoding="utf-8"));validate(previous)
    if args.validate_only:print("Personas mayores VALIDADO");return
    updated,warnings=build(previous,requests.Session());rendered=json.dumps(updated,ensure_ascii=False,indent=2)+"\n"
    changed=rendered!=DATA.read_text(encoding="utf-8")
    if changed:DATA.write_text(rendered,encoding="utf-8")
    page_changed=render_page(updated)
    for warning in warnings:print("ADVERTENCIA ·",warning)
    print("Personas mayores:","datos actualizados" if changed or page_changed else "sin cambios validados")
if __name__=="__main__":main()
