#!/usr/bin/env python3
"""CEPOES · Salud reproductiva / PAEV · monitor de fuentes oficiales.

No convierte menciones o denuncias en evidencia. Revisa disponibilidad y huellas
de las fuentes; la matriz de transparencia sólo cambia mediante revisión validada.
"""
from __future__ import annotations
import hashlib,json,re,urllib.request
from datetime import datetime,timezone
from pathlib import Path
DATA=Path('deploy/site-overlay/assets/data/salud-reproductiva.json');ROOT=Path('salud_reproductiva.json');UA='CEPOES-data-monitor/1.0 (+https://cepoes.org)'
def get(url,timeout=90):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
def fingerprint(raw,url):
    low=url.lower().split('?',1)[0]
    if low.endswith(('.pdf','.xlsx','.xls','.csv')):payload=raw
    else:
        text=raw.decode('utf-8','ignore')
        text=re.sub(r'<!--.*?-->',' ',text,flags=re.S)
        text=re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',text,flags=re.I|re.S)
        text=re.sub(r'\s+',' ',text).strip()
        payload=text.encode('utf-8')
    return hashlib.sha256(payload).hexdigest()
def main():
    d=json.loads(DATA.read_text(encoding='utf-8'));prior=d.get('monitoring',{}).get('source_hashes',{});review=bool(d.get('monitoring',{}).get('review_required',False));hashes={}
    for s in d['sources']:
        if s['id']=='proyecto_control':continue
        h=fingerprint(get(s['url']),s['url']);hashes[s['id']]=h
        if prior.get(s['id']) and prior[s['id']]!=h:review=True
    xlsx=d.get('ive_ile',{}).get('xlsx')
    if xlsx:
        h=fingerprint(get(xlsx),xlsx);hashes['idecba_ive_xlsx']=h
        if prior.get('idecba_ive_xlsx') and prior['idecba_ive_xlsx']!=h:review=True
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z');d['monitoring']={'last_checked_at':now,'source_hashes':hashes,'review_required':review};d['generated_at']=now
    text=json.dumps(d,ensure_ascii=False,indent=2)+'\n';DATA.write_text(text,encoding='utf-8');ROOT.write_text(text,encoding='utf-8');print(f'salud reproductiva: {len(hashes)} fuentes revisadas; revisión={review}')
if __name__=='__main__':main()
