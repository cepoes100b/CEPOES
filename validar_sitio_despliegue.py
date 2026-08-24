#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET

root=Path(sys.argv[1] if len(sys.argv)>1 else '_site').resolve()
assert root.is_dir(), root


def patch_territorio_navigation(site_root: Path) -> None:
    """Normaliza enlaces HTML reales de los módulos de Territorio.

    Producción se arma como respaldo vigente + overlay. Esta pasada deja los
    accesos persistidos en HTML antes de validar y evita depender del JS/cache.
    """
    changed=[]
    for p in site_root.rglob('*.html'):
        s=p.read_text(encoding='utf-8',errors='replace')
        original=s
        s=re.sub(r'(/assets/common\.js)(?:\?v=\d+)?', r'\1?v=241', s)
        rel=p.relative_to(site_root).as_posix()
        if rel.startswith('territorio/'):
            structure='/territorio/estructura-productiva/'
            migrations='/territorio/migraciones/'
            debt='/territorio/endeudamiento/'
            if f'href="{structure}"' not in s:
                anchor=re.search(r'<a\b[^>]*href="/territorio/migraciones/"[^>]*>',s,re.I) or re.search(r'<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>',s,re.I)
                if anchor:s=s[:anchor.start()]+'<a href="/territorio/estructura-productiva/">Estructura productiva</a>'+s[anchor.start():]
            if f'href="{migrations}"' not in s:
                anchor=re.search(r'<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>',s,re.I)
                if anchor:s=s[:anchor.start()]+'<a href="/territorio/migraciones/">Migraciones</a>'+s[anchor.start():]

            if rel=='territorio/index.html':
                if 'data-cepoes-estructura-productiva-access="1"' not in s:
                    anchors=list(re.finditer(r'(<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>)(.*?)(</a>)',s,re.I|re.S))
                    if anchors:
                        m=anchors[-1]
                        opening=m.group(1).replace('href="/territorio/endeudamiento/"','href="/territorio/estructura-productiva/" data-cepoes-estructura-productiva-access="1"')
                        s=s[:m.start()]+opening+'Estructura productiva →'+m.group(3)+s[m.start():]
                if 'data-cepoes-migraciones-access="1"' not in s:
                    anchors=list(re.finditer(r'(<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>)(.*?)(</a>)',s,re.I|re.S))
                    if anchors:
                        m=anchors[-1]
                        opening=m.group(1).replace('href="/territorio/endeudamiento/"','href="/territorio/migraciones/" data-cepoes-migraciones-access="1"')
                        s=s[:m.start()]+opening+'Migraciones →'+m.group(3)+s[m.start():]
        if s!=original:
            p.write_text(s,encoding='utf-8')
            changed.append(rel)
    print(f'Navegación Territorio normalizada en {len(changed)} HTML')


def patch_sitemap(site_root: Path) -> None:
    p=site_root/'sitemap.xml'
    s=p.read_text(encoding='utf-8',errors='replace')
    url='https://cepoes.org/territorio/estructura-productiva/'
    if url not in s:
        item=f'  <url><loc>{url}</loc><lastmod>{date.today().isoformat()}</lastmod></url>\n'
        assert '</urlset>' in s, 'sitemap sin cierre urlset'
        p.write_text(s.replace('</urlset>',item+'</urlset>'),encoding='utf-8')
        print('Sitemap: agregado Estructura productiva')


patch_territorio_navigation(root)
patch_sitemap(root)

required=[
    'index.html','404.html','robots.txt','sitemap.xml','site.webmanifest',
    'assets/site.css','assets/common.js','assets/data.js','assets/favicon.svg',
    'legislatura/index.html','territorio/endeudamiento/index.html','territorio/migraciones/index.html',
    'territorio/estructura-productiva/index.html','assets/estructura-productiva.js','assets/estructura-productiva.css',
    'assets/data/estructura-productiva/manifest.json','assets/data/estructura-productiva/mapa.json',
    'assets/data/estructura-productiva/dinamica.json',
]
required += [f'assets/data/estructura-productiva/comuna-{c:02d}.json' for c in range(1,16)]
for rel in required:
    p=root/rel
    assert p.is_file() and p.stat().st_size>0, f'Falta {rel}'

html=list(root.rglob('*.html'))
assert len(html)>=100, len(html)
barrios=[p for p in (root/'territorio'/'barrios').glob('*/index.html')]
assert len(barrios)==48, f'barrios={len(barrios)}'

territorio=(root/'territorio'/'index.html').read_text(encoding='utf-8',errors='replace')
assert 'href="/territorio/migraciones/"' in territorio, 'Territorio no enlaza Migraciones'
assert 'data-cepoes-migraciones-access="1"' in territorio, 'Falta acceso visible a Migraciones'
assert 'href="/territorio/estructura-productiva/"' in territorio, 'Territorio no enlaza Estructura productiva'
assert 'data-cepoes-estructura-productiva-access="1"' in territorio, 'Falta acceso visible a Estructura productiva'

# Validación específica de la base estructural.
ep=root/'assets'/'data'/'estructura-productiva'
m=json.loads((ep/'manifest.json').read_text(encoding='utf-8'))
assert str(m.get('periodo_rus'))=='2017', f"periodo_rus={m.get('periodo_rus')}"
assert m.get('base_tipo')=='stock_estructural', m.get('base_tipo')
assert int(m.get('total',0))>=10000, m.get('total')
assert int(m.get('manzanas_actividad',0))>=1000, m.get('manzanas_actividad')
assert float(m.get('join_cartografia',0))>=.75, m.get('join_cartografia')
assert len(m.get('comunas',[]))==15
assert len(m.get('sectores',[]))>=8
geo=json.loads((ep/'mapa.json').read_text(encoding='utf-8'))
assert geo.get('type')=='FeatureCollection'
assert len(geo.get('features',[]))==int(m['manzanas_actividad'])

# Dinámica reciente: flujo separado y sin campos personales/fiscales.
d=json.loads((ep/'dinamica.json').read_text(encoding='utf-8'))
assert d.get('schema')==1
assert d.get('lectura')=='flujo_administrativo'
assert {'2024','2025','2026'}.issubset(set(d.get('anios',{})))
assert len(d.get('comunas',[]))==15
assert len(d.get('manzanas',{}))>=500
serialized=json.dumps(d,ensure_ascii=False).lower()
for bad in ('"cuit"','"titular"','"telefono"','"razon_social"'):
    assert bad not in serialized, f'Campo no publicable en dinámica: {bad}'

# La interfaz debe explicitar la diferencia stock/flujo y la antigüedad de la base.
ep_html=(root/'territorio'/'estructura-productiva'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ('RUS 2017','2024–2026','flujo administrativo','no equivalen al stock'):
    assert token.lower() in ep_html.lower(), f'Falta aclaración metodológica: {token}'

# Sitemap.
tree=ET.parse(root/'sitemap.xml')
ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
urls=tree.findall('.//s:url',ns)
assert len(urls)>=100, len(urls)
locs=[]
for u in urls:
    loc=u.find('s:loc',ns);last=u.find('s:lastmod',ns)
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
    if not p.is_file():continue
    n=p.name.lower()
    if p.suffix.lower() in {'.7z','.part'} or ('deudores' in n and p.suffix.lower() in {'.txt','.csv','.7z'}) or ('padron' in n and p.suffix.lower() in {'.txt','.csv','.7z'}):blocked.append(str(p.relative_to(root)))
assert not blocked, f'Archivos no publicables: {blocked[:10]}'

key=(root/'indexnow-key.txt').read_text(encoding='utf-8').strip()
assert re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key), 'IndexNow key inválida'
print(f"OK sitio: {len(html)} HTML · {len(barrios)} barrios · {len(urls)} URLs · estructura productiva {m['total']:,} registros / {m['manzanas_actividad']:,} manzanas · sin crudos")
