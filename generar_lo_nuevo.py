#!/usr/bin/env python3
"""Genera novedades públicas durante cada publicación, comparando con producción."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

SECTIONS = {'publicaciones', 'prensa', 'balance', 'territorio', 'observatorio',
            'presupuesto', 'legislatura', 'propuestas', 'cepoes', 'datos'}
LABELS = {'boletin': 'Boletín', 'informe': 'Informe', 'analisis': 'Análisis', 'prensa': 'Prensa',
          'balance': 'Balance', 'herramienta': 'Herramienta', 'datos': 'Datos'}
MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
CANONICAL_ROUTES = {
    '/observatorio/presupuesto/': '/presupuesto/ejecucion/',
    '/territorio/presupuesto/': '/presupuesto/territorio/',
}


def canonical_url(url):
    return CANONICAL_ROUTES.get(url, url)


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.title = []
        self.text = []
        self.description = ''
        self.main = self.heading = self.skip = 0
        self.refs = set()
        self.excluded = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta':
            if a.get('name') == 'description':
                self.description = a.get('content', '')
            if a.get('name') == 'robots' and 'noindex' in a.get('content', ''):
                self.excluded = True
        if tag in ('script', 'style', 'nav', 'footer'):
            self.skip += 1
        if tag == 'main':
            self.main += 1
        if tag == 'h1':
            self.heading += 1
        if tag == 'script' and a.get('src'):
            self.refs.add(a['src'])

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav', 'footer'):
            self.skip = max(0, self.skip - 1)
        if tag == 'main':
            self.main = max(0, self.main - 1)
        if tag == 'h1':
            self.heading = max(0, self.heading - 1)

    def handle_data(self, data):
        if not self.skip:
            if self.heading:
                self.title.append(data.strip())
            if self.main:
                self.text.append(data.strip())


def local_path(root, ref, parent):
    parsed = urlsplit(ref)
    if parsed.netloc and parsed.netloc != 'cepoes.org':
        return None
    path = root / parsed.path.lstrip('/') if parsed.path.startswith('/') else parent / parsed.path
    path = path.resolve()
    return path if path.is_relative_to(root.resolve()) else None


def snapshot(root, path):
    source = path.read_text(encoding='utf-8')
    page = Page(source)
    title = ' '.join(page.title)
    if not title or page.excluded or re.search(r'<meta[^>]+http-equiv=["\']refresh', source, re.I):
        return None
    # Sólo texto público y datos JSON vinculados: CSS, navegación y versiones JS
    # no alteran por sí solos la fecha de la novedad.
    data = set(re.findall(r'["\']([^"\'\s]+\.json(?:\?[^"\'\s]*)?)["\']', source))
    for ref in page.refs:
        if urlsplit(ref).path in ('/assets/common.js', '/assets/related.js'):
            continue
        script = local_path(root, ref, path.parent)
        if script and script.is_file():
            for ref_data in re.findall(r'["\']([^"\'\s]+\.json(?:\?[^"\'\s]*)?)["\']', script.read_text(encoding='utf-8')):
                data.add(ref_data)
    parts = [title, page.description, ' '.join(' '.join(page.text).split())]
    for ref in sorted(data):
        file = local_path(root, ref, path.parent)
        if file and file.is_file() and file.suffix == '.json':
            value = json.loads(file.read_text(encoding='utf-8'))
            # Las fechas de procesamiento no son nuevos valores estadísticos.
            def clean(item):
                if isinstance(item, dict):
                    return {k: clean(v) for k, v in item.items() if k not in
                            {'generated_at', 'processed_at', 'fecha_generacion', 'fecha_procesamiento'}}
                return [clean(v) for v in item] if isinstance(item, list) else item
            parts.append(json.dumps(clean(value), sort_keys=True, ensure_ascii=False))
    dates = re.findall(r'"date(?:Published|Modified)"\s*:\s*"(\d{4}-\d{2}-\d{2})', source)
    return {'title': title, 'description': page.description,
            'fingerprint': hashlib.sha256('\n'.join(parts).encode()).hexdigest(),
            'declared_date': max(dates) if dates else None}


def kind(url):
    if url.startswith('/publicaciones/boletines/') and url != '/publicaciones/boletines/':
        return 'boletin'
    if '/informes/' in url or url.startswith('/publicaciones/informe-'):
        return 'informe'
    if url.startswith('/prensa/'):
        return 'prensa'
    if '/notas/' in url or url.startswith('/propuestas/'):
        return 'analisis'
    if url.startswith('/balance/'):
        return 'balance'
    if url.startswith('/datos/'):
        return 'datos'
    return 'herramienta'


def generate(site, previous, today=None):
    today = today or datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).date().isoformat()
    target = site / 'lo-nuevo/index.html'
    template = target.read_text(encoding='utf-8')
    old_registry = previous / 'assets/data/lo-nuevo.json'
    registry = json.loads(old_registry.read_text(encoding='utf-8')) if old_registry.exists() else {'entries': []}
    entries = {}
    for entry in registry['entries']:
        url = canonical_url(entry['url'])
        entries[url] = {**entry, 'url': url}
    # Migración: conserva el historial editorial de las tarjetas originales.
    if not old_registry.exists():
        for card in re.findall(r'<article\b[^>]*class="new-card[^>]*>.*?</article>', template, re.S):
            link = re.search(r'class="new-card-link" href="([^"]+)"', card)
            date = re.search(r'(\d{1,2}) (' + '|'.join(MONTHS) + r') (\d{4})', card)
            if link and date:
                url = canonical_url(link[1])
                entries[url] = {'url': url, 'date': f'{date[3]}-{MONTHS.index(date[2])+1:02d}-{int(date[1]):02d}', 'event': 'Publicado'}
    valid = set()
    for path in sorted(site.rglob('index.html')):
        rel = path.relative_to(site)
        if rel.parts[0] not in SECTIONS or any(part in {'privado', 'admin', 'borradores', 'revision'} for part in rel.parts):
            continue
        current = snapshot(site, path)
        if not current:
            continue
        url = canonical_url('/' + str(rel.parent).replace('\\', '/') + '/')
        valid.add(url)
        old_path = previous / rel
        old = snapshot(previous, old_path) if old_path.exists() else None
        prior = entries.get(url)
        if not old or current['fingerprint'] != old['fingerprint']:
            date, event = today, 'Actualizado' if old else 'Nuevo'
        elif prior:
            date, event = prior['date'], prior.get('event', 'Publicado')
        elif current['declared_date'] and current['declared_date'] <= today:
            date, event = current['declared_date'], 'Publicado'
        elif kind(url) == 'boletin':
            # Recupera ediciones anteriores sin atribuirles una fecha de publicación inventada.
            date, event = today, 'Incorporado al archivo'
        else:
            # Sin fecha comprobable, una página heredada ingresa al modificarse.
            continue
        entries[url] = {**current, 'url': url, 'date': date, 'event': event, 'type': kind(url)}
    entries = sorted((e for u, e in entries.items() if u in valid and 'title' in e),
                     key=lambda e: (e['date'], e['url']), reverse=True)
    cards = []
    esc = html.escape
    for e in entries:
        year, month, day = map(int, e['date'].split('-'))
        cards.append(f'<article class="new-card" data-type="{e["type"]}" data-topic="{esc(e["url"].split("/")[1])}">'
                     f'<div class="new-card-date"><span>{LABELS[e["type"]]}</span><time datetime="{e["date"]}">{day} {MONTHS[month-1]} {year}</time></div>'
                     f'<div><h3>{esc(e["title"])}</h3><p>{esc(e["description"])}</p><div class="new-card-meta"><span>{e["event"]}</span></div></div>'
                     f'<a class="new-card-link" href="{esc(e["url"], quote=True)}">Ver contenido →</a></article>')
    template, count = re.subn(r'(<div class="new-list" id="new-list">).*?(</div><div class="new-empty")',
                              lambda m: m[1] + '\n' + '\n'.join(cards) + '\n' + m[2], template, flags=re.S)
    assert count == 1, 'No se encontró el contenedor de novedades'
    latest = entries[0]['date'] if entries else today
    template = re.sub(r'<aside class="new-summary">.*?</aside>',
                      f'<aside class="new-summary"><strong>{len(entries)}</strong><span>contenidos recientes</span><p>Se actualiza automáticamente con cada publicación del sitio. Última novedad: <time datetime="{latest}">{latest}</time>.</p></aside>', template, flags=re.S)
    options = ''.join(f'<option value="{key}">{value}</option>' for key, value in LABELS.items())
    template = re.sub(r'(<select id="new-type">).*?</select>', lambda m: m[1] + '<option value="">Todos</option>' + options + '</select>', template)
    options = ''.join(f'<option value="{s}">{s.capitalize()}</option>' for s in sorted({e['url'].split('/')[1] for e in entries}))
    template = re.sub(r'(<select id="new-topic">).*?</select>', lambda m: m[1] + '<option value="">Todas las secciones</option>' + options + '</select>', template)
    template = template.replace('<label>Tema<select id="new-topic">', '<label>Sección<select id="new-topic">')
    template = re.sub(r'(<aside class="new-criterion"><h2>Qué entra en “Lo nuevo”</h2>)<p>.*?</p>',
                      lambda m: m[1] + '<p>Los boletines, las nuevas páginas públicas y las actualizaciones de sus contenidos o datos se incorporan con cada publicación del sitio. La fecha indica cuándo se publicó o actualizó el contenido. Las ediciones recuperadas sin fecha comprobable se señalan como «Incorporado al archivo». Los cambios de estilos y navegación conservan la fecha anterior.</p>', template, flags=re.S)
    target.write_text(template, encoding='utf-8')
    output = site / 'assets/data/lo-nuevo.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'version': 1, 'entries': entries}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert len({e['url'] for e in entries}) == len(entries)
    print(f'Lo nuevo: {len(entries)} contenidos públicos; fechas y enlaces verificados')
    return entries


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('site', type=Path)
    parser.add_argument('--previous', type=Path, required=True)
    args = parser.parse_args()
    generate(args.site, args.previous)

