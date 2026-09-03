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
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/pdf,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
def main():
    d=json.loads(DATA.read_text(encoding='utf-8'));hashes={};review=False;prior=d.get('monitoring',{}).get('source_hashes',{})
    for s in d['sources']:
        if s['id']=='proyecto_control':continue
        raw=get(s['url']);h=hashlib.sha256(raw).hexdigest();hashes[s['id']]=h
        if prior.get(s['id']) and prior[s['id']]!=h:review=True
        if s['id']=='idecba_ive':
            text=raw.decode('utf-8','ignore');yrs=[int(x) for x in re.findall(r'20\d{2}',text)]
            if yrs and max(yrs)>2025:review=True
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z');d['monitoring']={'last_checked_at':now,'source_hashes':hashes,'review_required':review};d['generated_at']=now
    text=json.dumps(d,ensure_ascii=False,indent=2)+'\n';DATA.write_text(text,encoding='utf-8');ROOT.write_text(text,encoding='utf-8');print(f'salud reproductiva: {len(hashes)} fuentes revisadas; revisión={review}')
if __name__=='__main__':main()
