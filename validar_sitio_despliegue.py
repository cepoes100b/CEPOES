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
        s=re.sub(r'(/assets/common\.js)(?:\?v=\d+)?', r'\1?v=254', s)
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
ensure_sitemap_url(root,'/presupuesto/ejecucion/')
ensure_sitemap_url(root,'/presupuesto/territorio/')
ensure_sitemap_url(root,'/temas/')

required=[
    'index.html','404.html','robots.txt','sitemap.xml','site.webmanifest',
    'assets/site.css','assets/common.js','assets/data.js','assets/favicon.svg',
    'assets/arquitectura.css','assets/data/taxonomia.json','temas/index.html',
    'legislatura/index.html','territorio/endeudamiento/index.html',
    'territorio/migraciones/index.html','territorio/estructura-productiva/index.html',
    'territorio/deporte-salud/index.html',
    'presupuesto/ejecucion/index.html','presupuesto/territorio/index.html',
    'assets/deporte-salud.js','assets/deporte-salud.css','assets/data/deporte-salud.json',
    'assets/data/deporte-accesibilidad.json','assets/data/deporte-accesibilidad-peatonal.json',
    'assets/estructura-productiva.js','assets/estructura-productiva-bootstrap.js','assets/estructura-productiva.css',
    'assets/data/estructura-productiva/actual.json','assets/data/estructura-productiva/comunas.geojson',
]
for rel in required:
    p=root/rel
    assert p.is_file() and p.stat().st_size>0, f'Falta {rel}'
html=list(root.rglob('*.html'))
assert len(html)>=100, len(html)
barrios=[p for p in (root/'territorio'/'barrios').glob('*/index.html')]
assert len(barrios)==48, f'barrios={len(barrios)}'

for p in html:
    rel=p.relative_to(root).as_posix()
    if rel.startswith('privado/'):
        continue
    s=p.read_text(encoding='utf-8',errors='replace')
    assert s.count('<nav class="site-nav">')==1, f'Navegación no canónica: {rel}'
    assert s.count('<footer class="footer">')==1, f'Footer no canónico: {rel}'
    assert len(re.findall(r'name=["\']theme-color["\']',s,re.I))==1, f'theme-color inválido: {rel}'
    assert len(re.findall(r'/assets/arquitectura\.css',s,re.I))==1, f'CSS de arquitectura duplicado: {rel}'
    assert 'href="/prensa/"' in s, f'Falta Prensa en navegación: {rel}'
    assert 'href="/observatorio/presupuesto/"' not in s, f'Enlace presupuestario antiguo: {rel}'
    assert 'href="/territorio/presupuesto/"' not in s, f'Enlace territorial antiguo: {rel}'

home=(root/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['id="home-budget-exec">—','id="home-debt-debtors">—','id="home-leg-recent">—']:
    assert token not in home, f'Fallback vacío en home: {token}'
for redundant in ['home-pulse-section','home-territory-section','home-topics-section','home-recent-section']:
    assert redundant not in home, f'Bloque redundante reapareció en home: {redundant}'
home_order=['home-editorial-hero','home-kpi-section','home-offer-section','home-latest-section','home-products-section','home-about-section']
home_positions=[home.find(token) for token in home_order]
assert all(pos>=0 for pos in home_positions) and home_positions==sorted(home_positions), f'Jerarquía de home inválida: {home_positions}'
for token in ['home-editorial-datum','home-comparison-grid','home-neighborhood-form','home-subscription-form','Leer la versión web →','/assets/home-redesign.js?v=1']:
    assert token in home, f'Bloque de portada incompleto: {token}'
assert home.count('class="home-comparison-card"')==4, 'La home debe mostrar exactamente cuatro datos comparados'
for token in ['El Boca–River de la mora','25,5% vs. 9,1%','/publicaciones/notas/el-boca-river-de-la-mora/']:
    assert token in home, f'Editorial central de endeudamiento incompleto: {token}'
observatorio=(root/'observatorio'/'index.html').read_text(encoding='utf-8',errors='replace')
assert 'id="obs-pulse"></div>' not in observatorio, 'Señales vacías en Observatorio'
assert observatorio.count('id="obs-pulse"')==1, 'Contenedor de señales duplicado en Observatorio'
assert observatorio.count('class="pulse-card"')==3, f'Señales duplicadas en Observatorio: {observatorio.count("class=\"pulse-card\"")}'
assert observatorio.count('observatory-overview')==1, 'Panorama del Observatorio duplicado'
presupuesto=(root/'presupuesto'/'index.html').read_text(encoding='utf-8',errors='replace')
assert 'Cargando último trimestre oficial' not in presupuesto and 'cargando…' not in presupuesto and '<b>—</b>' not in presupuesto, 'Fallback vacío en Presupuesto'
for rel,url in [('presupuesto/ejecucion/index.html','https://cepoes.org/presupuesto/ejecucion/'),('presupuesto/territorio/index.html','https://cepoes.org/presupuesto/territorio/')]:
    s=(root/rel).read_text(encoding='utf-8',errors='replace')
    canonical=re.search(r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*>',s,re.I)
    assert canonical and re.search(rf'\bhref=["\']{re.escape(url)}["\']',canonical.group(0),re.I), f'Canonical incorrecto: {rel}'
htaccess=(root/'.htaccess').read_text(encoding='utf-8',errors='replace')
for rule in ['Redirect 301 /observatorio/presupuesto/ /presupuesto/ejecucion/','Redirect 301 /territorio/presupuesto/ /presupuesto/territorio/']:
    assert rule in htaccess, f'Falta redirect: {rule}'

territorio=(root/'territorio'/'index.html').read_text(encoding='utf-8',errors='replace')
for path,label in [('/territorio/migraciones/','Migraciones'),('/territorio/estructura-productiva/','Estructura productiva'),('/territorio/deporte-salud/','Deporte y salud')]:
    assert f'href="{path}"' in territorio, f'Territorio no enlaza {label}'
for token in ['Explorar','Temas territoriales','/presupuesto/territorio/']:
    assert token in territorio, f'Navegación territorial sin {token}'
for token in ['class="territory-desktop"','class="territory-mobile"','Explorar Territorio','class="territory-mobile-menu"']:
    assert token in territorio, f'Navegación territorial responsive incompleta: {token}'

publicaciones=(root/'publicaciones'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['id="archivo-por-tema"','Notas de prensa','/temas/#vivienda-y-habitat']:
    assert token in publicaciones, f'Archivo editorial incompleto: {token}'
for slug in ['boletin-01-mayo-2026','boletin-02-junio-2026','boletin-03-julio-2026','boletin-04-agosto-2026']:
    bulletin=(root/'publicaciones'/'boletines'/slug/'index.html').read_text(encoding='utf-8',errors='replace')
    for token in ['class="bol"','Descargar PDF','/assets/boletines-html.css?v=1','/assets/publicaciones-html-cepoes.css?v=3','/assets/boletines-html.js?v=1']:
        assert token in bulletin, f'Boletín HTML incompleto ({slug}): {token}'
    assert bulletin.count('class="bol"') == 1 and '</style>' not in bulletin, f'CSS visible como texto en {slug}'
    assert '.html"' not in bulletin, f'Navegación plana sin normalizar en {slug}'
debt_note=(root/'publicaciones'/'notas'/'el-boca-river-de-la-mora'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['25,5%','9,1%','La Boca','Núñez','estimación territorial agregada','/territorio/endeudamiento/']:
    assert token in debt_note, f'Nota de endeudamiento incompleta: {token}'
report=(root/'publicaciones'/'informe-coyuntura-01-junio-2026'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['class="bol inf"','Descargar PDF','/assets/informe-html.css?v=1','/assets/publicaciones-html-cepoes.css?v=3','/assets/boletines-html.js?v=1']:
    assert token in report, f'Informe HTML incompleto: {token}'
assert report.count('class="bol inf"') == 1 and '</style>' not in report, 'El informe contiene estilos incrustados como texto'
deporte=(root/'territorio'/'deporte-salud'/'index.html').read_text(encoding='utf-8',errors='replace')
assert all(token not in deporte for token in ('Siguiente etapa', 'El siguiente salto', 'Una etapa posterior')), 'Deporte y salud expone contenido futuro'
migraciones=(root/'territorio'/'migraciones'/'index.html').read_text(encoding='utf-8',errors='replace')
assert 'Línea de trabajo prioritaria' not in migraciones and 'Movilidad internacional' in migraciones, 'Rótulo institucional de Migraciones incorrecto'
temas=(root/'temas'/'index.html').read_text(encoding='utf-8',errors='replace')
assert temas.count('class="ia-topic-card"')==8, 'Taxonomía pública incompleta'
taxonomy=json.loads((root/'assets/data/taxonomia.json').read_text(encoding='utf-8'))
assert len(taxonomy.get('temas') or [])==8 and len({x['slug'] for x in taxonomy['temas']})==8

productiva=(root/'territorio'/'estructura-productiva'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Perfil comercial de las 15 comunas','Comparar comunas','Matriz comuna × rubro','Ocupación comercial 2025 → 2026','Archivo histórico · RUS 2017','/assets/estructura-productiva-bootstrap.js']:
    assert token in productiva, f'Estructura productiva V2 incompleta: {token}'

deporte=(root/'territorio'/'deporte-salud'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Deporte y vida saludable en CABA','Accesibilidad territorial','ds-access-table','ds-access-method','ds-access-compare','Recorrido peatonal estimado','OpenStreetMap','Brechas comunales de infraestructura y sedes','Estaciones Saludables','Centros de Salud y Acción Comunitaria','/assets/deporte-salud.js?v=3']:
    assert token in deporte, f'Deporte y salud V3 incompleto: {token}'

js=(root/'assets'/'deporte-salud.js').read_text(encoding='utf-8',errors='replace')
for token in ['deporte-accesibilidad-peatonal.json','accessWalk','accessEuclid','accessMethod','renderAccess']:
    assert token in js, f'JS Deporte V3 incompleto: {token}'

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
assert 'https://cepoes.org/territorio/deporte-salud/' in locs
assert 'https://cepoes.org/presupuesto/ejecucion/' in locs
assert 'https://cepoes.org/presupuesto/territorio/' in locs
assert 'https://cepoes.org/temas/' in locs
assert 'https://cepoes.org/observatorio/presupuesto/' not in locs
assert 'https://cepoes.org/territorio/presupuesto/' not in locs

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
assert geo.get('type')=='FeatureCollection' and len(features)==15
assert {int((f.get('properties') or {}).get('comuna')) for f in features}==set(range(1,16))

sport=json.loads((root/'assets/data/deporte-salud.json').read_text(encoding='utf-8'))
assert sport.get('version')==1
assert set((sport.get('comunas') or {}).keys())=={str(i) for i in range(1,16)}
sr=sport.get('resumen') or {}
assert sr.get('clubes',0)>100 and sr.get('polideportivos',0)>=10 and sr.get('estaciones_saludables',0)>=10 and sr.get('cesac',0)>=20
assert 'programas_desactualizados' in (sport.get('alertas') or {})

access=json.loads((root/'assets/data/deporte-accesibilidad.json').read_text(encoding='utf-8'))
assert access.get('version')==1
ab=access.get('base_poblacional') or {}
assert ab.get('radios',0)>=3500 and 3_000_000<=ab.get('poblacion_radios',0)<=3_200_000
assert ab.get('diferencia_pct',1)<0.1
assert (access.get('metodologia') or {}).get('distancias_m')==[800,1000]
ac=access.get('cobertura') or {}
for key in ['clubes','polideportivos','red_deportiva']:
    assert key in ac and ac[key].get('puntos_georreferenciados',0)>0
    for dist in ['800','1000']:
        block=(ac[key].get('distancias') or {}).get(dist) or {}
        assert set((block.get('comunas') or {}).keys())=={str(i) for i in range(1,16)}
        pct=(block.get('ciudad') or {}).get('cobertura_pct')
        assert pct is not None and 0<=pct<=100
    assert ac[key]['distancias']['1000']['ciudad']['cobertura_pct']>=ac[key]['distancias']['800']['ciudad']['cobertura_pct']

walk=json.loads((root/'assets/data/deporte-accesibilidad-peatonal.json').read_text(encoding='utf-8'))
assert walk.get('version')==1
wm=walk.get('metodologia') or {}
assert wm.get('network_type')=='walk' and wm.get('distancias_m')==[800,1000]
wb=walk.get('base_poblacional') or {}
assert wb.get('poblacion_radios')==ab.get('poblacion_radios')
assert wb.get('muestras_ponderadas',0)>150_000
wg=walk.get('grafo_peatonal') or {}
assert wg.get('nodos',0)>20_000 and wg.get('aristas_dirigidas',0)>40_000
wc=(walk.get('control_conexion_red') or {}).get('umbrales') or {}
assert wc.get('100',{}).get('poblacion_pct',99)<0.5
assert wc.get('200',{}).get('poblacion_pct',99)<0.1
wcoverage=walk.get('cobertura') or {}
for key in ['clubes','polideportivos','red_deportiva']:
    assert key in wcoverage and wcoverage[key].get('puntos_georreferenciados',0)>0
    for dist in ['800','1000']:
        block=(wcoverage[key].get('distancias') or {}).get(dist) or {}
        assert set((block.get('comunas') or {}).keys())=={str(i) for i in range(1,16)}
        pct=(block.get('ciudad') or {}).get('cobertura_pct')
        assert pct is not None and 0<=pct<=100
        assert pct<=ac[key]['distancias'][dist]['ciudad']['cobertura_pct']+0.5
    assert wcoverage[key]['distancias']['1000']['ciudad']['cobertura_pct']>=wcoverage[key]['distancias']['800']['ciudad']['cobertura_pct']

blocked=[]
for p in root.rglob('*'):
    if not p.is_file(): continue
    n=p.name.lower()
    if p.suffix.lower() in {'.7z','.part'} or 'deudores' in n and p.suffix.lower() in {'.txt','.csv','.7z'} or 'padron' in n and p.suffix.lower() in {'.txt','.csv','.7z'}:
        blocked.append(str(p.relative_to(root)))
assert not blocked, f'Archivos no publicables: {blocked[:10]}'

key=(root/'indexnow-key.txt').read_text(encoding='utf-8').strip()
assert re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key), 'IndexNow key inválida'
print(f'OK sitio: {len(html)} HTML · {len(barrios)} barrios · {len(urls)} URLs indexables · estructura productiva + deporte/salud V3 validados · sin crudos')
