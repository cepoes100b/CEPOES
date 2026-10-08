#!/usr/bin/env python3
"""Integra las dos lecturas en metadata pública, sin publicar ni enviar comunicaciones."""
from pathlib import Path
import json,xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'deploy/site-overlay'
p=ROOT/'deploy/reports-registry.json';d=json.loads(p.read_text())
main=next(r for r in d['reports'] if r['url']=='/presupuesto/2027/')
main.update(title='Qué Ciudad financia el presupuesto 2027',subtitle='Análisis integral desde 100 Barrios',description='Ingresos, impuestos, deuda, gasto, inversión y políticas sectoriales del presupuesto porteño 2027, con un especial de Salud.',kind='Informe integral · Proyecto de presupuesto 2027')
special=next((r for r in d['reports'] if r['url']=='/presupuesto/2027/salud/'),None)
if special is None:
 special={};d['reports'].append(special)
special.update(url='/presupuesto/2027/salud/',title='La salud pierde prioridad en el presupuesto de la Ciudad',subtitle='Especial Salud · Presupuesto 2027',description='Hospitales, CeSAC, personal, salud mental y 30 inversiones sanitarias, desde la perspectiva de 100 Barrios.',kind='Especial Salud · Proyecto de presupuesto 2027',period='2026-10-08',format='web')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
p=SITE/'assets/data/prensa.json';d=json.loads(p.read_text())
next(r for r in d['notas'] if r['slug']=='presupuesto-2027-salud')['informe']='/presupuesto/2027/salud/'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
p=SITE/'sitemap.txt';s=p.read_text();url='https://cepoes.org/presupuesto/2027/salud/'
if url not in s.splitlines():p.write_text(s.rstrip()+'\n'+url+'\n')
p=SITE/'sitemap.xml';s=p.read_text()
if url not in s:s=s.replace('</urlset>',f'  <url><loc>{url}</loc><lastmod>2026-10-08</lastmod></url>\n</urlset>');p.write_text(s)
E.fromstring(s)
print('Principal y especial integrados, sin publicación')
