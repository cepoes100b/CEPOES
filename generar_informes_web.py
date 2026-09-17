#!/usr/bin/env python3
from __future__ import annotations

from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "deploy" / "site-overlay"


REPORTS = [
    {
        "slug": "publicaciones/informes/personas-mayores-caba",
        "kind": "Informe temático · Septiembre de 2026",
        "title": "Personas mayores en Buenos Aires",
        "full_title": "Las personas mayores en la Ciudad Autónoma de Buenos Aires: una problemática que debería ser reevaluada",
        "deck": "Envejecimiento, ingresos, vivienda, salud y cuidados en una Ciudad donde la longevidad también expresa desigualdades territoriales.",
        "pdf": "/publicaciones/informes/personas-mayores-caba/informe-personas-mayores-caba-cepoes.pdf",
        "related": ("Explorar datos de personas mayores", "/observatorio/personas-mayores/"),
        "accent": "#55b9e9",
        "stats": [("22,2%", "de la población tiene 60 años o más"), ("60,7%", "de las personas mayores son mujeres"), ("27,6%", "en la Comuna 2: máximo de la Ciudad"), ("15,0%", "en la Comuna 8: mínimo de la Ciudad")],
        "chart_title": "Una vejez territorialmente desigual",
        "chart_note": "Proporción de personas de 60 años o más por comunas seleccionadas.",
        "bars": [("Comuna 2", 27.6), ("Comuna 14", 26.1), ("Comuna 13", 25.6), ("Comuna 4", 17.8), ("Comuna 8", 15.0)],
        "insights": [
            ("La Ciudad envejece rápido", "La baja fecundidad y la mayor longevidad modifican la estructura demográfica y elevan la demanda de cuidados, salud y accesibilidad urbana."),
            ("El ingreso no alcanza", "En septiembre de 2026 la jubilación mínima con bono llega a $498.633. La brecha con las canastas de las personas mayores obliga a priorizar medicamentos, alimentos o vivienda."),
            ("Vivir más no significa vivir igual", "El norte concentra las mayores proporciones de personas mayores; el sur combina una estructura más joven con peores condiciones socioambientales y menor longevidad."),
        ],
        "actions": ["Ampliar cuidados domiciliarios y políticas de respiro.", "Priorizar infraestructura sociosanitaria en las comunas del sur.", "Fortalecer la atención del deterioro cognitivo en hospitales y CeSAC."],
        "sources": "IDECBA y EAH 2025; Censo 2022; CESBA; Defensorías de la Tercera Edad y del Pueblo de CABA; ANSES; PAMI; GCBA; Asociación Alzheimer Argentina y UBA.",
        "citation": "CEPOES (2026). «Las personas mayores en la Ciudad Autónoma de Buenos Aires: una problemática que debería ser reevaluada». Informe temático, septiembre de 2026. Centro de Estudios Políticos, Económicos y Sociales – Somos 100 Barrios.",
    },
    {
        "slug": "publicaciones/informes/situacion-de-calle-caba",
        "kind": "Informe temático · Septiembre de 2026",
        "title": "Más personas sin techo en Buenos Aires",
        "full_title": "La cara más helada del invierno en Buenos Aires: la población en situación de calle supera las 5.000 personas tras un marcado incremento interanual",
        "deck": "El conteo oficial supera las 5.000 personas y las mediciones sociales duplican esa magnitud. La emergencia exige pasar del refugio temporal a una política habitacional.",
        "pdf": "/publicaciones/informes/situacion-de-calle-caba/informe-situacion-de-calle-caba-cepoes.pdf",
        "related": ("Ver el balance de vivienda", "/balance/vivienda-y-alquiler/"),
        "accent": "#55b9e9",
        "stats": [("5.176", "personas en el registro oficial de 2026"), ("1.613", "permanecen a la intemperie"), ("3.563", "se alojan en centros y refugios"), ("+27,8%", "incremento interanual oficial")],
        "chart_title": "Dos mediciones, una brecha decisiva",
        "chart_note": "Personas relevadas. Las metodologías y coberturas no son equivalentes.",
        "bars": [("Registro oficial", 5176), ("Censo Popular", 11892)],
        "insights": [
            ("La crisis se concentra", "La Comuna 1 reúne el 35% de las personas observadas en la calle; las comunas 3 y 4 le siguen con 15,4% y 8,8%."),
            ("La red contiene, pero no resuelve", "Los centros y refugios absorben la mayor parte de la demanda, mientras la respuesta estructural sigue llegando después de la expulsión habitacional."),
            ("La cifra define la política", "La distancia entre el relevamiento oficial y el Censo Popular condiciona el presupuesto, las plazas necesarias y la dimensión de las soluciones permanentes."),
        ],
        "actions": ["Unificar y transparentar criterios de relevamiento.", "Articular prevención de desalojos, alquiler y acompañamiento social.", "Evaluar la red por egresos habitacionales, no sólo por plazas nocturnas."],
        "sources": "REPSIC e IDECBA; Dirección General Red de Atención del GCBA; Censo Popular de Personas en Situación de Calle de Proyecto 7, CELS, ACIJ y organizaciones sociales.",
        "citation": "CEPOES (2026). «La cara más helada del invierno en Buenos Aires: la población en situación de calle supera las 5.000 personas tras un marcado incremento interanual». Informe temático, septiembre de 2026. Centro de Estudios Políticos, Económicos y Sociales – Somos 100 Barrios.",
    },
    {
        "slug": "publicaciones/informes/endeudarse-para-llegar-a-fin-de-mes",
        "kind": "Informe especial · Septiembre de 2026",
        "title": "Endeudarse para llegar a fin de mes",
        "full_title": "Endeudarse para llegar a fin de mes: radiografía de la deuda de los hogares en CABA",
        "deck": "Más de dos millones de personas registran deudas en la Ciudad y la mora alcanza a más de 313 mil. El crédito funciona cada vez más como extensión del ingreso.",
        "pdf": "/publicaciones/informes/endeudarse-para-llegar-a-fin-de-mes/endeudamiento-caba-cepoes.pdf",
        "related": ("Explorar el mapa de endeudamiento", "/territorio/endeudamiento/"),
        "accent": "#55b9e9",
        "stats": [("2,04 M", "personas con deuda registrada"), ("313.571", "personas en situación de mora"), ("12,37%", "del monto adeudado está en mora"), ("$14,45 B", "monto total de deuda en CABA")],
        "chart_title": "La deuda se vuelve más frágil",
        "chart_note": "Personas deudoras y personas en mora; julio de 2026.",
        "bars": [("Con deuda", 2040000), ("En mora", 313571)],
        "insights": [
            ("El crédito compensa ingresos", "La deuda ya no se explica sólo por consumos durables: aparece como respuesta cotidiana frente a gastos corrientes y costos esenciales."),
            ("La mora tiene geografía", "La estimación barrial muestra diferencias territoriales que conviene leer junto con ingresos, empleo, alquiler y estructura comercial."),
            ("No toda deuda implica lo mismo", "El informe distingue cantidad de personas, monto y situación de mora para evitar que un único promedio oculte perfiles diferentes."),
        ],
        "actions": ["Seguir mensualmente deuda, mora y cambios de situación.", "Vincular la lectura territorial con alquileres e ingresos.", "Publicar supuestos, cobertura y límites de la estimación barrial."],
        "sources": "Central de Deudores del BCRA y padrón ARCA; INDEC; IDECBA. La estimación barrial usa correspondencias CP4 y suprime celdas pequeñas.",
        "citation": "CEPOES (2026). «Endeudarse para llegar a fin de mes: radiografía de la deuda de los hogares en CABA». Informe especial, septiembre de 2026. Centro de Estudios Políticos, Económicos y Sociales – Somos 100 Barrios.",
    },
    {
        "slug": "publicaciones/informe-coyuntura-01-junio-2026",
        "kind": "Informe de coyuntura N.º 1 · Junio de 2026",
        "title": "Producción y empleo: una recuperación desigual",
        "full_title": "Estructura productiva argentina: recuperación parcial, empleo bajo presión y crisis del tejido productivo en CABA",
        "deck": "La mejora de algunos sectores convive con menor capacidad instalada, caída del empleo registrado y destrucción de empresas. En CABA, la retracción se vuelve visible en el comercio y los barrios.",
        "pdf": "/publicaciones/files/informe-coyuntura-01-junio-2026.pdf",
        "related": ("Explorar la estructura productiva", "/territorio/estructura-productiva/"),
        "accent": "#55b9e9",
        "stats": [("59,8%", "uso de la capacidad instalada industrial"), ("−310.930", "puestos registrados desde noviembre de 2023"), ("−23.160", "empleadores a nivel nacional"), ("+30,7%", "locales vacíos en CABA, interanual")],
        "chart_title": "Una recuperación sin recomposición plena",
        "chart_note": "Señales seleccionadas del primer cuatrimestre de 2026.",
        "bars": [("Capacidad utilizada", 59.8), ("Capacidad ociosa", 40.2)],
        "insights": [
            ("El rebote está concentrado", "La mejora se apoya en insumos básicos y ramas exportadoras, sin extenderse de igual modo a cadenas pyme e intensivas en empleo."),
            ("Se reduce el entramado productivo", "La pérdida de empleadores y puestos registrados constituye un daño estructural que una mejora coyuntural de la producción no revierte automáticamente."),
            ("CABA muestra el ajuste en el territorio", "La caída del empleo y la mayor vacancia comercial expresan la retracción del consumo urbano en calles, centros comerciales y barrios."),
        ],
        "actions": ["Sostener demanda, empleo y capital de trabajo pyme.", "Monitorear aperturas, cierres y vacancia por comuna.", "Orientar crédito e inversión hacia cadenas con mayor densidad laboral."],
        "sources": "INDEC; SIPA; SRT; CEPA; IDECBA y Cámara Argentina de Comercio y Servicios. Elaboración CEPOES.",
        "citation": "CEPOES (2026). «Estructura productiva argentina: recuperación parcial, empleo bajo presión y crisis del tejido productivo en CABA». Informe económico de coyuntura N.º 1, junio de 2026. Centro de Estudios Políticos, Económicos y Sociales – Somos 100 Barrios.",
    },
]


def nav() -> str:
    return '''<nav class="site-nav"><div class="wrap nav-in"><a class="brand" href="/"><span class="logo">CEP<b>OES</b></span><span class="brand-sep"></span><span class="brand-sub"><small>Centro de estudios de</small><strong>SOMOS 100 BARRIOS</strong></span></a><div class="nav-links"><a href="/observatorio/">Observatorio</a><a href="/balance/">Balance</a><a href="/presupuesto/">Presupuesto</a><a href="/territorio/">Territorio</a><a href="/legislatura/">Legislatura</a><a class="active" href="/publicaciones/">Publicaciones</a><a href="/propuestas/">Propuestas</a><a href="/prensa/">Prensa</a><a href="/cepoes/">CEPOES</a><a class="nav-cta" href="/territorio/equipamientos/">Qué hay en tu barrio →</a></div><button aria-label="Buscar en CEPOES" class="search-btn" data-search-open>⌕</button><button aria-label="Cambiar tema" class="theme-btn" data-theme-toggle>◐</button><button aria-label="Abrir menú" class="menu-btn" data-menu-toggle>☰</button></div></nav><nav class="subnav" aria-label="Producción editorial"><div class="wrap subnav-in"><a href="/publicaciones/">Publicaciones</a><a href="/publicaciones/boletines/">Boletines</a><a class="active" href="/publicaciones/informes/">Informes</a><a href="/publicaciones/notas/">Notas y análisis</a><a href="/prensa/">Notas de prensa</a><a href="/temas/">Temas</a></div></nav>'''


def footer() -> str:
    return '''<footer class="footer"><div class="wrap footer-grid"><div><a class="footer-brand" href="/"><span class="logo">CEP<b>OES</b></span></a><p>Datos, investigación y propuestas para CABA, desde los barrios.</p><strong>SOMOS 100 BARRIOS</strong></div><div><h5>Explorar</h5><a href="/observatorio/">Observatorio</a><a href="/balance/">Balance</a><a href="/presupuesto/">Presupuesto</a><a href="/territorio/">Territorio</a><a href="/legislatura/">Legislatura</a><a href="/publicaciones/">Publicaciones</a><a href="/propuestas/">Propuestas</a><a href="/prensa/">Prensa</a></div><div><h5>CEPOES</h5><a href="/cepoes/">Quiénes somos</a><a href="/metodologia/">Metodología y fuentes</a><a href="mailto:contacto@cepoes.org">contacto@cepoes.org</a></div></div><div class="wrap footer-copy">© 2026 CEPOES · Somos 100 Barrios</div></footer>'''


def cover(report: dict) -> str:
    title = report["title"]
    words = title.split()
    lines, current = [], []
    for word in words:
        if len(" ".join(current + [word])) > 20 and current:
            lines.append(" ".join(current)); current = [word]
        else:
            current.append(word)
    if current: lines.append(" ".join(current))
    tspans = "".join(f'<tspan x="62" dy="{0 if i == 0 else 68}">{escape(line)}</tspan>' for i, line in enumerate(lines[:4]))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1120" role="img" aria-label="Tapa de {escape(title)}"><rect width="800" height="1120" fill="#172a4a"/><rect x="0" y="0" width="18" height="1120" fill="{report['accent']}"/><circle cx="642" cy="822" r="220" fill="none" stroke="#10213c" stroke-width="58"/><circle cx="642" cy="822" r="135" fill="none" stroke="#10213c" stroke-width="42"/><text x="62" y="88" fill="#fff" font-family="Arial,sans-serif" font-size="24">{escape(report['kind'])}</text><text x="62" y="230" fill="{report['accent']}" font-family="Arial,sans-serif" font-weight="700" font-size="58">{tspans}</text><text x="62" y="1004" fill="{report['accent']}" font-family="Arial,sans-serif" font-weight="700" font-size="29">CEPOES</text><text x="205" y="1004" fill="#fff" font-family="Arial,sans-serif" font-size="19">Somos 100 Barrios · 2026</text></svg>'''


def page(r: dict) -> str:
    max_bar = max(v for _, v in r["bars"])
    stats = "".join(f'<article class="wr-stat"><strong>{escape(value)}</strong><span>{escape(label)}</span></article>' for value, label in r["stats"])
    def fmt_num(value: float) -> str:
        if float(value).is_integer():
            return f"{int(value):,}".replace(",", ".")
        return f"{value:.1f}".replace(".", ",")
    bars = "".join(f'<div class="wr-bar"><span>{escape(label)}</span><i><b style="width:{value/max_bar*100:.1f}%"></b></i><strong>{fmt_num(value)}</strong></div>' for label, value in r["bars"])
    insights = "".join(f'<article><span>0{i}</span><h3>{escape(title)}</h3><p>{escape(text)}</p></article>' for i, (title, text) in enumerate(r["insights"], 1))
    actions = "".join(f'<li>{escape(x)}</li>' for x in r["actions"])
    return f'''<!doctype html><html lang="es-AR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#16232F"><title>{escape(r['title'])} — CEPOES</title><meta name="description" content="{escape(r['deck'])}"><link rel="canonical" href="https://cepoes.org/{r['slug']}/"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"><link href="/assets/site.css?v=233" rel="stylesheet"><link href="/assets/arquitectura.css?v=19" rel="stylesheet"><link href="/assets/informes-web.css?v=2" rel="stylesheet"><script defer src="/assets/common.js?v=256"></script><script defer src="/assets/informes-web.js?v=1"></script></head><body>{nav()}<main class="web-report"><header class="wr-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">CEPOES</a> / <a href="/publicaciones/">Publicaciones</a> / <a href="/publicaciones/informes/">Informes</a></div><span class="wr-eyebrow">{escape(r['kind'])}</span><h1>{escape(r['title'])}</h1><p class="wr-deck">{escape(r['deck'])}</p><p class="wr-author">CEPOES</p><div class="wr-actions"><a class="btn btn-primary" download href="{r['pdf']}">Descargar informe completo ↓</a><a class="btn btn-outline" href="{r['related'][1]}">{escape(r['related'][0])} →</a></div></div></header><section class="wr-stats"><div class="wrap">{stats}</div></section><section class="wr-section"><div class="wrap"><div class="wr-section-head"><span class="wr-eyebrow">Lectura rápida</span><h2>Los datos principales</h2><p>Esta versión web presenta una síntesis visual. El argumento, las tablas, la metodología y las referencias completas están disponibles en el PDF.</p></div><div class="wr-chart"><div><h3>{escape(r['chart_title'])}</h3><p>{escape(r['chart_note'])}</p></div><div class="wr-bars">{bars}</div></div></div></section><section class="wr-section wr-section-alt"><div class="wrap"><div class="wr-section-head"><span class="wr-eyebrow">Qué muestra el informe</span><h2>Tres claves para interpretar el problema</h2></div><div class="wr-insights">{insights}</div></div></section><section class="wr-section"><div class="wrap wr-split"><div><span class="wr-eyebrow">Agenda pública</span><h2>Qué debería cambiar</h2><ul class="wr-actions-list">{actions}</ul></div><aside class="wr-download"><span class="wr-eyebrow">Documento completo</span><h3>{escape(r['full_title'])}</h3><p>Consultá el análisis íntegro, las fuentes y el desarrollo metodológico.</p><a class="btn btn-primary" download href="{r['pdf']}">Descargar informe completo ↓</a></aside></div></section><section class="wr-meta"><div class="wrap wr-meta-grid"><div><span class="wr-meta-label">Datos y fuentes</span><p>{escape(r['sources'])}</p></div><div><span class="wr-meta-label">Cita sugerida</span><p class="wr-citation" data-citation-text>{escape(r['citation'])}</p><button class="btn btn-outline" type="button" data-copy-citation>Copiar cita</button></div></div></section></main>{footer()}</body></html>'''


def main() -> None:
    cover_names = {
        "publicaciones/informes/personas-mayores-caba": "personas-mayores-caba.svg",
        "publicaciones/informes/situacion-de-calle-caba": "situacion-calle-caba.svg",
        "publicaciones/informes/endeudarse-para-llegar-a-fin-de-mes": "endeudamiento-caba.svg",
        "publicaciones/informe-coyuntura-01-junio-2026": "coyuntura-productiva-caba.svg",
    }
    for report in REPORTS:
        folder = SITE / report["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        report_page = page(report).replace('/assets/common.js?v=255', '/assets/common.js?v=256')
        (folder / "index.html").write_text(report_page, encoding="utf-8")
        (SITE / "assets" / "publicaciones" / cover_names[report["slug"]]).write_text(cover(report), encoding="utf-8")
    replacements = {
        "/assets/publicaciones/informe-endeudamiento-caba.jpg": "/assets/publicaciones/endeudamiento-caba.svg",
        "/assets/publicaciones/informe-coyuntura-01.jpg": "/assets/publicaciones/coyuntura-productiva-caba.svg",
        "Estructura productiva argentina: recuperación parcial, empleo bajo presión y crisis del tejido productivo en CABA": "Producción y empleo: una recuperación desigual",
        "Leer informe web →": "Ver síntesis web →",
        "Ver síntesis →": "Ver síntesis web →",
    }
    report_pdfs = [report["pdf"] for report in REPORTS]
    for rel in ("publicaciones/index.html", "publicaciones/informes/index.html"):
        path = SITE / rel
        source = path.read_text(encoding="utf-8")
        # Normalize labels first so running the generator repeatedly cannot
        # accidentally rename downloads belonging to bulletins or the viewer.
        source = source.replace("Descargar informe completo ↓", "Descargar PDF ↓")
        for old, new in replacements.items():
            source = source.replace(old, new)
        source = re.sub(r'<a\b(?=[^>]*data-pdf-viewer)[^>]*>\s*Leer online\s*</a\s*>', '', source, flags=re.S)
        source = re.sub(
            r'(<h3>\s*<a href="/publicaciones/informe-coyuntura-01-junio-2026/"\s*>).*?(</a\s*>\s*</h3>)',
            r'\1Producción y empleo: una recuperación desigual\2',
            source,
            flags=re.S,
        )
        for pdf in report_pdfs:
            source = re.sub(
                rf'(<a\b(?=[^>]*\bdownload(?:="")?)(?=[^>]*href="{re.escape(pdf)}")[^>]*>)\s*Descargar PDF ↓\s*(</a\s*>)',
                r'\1Descargar informe completo ↓\2',
                source,
                flags=re.S,
            )
        path.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
