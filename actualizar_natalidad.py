#!/usr/bin/env python3
"""CEPOES · Natalidad y cambio demográfico.

Actualiza con criterio fail-closed: verifica fuentes oficiales, detecta el último
CSV anual de DEIS y conserva el último dato validado si no puede interpretar un
cambio de esquema. No infiere causalidad.
"""
from __future__ import annotations
import csv, html, io, json, re, unicodedata, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

DATA=Path('deploy/site-overlay/assets/data/natalidad.json')
ROOT=Path('natalidad.json')
DEIS='https://www.argentina.gob.ar/salud/deis/datos/nacidosvivos'
UA='CEPOES-data-pipeline/1.0 (+https://cepoes.org)'

def get(url,timeout=120):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,text/csv,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','_',s).strip('_')

def decode(raw):
    for enc in ('utf-8-sig','utf-8','latin-1'):
        try:return raw.decode(enc)
        except UnicodeDecodeError:pass
    raise RuntimeError('CSV no decodificable')

def extract_links(page):
    text=decode(page);out=[]
    for href,label in re.findall(r'href=["\']([^"\']+\.csv[^"\']*)["\'][^>]*>(.*?)</a>',text,re.I|re.S):
        clean=re.sub('<[^>]+>',' ',label);m=re.search(r'(20\d{2})',html.unescape(clean))
        if m:out.append((int(m.group(1)),urljoin(DEIS,html.unescape(href))))
    return sorted(set(out))

def parse_number(value):
    s=str(value or '').strip().replace('\u00a0','').replace(' ','')
    if not s:return None
    try:
        if ',' in s and '.' in s:
            s=s.replace('.','').replace(',','.') if s.rfind(',')>s.rfind('.') else s.replace(',','')
        elif ',' in s:s=s.replace(',','.')
        return float(s)
    except ValueError:return None

def parse_total(raw,expected=None):
    text=decode(raw);sample=text[:50000]
    try:delim=csv.Sniffer().sniff(sample,delimiters=',;\t|').delimiter
    except csv.Error:delim=','
    rows=list(csv.DictReader(io.StringIO(text),delimiter=delim))
    if not rows:return None
    cols=list(rows[0].keys());ranked=[]
    for c in cols:
        nc=norm(c);score=sum(k in nc for k in ('cant','cantidad','frecuencia','cuenta','total','nacidos'))
        if not score:continue
        total=0;ok=0
        for r in rows:
            v=parse_number(r.get(c,''))
            if v is None:continue
            if v>=0 and abs(v-round(v))<1e-8:total+=int(round(v));ok+=1
        if ok and 100000<=total<=1000000:ranked.append((score,total,c,ok))
    if expected:
        exact=[x for x in ranked if x[1]==expected]
        if exact:return exact[0][1]
    if ranked:return max(ranked)[1]
    print('DEIS diagnóstico · delimitador=',repr(delim),'filas=',len(rows),'columnas=',cols)
    print('DEIS diagnóstico · primera fila=',{c:rows[0].get(c) for c in cols})
    return None

def main():
    d=json.loads(DATA.read_text(encoding='utf-8'));links=extract_links(get(DEIS))
    if not links:raise RuntimeError('DEIS: no se detectaron CSV anuales')
    year,url=links[-1];d['latest_deis_file_year']=year;known={x['year']:x['value'] for x in d['argentina']['births']};expected=known.get(year)
    try:total=parse_total(get(url),expected)
    except Exception as exc:print('ADVERTENCIA: no se pudo interpretar CSV DEIS:',exc);total=None
    if total is not None:
        if expected is not None and total!=expected:raise RuntimeError(f'DEIS {year}: {total} != ancla validada {expected}')
        if year not in known:d['argentina']['births'].append({'year':year,'value':total,'source':'DEIS'});d['argentina']['births'].sort(key=lambda x:x['year'])
        d['update_pending']=False
    elif year>max(known):d['update_pending']=True
    d['generated_at']=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    text=json.dumps(d,ensure_ascii=False,indent=2)+'\n';DATA.write_text(text,encoding='utf-8');ROOT.write_text(text,encoding='utf-8');print(f'natalidad: DEIS último archivo={year}; total={total}; pendiente={d["update_pending"]}')
if __name__=='__main__':main()
