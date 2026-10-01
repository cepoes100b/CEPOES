#!/usr/bin/env python3
"""Un catálogo editorial genera el archivo completo y los últimos cinco informes."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from generar_lo_nuevo import Page, local_path

REGISTRY = Path(__file__).resolve().parent / 'deploy/reports-registry.json'
ARCHIVE = 'publicaciones/informes/index.html'
LANDING = 'publicaciones/index.html'
PRIVATE = {'privado', 'admin', 'borradores', 'revision'}


def read_reports(registry=REGISTRY):
    data = json.loads(registry.read_text(encoding='utf-8'))
    assert data['version'] == 1 and data['reports'], 'Catálogo de informes vacío o inválido'
    reports = data['reports']
    urls = set()
    for report in reports:
        for key in ('url', 'title', 'description', 'kind', 'period', 'cover', 'pdf'):
            assert isinstance(report.get(key), str) and report[key].strip(), f'Falta {key}: {report}'
        for key in ('url', 'cover', 'pdf'):
            value = report[key]
            assert value.startswith('/') and not value.startswith('//') and '..' not in value and not urlsplit(value).query, f'Ruta inválida: {value}'
        assert report['url'].endswith('/') and report['pdf'].endswith('.pdf'), f'URL/PDF inválido: {report}'
        assert report['url'] not in urls, f'Informe duplicado: {report["url"]}'
        urls.add(report['url'])
        assert re.fullmatch(r'\d{4}-\d{2}(?:-\d{2})?', report['period']), 'Período inválido'
        date.fromisoformat(report['period'] + ('-01' if len(report['period']) == 7 else ''))
    # Los informes históricos con sólo mes conservan su orden editorial, sin inventar días.
    return sorted(reports, key=lambda r: r['period'], reverse=True)


def validate_sources(site, reports, check_assets=True):
    registered = {r['url']: r for r in reports}
    for path in site.rglob('index.html'):
        rel = path.relative_to(site)
        if PRIVATE.intersection(rel.parts) or str(rel) in (ARCHIVE, LANDING):
            continue
        source = path.read_text(encoding='utf-8')
        page = Page(source)
        if page.excluded or re.search(r'http-equiv=["\']refresh', source, re.I):
            continue
        url = '/' + rel.parent.as_posix() + '/'
        report_page = url.startswith('/publicaciones/informes/') or bool(re.search(r'class=["\'][^"\']*\bweb-report\b', source))
        # Incluye informes alojados junto a un monitor, como Tierras y soberanía.
        for anchor in re.findall(r'<a\b[^>]*>.*?</a>', source, re.S | re.I):
            href = re.search(r'href=["\']([^"\']+\.pdf)["\']', anchor, re.I)
            if href and re.search(r'descargar\s+informe\s+completo', re.sub('<[^>]+>', '', anchor), re.I):
                pdf = local_path(site, href[1], path.parent)
                report_page |= bool(pdf and pdf.parent == path.parent.resolve())
        assert not report_page or url in registered, f'Informe fuera del catálogo: {url}. Registrarlo en deploy/reports-registry.json antes de publicar.'
    for report in reports:
        path = site / report['url'].strip('/') / 'index.html'
        assert path.is_file(), f'Informe sin página: {report["url"]}'
        source = path.read_text(encoding='utf-8')
        assert not Page(source).excluded and not PRIVATE.intersection(path.relative_to(site).parts), f'Informe privado en catálogo: {report["url"]}'
        assert not re.search(r'http-equiv=["\']refresh', source, re.I), f'Informe redirigido: {report["url"]}'
        pdfs = {local_path(site, href, path.parent) for href in re.findall(r'href=["\']([^"\']+\.pdf)["\']', source, re.I)}
        assert (site / report['pdf'].lstrip('/')).resolve() in pdfs, f'PDF no enlazado desde el informe: {report["url"]}'
        if check_assets:
            for key in ('pdf', 'cover'):
                assert (site / report[key].lstrip('/')).is_file(), f'Falta {key}: {report[key]}'


def card(report, latest=False):
    r = {k: escape(v, quote=True) for k, v in report.items()}
    cls = 'report-feature" data-publications-latest-report' if latest else 'report-row"'
    thumb = 'report-thumb' if latest else 'report-row-thumb'
    copy = '' if latest else ' class="report-row-copy"'
    subtitle = f'<p class="report-subtitle">{r["subtitle"]}</p>' if r.get('subtitle') else ''
    return (f'<article class="{cls}>'
            f'<a class="{thumb}" href="{r["url"]}"><img alt="Tapa de {r["title"]}" src="{r["cover"]}" loading="lazy" /></a>'
            f'<div{copy}><span class="tag-soft">{r["kind"]}</span>'
            f'<h3><a href="{r["url"]}">{r["title"]}</a></h3>{subtitle}<p>{r["description"]}</p>'
            f'<div class="compact-actions"><a class="more" href="{r["url"]}">Ver síntesis web →</a>'
            f'<a class="text-action" download href="{r["pdf"]}">Descargar informe completo ↓</a></div></div></article>')


def generate(site, registry=REGISTRY, check_assets=True):
    reports = read_reports(registry)
    validate_sources(site, reports, check_assets)
    outputs = []
    for rel, latest in ((ARCHIVE, False), (LANDING, True)):
        path = site / rel
        source = path.read_text(encoding='utf-8')
        pattern = r'<article class="report-feature" data-publications-latest-report>.*?</article>' if latest else r'<article class="report-row">.*?</article>'
        matches = list(re.finditer(pattern, source, re.S))
        assert matches, f'No se encontró la plantilla de informes: {rel}'
        between = source[matches[0].start():matches[-1].end()]
        assert not re.sub(pattern, '', between, flags=re.S).strip(), f'Tarjetas no contiguas: {rel}'
        cards = '\n'.join(card(r, latest) for r in (reports[:5] if latest else reports))
        outputs.append((path, source[:matches[0].start()] + cards + source[matches[-1].end():]))
    for path, content in outputs:
        path.write_text(content, encoding='utf-8')
    print(f'Catálogo: {len(reports)} informes; últimos {min(5, len(reports))} en Publicaciones')
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('site', type=Path)
    parser.add_argument('--registry', type=Path, default=REGISTRY)
    parser.add_argument('--check-source', action='store_true', help='Verifica la cobertura del overlay; los activos heredados se verifican en el build completo.')
    args = parser.parse_args()
    if args.check_source:
        validate_sources(args.site, read_reports(args.registry), check_assets=False)
    else:
        generate(args.site, args.registry)
