#!/usr/bin/env python3
"""Catalog published bulletin pages; drafts and PDFs alone never trigger email."""
import argparse,json,re,html
from pathlib import Path

def editions(site):
    result=[]
    for path in (site/'publicaciones/boletines').glob('boletin-*/index.html'):
        match=re.fullmatch(r'boletin-(\d+)-[a-z]+-\d{4}',path.parent.name)
        if not match:continue
        source=path.read_text(encoding='utf-8')
        if re.search(r'<meta[^>]+(?:noindex|http-equiv=["\']refresh)',source,re.I):continue
        title=re.search(r'<h1[^>]*>(.*?)</h1>',source,re.S)
        description=re.search(r'<meta name="description" content="([^"]+)"',source)
        if not title or not description:raise ValueError('Boletín sin título o descripción: '+path.parent.name)
        result.append(dict(edition=int(match[1]),url='/'+path.parent.relative_to(site).as_posix()+'/',title=html.unescape(re.sub('<[^>]+>','',title[1])).strip(),summary=html.unescape(description[1])))
    numbers=[x['edition'] for x in result]
    if len(numbers)!=len(set(numbers)):raise ValueError('Dos boletines con el mismo número')
    return sorted(result,key=lambda x:x['edition'])

def generate(site):
    data={'version':1,'editions':editions(site)}
    if not data['editions']:raise ValueError('Catálogo de boletines vacío')
    path=site/'assets/data/newsletter-editions.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return data
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('site',type=Path);args=p.parse_args();print('Boletines públicos:',len(generate(args.site)['editions']))
