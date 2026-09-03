#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def patch(source: str) -> str:
    source = re.sub(r'<section\b[^>]*\bclass=["\'][^"\']*\bobservatory-(?:people|mental)-bridge\b[^"\']*["\'][^>]*>.*?</section>', '', source, flags=re.S | re.I)
    source = re.sub(r'<section\b[^>]*\bid=["\']observatorio-salud-cuidados["\'][^>]*>.*?</section>', '', source, flags=re.S | re.I)
    source = re.sub(r'<style\b[^>]*\bid=["\']observatorio-health-hub-style["\'][^>]*>.*?</style>', '', source, flags=re.S | re.I)

    style = '''<style id="observatorio-health-hub-style">
#observatorio-salud-cuidados{background:var(--soft,#f3f7fa);border-top:1px solid rgba(23,33,38,.08);border-bottom:1px solid rgba(23,33,38,.08)}
#observatorio-salud-cuidados .section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin-bottom:22px}
#observatorio-salud-cuidados .section-head p{max-width:760px;margin:.55rem 0 0;color:var(--muted,#5f696e)}
.obs-health-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.obs-health-card{display:flex;flex-direction:column;min-height:205px;padding:22px;border:1px solid rgba(23,33,38,.13);border-radius:18px;background:var(--surface,#fff);text-decoration:none;color:inherit;transition:transform .18s ease,border-color .18s ease}
.obs-health-card:hover{transform:translateY(-2px);border-color:rgba(23,33,38,.28)}
.obs-health-card span{font-size:.78rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--muted,#5f696e)}
.obs-health-card strong{font-size:1.25rem;line-height:1.18;margin:.55rem 0}
.obs-health-card p{margin:0 0 18px;color:var(--muted,#5f696e);line-height:1.5}
.obs-health-card em{margin-top:auto;font-style:normal;font-weight:700}
@media(max-width:760px){#observatorio-salud-cuidados .section-head{align-items:flex-start;flex-direction:column}.obs-health-grid{grid-template-columns:1fr}}
</style>'''

    block = '''<section class="section alt observatory-health-hub" id="observatorio-salud-cuidados"><div class="wrap">
<div class="section-head"><div><span class="eyebrow">Eje transversal</span><h2>Salud y cuidados</h2><p>Indicadores y análisis sobre acceso a la salud, salud mental, salud reproductiva, cambios demográficos y cuidados en la Ciudad.</p></div><a class="more" href="/temas/#salud-y-cuidados">Explorar el tema →</a></div>
<div class="obs-health-grid">
<a class="obs-health-card" href="/observatorio/salud-mental/"><span>Salud mental</span><strong>Atención, demanda y red territorial</strong><p>Serie SNIC 2016–2025, comparación federal, advertencias de comparabilidad y red de atención en CABA.</p><em>Explorar →</em></a>
<a class="obs-health-card" href="/observatorio/natalidad/"><span>Natalidad y demografía</span><strong>La caída de nacimientos en perspectiva</strong><p>Nacimientos, fecundidad y reemplazo generacional en Argentina y CABA, con lectura temporal de la Ley 27.610.</p><em>Explorar →</em></a>
<a class="obs-health-card" href="/observatorio/salud-reproductiva/"><span>Salud reproductiva</span><strong>PAEV, IVE/ILE y transparencia</strong><p>Monitor de acceso y neutralidad del PAEV, fuentes oficiales y matriz de información pública disponible y faltante.</p><em>Explorar →</em></a>
<a class="obs-health-card" href="/observatorio/personas-mayores/"><span>Personas mayores</span><strong>Demografía, ingresos, vivienda y cuidados</strong><p>Indicadores públicos para analizar envejecimiento, condiciones de vida y necesidades de cuidado en la Ciudad.</p><em>Explorar →</em></a>
</div></div></section>'''

    if '</head>' not in source:
        raise SystemExit('No se encontró </head>')
    source = source.replace('</head>', style + '</head>', 1)

    # Quitar un eventual enlace Salud previo y reinsertarlo antes de Agenda.
    source = re.sub(r'<a\b[^>]*href=["\'][^"\']*#observatorio-salud-cuidados["\'][^>]*>\s*Salud\s*</a>', '', source, flags=re.I)
    salud = '<a href="/observatorio/#observatorio-salud-cuidados">Salud</a>'
    agenda = re.search(r'<a\b[^>]*>\s*Agenda\s*</a>', source, flags=re.I)
    if agenda:
        source = source[:agenda.start()] + salud + source[agenda.start():]
    else:
        sub = re.search(r'<nav\b[^>]*class=["\'][^"\']*subnav[^"\']*["\'][^>]*>', source, flags=re.I)
        if not sub:
            raise SystemExit('No se encontró subnav del Observatorio')
        end = source.find('</nav>', sub.end())
        if end < 0:
            raise SystemExit('Subnav sin cierre')
        source = source[:end] + salud + source[end:]

    # Insertar inmediatamente después del header principal del Observatorio.
    main = re.search(r'<main\b[^>]*>', source, flags=re.I)
    start = main.end() if main else 0
    header = re.search(r'<header\b[^>]*>.*?</header>', source[start:], flags=re.S | re.I)
    if not header:
        raise SystemExit('No se encontró header del Observatorio')
    insert_at = start + header.end()
    source = source[:insert_at] + block + source[insert_at:]

    required = [
        'id="observatorio-salud-cuidados"',
        '>Salud mental<',
        '>Natalidad y demografía<',
        '>Salud reproductiva<',
        '>Personas mayores<',
        '/observatorio/#observatorio-salud-cuidados">Salud</a>',
    ]
    missing = [x for x in required if x not in source]
    if missing:
        raise SystemExit('Parche incompleto: ' + ', '.join(missing))
    if source.count('id="observatorio-salud-cuidados"') != 1:
        raise SystemExit('El bloque Salud quedó duplicado')
    return source


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('uso: parche_observatorio_salud.py RUTA_HTML')
    path = Path(sys.argv[1])
    patched = patch(path.read_text(encoding='utf-8'))
    path.write_text(patched, encoding='utf-8')
    print('Observatorio: Salud y cuidados insertado server-side · 4 accesos · subnav Salud OK')


if __name__ == '__main__':
    main()
