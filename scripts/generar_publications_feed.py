#!/usr/bin/env python3
"""Published editorial content only; URL is its stable delivery identity."""
import argparse, json, re
from pathlib import Path
from scripts.generar_newsletter_feed import editions

ARCHIVES = {'/publicaciones/', '/publicaciones/notas/', '/publicaciones/informes/',
            '/publicaciones/boletines/', '/prensa/', '/propuestas/'}
KINDS = {'boletin', 'informe', 'analisis', 'prensa'}

def publications(site):
    registry = json.loads((site/'assets/data/lo-nuevo.json').read_text(encoding='utf-8'))
    if registry.get('version') != 1: raise ValueError('Invalid public registry')
    bulletins = {e['url']:e for e in editions(site)}
    result = {}
    for entry in registry['entries']:
        url = entry['url']
        if not re.fullmatch(r'/[a-z0-9/-]+/', url) or url in ARCHIVES: continue
        path = site/url.lstrip('/')/'index.html'
        if not path.is_file(): continue
        source = path.read_text(encoding='utf-8')
        if re.search(r'<meta[^>]+(?:noindex|http-equiv=["\']refresh)', source, re.I): continue
        notice = entry.get('publication_type') == 'notice' or bool(re.search(r'<meta\s+name=["\']cepoes:publication["\']\s+content=["\']notice["\']', source))
        kind = 'aviso' if notice else entry['type']
        if kind not in KINDS and kind != 'aviso': continue
        if len(url.strip('/').split('/')) < 2: continue
        item = dict(key=url,url=url,kind=kind,title=entry['title'],summary=entry['description'],date=entry['date'])
        if url in bulletins: item.update(edition=bulletins[url]['edition'],email_content=bulletins[url]['email_content'])
        result[url] = item
    # Bulletin extraction remains canonical even when an older issue lacks a date.
    for url, bulletin in bulletins.items():
        result.setdefault(url,dict(key=url,kind='boletin',date=bulletin['email_content']['date'],**bulletin))
    return sorted(result.values(),key=lambda x:x['key'])

def generate(site):
    data = {'version':1,'publications':publications(site)}
    if not data['publications']: raise ValueError('Empty editorial catalog')
    target=site/'assets/data/newsletter-publications.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('site',type=Path)
    print('Publicaciones para novedades:',len(generate(p.parse_args().site)['publications']))
