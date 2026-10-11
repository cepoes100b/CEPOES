"""Piezas de difusión y metadatos estáticos; sólo contenido público canónico."""
from __future__ import annotations
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse, urlencode
from PIL import Image, ImageDraw, ImageFont, ImageOps

ORIGIN = 'https://cepoes.org'
BLOCKED = re.compile(r'/(?:privado|private|admin|login|auth|newsletter|suscripcion|subscribe|unsubscribe|confirmar|baja|legislativa)(?:/|$)', re.I)
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
BOLD = FONT.with_name('DejaVuSans-Bold.ttf')


def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', '', value))).strip()


def attr(tag, name):
    match = re.search(r'\b' + name + r'\s*=\s*(["\'])(.*?)\1', tag, re.S | re.I)
    return html.unescape(match[2]) if match else ''


def meta(source, key):
    for tag in re.findall(r'<meta\b[^>]*>', source, re.I):
        if attr(tag, 'name') == key or attr(tag, 'property') == key:
            return attr(tag, 'content')
    return ''


def canonical(source, rel):
    if BLOCKED.search(rel) or not rel.endswith('/index.html') and rel != '/index.html':
        return None
    if meta(source, 'robots').lower().find('noindex') >= 0 or re.search(r'http-equiv=["\']refresh', source, re.I):
        return None
    route = rel[:-10]
    for tag in re.findall(r'<link\b[^>]*>', source, re.I):
        if attr(tag, 'rel') == 'canonical':
            u = urlparse(attr(tag, 'href'))
            if u.netloc not in ('cepoes.org', 'www.cepoes.org') or u.path != route or u.query or u.fragment:
                return None
    return route


def lines(draw, text, font, width):
    result, line = [], ''
    for word in text.split():
        # Break exceptionally long words, preserving all characters.
        pieces = []
        while draw.textlength(word, font=font) > width and len(word) > 1:
            n = len(word) - 1
            while draw.textlength(word[:n], font=font) > width: n -= 1
            pieces.append(word[:n]); word = word[n:]
        pieces.append(word)
        for piece in pieces:
            candidate = (line + ' ' + piece).strip()
            if line and draw.textlength(candidate, font=font) > width:
                result.append(line); line = piece
            else: line = candidate
    if line: result.append(line)
    return result


def textblock(draw, text, box, size, color, bold=False):
    x, y, w, h = box
    while size >= 16:
        f = ImageFont.truetype(str(BOLD if bold else FONT), size)
        wrapped = lines(draw, text, f, w)
        step = int(size * 1.3)
        if len(wrapped) * step <= h: break
        size -= 2
    if len(wrapped) * step > h:
        raise ValueError('Texto demasiado largo para la placa')
    for line in wrapped:
        draw.text((x, y), line, font=f, fill=color); y += step


def card(destination, title, description, label, size, cover=None, branded=True, pink=False):
    w, h = size
    image = Image.new('RGB', size, '#16232f')
    d = ImageDraw.Draw(image)
    accent = '#f1a2c3' if pink else '#3ec8f0'
    margin = 64 if w == 1200 else 72
    story = h == 1920
    top = 210 if story else 52
    d.rectangle((0, 0, 18, h), fill=accent)
    # Decorative city blocks, intentionally without scales or data.
    for i in range(9):
        x = w - 360 + i * 42
        height = [90, 140, 110, 175, 130, 195, 155, 100, 170][i]
        d.rounded_rectangle((x, h - height - 80, x + 28, h - 80), 4, fill='#223d4a')
    if branded:
        d.text((margin, top), 'CEP', font=ImageFont.truetype(str(BOLD), 42), fill='white')
        dx = d.textlength('CEP', font=ImageFont.truetype(str(BOLD), 42))
        d.text((margin + dx, top), 'OES', font=ImageFont.truetype(str(BOLD), 42), fill=accent)
        d.text((margin, top + 58), 'SOMOS 100 BARRIOS', font=ImageFont.truetype(str(BOLD), 19), fill='white')
    textblock(d, label.upper(), (margin, top + 115, w - margin * 2, 70), 22, accent, True)
    text_y = top + 210
    cover_width = 310 if w == 1200 and cover else 0
    text_width = w - margin * 2 - cover_width - (35 if cover_width else 0)
    title_height = 220 if w == 1200 else (420 if story else 360)
    textblock(d, title, (margin, text_y, text_width, title_height), 56 if w == 1200 else 64, 'white', True)
    if description and w != 1200:
        textblock(d, description[:350], (margin, text_y + title_height + 45, text_width, 290), 29, '#dbe9ed')
    if cover_width:
        thumbnail = ImageOps.contain(Image.open(cover).convert('RGB'), (cover_width, 420))
        image.paste(thumbnail, (w - margin - cover_width, top + 110))
    elif cover and h == 1920:
        thumbnail = ImageOps.contain(Image.open(cover).convert('RGB'), (500, 480))
        image.paste(thumbnail, (margin, 1130))
    d.text((margin, h - (230 if story else 100)), 'Leé más en cepoes.org', font=ImageFont.truetype(str(BOLD), 26), fill=accent)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, optimize=True)


def inject(source, rel, site, reports):
    route = canonical(source, rel)
    if route is None or '</head>' not in source or '</body>' not in source:
        return source
    report = reports.get(route, {})
    h1 = re.search(r'<h1\b[^>]*>(.*?)</h1>', source, re.S | re.I)
    t = re.search(r'<title\b[^>]*>(.*?)</title>', source, re.S | re.I)
    # The home h1 belongs to the featured article, not to the institution.
    if route == '/':
        title = clean(t[1]) if t else 'CEPOES'
    else:
        title = report.get('title') or clean(h1[1] if h1 else t[1] if t else 'CEPOES')
        title = re.sub(r'\s*[|·—-]\s*CEPOES.*$', '', title).strip()
    description = report.get('description') or meta(source, 'description')
    label = report.get('kind') or ('Boletín' if '/boletin-' in route else 'Territorio' if route.startswith('/territorio/') else 'Presupuesto' if route.startswith('/presupuesto/') else 'Observatorio' if route.startswith('/observatorio/') else 'CEPOES / 100 Barrios')
    cover = site / report.get('cover', '').lstrip('/')
    if cover.suffix.lower() not in ('.png', '.jpg', '.jpeg') or not cover.is_file(): cover = None
    branded = route != '/territorio/seguridad-barrios-populares/'
    digest = hashlib.sha256(json.dumps([1, title, description, label, branded, cover.read_bytes().hex() if cover else ''], ensure_ascii=False).encode()).hexdigest()[:12]
    base = '/assets/compartir/' + hashlib.sha256(route.encode()).hexdigest()[:12] + '-' + digest
    for name, size in [('enlace', (1200, 630)), ('publicacion', (1080, 1350)), ('historia', (1080, 1920))]:
        dest = site / (base + '-' + name + '.png').lstrip('/')
        if not dest.is_file(): card(dest, title, description, label, size, cover, branded, 'octubre-rosa' in route)
    def escape(value): return html.escape(value, quote=True)
    # Replace rather than append: previews remain deterministic across builds.
    source = re.sub(r'<meta\b(?=[^>]*(?:property|name)=["\'](?:og:[\w:]+|twitter:[\w:]+)["\'])[^>]*>', '', source, flags=re.I)
    metadata = {'og:title': title, 'og:description': description, 'og:url': ORIGIN + route, 'og:type': 'article' if report or '/boletin-' in route else 'website', 'og:site_name': 'CEPOES', 'og:locale': 'es_AR', 'og:image': ORIGIN + base + '-enlace.png', 'og:image:width': '1200', 'og:image:height': '630', 'og:image:alt': title, 'twitter:card': 'summary_large_image', 'twitter:title': title, 'twitter:description': description, 'twitter:image': ORIGIN + base + '-enlace.png', 'twitter:image:alt': title}
    tags = ''.join(f'<meta {"name" if k.startswith("twitter:") else "property"}="{k}" content="{escape(v)}">' for k,v in metadata.items())
    source = re.sub(r'<link\b[^>]*href=[\"\']/assets/compartir\.css(?:\?[^\"\']*)?[\"\'][^>]*>', '', source, flags=re.I)
    source = re.sub(r'<script\b[^>]*src=[\"\']/assets/compartir\.js(?:\?[^\"\']*)?[\"\'][^>]*></script>', '', source, flags=re.I)
    def revision(name):
        asset = site / ('assets/' + name)
        return hashlib.sha256(asset.read_bytes()).hexdigest()[:12] if asset.is_file() else '1'
    tags += f'<link rel="stylesheet" href="/assets/compartir.css?v={revision("compartir.css")}"><script defer src="/assets/compartir.js?v={revision("compartir.js")}"></script>'
    source = source.replace('</head>', tags + '</head>', 1)
    url = ORIGIN + route
    def share_url(platform):
        return url + '?' + urlencode({'utm_source': platform, 'utm_medium': 'social', 'utm_campaign': 'compartir'})
    wa = 'https://wa.me/?' + urlencode({'text': title + '\n' + share_url('whatsapp')})
    x = 'https://twitter.com/intent/tweet?' + urlencode({'text': title, 'url': share_url('x')})
    fb = 'https://www.facebook.com/sharer/sharer.php?' + urlencode({'u': share_url('facebook')})
    icons = {
        'native': '<path d="M12 16V3m-5 5 5-5 5 5M5 13v7h14v-7"/>',
        'whatsapp': '<path d="M21 11.5a9 9 0 0 1-13.6 7.8L3 21l1.7-4.4A9 9 0 1 1 21 11.5Z"/><path d="M8 7c-1 3 2 7 5 8l2-2-3-1-1 1-2-2 1-1-2-3Z"/>',
        'x': '<path d="m4 4 16 16M20 4 4 20M4 4h5l11 16h-5Z"/>',
        'facebook': '<path d="M14 21V12h4l1-4h-5V6c0-1 1-2 2-2h3V1h-3c-4 0-6 2-6 5v2H7v4h3v9"/>',
        'copy': '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M15 8V4H4v11h4"/>',
        'instagram': '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".7"/>',
    }
    def icon(key, label):
        return '<svg class="share-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + icons[key] + '</svg><span class="share-sr">' + label + '</span>'
    block = f'''<section class="cepoes-share" aria-label="Compartir este contenido" data-share-url="{escape(url)}" data-share-title="{escape(title)}" data-share-image="{base}"><div class="wrap"><div class="share-heading"><span>Compartir</span><p>Compartí información para conocer y transformar nuestros barrios.</p></div><div class="share-actions"><button type="button" data-share-native title="Compartir desde tu dispositivo" hidden>{icon("native", "Compartir desde tu dispositivo")}</button><a data-share-platform="whatsapp" href="{escape(wa)}" target="_blank" rel="noopener noreferrer" title="Compartir en WhatsApp">{icon("whatsapp", "Compartir en WhatsApp")}</a><a data-share-platform="x" href="{escape(x)}" target="_blank" rel="noopener noreferrer" title="Compartir en X">{icon("x", "Compartir en X")}</a><a data-share-platform="facebook" href="{escape(fb)}" target="_blank" rel="noopener noreferrer" title="Compartir en Facebook">{icon("facebook", "Compartir en Facebook")}</a><button type="button" data-share-copy title="Copiar enlace">{icon("copy", "Copiar enlace")}</button><button type="button" data-share-instagram title="Preparar para Instagram">{icon("instagram", "Preparar para Instagram")}</button></div><p class="share-status" role="status" aria-live="polite"></p><dialog class="share-dialog" aria-label="Preparar para Instagram"><button class="share-close" type="button" data-share-close aria-label="Cerrar">×</button><h2>Listo para Instagram</h2><p>Elegí una placa, guardala y subila a Instagram. En historias, agregá el enlace con el sticker «Enlace».</p><div class="share-preview"><img src="{base}-publicacion.png" alt="{escape(title)}" loading="lazy" width="1080" height="1350"></div><div class="share-actions"><a href="{base}-publicacion.png" download data-share-platform="instagram_download">Guardar publicación</a><a href="{base}-historia.png" download data-share-platform="instagram_download">Guardar historia</a><button type="button" data-share-file hidden>Compartir imagen…</button><button type="button" data-share-caption>Copiar texto y enlace</button></div><p class="share-status" role="status" aria-live="polite"></p></dialog></div></section>'''
    source = re.sub(r'<section class="cepoes-share".*?</section>', '', source, flags=re.S)
    # After reading, before global search/footer. Does not displace map controls.
    return source.replace('<footer class="footer">', block + '<footer class="footer">', 1) if '<footer class="footer">' in source else source.replace('</body>', block + '</body>', 1)


def prepare(site, registry):
    reports = {r['url']: r for r in json.loads(registry.read_text())['reports']}
    count = 0
    for path in site.rglob('*.html'):
        source = path.read_text(encoding='utf-8')
        updated = inject(source, '/' + path.relative_to(site).as_posix(), site, reports)
        if updated != source:
            path.write_text(updated, encoding='utf-8'); count += 1
    referenced = set()
    for page in site.rglob('*.html'):
        referenced.update(re.findall(r'/assets/compartir/([a-f0-9]{12}-[a-f0-9]{12})', page.read_text(encoding='utf-8')))
    directory = site / 'assets/compartir'
    for image in directory.glob('*.png'):
        match = re.fullmatch(r'([a-f0-9]{12}-[a-f0-9]{12})-(enlace|publicacion|historia)\.png', image.name)
        if match and match[1] not in referenced: image.unlink()
    return count
