#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET

root=Path(sys.argv[1] if len(sys.argv)>1 else '_site').resolve()
assert root.is_dir(), root


def patch_territorio_navigation(site_root: Path) -> None:
    """Normaliza accesos HTML reales a módulos territoriales nuevos.

    El despliegue se arma sobre producción + overlay. Esta pasada evita que una
    página antigua dependa exclusivamente de una inyección JS y actualiza el
    query de common.js para invalidar caché.
    """
    changed=[]
    for p in site_root.rglob('*.html'):
        s=p.read_text(encoding='utf-8',errors='replace')
        original=s
        s=re.sub(r'(/assets/common\.js)(?:\?v=\d+)?', r'\1?v=252', s)
        rel=p.relative_to(site_root).as_posix()
        if rel.startswith('territorio/'):
            # Estructura productiva antes de Migraciones/Endeudamiento.
            prod='/territorio/estructura-productiva/'
            if f'href="{prod}"' not in s:
                target=re.search(r'<a\b[^>]*href="/territorio/migraciones/"[^>]*>',s,re.I)
                if not target:
                    target=re.search(r'<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>',s,re.I)
                if target:
                    s=s[:target.start()]+'<a href="/territorio/estructura-productiva/">Estructura productiva</a>'+s[target.start():]

            # Migraciones antes de Endeudamiento.
            mig='/territorio/migraciones/'
            if f'href="{mig}"' not in s:
                debt=re.search(r'<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>',s,re.I)
                if debt:
                    s=s[:debt.start()]+'<a href="/territorio/migraciones/">Migraciones</a>'+s[debt.start():]

            if rel=='territorio/index.html':
                # Accesos visibles desde la portada, clonando el formato de un
                # acceso territorial existente para preservar el diseño actual.
                marker='data-cepoes-estructura-productiva-access="1"'
                if marker not in s:
                    anchors=list(re.finditer(r'(<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>)(.*?)(</a>)',s,re.I|re.S))
                    if anchors:
                        m=anchors[-1]
                        opening=m.group(1).replace('href="/territorio/endeudamiento/"','href="/territorio/estructura-productiva/" '+marker)
                        clone=opening+'Estructura productiva →'+m.group(3)
                        s=s[:m.start()]+clone+s[m.start():]

                marker='data-cepoes-migraciones-access="1"'
                if marker not in s:
                    anchors=list(re.finditer(r'(<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>)(.*?)(</a>)',s,re.I|re.S))
                    if anchors:
                        m=anchors[-1]
                        opening=m.group(1).replace('href="/territorio/endeudamiento/"','href="/territorio/migraciones/" '+marker)
                        clone=opening+'Migraciones →'+m.group(3)
                        s=s[:m.start()]+clone+s[m.start():]

        if s!=original:
            p.write_text(s,encoding='utf-8')
            changed.append(rel)
    print(f'Navegación territorial normalizada en {len(changed)} HTML')


def ensure_sitemap_url(site_root: Path, path: str) -> None:
    """Agrega una ruta nueva al sitemap heredado de producción si falta."""
    p=site_root/'sitemap.xml'
    s=p.read_text(encoding='utf-8',errors='replace')
    url='https://cepoes.org'+path
    if url in s:
        return
    entry=f'  <url><loc>{url}</loc><lastmod>{date.today().isoformat()}</lastmod></url>\n'
    if '</urlset>' not in s:
        raise AssertionError('sitemap.xml sin cierre urlset')
    p.write_text(s.replace('</urlset>',entry+'</urlset>'),encoding='utf-8')
    print(f'Sitemap: agregada {url}')


patch_territorio_navigation(root)
ensure_sitemap_url(root,'/territorio/estructura-productiva/')

required=[
    'index.html','404.html','robots.txt','sitemap.xml','site.webmanifest',
    'assets/site.css','assets/common.js','assets/data.js','assets/favicon.svg',
    'legislatura/index.html','territorio/endeudamiento/index.html',
    'territorio/migraciones/index.html','territorio/estructura-productiva/index.html',
    'assets/estructura-productiva.js','assets/estructura-productiva.css',
    'assets/data/estructura-productiva/actual.json',
]
for rel in required:
    p=root/rel
    assert p.is_file() and p.stat().st_size>0, f'Falta {rel}'
html=list(root.rglob('*.html'))
assert len(html)>=100, len(html)
barrios=[p for p in (root/'territorio'/'barrios').glob('*/index.html')]
assert len(barrios)==48, f'barrios={len(barrios)}'

territorio=(root/'territorio'/'index.html').read_text(encoding='utf-8',errors='replace')
assert 'href="/territorio/migraciones/"' in territorio, 'Territorio no enlaza Migraciones'
assert 'href="/territorio/estructura-productiva/"' in territorio, 'Territorio no enlaza Estructura productiva'
assert 'data-cepoes-migraciones-access="1"' in territorio, 'Falta acceso visible a Migraciones en portada Territorio'
assert 'data-cepoes-estructura-productiva-access="1"' in territorio, 'Falta acceso visible a Estructura productiva en portada Territorio'

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
assert 'https://cepoes.org/territorio/estructura-productiva/' in locs, 'Estructura productiva ausente del sitemap'

manifest=json.loads((root/'site.webmanifest').read_text(encoding='utf-8'))
assert manifest.get('name')=='CEPOES'
assert manifest.get('theme_color')=='#16232F'
for p in html:
    s=p.read_text(encoding='utf-8',errors='replace')
    assert '/assets/favicon.svg' in s, p

actual=json.loads((root/'assets/data/estructura-productiva/actual.json').read_text(encoding='utf-8'))
assert actual['panorama']['empresas_registradas']['periodo']>=2024
assert actual['panorama']['ejes_comerciales']['periodo']['anio']>=2026
assert len(actual['panorama']['ejes_comerciales']['comunas'])==15

blocked=[]
for p in root.rglob('*'):
    if not p.is_file(): continue
    n=p.name.lower()
    if p.suffix.lower() in {'.7z','.part'} or 'deudores' in n and p.suffix.lower() in {'.txt','.csv','.7z'} or 'padron' in n and p.suffix.lower() in {'.txt','.csv','.7z'}:
        blocked.append(str(p.relative_to(root)))
assert not blocked, f'Archivos no publicables: {blocked[:10]}'

key=(root/'indexnow-key.txt').read_text(encoding='utf-8').strip()
assert re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key), 'IndexNow key inválida'
print(f'OK sitio: {len(html)} HTML · {len(barrios)} barrios · {len(urls)} URLs indexables · estructura productiva incluida · sin crudos')