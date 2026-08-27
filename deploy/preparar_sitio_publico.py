#!/usr/bin/env python3
"""Normaliza la capa publica y deja contenido util sin depender de JavaScript."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEME_COLOR = "#16232F"
ARCHITECTURE_CSS = "/assets/arquitectura.css?v=8"


TOPICS = [
    ("vivienda-y-habitat", "Vivienda y hábitat"),
    ("salud-y-cuidados", "Salud y cuidados"),
    ("educacion-e-infancias", "Educación e infancias"),
    ("trabajo-e-ingresos", "Trabajo e ingresos"),
    ("precios-y-consumo", "Precios y consumo"),
    ("produccion-y-comercio", "Producción y comercio"),
    ("presupuesto-y-estado", "Presupuesto y Estado"),
    ("ambiente-y-movilidad", "Ambiente y movilidad"),
]


def load_json(name: str) -> dict:
    with (ROOT / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def active_for(path: Path, site: Path) -> str:
    rel = "/" + path.relative_to(site).as_posix()
    if rel.endswith("index.html"):
        rel = rel[: -len("index.html")]
    for section in ("observatorio", "presupuesto", "territorio", "legislatura", "publicaciones", "propuestas", "prensa", "cepoes"):
        if rel.startswith(f"/{section}/"):
            return section
    return ""


def nav(active: str) -> str:
    items = [
        ("observatorio", "/observatorio/", "Observatorio"),
        ("presupuesto", "/presupuesto/", "Presupuesto"),
        ("territorio", "/territorio/", "Territorio"),
        ("legislatura", "/legislatura/", "Legislatura"),
        ("publicaciones", "/publicaciones/", "Publicaciones"),
        ("propuestas", "/propuestas/", "Propuestas"),
        ("prensa", "/prensa/", "Prensa"),
        ("cepoes", "/cepoes/", "CEPOES"),
    ]
    links = "".join(
        f'<a{(" class=\"active\"" if key == active else "")} href="{url}">{label}</a>'
        for key, url, label in items
    )
    return (
        '<nav class="site-nav"><div class="wrap nav-in">'
        '<a class="brand" href="/"><span class="logo">CEP<b>OES</b></span>'
        '<span class="brand-sep"></span><span class="brand-sub"><small>Centro de estudios de</small>'
        '<strong>SOMOS 100 BARRIOS</strong></span></a>'
        f'<div class="nav-links">{links}'
        '<a class="nav-cta" href="/territorio/equipamientos/">Qué hay en tu barrio →</a></div>'
        '<button aria-label="Buscar en CEPOES" class="search-btn" data-search-open title="Buscar en CEPOES">'
        '<svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="6.5"></circle>'
        '<path d="m16 16 4 4"></path></svg></button>'
        '<button aria-label="Cambiar tema" class="theme-btn" data-theme-toggle>◐</button>'
        '<button aria-label="Abrir menú" class="menu-btn" data-menu-toggle>☰</button>'
        '</div></nav>'
    )


SEARCH = (
    '<dialog aria-labelledby="site-search-title" class="search-modal" id="site-search"><div class="search-shell">'
    '<div class="search-head"><div><span class="eyebrow">CEPOES</span><strong id="site-search-title">Buscar en el sitio</strong></div>'
    '<button aria-label="Cerrar búsqueda" class="search-close" data-search-close type="button">×</button></div>'
    '<label class="search-field"><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="6.5"></circle>'
    '<path d="m16 16 4 4"></path></svg><input autocomplete="off" id="site-search-input" '
    'placeholder="Indicadores, comunas, expedientes, publicaciones, propuestas…" type="search"></label>'
    '<div class="search-filters" id="site-search-filters">'
    '<button class="chip active" data-search-filter="Todo">Todo</button>'
    '<button class="chip" data-search-filter="Datos">Datos</button>'
    '<button class="chip" data-search-filter="Publicaciones">Publicaciones</button>'
    '<button class="chip" data-search-filter="Territorio">Territorio</button>'
    '<button class="chip" data-search-filter="Propuestas">Propuestas</button>'
    '<button class="chip" data-search-filter="Legislatura">Legislatura</button>'
    '<a class="chip" href="/temas/">Explorar temas</a></div>'
    '<div class="search-results" id="site-search-results"><p class="search-empty">Escribí al menos dos caracteres para buscar.</p>'
    '</div></div></dialog>'
)


FOOTER = (
    '<footer class="footer"><div class="wrap"><div class="footer-grid"><div class="footer-about">'
    '<a class="logo" href="/">CEP<b>OES</b></a><p>Datos, investigación y propuestas para CABA, desde los barrios.</p>'
    '<strong class="footer-100">SOMOS 100 BARRIOS</strong></div><div class="footer-links"><h5>Explorar</h5><ul>'
    '<li><a href="/observatorio/">Observatorio</a></li><li><a href="/presupuesto/">Presupuesto</a></li>'
    '<li><a href="/territorio/">Territorio</a></li><li><a href="/territorio/equipamientos/">Qué hay en tu barrio</a></li>'
    '<li><a href="/legislatura/">Legislatura</a></li><li><a href="/publicaciones/">Publicaciones</a></li>'
    '<li><a href="/propuestas/">Propuestas</a></li><li><a href="/prensa/">Prensa</a></li>'
    '<li><a href="/temas/">Explorar por tema</a></li></ul></div>'
    '<div class="footer-links"><h5>CEPOES</h5><ul><li><a href="/cepoes/">Quiénes somos</a></li>'
    '<li><a href="/cepoes/metodologia/">Metodología y fuentes</a></li>'
    '<li><a href="mailto:contacto@cepoes.org">contacto@cepoes.org</a></li>'
    '<li><a href="https://somos100barrios.com.ar/" rel="noopener" target="_blank">Somos 100 Barrios ↗</a></li>'
    '</ul></div></div><div class="footer-copy"><span>© 2026 CEPOES · Somos 100 Barrios</span>'
    '<span>Datos: IDECBA · INDEC · BA Data · Legislatura CABA · Elaboración propia</span></div></div></footer>'
)


def active_link(rel: str, href: str) -> str:
    path = "/" + rel.lstrip("/").removesuffix("index.html")
    active = path == href or ("#" not in href and href != "/territorio/" and path.startswith(href))
    return ' class="active"' if active else ""


def territory_subnav(rel: str) -> str:
    explore = [
        ("/territorio/#comunas", "Comunas"),
        ("/territorio/barrios/", "Barrios"),
        ("/territorio/equipamientos/", "Qué hay en tu barrio"),
        ("/territorio/mapa-tematico/", "Mapa temático"),
        ("/territorio/comparar/", "Comparar"),
        ("/territorio/brechas/", "Brechas"),
    ]
    thematic = [
        ("/territorio/endeudamiento/", "Endeudamiento"),
        ("/territorio/migraciones/", "Migraciones"),
        ("/territorio/estructura-productiva/", "Estructura productiva"),
        ("/territorio/deporte-salud/", "Deporte y salud"),
        ("/presupuesto/territorio/", "Presupuesto"),
    ]
    def links(items: list[tuple[str, str]]) -> str:
        return "".join(f'<a{active_link(rel, href)} href="{href}">{label}</a>' for href, label in items)
    return (
        '<nav aria-label="Navegación territorial" class="subnav territory-subnav"><div class="wrap territory-nav">'
        '<div class="territory-desktop">'
        f'<div class="territory-primary">{links(explore)}</div>'
        '<details class="territory-topics"><summary>Temas territoriales <span aria-hidden="true">⌄</span></summary>'
        f'<div class="territory-topics-menu">{links(thematic)}</div></details></div>'
        '<details class="territory-mobile"><summary><span>Explorar Territorio</span><span aria-hidden="true">⌄</span></summary>'
        '<div class="territory-mobile-menu"><strong>Explorar</strong>'
        f'<div>{links(explore)}</div><strong>Temas territoriales</strong><div>{links(thematic)}</div></div></details>'
        '</div></nav>'
    )


def budget_subnav(rel: str) -> str:
    items = [
        ("/presupuesto/", "Panorama"),
        ("/presupuesto/ejecucion/", "Ejecución y estructura"),
        ("/presupuesto/territorio/", "Territorio"),
        ("/presupuesto/diagnostico/", "Diagnóstico"),
    ]
    links = "".join(f'<a{active_link(rel, href)} href="{href}">{label}</a>' for href, label in items)
    return f'<nav aria-label="Navegación de Presupuesto" class="subnav"><div class="wrap subnav-in">{links}</div></nav>'


def editorial_subnav(active: str) -> str:
    items = [
        ("publicaciones", "/publicaciones/", "Publicaciones"),
        ("boletines", "/publicaciones/boletines/", "Boletines"),
        ("informes", "/publicaciones/informes/", "Informes"),
        ("prensa", "/prensa/", "Notas de prensa"),
        ("temas", "/temas/", "Temas"),
    ]
    links = "".join(f'<a{(" class=\"active\"" if key == active else "")} href="{href}">{label}</a>' for key, href, label in items)
    return f'<nav aria-label="Producción editorial" class="subnav"><div class="wrap subnav-in">{links}</div></nav>'


def topic_chips() -> str:
    return "".join(f'<a href="/temas/#{slug}">{label}</a>' for slug, label in TOPICS)


def prepare_canonical_routes(site: Path) -> None:
    copies = [
        (site / "observatorio" / "presupuesto", site / "presupuesto" / "ejecucion"),
        (site / "territorio" / "presupuesto", site / "presupuesto" / "territorio"),
    ]
    for source, target in copies:
        if not source.is_dir():
            raise SystemExit(f"No se encontró la ruta que debe conservarse: {source}")
        shutil.copytree(source, target, dirs_exist_ok=True)

    htaccess = site / ".htaccess"
    current = htaccess.read_text(encoding="utf-8") if htaccess.exists() else ""
    start, end = "# BEGIN CEPOES IA", "# END CEPOES IA"
    block = (
        f"{start}\n"
        "Redirect 301 /observatorio/presupuesto/ /presupuesto/ejecucion/\n"
        "Redirect 301 /territorio/presupuesto/ /presupuesto/territorio/\n"
        f"{end}"
    )
    current = re.sub(rf"{re.escape(start)}.*?{re.escape(end)}", block, current, flags=re.S)
    if start not in current:
        current = block + "\n\n" + current.lstrip()
    htaccess.write_text(current.rstrip() + "\n", encoding="utf-8")
    replacements = {
        "https://cepoes.org/observatorio/presupuesto/": "https://cepoes.org/presupuesto/ejecucion/",
        "https://cepoes.org/territorio/presupuesto/": "https://cepoes.org/presupuesto/territorio/",
    }
    for name in ("sitemap.xml", "sitemap.txt"):
        sitemap = site / name
        if not sitemap.exists():
            continue
        source = sitemap.read_text(encoding="utf-8")
        for old, new in replacements.items():
            source = source.replace(old, new)
        sitemap.write_text(source, encoding="utf-8")


def inject_editorial_bridge(source: str) -> str:
    if 'id="archivo-por-tema"' in source:
        return source
    block = (
        '<section class="section ia-editorial-bridge" id="archivo-por-tema"><div class="wrap">'
        '<div class="ia-editorial-head"><div><span class="eyebrow">Archivo transversal</span>'
        '<h2>Publicaciones y notas, conectadas por tema</h2><p>Los boletines e informes conservan su formato. Las notas breves para medios viven en Prensa y se integran al mismo archivo temático.</p></div>'
        '<a class="btn btn-outline" href="/prensa/">Ver notas de prensa →</a></div>'
        f'<div class="ia-theme-chips" aria-label="Explorar publicaciones por tema">{topic_chips()}</div>'
        '</div></section>'
    )
    marker = '<section class="section alt editorial-territory">'
    return source.replace(marker, block + marker, 1) if marker in source else source.replace("</main>", block + "</main>", 1)


def fmt_period(value: str) -> str:
    months = {"01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril", "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto", "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"}
    short_months = {"Ene": "Enero", "Feb": "Febrero", "Mar": "Marzo", "Abr": "Abril", "May": "Mayo", "Jun": "Junio", "Jul": "Julio", "Ago": "Agosto", "Sep": "Septiembre", "Oct": "Octubre", "Nov": "Noviembre", "Dic": "Diciembre"}
    if m := re.fullmatch(r"([A-Za-zÁÉÍÓÚáéíóú]{3})-(\d{2})", str(value)):
        if m.group(1) in short_months:
            return f"{short_months[m.group(1)]} 20{m.group(2)}"
    if m := re.fullmatch(r"(\d{4})-T([1-4])", str(value)):
        ordinal = {"1": "1.er", "2": "2.º", "3": "3.er", "4": "4.º"}[m.group(2)]
        return f"{ordinal} trimestre {m.group(1)}"
    if m := re.fullmatch(r"(\d{4})-(\d{2})", str(value)):
        return f"{months[m.group(2)]} {m.group(1)}"
    return str(value)


def fmt_number(value: float, digits: int = 1) -> str:
    raw = f"{value:,.{digits}f}"
    return raw.replace(",", "X").replace(".", ",").replace("X", ".")


def compact(value: float, money: bool = False) -> str:
    prefix = "$ " if money else ""
    value = float(value)
    if abs(value) >= 1_000_000_000_000:
        return f"{prefix}{fmt_number(value / 1_000_000_000_000, 2)} billones"
    if abs(value) >= 1_000_000:
        return f"{prefix}{fmt_number(value / 1_000_000, 2)} M"
    if abs(value) >= 1_000:
        return f"{prefix}{fmt_number(value / 1_000, 1)} mil"
    return f"{prefix}{fmt_number(value, 0)}"


def fmt_int(value: float) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def replace_id_text(source: str, element_id: str, value: str) -> str:
    pattern = rf'(<(?P<tag>[a-zA-Z0-9]+)\b[^>]*\bid=["\']{re.escape(element_id)}["\'][^>]*>)(.*?)(</(?P=tag)>)'
    return re.sub(pattern, lambda m: m.group(1) + html.escape(str(value)) + m.group(4), source, count=1, flags=re.S)


def replace_id_html(source: str, element_id: str, value: str) -> str:
    opening = re.search(
        rf'<(?P<tag>[a-zA-Z0-9]+)\b[^>]*\bid=["\']{re.escape(element_id)}["\'][^>]*>',
        source,
        flags=re.S,
    )
    if not opening:
        return source

    # The target containers frequently contain nested divs. A non-greedy regex
    # stops at the first child closing tag and leaves stale fragments behind on
    # every deploy. Walk tags of the same name so the whole element is replaced.
    tag = opening.group("tag")
    token = re.compile(rf'</?{re.escape(tag)}\b[^>]*>', flags=re.I | re.S)
    depth = 1
    for match in token.finditer(source, opening.end()):
        if match.group(0).startswith("</"):
            depth -= 1
        elif not match.group(0).rstrip().endswith("/>"):
            depth += 1
        if depth == 0:
            return source[:opening.end()] + value + source[match.start():]
    return source


def element_span(source: str, opening: re.Match) -> tuple[int, int] | None:
    """Return the complete span of an element, including nested equal tags."""
    tag = opening.group("tag")
    token = re.compile(rf'</?{re.escape(tag)}\b[^>]*>', flags=re.I | re.S)
    depth = 1
    for match in token.finditer(source, opening.end()):
        if match.group(0).startswith("</"):
            depth -= 1
        elif not match.group(0).rstrip().endswith("/>"):
            depth += 1
        if depth == 0:
            return opening.start(), match.end()
    return None


def replace_class_element(source: str, tag: str, class_name: str, value: str) -> str:
    opening = re.search(
        rf'<(?P<tag>{re.escape(tag)})\b(?=[^>]*\bclass=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'])[^>]*>',
        source,
        flags=re.I | re.S,
    )
    if not opening or not (span := element_span(source, opening)):
        return source
    return source[:span[0]] + value + source[span[1]:]


def pop_class_element(source: str, tag: str, class_name: str) -> tuple[str, str]:
    opening = re.search(
        rf'<(?P<tag>{re.escape(tag)})\b(?=[^>]*\bclass=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'])[^>]*>',
        source,
        flags=re.I | re.S,
    )
    if not opening or not (span := element_span(source, opening)):
        return source, ""
    return source[:span[0]] + source[span[1]:], source[span[0]:span[1]]


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def comparison_card(label: str, value: str, period: str, change: float, comparison: str, color: str) -> str:
    if abs(change) < .05:
        direction, icon, verb = "flat", "→", "Sin cambios"
    elif change > 0:
        direction, icon, verb = "up", "↑", "Subió"
    else:
        direction, icon, verb = "down", "↓", "Bajó"
    delta = fmt_number(abs(change))
    return (
        f'<article class="home-comparison-card" style="--kpi-color:{color}">'
        f'<span class="home-comparison-label">{html.escape(label)}</span>'
        f'<strong>{html.escape(value)}</strong><span class="home-comparison-period">{html.escape(period)}</span>'
        f'<p class="home-comparison-change is-{direction}"><b>{icon} {verb} {delta} p.p.</b> {html.escape(comparison)}</p>'
        '</article>'
    )


def restructure_home(source: str) -> str:
    """Build the six-block editorial home from data and editable content."""
    data = load_json("datos.json")
    editorial = load_json("deploy/site-overlay/assets/data/home-editorial.json")
    ipc, employment, pgb, poverty = data["ipcba"], data["empleo"], data["pgb"], data["pobreza"]

    hero = (
        '<header class="hero home-hero home-editorial-hero"><div class="wrap home-editorial-grid"><div>'
        f'<span class="eyebrow">{html.escape(editorial["eyebrow"])}</span>'
        f'<h1>{html.escape(editorial["title"])}</h1><p>{html.escape(editorial["summary"])}</p>'
        f'<a class="btn btn-primary" href="{html.escape(editorial["url"])}">{html.escape(editorial["cta"])} →</a>'
        '</div><aside class="home-editorial-datum" aria-label="Dato central">'
        f'<strong>{html.escape(editorial["datum"]["value"])}</strong><p>{html.escape(editorial["datum"]["label"])}</p>'
        f'<small>{html.escape(editorial["datum"]["source"])}</small></aside></div></header>'
    )
    source = replace_class_element(source, "header", "home-hero", hero)

    kpis = "".join([
        comparison_card("Inflación · IPCBA", f'+{fmt_number(ipc["var_m"][-1])}%', fmt_period(ipc["meses"][-1]), ipc["var_m"][-1]-ipc["var_m"][-2], f'frente al mes anterior · {fmt_number(ipc["var_ia"][-1])}% interanual', "var(--lH)"),
        comparison_card("Desocupación", f'{fmt_number(employment["desocupacion"][-1])}%', fmt_period(employment["trimestres"][-1]), employment["desocupacion"][-1]-employment["desocupacion"][-2], f'frente al trimestre anterior · {fmt_number(employment["desocupacion"][-1]-employment["desocupacion"][-5])} p.p. interanual', "var(--lB)"),
        comparison_card("Actividad · PGB", f'+{fmt_number(pgb["total"][-1])}% i.a.', fmt_period(pgb["trimestres"][-1]), pgb["total"][-1]-pgb["total"][-2], 'frente a la variación interanual del trimestre anterior', "var(--lA)"),
        comparison_card("Pobreza", f'{fmt_number(poverty["pob_per_pct"][-1])}%', fmt_period(poverty["periodos"][-1]), poverty["pob_per_pct"][-1]-poverty["pob_per_pct"][-5], 'frente al mismo trimestre del año anterior', "var(--lE)"),
    ])
    kpi_section = (
        '<section class="section alt home-kpi-section"><div class="wrap"><div class="section-head"><div>'
        '<span class="eyebrow">Cuatro datos para situarse</span><h2>La comparación le da sentido al número</h2>'
        '</div></div><div class="home-comparison-grid">' + kpis + '</div>'
        '<p class="source home-comparison-source">Fuentes: IDECBA · INDEC · Elaboración CEPOES. Cada tarjeta conserva el período de referencia.</p>'
        '</div></section>'
    )

    barrio_names = sorted({("La Paternal" if name == "Paternal" else name) for c in data["censo"]["comunas"].values() for name in c.get("barrios", {})}, key=str.casefold)
    barrio_options = "".join(f'<option value="{slugify(name)}">{html.escape(name)}</option>' for name in barrio_names)
    offer_section = (
        '<section class="section home-offer-section"><div class="wrap home-neighborhood-band"><div>'
        '<span class="eyebrow">El dato baja al territorio</span><h2>Buscá tu barrio</h2>'
        '<p>Entrá directamente a su ficha para ver población, servicios, brechas y contexto comunal.</p></div>'
        '<form class="home-neighborhood-form" id="home-neighborhood-form">'
        '<label for="home-neighborhood">Elegí uno de los 48 barrios</label><div>'
        '<select id="home-neighborhood" required><option value="">Seleccionar barrio…</option>' + barrio_options + '</select>'
        '<button class="btn btn-primary" type="submit">Ver ficha →</button></div></form></div></section>'
    )

    sections: dict[str, str] = {}
    order = [
        "home-kpi-section",
        "home-offer-section",
        "home-latest-section",
        "home-products-section",
        "home-about-section",
    ]
    for class_name in order:
        source, sections[class_name] = pop_class_element(source, "section", class_name)
    for redundant in ("home-territory-section", "home-topics-section", "home-recent-section"):
        source, _ = pop_class_element(source, "section", redundant)
    source, _ = pop_class_element(source, "section", "home-pulse-section")
    sections["home-kpi-section"] = kpi_section
    sections["home-offer-section"] = offer_section
    latest = sections.get("home-latest-section", "")
    if latest:
        # La normalización parte de la copia publicada. Debe ser idempotente:
        # retirar formularios previos antes de insertar la única suscripción.
        while 'home-subscription' in latest:
            cleaned, removed = pop_class_element(latest, "div", "home-subscription")
            if not removed:
                break
            latest = cleaned
        latest = latest.replace("Ver síntesis →", "Leer la versión web →")
        latest = re.sub(r'<a class="btn btn-outline"[^>]*>Leer online</a>', '', latest)
        subscription = (
            '<div class="home-subscription"><span class="eyebrow">Recibir novedades</span><h3>El boletín, en tu correo</h3>'
            '<form id="home-subscription-form"><label for="home-subscription-email">Correo electrónico</label>'
            '<div><input autocomplete="email" id="home-subscription-email" name="email" placeholder="tu@email.com" required type="email">'
            '<button class="btn btn-primary" type="submit">Suscribirme</button></div>'
            '<label class="home-consent"><input name="consent" required type="checkbox"> Acepto recibir publicaciones de CEPOES. Puedo pedir la baja o el borrado de mis datos escribiendo a contacto@cepoes.org.</label>'
            '<input aria-hidden="true" class="home-honeypot" name="company" tabindex="-1" type="text">'
            '<p aria-live="polite" class="home-subscription-status" id="home-subscription-status"></p></form></div>'
        )
        latest = latest.replace('</div></div></div></section>', '</div>' + subscription + '</div></div></section>', 1)
        sections["home-latest-section"] = latest
    block = "".join(sections[name] for name in order if sections[name])
    footer_at = source.find('<dialog', source.find('</header>'))
    if footer_at < 0:
        footer_at = source.find('<footer')
    result = source[:footer_at] + block + source[footer_at:] if footer_at >= 0 else source + block
    if '/assets/home-redesign.js?v=1' not in result:
        result = result.replace('</body>', '<script defer src="/assets/home-redesign.js?v=1"></script></body>', 1)
    return result


def apply_fallbacks(source: str, rel: str) -> str:
    budget = load_json("presupuesto.json")
    diagnostic = load_json("diagnostico_presupuestario.json")
    debt_manifest = load_json("datos/endeudamiento/manifest.json")
    debt_period = debt_manifest["ultimo_periodo"]
    debt_file = debt_manifest.get("archivos", {}).get(debt_period, f"{debt_period}.json")
    debt = load_json(f"datos/endeudamiento/{debt_file}")["caba"]["total"]
    leg = load_json("legislatura_publica.json")

    values = {
        "home-budget-period": fmt_period(budget["periodo"]),
        "home-budget-exec": f'{fmt_number(budget["total"]["ejecucion_pct"])}%',
        "home-budget-vig": compact(budget["total"]["vigente"], money=True),
        "home-budget-dev": compact(budget["total"]["devengado"], money=True),
        "home-budget-mod": compact(budget["total"]["modificaciones"], money=True),
        "home-debt-period": f"{fmt_period(debt_period)} · 48 barrios",
        "home-debt-debtors": compact(debt["deudores"]),
        "home-debt-mora": compact(debt["personas_mora"]),
        "home-debt-total": compact(debt["deuda_total_pesos"], money=True),
        "budget-hub-period": fmt_period(budget["periodo"]),
    }
    data = load_json("datos.json")
    values.update({
        "home-pgb": f'+{fmt_number(data["pgb"]["ultimo_var"])}% i.a.',
        "home-des": f'{fmt_number(data["empleo"]["desocupacion"][-1])}% desocupación',
        "home-ipc": f'+{fmt_number(data["ipcba"]["var_m"][-1])}% mensual',
        "home-pob": f'{fmt_number(data["pobreza"]["pob_per_pct"][-1])}% pobreza',
        "home-ejec": f'{fmt_number(data["presupuesto"]["kpi"]["ejec_pct"])}% ejecución',
    })
    generated = datetime.fromisoformat(leg["generado"])
    since = generated - timedelta(days=7)
    recent = sum(datetime.fromisoformat(x["fecha_ingreso"]) >= since.replace(tzinfo=None) for x in leg.get("radar_ingresos", {}).get("expedientes", []))
    values["home-leg-recent"] = str(recent)
    values["home-leg-next-count"] = str(leg.get("resumen", {}).get("reuniones_proximas", 0))
    for key, value in values.items():
        source = replace_id_text(source, key, value)

    if rel == "/index.html":
        locales = data["comunas_locales"]["total"]
        vac = 100 - locales["tasa_ocup"]
        ipc = data["ipcba"]
        now, before = ipc["var_m"][-1], ipc["var_m"][-2]
        signals = (
            f'<div class="pulse-card" style="--c:var(--lD)"><div class="top"><span>Comercio urbano</span></div>'
            f'<div class="num">{fmt_number(vac)}% vacancia</div><p>Sobre {fmt_int(locales["relevados"])} locales relevados, '
            f'{fmt_int(locales["relevados"]-locales["ocupados"])} están vacíos, cerrados o en refacción.</p></div>'
            f'<div class="pulse-card" style="--c:var(--lN)"><div class="top"><span>Estado porteño</span></div>'
            f'<div class="num">{fmt_number(data["presupuesto"]["kpi"]["ejec_pct"])}% ejecución</div>'
            '<p>El último ejercicio disponible conserva fecha, fuente y nivel de ejecución sobre el crédito vigente.</p></div>'
            f'<div class="pulse-card" style="--c:var(--lH)"><div class="top"><span>Inflación</span></div>'
            f'<div class="num">+{fmt_number(now)}% mensual</div><p>La inflación {"se aceleró" if now > before else "desaceleró"} '
            f'{fmt_number(abs(now-before))} puntos frente al mes previo; la variación interanual fue {fmt_number(ipc["var_ia"][-1])}%.</p></div>'
        )
        pulse_section = (
            '<section class="section home-pulse-section"><div class="wrap">'
            '<div class="section-head"><div><span class="eyebrow">Lectura CEPOES</span>'
            '<h2>Tres señales de coyuntura</h2></div></div>'
            f'<div class="pulse-grid home-pulse" id="home-pulse">{signals}</div>'
            '</div></section>'
        )
        # Replace the entire section to remove malformed fragments left by the
        # old nested-div replacement, not only the first inner container.
        source = replace_class_element(source, "section", "home-pulse-section", pulse_section)

    if rel == "/observatorio/index.html":
        ipc = data["ipcba"]
        employment = data["empleo"]
        pgb = data["pgb"]
        poverty = data["pobreza"]
        locales = data["comunas_locales"]["total"]
        vacancy = 100 - locales["tasa_ocup"]
        kpis = (
            f'<a class="kpi kpi-link" href="/observatorio/precios/ipc/" style="--c:var(--lB)"><div class="label">IPCBA · interanual</div><div class="value">+{fmt_number(ipc["var_ia"][-1])}%</div><div class="small">{fmt_period(ipc["meses"][-1])}</div><span class="kpi-go">Ver serie →</span></a>'
            f'<a class="kpi kpi-link" href="/observatorio/precios/ipc/" style="--c:var(--lH)"><div class="label">IPCBA · mensual</div><div class="value">+{fmt_number(ipc["var_m"][-1])}%</div><div class="small">{fmt_period(ipc["meses"][-1])}</div><span class="kpi-go">Ver serie →</span></a>'
            f'<a class="kpi kpi-link" href="/observatorio/produccion/pgb/" style="--c:var(--lA)"><div class="label">Actividad · PGB</div><div class="value">+{fmt_number(pgb["ultimo_var"])}%</div><div class="small">{fmt_period(pgb["ultimo_trim"])}</div><span class="kpi-go">Ver serie →</span></a>'
            f'<a class="kpi kpi-link" href="/observatorio/produccion/locales-vacantes/" style="--c:var(--lN)"><div class="label">Locales vacantes</div><div class="value">{fmt_number(vacancy)}%</div><div class="small">1.er relevamiento 2026</div><span class="kpi-go">Ver serie →</span></a>'
            f'<a class="kpi kpi-link" href="/observatorio/trabajo/empleo/" style="--c:var(--lD)"><div class="label">Tasa de empleo</div><div class="value">{fmt_number(employment["empleo"][-1])}%</div><div class="small">{fmt_period(employment["trimestres"][-1])}</div><span class="kpi-go">Ver serie →</span></a>'
            f'<a class="kpi kpi-link" href="/observatorio/condiciones-de-vida/pobreza/" style="--c:var(--lE)"><div class="label">Pobreza</div><div class="value">{fmt_number(poverty["pob_per_pct"][-1])}%</div><div class="small">{fmt_period(poverty["periodos"][-1])}</div><span class="kpi-go">Ver serie →</span></a>'
        )
        signals = (
            f'<div class="pulse-card" style="--c:var(--lH)"><div class="top"><span>Precios</span></div>'
            f'<div class="num">+{fmt_number(ipc["var_m"][-1])}% mensual</div><p>{fmt_period(ipc["meses"][-1])}: '
            f'la variación interanual fue {fmt_number(ipc["var_ia"][-1])}%.</p></div>'
            f'<div class="pulse-card" style="--c:var(--lB)"><div class="top"><span>Trabajo</span></div>'
            f'<div class="num">{fmt_number(employment["desocupacion"][-1])}% desocupación</div><p>Último dato disponible: '
            f'{fmt_period(employment["trimestres"][-1])}.</p></div>'
            f'<div class="pulse-card" style="--c:var(--lA)"><div class="top"><span>Actividad</span></div>'
            f'<div class="num">+{fmt_number(pgb["ultimo_var"])}% interanual</div><p>Producto Geográfico Bruto de CABA, '
            f'{fmt_period(pgb["ultimo_trim"])}.</p></div>'
        )
        overview = (
            '<section class="section alt observatory-overview"><div class="wrap">'
            '<div class="section-head"><div><span class="eyebrow">Panorama</span><h2>La Ciudad hoy</h2></div></div>'
            f'<div class="kpis observatory-kpis">{kpis}</div>'
            '<div class="section-head observatory-signals-head"><div><span class="eyebrow">Lectura rápida</span><h2>Tres señales</h2></div></div>'
            f'<div class="pulse-grid observatory-pulse" id="obs-pulse">{signals}</div>'
            '</div></section>'
        )
        source = re.sub(r'<section class="section alt">.*?</section>', overview, source, count=1, flags=re.S)
        people_bridge = (
            '<section class="section observatory-people-bridge"><div class="wrap">'
            '<a class="ia-topic-card" href="/observatorio/personas-mayores/">'
            '<span class="eyebrow">Eje transversal · Salud y cuidados</span><h2>Personas mayores</h2>'
            '<p>Demografía, costo de vida, vivienda y cuidados: datos públicos con actualización automática y último valor validado.</p>'
            '<span class="ia-topic-link">Explorar el eje →</span></a></div></section>'
        )
        if '/observatorio/personas-mayores/' not in source:
            source = source.replace(overview, overview + people_bridge, 1)
        source = replace_id_text(source, "data-date", "26 de agosto de 2026")

    if rel == "/prensa/index.html":
        press = load_json("deploy/site-overlay/assets/data/prensa.json")
        notes = [note for note in press.get("notas", []) if note.get("estado") == "aprobada"]
        cards = "".join(
            f'<a class="press-card" href="/prensa/{html.escape(note["slug"])}/">'
            f'<div class="press-meta"><span class="press-tag">{html.escape(note["tema"])}</span>'
            f'<span>{html.escape(fmt_period(note["fecha"][:7]))}</span></div>'
            f'<h3>{html.escape(note["titulo"])}</h3><p>{html.escape(note["bajada"])}</p>'
            '<span class="more">Leer nota →</span></a>'
            for note in notes
        )
        source = replace_id_html(source, "press-list", cards or '<p class="press-empty">Todavía no hay notas publicadas.</p>')
        source = replace_id_text(source, "press-total", f'{len(notes)} {"nota" if len(notes) == 1 else "notas"}')

    if rel == "/presupuesto/index.html":
        source = replace_id_text(source, "data-date", "26 de agosto de 2026")
        status = f"Último dato oficial: {fmt_period(budget['periodo'])}"
        source = re.sub(r'(<div class="budget-status" id="budget-hub-status"><span class="status-dot"></span><span>).*?(</span>)', rf'\1{status}\2', source, count=1, flags=re.S)
        cells = [
            (compact(budget["total"]["vigente"], money=True), "Último dato oficial"),
            (compact(budget["total"]["devengado"], money=True), "Gasto reconocido"),
            (f'{fmt_number(budget["total"]["ejecucion_pct"])}%', "Devengado / vigente"),
            (compact(budget["total"]["modificaciones"], money=True), "Vigente − sancionado"),
        ]
        cell_index = 0
        def fill_cell(match: re.Match) -> str:
            nonlocal cell_index
            if cell_index >= len(cells):
                return match.group(0)
            value, label = cells[cell_index]
            cell_index += 1
            return match.group(1) + value + match.group(2) + label + match.group(3)
        source = re.sub(r'(<div class="mini-stat"><span>[^<]+</span><b>).*?(</b><small>).*?(</small></div>)', fill_cell, source, flags=re.S)
        inc = diagnostic["modificaciones"]["funciones_mayores_ampliaciones"][0]
        exe = diagnostic["ejecucion_relativa"][0]
        terr = diagnostic["territorio"][0]
        cards = (
            f'<a class="budget-signal-card" href="/presupuesto/diagnostico/#modificaciones"><span class="eyebrow">Crédito</span><h3>Mayor ampliación funcional</h3><strong>{html.escape(inc["nombre"])}</strong><p>{compact(inc["modificacion"], money=True)} respecto del sancionado.</p><span class="more">Ver detalle →</span></a>'
            f'<a class="budget-signal-card" href="/presupuesto/diagnostico/#ejecucion"><span class="eyebrow">Ejecución</span><h3>Mayor distancia a la mediana</h3><strong>{html.escape(exe["nombre"])}</strong><p>{fmt_number(exe["ejecucion_pct"])}% de ejecución; {fmt_number(abs(exe["diferencia_mediana_pp"]))} p.p. de diferencia.</p><span class="more">Ver detalle →</span></a>'
            f'<a class="budget-signal-card" href="/presupuesto/diagnostico/#territorio"><span class="eyebrow">Territorio</span><h3>Prioridad de lectura territorial</h3><strong>{html.escape(terr["nombre"])}</strong><p>{terr["dimensiones_debajo_caba"]} de 10 dimensiones debajo de CABA.</p><span class="more">Ver detalle →</span></a>'
        )
        source = re.sub(r'(<div class="budget-hub-signals" id="budget-hub-signals">).*?(</div></div></div></section>)', lambda m: m.group(1) + cards + m.group(2), source, count=1, flags=re.S)
    return source


def normalize_html(path: Path, site: Path) -> None:
    rel = "/" + path.relative_to(site).as_posix()
    if rel.startswith("/privado/"):
        return
    source = path.read_text(encoding="utf-8")
    source = source.replace('href="/observatorio/presupuesto/"', 'href="/presupuesto/ejecucion/"')
    source = source.replace('href="/territorio/presupuesto/"', 'href="/presupuesto/territorio/"')
    source = re.sub(r'/assets/endeudamiento\.js(?:\?v=\d+)?', '/assets/endeudamiento.js?v=232', source)
    source = re.sub(r'<link\b[^>]*href=["\']/assets/arquitectura\.css(?:\?[^"\']*)?["\'][^>]*>', '', source, flags=re.I)
    source = source.replace("</head>", f'<link href="{ARCHITECTURE_CSS}" rel="stylesheet"></head>', 1)
    if '/assets/favicon.svg' not in source:
        source = source.replace("</head>", '<link href="/assets/favicon.svg" rel="icon" type="image/svg+xml"></head>', 1)
    source = re.sub(r'<meta\s+(?:content=["\'][^"\']+["\']\s+name=["\']theme-color["\']|name=["\']theme-color["\']\s+content=["\'][^"\']+["\'])\s*/?>', "", source, flags=re.I)
    viewport = re.search(r'<meta\b[^>]*name=["\']viewport["\'][^>]*>', source, flags=re.I)
    if viewport:
        source = source[: viewport.end()] + f'<meta name="theme-color" content="{THEME_COLOR}">' + source[viewport.end():]
    canonical_nav = nav(active_for(path, site))
    source, nav_count = re.subn(r'<nav class="site-nav">.*?</nav>', canonical_nav, source, count=1, flags=re.S)
    if not nav_count and "<body" in source:
        source = re.sub(r'(<body\b[^>]*>)', r'\1' + canonical_nav, source, count=1, flags=re.I)

    contextual = None
    if rel.startswith("/territorio/"):
        contextual = territory_subnav(rel)
    elif rel.startswith("/presupuesto/"):
        contextual = budget_subnav(rel)
    elif rel.startswith("/publicaciones/"):
        active = "boletines" if rel.startswith("/publicaciones/boletines/") else "informes" if rel.startswith("/publicaciones/informes/") or "informe-" in rel else "publicaciones"
        contextual = editorial_subnav(active)
    elif rel.startswith("/prensa/"):
        contextual = editorial_subnav("prensa")
    elif rel == "/temas/index.html":
        contextual = editorial_subnav("temas")
    if contextual:
        source, subnav_count = re.subn(r'<nav\b[^>]*class=["\'][^"\']*\bsubnav\b[^"\']*["\'][^>]*>.*?</nav>', contextual, source, count=1, flags=re.S | re.I)
        if not subnav_count:
            source = source.replace(canonical_nav, canonical_nav + contextual, 1)
    source, footer_count = re.subn(r'<footer class="footer">.*?</footer>', FOOTER, source, count=1, flags=re.S)
    if not footer_count and "</body>" in source:
        source = source.replace("</body>", FOOTER + "</body>", 1)
    source = re.sub(r'<dialog\b[^>]*id=["\']site-search["\'][^>]*>.*?</dialog>', SEARCH, source, count=1, flags=re.S)
    if 'id="site-search"' not in source:
        source = source.replace('<footer class="footer">', SEARCH + '<footer class="footer">', 1)
    source = re.sub(r'(<a\b[^>]*href=["\']/territorio/equipamientos/(?:\?[^"\']*)?["\'][^>]*>)(?:Información territorial|Oferta territorial)(\s*→)?(</a>)', lambda m: m.group(1) + "Qué hay en tu barrio" + (m.group(2) or "") + m.group(3), source, flags=re.I)
    if rel == "/publicaciones/index.html":
        source = inject_editorial_bridge(source)
        source = re.sub(r'(<a\b[^>]*href=["\']/publicaciones/boletines/boletin-04-agosto-2026/["\'][^>]*>)Ver síntesis →(</a>)', r'\1Leer boletín web →\2', source, count=1)
        source = re.sub(r'(<a\b[^>]*href=["\']/publicaciones/informe-coyuntura-01-junio-2026/["\'][^>]*>)Ver síntesis →(</a>)', r'\1Leer informe web →\2', source, count=1)
        source = re.sub(r'<a\b[^>]*data-pdf-viewer=["\'][^"\']+["\'][^>]*>Leer online</a>', '', source, flags=re.S)
    canonical_routes = {
        "/presupuesto/ejecucion/index.html": "https://cepoes.org/presupuesto/ejecucion/",
        "/presupuesto/territorio/index.html": "https://cepoes.org/presupuesto/territorio/",
    }
    if rel in canonical_routes:
        target = canonical_routes[rel]
        source = re.sub(
            r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*>',
            lambda m: re.sub(r'\bhref=["\'][^"\']+["\']', f'href="{target}"', m.group(0), count=1),
            source,
            count=1,
            flags=re.I,
        )
        source = re.sub(
            r'<meta\b(?=[^>]*\bproperty=["\']og:url["\'])[^>]*>',
            lambda m: re.sub(r'\bcontent=["\'][^"\']+["\']', f'content="{target}"', m.group(0), count=1),
            source,
            count=1,
            flags=re.I,
        )
    source = apply_fallbacks(source, rel)
    if rel == "/index.html":
        source = restructure_home(source)
    path.write_text(source, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not (site / "index.html").is_file():
        raise SystemExit(f"No se encontró el sitio en {site}")
    prepare_canonical_routes(site)
    count = 0
    for path in site.rglob("*.html"):
        normalize_html(path, site)
        count += 1
    print(f"Capa pública normalizada: {count} páginas HTML")


if __name__ == "__main__":
    main()
