"""Catálogo transversal compartido por Salud, Educación, Temas y Territorio."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'deploy/axes-registry.json'

@lru_cache(maxsize=1)
def registry():
    data = json.loads(REGISTRY.read_text(encoding='utf-8'))
    assert data['version'] == 1
    theme_ids = {t['id'] for t in data['themes']}
    assert len(theme_ids) == len(data['themes'])
    seen, groups = set(), set()
    for group in data['groups']:
        assert group['id'] not in groups and set(group['themes']) <= theme_ids
        assert set(group['axes']) <= {'salud', 'educacion', 'territorio'}
        groups.add(group['id'])
        for item in group['links']:
            route = item['url']
            assert route.startswith('/') and not route.startswith('//') and '..' not in route
            assert route not in seen, f'Contenido duplicado: {route}'
            assert item['label'] and item['title']
            seen.add(route)
    return data

def card(group):
    links = ''.join(f'<a href="{escape(x["url"], quote=True)}">{escape(x["label"])} <span aria-hidden="true">→</span></a>' for x in group['links'])
    return (f'<article class="ia-topic-card axis-topic-card" data-axis-group="{escape(group["id"])}">'
            f'<h3>{escape(group["title"])}</h3><p>{escape(group["summary"])}</p>'
            f'<div class="ia-topic-links axis-content-links">{links}</div></article>')

def axis_grid(axis):
    return '<div class="ia-topic-grid axis-topic-grid">' + ''.join(card(g) for g in registry()['groups'] if axis in g['axes']) + '</div>'

def replace_axis_grid(source, axis):
    # One controlled catalog in each landing; repeated normalization is stable.
    pattern = r'<div class="ia-topic-grid(?: axis-topic-grid)?">.*?(?=</div></div></section>)'
    match = re.search(pattern, source, re.S)
    if not match:
        raise ValueError(f'No se encontró la grilla del eje {axis}')
    return source[:match.start()] + axis_grid(axis)[:-6] + source[match.end():]

def territory_catalog(source):
    source = re.sub(r"<h1\b[^>]*>.*?</h1>", "<h1>Territorio</h1>", source, count=1, flags=re.S)
    source = re.sub(r'<section\b[^>]*id=["\'](?:territorio-catalogo|tierras-soberania-acceso|limpieza-urbana-acceso)["\'][^>]*>.*?</section>', '', source, flags=re.S)
    tools = ''.join(f'<a href="{escape(t["url"], quote=True)}">{escape(t["label"])}</a>' for t in registry()['tools'])
    block = ('<section class="section axis-territory-catalog" id="territorio-catalogo"><div class="wrap">'
             '<div class="section-head"><div><span class="eyebrow">Todos los accesos a la vista</span>'
             '<h2>Explorar Territorio</h2><p>Elegí un tema o recorré los mapas, las comunas y los barrios.</p></div></div>'
             f'<nav class="axis-tool-links" aria-label="Mapas y herramientas territoriales">{tools}</nav>'
             '<h2 id="temas-territoriales" class="axis-catalog-title">Temas de los barrios</h2>'
             + axis_grid('territorio') + '</div></section>')
    header = re.search(r'<header\b[^>]*class=["\'][^"\']*page-hero[^"\']*["\'][^>]*>.*?</header>', source, re.S)
    if not header:
        raise ValueError('Portada territorial sin encabezado principal')
    return source[:header.end()] + block + source[header.end():]

def themes_catalog(source):
    themes = registry()['themes']
    top, sections = [], []
    for theme in themes:
        tid, title = theme['id'], escape(theme['title'])
        portal = theme['portal']
        top.append('<article class="ia-topic-card"><h2>' + title + '</h2><p>' + escape(theme['summary']) + '</p>'
                   + '<div class="ia-topic-links"><a href="#' + tid + '">Ver todos los contenidos →</a>'
                   + (f'<a href="{portal}">Ir al eje →</a>' if not portal.startswith('/temas/#') else '')
                   + '</div></article>')
        groups = ''.join(card(g) for g in registry()['groups'] if tid in g['themes'])
        sections.append(f'<section class="section axis-theme-section" id="{tid}"><div class="wrap">'
                        f'<div class="section-head"><div><h2>{title}</h2><p>{escape(theme["summary"])}</p></div></div>'
                        '<div class="ia-topic-grid axis-topic-grid">' + groups + '</div></div></section>')
    start, end = source.index('<section'), source.rindex('</main>')
    block = '<section class="section"><div class="wrap"><div class="ia-topic-grid">' + ''.join(top) + '</div></div></section>' + ''.join(sections)
    source = source[:start] + block + source[end:]
    source = source.replace('El producto, el tema y el territorio son dimensiones distintas de un mismo contenido.',
                            'Encontrá cada contenido desde los ejes con los que se relaciona y accedé directamente a sus mapas, informes y notas.')
    return source

def context_links(source, route):
    source = re.sub(r'<nav class="axis-context".*?</nav>', '', source, flags=re.S)
    groups = [g for g in registry()['groups'] if any(urlsplit(x['url']).path == route for x in g['links'])]
    if not groups:
        return source
    axes = {a for g in groups for a in g['axes']}
    themes = {t for g in groups for t in g['themes']}
    items = [('salud', 'Salud'), ('educacion', 'Educación'), ('territorio', 'Territorio')]
    links = [f'<a href="/{key}/">{label}</a>' for key, label in items if key in axes]
    for theme in registry()['themes']:
        if theme['id'] in themes and theme['portal'] not in {'/salud/' if 'salud' in axes else '', '/educacion/' if 'educacion' in axes else ''}:
            links.append(f'<a href="{escape(theme["portal"], quote=True)}">{escape(theme["title"])}</a>')
    block = '<nav class="axis-context" aria-label="Ejes de este contenido"><span>En estos ejes:</span>' + ''.join(links) + '</nav>'
    if re.search(r'<main\b', source):
        return re.sub(r'(<main\b[^>]*>)', lambda m: m[0] + block, source, count=1)
    return re.sub(r'(</header>)', lambda m: m[0] + block, source, count=1)

def prepare(source, rel):
    if rel == '/salud/index.html':
        return replace_axis_grid(source, 'salud')
    if rel == '/educacion/index.html':
        return replace_axis_grid(source, 'educacion')
    if rel == '/territorio/index.html':
        return territory_catalog(source)
    if rel == '/temas/index.html':
        return themes_catalog(source)
    return context_links(source, rel.removesuffix('index.html'))

def audit(site):
    """Bloquea enlaces rotos y nuevos informes sin clasificación editorial."""
    data = registry()
    routes = {x['url'] for g in data['groups'] for x in g['links']}
    for route in routes:
        target = site / urlsplit(route).path.lstrip('/') / 'index.html'
        assert target.is_file(), f'Destino de eje ausente: {route}'
    reports = json.loads((ROOT / 'deploy/reports-registry.json').read_text())['reports']
    for report in reports:
        assert report['url'] in routes, f'Informe sin eje: {report["url"]}. Agregarlo a deploy/axes-registry.json.'
    aliases = {"/observatorio/presupuesto/": "/presupuesto/ejecucion/",
               "/territorio/presupuesto/": "/presupuesto/territorio/"}
    thematic = set()
    for pattern in ('salud/*/index.html', 'educacion/*/index.html', 'publicaciones/notas/*/index.html', 'publicaciones/informes/*/index.html', 'observatorio/*/index.html', 'territorio/*/index.html'):
        for page in site.glob(pattern):
            route = '/' + page.parent.relative_to(site).as_posix() + '/'
            if route in aliases:
                assert aliases[route] in routes, f'Redirección sin eje de destino: {route}'
                continue
            if route in {'/observatorio/agenda/', '/territorio/barrios/', '/territorio/comparar/', '/territorio/mapa-tematico/'} or re.fullmatch(r'/territorio/comuna-\d+/', route):
                continue
            if re.search(r'http-equiv=["\']refresh', page.read_text(), re.I):
                continue
            thematic.add(route)
    missing = thematic - {urlsplit(r).path for r in routes}
    assert not missing, 'Contenidos temáticos sin eje: ' + ', '.join(sorted(missing))
    return {'groups': len(data['groups']), 'contents': len(routes), 'thematic_pages': len(thematic)}

def update_sitemaps(site):
    """Agrega rutas clasificadas faltantes conservando las fechas existentes."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    modified = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date().isoformat()
    routes = sorted({x['url'] for g in registry()['groups'] for x in g['links']})
    path = site / 'sitemap.txt'
    if path.exists():
        source = path.read_text().rstrip() + '\n'
        lines = set(source.splitlines())
        source += ''.join('https://cepoes.org' + r + '\n' for r in routes if 'https://cepoes.org' + r not in lines)
        path.write_text(source)
    path = site / 'sitemap.xml'
    if path.exists():
        source = path.read_text()
        existing = set(re.findall(r'<loc>([^<]+)</loc>', source))
        additions = ''.join('  <url><loc>https://cepoes.org' + escape(r) + '</loc><lastmod>' + modified + '</lastmod></url>\n' for r in routes if 'https://cepoes.org' + r not in existing)
        source = source.replace('</urlset>', additions + '</urlset>')
        path.write_text(source)
