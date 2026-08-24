#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
import xml.etree.ElementTree as ET

root=Path(sys.argv[1] if len(sys.argv)>1 else '_site').resolve()
assert root.is_dir(), root


def patch_migraciones_navigation(site_root: Path) -> None:
    """Deja enlaces HTML reales a Migraciones y fuerza common.js actualizado.

    El sitio se arma a partir de la producción existente + overlay. Por eso esta
    normalización se ejecuta sobre la copia completa justo antes de validarla y
    publicarla, evitando depender de una inyección JS que pueda quedar cacheada.
    """
    changed=[]
    for p in site_root.rglob('*.html'):
        s=p.read_text(encoding='utf-8',errors='replace')
        original=s

        # Todas las páginas deben pedir la revisión nueva del JS común.
        s=re.sub(r'(/assets/common\.js)(?:\?v=\d+)?', r'\1?v=236', s)

        rel=p.relative_to(site_root).as_posix()
        if rel.startswith('territorio/'):
            href='/territorio/migraciones/'

            # En la subnavegación de Territorio, insertar Migraciones antes de
            # Endeudamiento si todavía no existe como enlace HTML real.
            if f'href="{href}"' not in s:
                debt=re.search(r'<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>',s,re.I)
                if debt:
                    s=s[:debt.start()]+'<a href="/territorio/migraciones/">Migraciones</a>'+s[debt.start():]

            # En la portada de Territorio, agregar además un acceso visible en
            # el mismo grupo que "Endeudamiento y mora", copiando su estilo.
            if rel=='territorio/index.html':
                marker='data-cepoes-migraciones-access="1"'
                if marker not in s:
                    anchors=list(re.finditer(
                        r'(<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>)(.*?)(</a>)',
                        s,re.I|re.S
                    ))
                    if anchors:
                        m=anchors[-1]
                        opening=m.group(1).replace(
                            'href="/territorio/endeudamiento/"',
                            'href="/territorio/migraciones/" '+marker
                        )
                        clone=opening+'Migraciones →'+m.group(3)
                        s=s[:m.start()]+clone+s[m.start():]

        if s!=original:
            p.write_text(s,encoding='utf-8')
            changed.append(rel)

    print(f'Navegación Migraciones normalizada en {len(changed)} HTML')


patch_migraciones_navigation(root)

required=[
    'index.html','404.html','robots.txt','sitemap.xml','site.webmanifest',
    'assets/site.css','assets/common.js','assets/data.js','assets/favicon.svg',
    'legislatura/index.html','territorio/endeudamiento/index.html',
    'territorio/migraciones/index.html',
]
for rel in required:
    p=root/rel
    assert p.is_file() and p.stat().st_size>0, f'Falta {rel}'
html=list(root.rglob('*.html'))
assert len(html)>=100, len(html)
barrios=[p for p in (root/'territorio'/'barrios').glob('*/index.html')]
assert len(barrios)==48, f'barrios={len(barrios)}'

# Verificar explícitamente que Migraciones sea descubrible desde Territorio.
territorio=(root/'territorio'/'index.html').read_text(encoding='utf-8',errors='replace')
assert 'href="/territorio/migraciones/"' in territorio, 'Territorio no enlaza Migraciones'
assert 'data-cepoes-migraciones-access="1"' in territorio, 'Falta acceso visible a Migraciones en portada Territorio'

tree=ET.parse(root/'sitemap.xml')
ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
urls=tree.findall('.//s:url',ns)
assert len(urls)>=100, len(urls)
for u in urls:
    loc=u.find('s:loc',ns); last=u.find('s:lastmod',ns)
    assert loc is not None and (loc.text or '').startswith('https://cepoes.org/')
    assert last is not None and re.fullmatch(r'\d{4}-\d{2}-\d{2}',(last.text or '').strip())

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
print(f'OK sitio: {len(html)} HTML · {len(barrios)} barrios · {len(urls)} URLs indexables · sin crudos')
