#!/usr/bin/env python3
"""Genera una vista autónoma desde una salida pública completa, sin publicar."""
import argparse,re
from pathlib import Path

def build(site,output):
 s=(site/'territorio/limpieza-urbana/index.html').read_text()
 for name in ['site.css','arquitectura.css','limpieza-urbana.css']:
  s=re.sub(r'<link[^>]+href="/assets/'+re.escape(name)+r'(?:\?[^" ]*)?"[^>]*>',lambda m:'<style>'+(site/'assets'/name).read_text()+'</style>',s)
 s=re.sub(r'<link[^>]+(?:href="/(?:favicon|assets/(?:favicon|apple-touch)|site.webmanifest))[^>]*>','',s)
 s=re.sub(r'<script defer src="/assets/common(?:-r1)?\.js(?:\?[^" ]*)?"></script>',lambda m:'<script>'+(site/'assets/common.js').read_text()+'</script>',s)
 js=(site/'assets/limpieza-urbana.js').read_text();data=(site/'assets/data/limpieza-urbana.json').read_text()
 js=js.replace("await fetch('/assets/data/limpieza-urbana.json')", "{ok:true,json:async()=>JSON.parse(document.getElementById('lu-inline-data').textContent)}")
 s=re.sub(r'<script defer src="/assets/limpieza-urbana\.js(?:\?[^" ]*)?"></script>','',s)
 s=s.replace('</body>','<script id="lu-inline-data" type="application/json">'+data+'</script><script>'+js+'</script></body>')
 s=s.replace('href="/assets/data/limpieza-urbana.json"','href="../../deploy/site-overlay/assets/data/limpieza-urbana.json"').replace('href="/','href="https://cepoes.org/')
 s=s.replace('</head>', '''<script>document.addEventListener('DOMContentLoaded',()=>{const w=Number(new URLSearchParams(location.search).get('viewport'));if([320,390,430].includes(w)&&window.top===window.self){const frame=document.createElement('iframe');frame.title='Vista móvil del monitor de limpieza urbana';frame.src=location.pathname;frame.style.cssText='width:'+w+'px;height:860px;max-width:100%;border:1px solid #a8bbc6;background:white';document.body.replaceChildren(frame);document.body.style.cssText='margin:0;padding:20px;background:#e8eef2;display:flex;justify-content:center;min-height:100vh'}});</script></head>''')
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(s)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--site',type=Path,required=True);p.add_argument('--output',type=Path,default=Path(__file__).with_name('index.html'));a=p.parse_args();build(a.site,a.output)
