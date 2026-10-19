"""Build bulletin landing pages from the same public catalog on every deployment."""
import html
import re
from pathlib import Path
from scripts.generar_newsletter_feed import editions
from scripts.newsletter_editorial import Tree


def catalog(site):
    items = editions(site)
    for item in items:
        page = site / item['url'].lstrip('/') / 'index.html'
        root = Tree(page.read_text(encoding='utf-8')).root
        covers = root.find('img', cls='bol-hero__cover')
        pdfs = [a.attrs['href'] for a in root.find('a') if a.attrs.get('href', '').startswith('/publicaciones/files/') and a.attrs['href'].endswith('.pdf')]
        if not covers or not pdfs:
            raise ValueError('Boletín sin portada o PDF: ' + item['url'])
        item['cover'] = covers[0].attrs['src']
        item['pdf'] = pdfs[0]
        item['period'] = page.parent.name.split('-', 2)[2].replace('-', ' ').capitalize()
    if not items:
        raise ValueError('Catálogo de boletines vacío')
    return list(reversed(items))


def render(items):
    esc = lambda value: html.escape(str(value), quote=True)
    latest = items[0]
    label = lambda item: f"N.º {item['edition']} · {item['period']}"
    lead = ('<section class="section publications-latest" data-bulletin-latest><div class="wrap">'
        '<div class="section-head"><div><span class="eyebrow">Último boletín</span>'
        f'<h2>{esc(label(latest))}</h2></div><a class="more" href="/publicaciones/boletines/">Ver la serie completa →</a></div>'
        f'<div class="publication-lead"><a class="publication-lead-cover" href="{esc(latest["url"])}">'
        f'<img src="{esc(latest["cover"])}" alt="Tapa de {esc(label(latest))}"></a>'
        '<div class="publication-lead-copy"><span class="tag-soft">La Ciudad que habitamos</span>'
        f'<h3>{esc(latest["title"])}</h3><p class="publication-lead-subtitle">{esc(latest["summary"])}</p>'
        f'<div class="bulletin-actions"><a class="btn btn-primary" href="{esc(latest["url"])}">Leer boletín web →</a>'
        f'<a class="text-action" download href="{esc(latest["pdf"])}">Descargar PDF ↓</a></div></div></div></div></section>')
    cards = []
    for item in items:
        cards.append(f'<a class="bulletin-cover-card" href="{esc(item["url"])}"><div class="bulletin-cover-image">'
            f'<img src="{esc(item["cover"])}" alt="Tapa de {esc(label(item))}" loading="lazy"></div>'
            f'<div><span class="eyebrow">{esc(label(item))}</span><h3>{esc(item["title"])}</h3>'
            '<span class="more">Leer →</span></div></a>')
    archive = ('<section class="section alt" data-bulletin-archive><div class="wrap"><div class="section-head"><div>'
        '<span class="eyebrow">Serie mensual</span><h2>La Ciudad que habitamos · Todas las ediciones</h2></div></div>'
        '<p class="section-sub">Vivienda, salud, empleo, finanzas públicas y educación en CABA.</p>'
        '<div class="bulletin-covers-grid">' + ''.join(cards) + '</div></div></section>')
    return lead, archive


def generate(site):
    site = Path(site)
    items = catalog(site)
    lead, archive = render(items)
    for relative in ('publicaciones/index.html', 'publicaciones/boletines/index.html'):
        path = site / relative
        source = path.read_text(encoding='utf-8')
        found = [0, 0]
        def replace(match):
            section = match[0]
            if re.search(r'data-bulletin-latest|class="[^"]*(?:publications-latest|latest-bulletin)', section):
                found[0] += 1
                return lead
            if re.search(r'data-bulletin-archive|class="(?:bulletin-grid|bulletin-covers-grid)"', section):
                found[1] += 1
                return archive
            return section
        updated = re.sub(r'<section\b[^>]*>.*?</section>', replace, source, flags=re.S)
        if found != [1, 1]:
            raise ValueError(f'Bloques de boletines ausentes o duplicados en {relative}: {found}')
        path.write_text(updated, encoding='utf-8')
    validate(site, items)
    return items


def validate(site, items=None, require_resources=False):
    site = Path(site)
    items = catalog(site) if items is None else items
    if require_resources:
        for item in items:
            for resource in ('cover', 'pdf'):
                if not (site / item[resource].lstrip('/')).is_file():
                    raise ValueError('Recurso del boletín ausente: ' + item[resource])
    for relative in ('publicaciones/index.html', 'publicaciones/boletines/index.html'):
        root = Tree((site / relative).read_text(encoding='utf-8')).root
        latest = [n for n in root.find('section') if 'data-bulletin-latest' in n.attrs]
        archives = [n for n in root.find('section') if 'data-bulletin-archive' in n.attrs]
        if len(latest) != 1 or len(archives) != 1:
            raise ValueError('Falta catálogo automático en ' + relative)
        urls = [a.attrs.get('href') for a in archives[0].find('a', cls='bulletin-cover-card')]
        if urls != [item['url'] for item in items]:
            raise ValueError('Archivo de boletines desactualizado en ' + relative)
        lead_urls = [a.attrs.get('href') for a in latest[0].find('a')]
        if items[0]['url'] not in lead_urls or items[0]['pdf'] not in lead_urls:
            raise ValueError('Último boletín desactualizado en ' + relative)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('site', type=Path)
    args = parser.parse_args()
    print('Catálogo de boletines:', len(generate(args.site)))
