#!/usr/bin/env python3
"""Lecturas autónomas para revisión: sin afirmar QA del navegador ni publicación."""
from pathlib import Path
import re,base64,sys
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'deploy/site-overlay'
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'outputs';OUT.mkdir(parents=True,exist_ok=True)
css=':root{--tinta:#17364a;--tinta2:#314b5c;--papel:#fff;--papel2:#f3f6f7;--panel:#fff;--borde:#d5dfe4;--marca-osc:#005b67;--marca-cl:#e7f3f2}*{box-sizing:border-box}body{margin:0;background:var(--papel);font-family:Arial,system-ui,sans-serif;color:var(--tinta2)}a{color:var(--marca-osc)}.review{background:#17364a;color:white;padding:16px 24px;font-size:14px}'+(SITE/'assets/presupuesto-2027.css').read_text()
files={'/presupuesto/2027/':'Presupuesto_2027_Analisis_Integral_100_Barrios.html','/presupuesto/2027/salud/':'Presupuesto_2027_Salud_100_Barrios.html'}
for route,name in files.items():
 source=(SITE/route.strip('/')/'index.html').read_text();body=re.search(r'<main[\s\S]*?</main>',source).group()
 data=re.search(r'<script id="p27-(?:general-)?data"[\s\S]*?</script>',source).group()
 css+=(SITE/'assets/presupuesto-2027-visuales.css').read_text() if 'p27-visual' in body and 'p27-chart-positive' not in css else ''
 for href in set(re.findall(r'href="([^"]+)"',body)):
  if href.startswith('/assets/data/presupuesto-2027'):
   path=SITE/href.lstrip('/');mime='application/json' if path.suffix=='.json' else 'text/csv'
   uri='data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
   body=body.replace('download href="'+href+'"','download="'+path.name+'" href="'+uri+'"')
  elif href in files:body=body.replace('href="'+href+'"','href="'+files[href]+'"')
  elif href.startswith('/'):body=body.replace('href="'+href+'"','href="https://cepoes.org'+href+'"')
 js='presupuesto-2027-integral.js' if route=='/presupuesto/2027/' else 'presupuesto-2027.js'
 title=re.search(r'<title>(.*?)</title>',source).group(1)
 output='<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>'+title+'</title><style>'+css+'</style></head><body><div class="review">100 Barrios · Borrador para revisión · 8 de octubre de 2026 · No publicado · Revisión visual en navegador pendiente</div>'+body+data+'<script>'+(SITE/'assets'/js).read_text()+'</script><script>'+(SITE/'assets/presupuesto-2027-graficos.js').read_text()+'</script></body></html>'
 (OUT/name).write_text(output)
 print(name,len(output),'caracteres')
