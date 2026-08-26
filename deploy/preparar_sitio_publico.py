#!/usr/bin/env python3
"""Normaliza la capa publica y deja contenido util sin depender de JavaScript."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEME_COLOR = "#16232F"
ARCHITECTURE_CSS = "/assets/arquitectura.css?v=3"


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
        f'<div class="territory-primary">{links(explore)}</div>'
        '<details class="territory-topics"><summary>Temas territoriales <span aria-hidden="true">⌄</span></summary>'
        f'<div class="territory-topics-menu">{links(thematic)}</div></details>'
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
        source = replace_id_html(source, "home-pulse", signals)

    if rel == "/observatorio/index.html":
        ipc = data["ipcba"]
        employment = data["empleo"]
        pgb = data["pgb"]
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
        source = replace_id_html(source, "obs-pulse", signals)

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
    if ARCHITECTURE_CSS not in source:
        source = source.replace("</head>", f'<link href="{ARCHITECTURE_CSS}" rel="stylesheet"></head>', 1)
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
