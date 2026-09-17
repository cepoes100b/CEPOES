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
        s=re.sub(r'(/assets/common\.js)(?:\?v=\d+)?', r'\1?v=255', s)
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

            mental='/observatorio/salud-mental/'
            if f'href="{mental}"' not in s:
                target=re.search(r'<a\b[^>]*href="/observatorio/personas-mayores/"[^>]*>',s,re.I)
                if not target:
                    target=re.search(r'<a\b[^>]*href="/territorio/deporte-salud/"[^>]*>',s,re.I)
                if target:
                    s=s[:target.start()]+'<a href="/observatorio/salud-mental/">Salud mental</a>'+s[target.start():]

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
ensure_sitemap_url(root,'/observatorio/personas-mayores/')
ensure_sitemap_url(root,'/observatorio/salud-mental/')
ensure_sitemap_url(root,'/balance/')
ensure_sitemap_url(root,'/balance/vivienda-y-alquiler/')
ensure_sitemap_url(root,'/balance/salud-publica/')
ensure_sitemap_url(root,'/balance/presupuesto-y-modelo-de-gestion/')

required=[
    'index.html','404.html','robots.txt','sitemap.xml','site.webmanifest','balance/index.html',
    'balance/vivienda-y-alquiler/index.html','balance/salud-publica/index.html',
    'balance/presupuesto-y-modelo-de-gestion/index.html',
    'assets/site.css','assets/common.js','assets/data.js','assets/favicon.svg',
    'assets/arquitectura.css','assets/data/taxonomia.json','temas/index.html',
    'observatorio/personas-mayores/index.html','assets/personas-mayores.css',
    'assets/personas-mayores.js','assets/data/personas-mayores.json',
    'observatorio/salud-mental/index.html','assets/salud-mental.css','assets/salud-mental.js','assets/data/salud-mental.json',
    'legislatura/index.html','territorio/endeudamiento/index.html',
    'territorio/migraciones/index.html','territorio/estructura-productiva/index.html',
    'territorio/deporte-salud/index.html',
    'presupuesto/ejecucion/index.html','presupuesto/territorio/index.html',
    'presupuesto/descentralizacion/index.html','assets/descentralizacion.css',
    'assets/descentralizacion-observatorio.js',
    'assets/data/descentralizacion-comunas.json','assets/data/descentralizacion-transparencia-2024.json',
    'assets/data/descentralizacion-competencias.json',
    'assets/deporte-salud.js','assets/deporte-salud.css','assets/data/deporte-salud.json',
    'assets/data/deporte-accesibilidad.json','assets/data/deporte-accesibilidad-peatonal.json',
    'assets/estructura-productiva.js','assets/estructura-productiva-bootstrap.js','assets/estructura-productiva.css',
    'assets/data/estructura-productiva/actual.json','assets/data/estructura-productiva/comunas.geojson',
    'assets/informes-tematicos.css','assets/publicaciones/personas-mayores-caba.svg',
    'assets/publicaciones/situacion-calle-caba.svg',
    'assets/endeudamiento-informe.css',
    'publicaciones/informes/personas-mayores-caba/index.html',
    'publicaciones/informes/personas-mayores-caba/informe-personas-mayores-caba-cepoes.pdf',
    'publicaciones/informes/situacion-de-calle-caba/index.html',
    'publicaciones/informes/situacion-de-calle-caba/informe-situacion-de-calle-caba-cepoes.pdf',
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
    assert '/assets/arquitectura.css?v=16' in s, f'CSS de arquitectura sin versión vigente: {rel}'
    assert 'href="/prensa/"' in s, f'Falta Prensa en navegación: {rel}'
    nav_block=re.search(r'<nav class="site-nav">.*?</nav>',s,re.S)
    footer_block=re.search(r'<footer class="footer">.*?</footer>',s,re.S)
    assert nav_block and 'href="/balance/"' in nav_block.group(0), f'Falta Balance en navegación: {rel}'
    assert footer_block and 'href="/balance/"' in footer_block.group(0), f'Falta Balance en footer: {rel}'
    assert 'href="/observatorio/presupuesto/"' not in s, f'Enlace presupuestario antiguo: {rel}'
    assert 'href="/territorio/presupuesto/"' not in s, f'Enlace territorial antiguo: {rel}'

common_search=(root/'assets'/'common.js').read_text(encoding='utf-8',errors='replace')
for route in ['/balance/','/balance/vivienda-y-alquiler/','/balance/salud-publica/','/balance/presupuesto-y-modelo-de-gestion/']:
    assert route in common_search, f'Falta indexar en búsqueda: {route}'
assert "group:'Balance'" in common_search and 'x.priority||0' in common_search, 'Buscador sin grupo o prioridad de Balance'
assert 'const merged=new Map()' in common_search, 'Buscador sin deduplicación por URL'
architecture_css=(root/'assets'/'arquitectura.css').read_text(encoding='utf-8',errors='replace')
for token in ['max-width:1450px','max-width:1240px','min-width:761px','.site-nav .nav-links.open{display:flex}']:
    assert token in architecture_css, f'Navegación adaptable incompleta: {token}'
assert '@media(min-width:761px){.budget-page .wrap{max-width:var(--max)}}' in architecture_css, 'Ejecución presupuestaria sin ancho editorial en escritorio'

for report_rel, required_tokens in {
    'publicaciones/informes/personas-mayores-caba/index.html': [
        'LAS PERSONAS MAYORES EN LA CIUDAD AUTÓNOMA DE BUENOS AIRES',
        'Autoría institucional:',
        'informe-personas-mayores-caba-cepoes.pdf',
        'class="article full-report"',
        'TABLA 2: RESIDENCIAS DE LARGA ESTADÍA EN EL ENTORNO URBANO',
        'REFERENCIAS BIBLIOGRÁFICAS',
    ],
    'publicaciones/informes/situacion-de-calle-caba/index.html': [
        'La cara más helada del invierno en Buenos Aires',
        'Autoría institucional:',
        'informe-situacion-de-calle-caba-cepoes.pdf',
        'class="article full-report"',
        'La economía del margen: changas, reciclaje e ingresos de subsistencia',
        '5.176',
        '3.563',
        '68,8%',
    ],
}.items():
    report_html=(root/report_rel).read_text(encoding='utf-8',errors='replace')
    for token in required_tokens:
        assert token in report_html, f'Informe temático incompleto ({report_rel}): {token}'
reports_index=(root/'publicaciones/informes/index.html').read_text(encoding='utf-8',errors='replace')
for route in ['/publicaciones/informes/personas-mayores-caba/','/publicaciones/informes/situacion-de-calle-caba/']:
    assert route in reports_index and route in common_search, f'Informe no integrado en archivo o buscador: {route}'
debt_report=(root/'publicaciones/informes/endeudarse-para-llegar-a-fin-de-mes/index.html').read_text(encoding='utf-8',errors='replace')
for token in ['/assets/informes-tematicos.css?v=1','/assets/endeudamiento-informe.css?v=1','class="site-nav"','class="subnav"','Autoría institucional:','data-pdf-viewer=','Leer PDF']:
    assert token in debt_report, f'Informe de endeudamiento fuera del sistema visual común: {token}'

home=(root/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['id="home-budget-exec">—','id="home-debt-debtors">—','id="home-leg-recent">—']:
    assert token not in home, f'Fallback vacío en home: {token}'
for redundant in ['home-pulse-section','home-territory-section','home-topics-section','home-recent-section']:
    assert redundant not in home, f'Bloque redundante reapareció en home: {redundant}'
home_order=['home-editorial-hero','home-strategy-section','home-kpi-section','home-offer-section','home-latest-section','home-products-section','home-about-section']
home_positions=[home.find(token) for token in home_order]
assert all(pos>=0 for pos in home_positions) and home_positions==sorted(home_positions), f'Jerarquía de home inválida: {home_positions}'
for token in ['home-editorial-datum','home-strategy-grid','La Ciudad hoy','Balance de gestión 2007–2026','Una Ciudad posible','href="/balance/"','home-comparison-grid','home-neighborhood-form','home-subscription-form','Leer la versión web →','/assets/home-redesign.js?v=1']:
    assert token in home, f'Bloque de portada incompleto: {token}'
assert home.count('class="home-comparison-card"')==4, 'La home debe mostrar exactamente cuatro datos comparados'
assert home.count('home-strategy-card')==3, 'La home debe mostrar exactamente tres recorridos estratégicos'
balance=(root/'balance'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Balance de gestión 2007–2026','Decisiones públicas','Impacto territorial','Capacidad estatal','Vivienda y alquiler','Salud pública','Presupuesto y modelo de gestión']:
    assert token in balance, f'Portada de Balance incompleta: {token}'
assert 'href="/balance/vivienda-y-alquiler/"' in balance, 'Balance no enlaza el dossier publicado de Vivienda'
assert 'href="/balance/salud-publica/"' in balance, 'Balance no enlaza el dossier publicado de Salud'
assert 'href="/balance/presupuesto-y-modelo-de-gestion/"' in balance, 'Balance no enlaza el dossier publicado de Presupuesto'
housing=(root/'balance'/'vivienda-y-alquiler'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Vivienda y alquiler','Dos salarios mínimos para un monoambiente','−15%','−27%','Desigualdad territorial','Qué decisiones explican el resultado','Qué propone CEPOES','Alcance de esta primera versión','/publicaciones/boletines/boletin-04-agosto-2026/']:
    assert token in housing, f'Dossier de Vivienda incompleto: {token}'
assert housing.count('class="housing-kpi"')==3, 'El dossier debe mostrar exactamente tres indicadores principales'
assert '2007–2026 completo' not in housing, 'El dossier no debe presentar como completa una serie todavía parcial'
health=(root/'balance'/'salud-publica'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Salud pública','El piso más bajo en cuatro años','−12%','34','50','Una red extensa, con cargas desiguales','Qué decisiones explican el resultado','La salud mental exige una red accesible','Claudia Negri','Qué propone CEPOES','Alcance de esta primera versión','/publicaciones/boletines/boletin-04-agosto-2026/']:
    assert token in health, f'Dossier de Salud incompleto: {token}'
assert health.count('class="housing-kpi"')==3, 'El dossier de Salud debe mostrar exactamente tres indicadores principales'
assert '2007–2026 completo' not in health, 'El dossier de Salud no debe presentar como completa una serie todavía parcial'
budget=(root/'balance'/'presupuesto-y-modelo-de-gestion'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Presupuesto y modelo de gestión','El gasto cae, pero no en todas partes','−10%','+34%','−7%','Pagar más; controlar menos','Qué revela la ejecución','Tres dossiers, una misma pregunta','Qué propone CEPOES','Alcance de esta primera versión','/publicaciones/boletines/boletin-04-agosto-2026/']:
    assert token in budget, f'Dossier de Presupuesto incompleto: {token}'
assert budget.count('class="housing-kpi"')==3, 'El dossier de Presupuesto debe mostrar exactamente tres indicadores principales'
assert '2007–2026 completo' not in budget, 'El dossier de Presupuesto no debe presentar como completa una serie todavía parcial'
proposals=(root/'propuestas'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Una Ciudad posible','Un banco de políticas públicas en construcción','instrumentos, responsables, costos, plazos, metas e indicadores']:
    assert token in proposals, f'Portada de propuestas no migrada: {token}'
# La editorial de portada debe coincidir con la configuración editorial vigente.
editorial_path = root/'assets'/'data'/'home-editorial.json'
assert editorial_path.is_file(), 'Falta assets/data/home-editorial.json'

editorial = json.loads(editorial_path.read_text(encoding='utf-8'))

editorial_required = {
    'title': editorial.get('title'),
    'url': editorial.get('url'),
    'datum.value': (editorial.get('datum') or {}).get('value'),
}

for field, token in editorial_required.items():
    assert token, f'Editorial vigente sin {field}: home-editorial.json'
    assert token in home, (
        f'La portada no coincide con home-editorial.json · '
        f'{field}: {token}'
    )
observatorio=(root/'observatorio'/'index.html').read_text(encoding='utf-8',errors='replace')
assert 'id="obs-pulse"></div>' not in observatorio, 'Señales vacías en Observatorio'
assert observatorio.count('id="obs-pulse"')==1, 'Contenedor de señales duplicado en Observatorio'
assert observatorio.count('class="pulse-card"')==3, f'Señales duplicadas en Observatorio: {observatorio.count("class=\"pulse-card\"")}'
assert observatorio.count('observatory-overview')==1, 'Panorama del Observatorio duplicado'
assert '/observatorio/personas-mayores/' in observatorio, 'Observatorio no enlaza el eje Personas mayores'
assert '/observatorio/salud-mental/' in observatorio, 'Observatorio no enlaza el eje Salud mental'
personas=(root/'observatorio'/'personas-mayores'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Una Ciudad envejecida no es, por eso, una Ciudad cuidada','17,7%','$2.835.928','Dato, elaboración e interpretación','/assets/data/personas-mayores.json']:
    assert token in personas, f'Eje Personas mayores incompleto: {token}'
assert 'cargando' not in personas.lower() and '>—<' not in personas, 'Personas mayores tiene un fallback vacío'
personas_data=json.loads((root/'assets/data/personas-mayores.json').read_text(encoding='utf-8'))
assert personas_data.get('schema')=='cepoes-personas-mayores-v1' and personas_data.get('status')=='VALIDADO'
assert personas_data['indicadores']['canasta_inquilinos']['valor']>personas_data['indicadores']['canasta_propietarios']['valor']
salud_mental=(root/'observatorio'/'salud-mental'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Salud mental: mirar la tendencia sin perder de vista el territorio','5.209','11,84','236','7,97','0800-999-0091','/assets/salud-mental.css?v=2','/assets/salud-mental.js?v=2']:
    assert token in salud_mental, f'Eje Salud mental incompleto: {token}'
sm_js=(root/'assets/salud-mental.js').read_text(encoding='utf-8',errors='replace')
assert '/assets/data/salud-mental.json' in sm_js, 'JS de Salud mental no enlaza el dataset validado'
assert '/assets/data/estructura-productiva/comunas.geojson' in sm_js, 'JS de Salud mental no enlaza la geometría comunal'
sm_data=json.loads((root/'assets/data/salud-mental.json').read_text(encoding='utf-8'))
assert sm_data.get('schema')=='cepoes-salud-mental-v3' and sm_data.get('status')=='VALIDADO'
assert sm_data['headline']['argentina']['suicidios_snic']==5209
assert sm_data['headline']['caba']['suicidios_snic']==236
assert len(sm_data.get('jurisdicciones_2025') or [])==24
assert sum(int(x['suicidios_2025']) for x in sm_data['jurisdicciones_2025'])==5209
assert len(sm_data.get('red_atencion_caba',{}).get('cesac_con_salud_mental') or [])>=43
assert len(sm_data.get('red_atencion_caba',{}).get('efectores_especializados') or [])==5
assert sm_data.get('contraste_deis',{}).get('estado') in {'ACTUALIZADO','ULTIMO_DATO_VALIDADO'}
presupuesto=(root/'presupuesto'/'index.html').read_text(encoding='utf-8',errors='replace')
assert 'Cargando último trimestre oficial' not in presupuesto and 'cargando…' not in presupuesto and '<b>—</b>' not in presupuesto, 'Fallback vacío en Presupuesto'
for modulo in ['ejecucion', 'territorio', 'diagnostico']:
    presupuesto_modulo=(root/'presupuesto'/modulo/'index.html').read_text(encoding='utf-8',errors='replace')
    assert not re.search(r'id=["\']data-date["\'][^>]*>\s*cargando', presupuesto_modulo, re.I), f'Fecha de actualización pendiente en presupuesto/{modulo}'
descentralizacion=(root/'presupuesto'/'descentralizacion'/'index.html').read_text(encoding='utf-8',errors='replace')
for token in ['Descentralización: cuánto administran las Comunas','class="budget-decentralization-page"','class="page-hero"','class="breadcrumbs"','/assets/descentralizacion.css?v=1','id="commune-map"','id="ranking"','id="selected-title"','Ver competencias transferidas y pendientes','/assets/descentralizacion-observatorio.js?v=4']:
    assert token in descentralizacion, f'Descentralización incompleta: {token}'
assert descentralizacion.count('id="content"')==1 and descentralizacion.count('id="content-body"')==1, 'Contenedores de Descentralización duplicados'
assert '<style' not in descentralizacion, 'Descentralización conserva CSS incrustado'
assert not re.search(r'id=["\']data-date["\'][^>]*>\s*cargando', descentralizacion, re.I), 'Fecha de actualización pendiente en Descentralización'
dc_js=(root/'assets'/'descentralizacion-observatorio.js').read_text(encoding='utf-8',errors='replace')
for token in ['estructura-productiva/comunas.geojson','drawMap','renderDetail','descentralizacion-transparencia-2024.json']:
    assert token in dc_js, f'JS de Descentralización incompleto: {token}'
dc_data=json.loads((root/'assets/data/descentralizacion-comunas.json').read_text(encoding='utf-8'))
assert dc_data.get('schema')=='cepoes-descentralizacion-comunas-v2' and dc_data.get('status')=='VALIDADO'
assert len(dc_data.get('comunas') or [])==15 and {x.get('comuna') for x in dc_data['comunas']}==set(range(1,16))
for rel,url in [('presupuesto/ejecucion/index.html','https://cepoes.org/presupuesto/ejecucion/'),('presupuesto/territorio/index.html','https://cepoes.org/presupuesto/territorio/')]:
    s=(root/rel).read_text(encoding='utf-8',errors='replace')
    canonical=re.search(r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*>',s,re.I)
    assert canonical and re.search(rf'\bhref=["\']{re.escape(url)}["\']',canonical.group(0),re.I), f'Canonical incorrecto: {rel}'
htaccess=(root/'.htaccess').read_text(encoding='utf-8',errors='replace')
for rule in ['Redirect 301 /observatorio/presupuesto/ /presupuesto/ejecucion/','Redirect 301 /territorio/presupuesto/ /presupuesto/territorio/']:
    assert rule in htaccess, f'Falta redirect: {rule}'

territorio=(root/'territorio'/'index.html').read_text(encoding='utf-8',errors='replace')
for path,label in [('/territorio/migraciones/','Migraciones'),('/territorio/estructura-productiva/','Estructura productiva'),('/territorio/deporte-salud/','Deporte y salud'),('/observatorio/salud-mental/','Salud mental')]:
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
assert 'https://cepoes.org/observatorio/personas-mayores/' in locs
assert 'https://cepoes.org/presupuesto/descentralizacion/' in locs
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
