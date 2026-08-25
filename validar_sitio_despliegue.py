#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET

root=Path(sys.argv[1] if len(sys.argv)>1 else '_site').resolve()
assert root.is_dir(), root


def patch_territorio_navigation(site_root: Path) -> None:
    """Normaliza accesos HTML reales y pequeños ajustes de integración."""
    changed=[]
    for p in site_root.rglob('*.html'):
        s=p.read_text(encoding='utf-8',errors='replace')
        original=s
        s=re.sub(r'(/assets/common\.js)(?:\?v=\d+)?', r'\1?v=253', s)
        rel=p.relative_to(site_root).as_posix()
        if rel.startswith('territorio/'):
            sport='/territorio/deporte-salud/'
            if f'href="{sport}"' not in s:
                target=re.search(r'<a\b[^>]*href="/territorio/estructura-productiva/"[^>]*>',s,re.I)
                if not target:
                    target=re.search(r'<a\b[^>]*href="/territorio/migraciones/"[^>]*>',s,re.I)
                if target:
                    s=s[:target.start()]+'<a href="/territorio/deporte-salud/">Deporte y salud</a>'+s[target.start():]

            prod='/territorio/estructura-productiva/'
            if f'href="{prod}"' not in s:
                target=re.search(r'<a\b[^>]*href="/territorio/migraciones/"[^>]*>',s,re.I)
                if not target:
                    target=re.search(r'<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>',s,re.I)
                if target:
                    s=s[:target.start()]+'<a href="/territorio/estructura-productiva/">Estructura productiva</a>'+s[target.start():]

            mig='/territorio/migraciones/'
            if f'href="{mig}"' not in s:
                debt=re.search(r'<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>',s,re.I)
                if debt:
                    s=s[:debt.start()]+'<a href="/territorio/migraciones/">Migraciones</a>'+s[debt.start():]

            if rel=='territorio/index.html':
                marker='data-cepoes-deporte-salud-access="1"'
                if marker not in s:
                    anchors=list(re.finditer(r'(<a\b[^>]*href="/territorio/endeudamiento/"[^>]*>)(.*?)(</a>)',s,re.I|re.S))
                    if anchors:
                        m=anchors[-1]
                        opening=m.group(1).replace('href="/territorio/endeudamiento/"','href="/territorio/deporte-salud/" '+marker)
                        clone=opening+'Deporte y vida saludable →'+m.group(3)
                        s=s[:m.start()]+clone+s[m.start():]

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

            if rel=='territorio/estructura-productiva/index.html' and '/assets/estructura-productiva-bootstrap.js' not in s:
                target='<script defer src="/assets/estructura-productiva.js?v=260"></script>'
                bootstrap='<script defer src="/assets/estructura-productiva-bootstrap.js?v=260"></script>'
                if target in s:
                    s=s.replace(target,bootstrap+target)

        if s!=original:
            p.write_text(s,encoding='utf-8')
            changed.append(rel)
    print(f'Navegación/integración territorial normalizada en {len(changed)} HTML')


def ensure_sitemap_url(site_root: Path, path: str) -> None:
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
ensure_sitemap_url(root,'/territorio/deporte-salud/')

required=[
    'index.html','404.html','robots.txt','sitemap.xml','site.webmanifest',
    'assets/site.css','assets/common.js','assets/data.js','assets/favicon.svg',
    'legislatura/index.html','territorio/endeudamiento/index.html',
    'territorio/migraciones/index.html','territorio/estructura-productiva/index.html',
    'territorio/deporte-salud/index.html',
    'assets/deporte-salud.js','assets/deporte-salud.css','assets/data/deporte-salud.json','assets/data/deporte-accesibilidad.json',
    'assets/estructura-productiva.js','assets/estructura-productiva-bootstrap.js','assets/estructura-productiva.css',
    'assets/data/estructura-productiva/actual.json',
    'assets/data/estructura-productiva/comunas.geojson',
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
assert 'href="/territorio/deporte-salud/"' in territorio, 'Territorio no enlaza Deporte y salud'
assert 'data-cepoes-migraciones-access="1"' in territorio, 'Falta acceso visible a Migraciones en portada Territorio'
assert 'data-cepoes-estructura-productiva-access="1"' in territorio, 'Falta acceso visible a Estructura productiva en portada Territorio'
assert 'data-cepoes-deporte-salud-access="1"' in territorio, 'Falta acceso visible a Deporte y salud en portada Territorio'

productiva=(root/'territorio'/'estructura-productiva'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Perfil comercial de las 15 comunas','Comparar comunas','Matriz comuna × rubro','Ocupación comercial 2025 → 2026','Archivo histórico · RUS 2017','/assets/estructura-productiva-bootstrap.js']:
    assert token in productiva, f'Estructura productiva V2 incompleta: {token}'

deporte=(root/'territorio'/'deporte-salud'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Deporte y vida saludable en CABA','Accesibilidad territorial','ds-access-table','Brechas comunales de infraestructura y sedes','Estaciones Saludables','Centros de Salud y Acción Comunitaria','/assets/deporte-salud.js?v=2']:
    assert token in deporte, f'Deporte y salud V2 incompleto: {token}'

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
assert 'https://cepoes.org/territorio/deporte-salud/' in locs, 'Deporte y salud ausente del sitemap'

manifest=json.loads((root/'site.webmanifest').read_text(encoding='utf-8'))
assert manifest.get('name')=='CEPOES'
assert manifest.get('theme_color')=='#16232F'
for p in html:
    s=p.read_text(encoding='utf-8',errors='replace')
    assert '/assets/favicon.svg' in s, p

actual=json.loads((root/'assets/data/estructura-productiva/actual.json').read_text(encoding='utf-8'))
assert actual['panorama']['empresas_registradas']['periodo']>=2024
ejes=actual['panorama']['ejes_comerciales']
assert ejes['periodo']['anio']>=2026
assert len(ejes['comunas'])==15
assert all('variacion_interanual_pp' in x and 'tasa_ocupacion_anterior' in x for x in ejes['comunas'].values())

geo=json.loads((root/'assets/data/estructura-productiva/comunas.geojson').read_text(encoding='utf-8'))
features=geo.get('features') or []
assert geo.get('type')=='FeatureCollection' and len(features)==15, 'GeoJSON comunal inválido'
assert {int((f.get('properties') or {}).get('comuna')) for f in features}==set(range(1,16)), 'GeoJSON no contiene las 15 comunas'

sport=json.loads((root/'assets/data/deporte-salud.json').read_text(encoding='utf-8'))
assert sport.get('version')==1, 'Dataset Deporte y salud inválido'
assert set((sport.get('comunas') or {}).keys())=={str(i) for i in range(1,16)}, 'Deporte y salud no contiene 15 comunas'
sr=sport.get('resumen') or {}
assert sr.get('clubes',0)>100 and sr.get('polideportivos',0)>=10 and sr.get('estaciones_saludables',0)>=10 and sr.get('cesac',0)>=20, 'Totales Deporte y salud fuera de rango'
assert 'programas_desactualizados' in (sport.get('alertas') or {}), 'Falta control de vigencia de Programas Deportivos'

access=json.loads((root/'assets/data/deporte-accesibilidad.json').read_text(encoding='utf-8'))
assert access.get('version')==1, 'Dataset accesibilidad deportiva inválido'
ab=access.get('base_poblacional') or {}
assert ab.get('radios',0)>=3500 and 3_000_000<=ab.get('poblacion_radios',0)<=3_200_000, 'Base censal de accesibilidad fuera de rango'
assert ab.get('diferencia_pct',1)<0.1, 'Base de accesibilidad inconsistente con población territorial CEPOES'
assert (access.get('metodologia') or {}).get('distancias_m')==[800,1000], 'Distancias de accesibilidad inesperadas'
ac=access.get('cobertura') or {}
for key in ['clubes','polideportivos','red_deportiva']:
    assert key in ac and ac[key].get('puntos_georreferenciados',0)>0, f'Falta universo de accesibilidad {key}'
    for dist in ['800','1000']:
        block=(ac[key].get('distancias') or {}).get(dist) or {}
        assert set((block.get('comunas') or {}).keys())=={str(i) for i in range(1,16)}, f'Accesibilidad {key}/{dist} sin 15 comunas'
        pct=(block.get('ciudad') or {}).get('cobertura_pct')
        assert pct is not None and 0<=pct<=100, f'Cobertura inválida {key}/{dist}'
    assert ac[key]['distancias']['1000']['ciudad']['cobertura_pct']>=ac[key]['distancias']['800']['ciudad']['cobertura_pct'], f'Cobertura no monótona {key}'

blocked=[]
for p in root.rglob('*'):
    if not p.is_file(): continue
    n=p.name.lower()
    if p.suffix.lower() in {'.7z','.part'} or 'deudores' in n and p.suffix.lower() in {'.txt','.csv','.7z'} or 'padron' in n and p.suffix.lower() in {'.txt','.csv','.7z'}:
        blocked.append(str(p.relative_to(root)))
assert not blocked, f'Archivos no publicables: {blocked[:10]}'

key=(root/'indexnow-key.txt').read_text(encoding='utf-8').strip()
assert re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key), 'IndexNow key inválida'
print(f'OK sitio: {len(html)} HTML · {len(barrios)} barrios · {len(urls)} URLs indexables · estructura productiva + deporte/salud V2 validados · sin crudos')
