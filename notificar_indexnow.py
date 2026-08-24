#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import requests

p=argparse.ArgumentParser()
p.add_argument('--sitemap',default='sitemap.xml')
p.add_argument('--key-file',default='indexnow-key.txt')
a=p.parse_args()
key=Path(a.key_file).read_text(encoding='utf-8').strip()
tree=ET.parse(a.sitemap)
ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
urls=[(x.text or '').strip() for x in tree.findall('.//s:loc',ns) if (x.text or '').strip()]
assert urls and all(x.startswith('https://cepoes.org/') for x in urls)
payload={
  'host':'cepoes.org',
  'key':key,
  'keyLocation':'https://cepoes.org/indexnow-key.txt',
  'urlList':urls,
}
r=requests.post('https://api.indexnow.org/indexnow',json=payload,timeout=45,headers={'User-Agent':'CEPOES-IndexNow/1.0'})
if r.status_code not in {200,202}:
    raise SystemExit(f'IndexNow HTTP {r.status_code}: {r.text[:500]}')
print(f'IndexNow: {r.status_code} · {len(urls)} URLs notificadas')
