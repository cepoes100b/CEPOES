#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET

root=Path(sys.argv[1] if len(sys.argv)>1 else '_site').resolve()
assert root.is_dir(), root


def patch_territorio_navigation(site_root: Path) -> None:
    """Normaliza enlaces públicos de Territorio sobre la copia completa de producción."""
    changed=[]
    for p in site_root.rglob('*.html'):
        s=p.read_text(encoding='utf-8',errors='replace')
        original=s
        s=re.sub(r'(/assets/common\.js)(?:\?v=\d+)?', r'\1?v=240', s)
        rel=p.relative_to(site_root).as_posix()
        if rel.startswith('territorio/'):
            debt=re.search(r'<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>',s,re.I)
            mig=re.search(r'<a\b[^>]*href="/territorio/migraciones/"[^>]*>',s,re.I)
            if 'href="/territorio/estructura-productiva/"' not in s:
                before=mig or debt
                if before:
                    s=s[:before.start()]+'<a href="/territorio/estructura-productiva/">Estructura productiva</a>'+s[before.start():]
            if 'href="/territorio/migraciones/"' not in s:
                debt=re.search(r'<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>',s,re.I)
                if debt:
                    s=s[:debt.start()]+'<a href="/territorio/migraciones/">Migraciones</a>'+s[debt.start():]

            if rel=='territorio/index.html':
                def clone_access(current: str, href: str, marker: str, label: str) -> str:
                    if marker in current:
                        return current
                    anchors=list(re.finditer(r'(<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>)(.*?)(</a>)',current,re.I|re.S))
                    if not anchors:
                        return current
                    m=anchors[-1]
                    opening=m.group(1).replace('href="/territorio/endeudamiento/"',f'href="{href}" {marker}')
                    clone=opening+label+' →'+m.group(3)
                    return current[:m.start()]+clone+current[m.start():]
                s=clone_access(s,'/territorio/estructura-productiva/','data-cepoes-productiva-access="1"','Estructura productiva')
                s=clone_access(s,'/territorio/migraciones/','data-cepoes-migraciones-access="1"','Migraciones')
        if s!=original:
            p.write_text(s,encoding='utf-8')
            changed.append(rel)
    print(f'Navegación Territorio normalizada en {len(changed)} HTML')


def patch_sitemap(site_root: Path) -> None:
    p=site_root/'sitemap.xml'
    tree=ET.parse(p)
    ns='http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('',ns)
    root_el=tree.getroot()
    wanted='https://cepoes.org/territorio/estructura-productiva/'
    present={((u.find(f'{{{ns}}}loc').text or '').strip()) for u in root_el.findall(f'{{{ns}}}url') if u.find(f'{{{ns}}}loc') is not None}
    if wanted not in present:
        u=ET.SubElement(root_el,f'{{{ns}}}url')
        ET.SubElement(u,f'{{{ns}}}loc').text=wanted
        ET.SubElement(u,f'{{{ns}}}lastmod').text=date.today().isoformat()
        tree.write(p,encoding='utf-8',xml_declaration=True)
        print('Sitemap: agregada Estructura productiva')


patch_territorio_navigation(root)
patch_sitemap(root)

required=[
    'index.html','404.html','robots.txt','sitemap.xml','site.webmanifest',
    'assets/site.css','assets/common.js','assets/data.js','assets/favicon.svg',
    'legislatura/index.html','territorio/endeudamiento/index.html',
    'territorio/migraciones/index.html','territorio/estructura-productiva/index.html',
    'assets/data/estructura-productiva/manifest.json','assets/data/estructura-productiva/mapa.json',
]
for rel in required:
    p=root/rel
    assert p.is_file() and p.stat().st_size>0, f'Falta {rel}'
for c in range(1,16):
    p=root/f'assets/data/estructura-productiva/comuna-{c:02d}.json'
    assert p.is_file() and p.stat().st_size>10, f'Falta {p.name}'

prod=json.loads((root/'assets/data/estructura-productiva/manifest.json').read_text(encoding='utf-8'))
assert int(prod.get('total',0))>=10000, 'Estructura productiva sin registros suficientes'
assert int(prod.get('manzanas_actividad',0))>=1000, 'Estructura productiva sin manzanas suficientes'
assert float(prod.get('join_cartografia',0))>=.75, 'Join cartográfico insuficiente'
assert len(prod.get('comunas',[]))==15, 'Estructura productiva incompleta por comuna'

html=list(root.rglob('*.html'))
assert len(html)>=100, len(html)
barrios=[p for p in (root/'territorio'/'barrios').glob('*/index.html')]
assert len(barrios)==48, f'barrios={len(barrios)}'
territorio=(root/'territorio'/'index.html').read_text(encoding='utf-8',errors='replace')
assert 'href="/territorio/migraciones/"' in territorio, 'Territorio no enlaza Migraciones'
assert 'data-cepoes-migraciones-access="1"' in territorio, 'Falta acceso visible a Migraciones en portada Territorio'
assert 'href="/territorio/estructura-productiva/"' in territorio, 'Territorio no enlaza Estructura productiva'
assert 'data-cepoes-productiva-access="1"' in territorio, 'Falta acceso visible a Estructura productiva en portada Territorio'

tree=ET.parse(root/'sitemap.xml')
ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
urls=tree.findall('.//s:url',ns)
assert len(urls)>=100, len(urls)
locs=[]
for u in urls:
    loc=u.find('s:loc',ns); last=u.find('s:lastmod',ns)
    assert loc is not None and (loc.text or '').startswith('https://cepoes.org/')
    assert last is not None and re.fullmatch(r'\d{4}-\d{2}-\d{2}',(last.text or '').strip())
    locs.append((loc.text or '').strip())
assert 'https://cepoes.org/territorio/estructura-productiva/' in locs

manifest=json.loads((root/'site.webmanifest').read_text(encoding='utf-8'))
assert manifest.get('name')=='CEPOES'
assert manifest.get('theme_color')=='#16232F'
for p in html:
    s=p.read_text(encoding='utf-8',errors='replace')
    assert '/assets/favicon.svg' in s, p

blocked=[]
for p in root.rglob('*'):
    if not p.is_file(): continue
    n=p.name.lower()
    if p.suffix.lower() in {'.7z','.part'} or 'deudores' in n and p.suffix.lower() in {'.txt','.csv','.7z'} or 'padron' in n and p.suffix.lower() in {'.txt','.csv','.7z'}:
        blocked.append(str(p.relative_to(root)))
assert not blocked, f'Archivos no publicables: {blocked[:10]}'

key=(root/'indexnow-key.txt').read_text(encoding='utf-8').strip()
assert re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key), 'IndexNow key inválida'
print(f'OK sitio: {len(html)} HTML · {len(barrios)} barrios · {len(urls)} URLs indexables · estructura productiva validada · sin crudos')
