#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import urllib.error, urllib.request
import xml.etree.ElementTree as ET

p=argparse.ArgumentParser()
p.add_argument('--sitemap',default='sitemap.xml')
p.add_argument('--key-file',default='indexnow-key.txt')
a=p.parse_args()
key=Path(a.key_file).read_text(encoding='utf-8').strip()
tree=ET.parse(a.sitemap)
ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
urls=[(x.text or '').strip() for x in tree.findall('.//s:loc',ns) if (x.text or '').strip()]
assert urls and all(x.startswith('https://cepoes.org/') for x in urls)
payload=json.dumps({
  'host':'cepoes.org',
  'key':key,
  'keyLocation':'https://cepoes.org/indexnow-key.txt',
  'urlList':urls,
}).encode('utf-8')
req=urllib.request.Request('https://api.indexnow.org/indexnow',data=payload,method='POST',headers={
    'Content-Type':'application/json; charset=utf-8',
    'User-Agent':'CEPOES-IndexNow/1.0',
})
try:
    with urllib.request.urlopen(req,timeout=45) as r:
        status=r.status
        body=r.read(500).decode('utf-8','replace')
except urllib.error.HTTPError as e:
    body=e.read(500).decode('utf-8','replace')
    raise SystemExit(f'IndexNow HTTP {e.code}: {body}')
if status not in {200,202}:
    raise SystemExit(f'IndexNow HTTP {status}: {body}')
print(f'IndexNow: {status} · {len(urls)} URLs notificadas')
