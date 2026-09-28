#!/usr/bin/env python3
"""Genera la página pública sobre procedencia y fechas de los conjuntos."""

from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def date(value: str | None) -> str:
    if not value:
        return "Fecha no informada"
    raw = str(value).split("T", 1)[0]
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return html.escape(str(value))
    months = (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    )
    return f"{parsed.day} de {months[parsed.month - 1]} de {parsed.year}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()

    equipment = load("equipamientos/resumen-territorial.json")
    territory = load("territorio.json")
    budget = load("presupuesto.json")
    legislature = load("legislatura_publica.json")
    mental = load("deploy/site-overlay/assets/data/salud-mental.json")
    migration = load("deploy/site-overlay/assets/data/migraciones.json")

    rows = [
        ("Oferta territorial", "/territorio/equipamientos/", "/cepoes/metodologia/territorio/", "BA Data y fuentes oficiales primarias", equipment.get("generado"), f'{equipment.get("total_capas", "s/d")} capas · {equipment.get("total_registros", "s/d"):,} registros'.replace(",", ".")),
        ("Perfiles territoriales", "/territorio/", "/cepoes/metodologia/territorio/", "BA Data · Censo 2022", territory.get("generado"), f'{len(territory.get("comunas", {}))} comunas · {len(territory.get("barrios", {}))} barrios'),
        ("Presupuesto", "/presupuesto/", "/cepoes/metodologia/presupuesto/", "GCBA · datos presupuestarios oficiales", budget.get("generado"), f'Período {budget.get("periodo", "no informado")}'),
        ("Legislatura", "/legislatura/", "/cepoes/metodologia/legislatura/", "Legislatura de la Ciudad de Buenos Aires", legislature.get("generado"), f'{len(legislature.get("expedientes", []))} expedientes · {len(legislature.get("reuniones", []))} reuniones'),
        ("Salud mental", "/observatorio/salud-mental/", "/cepoes/metodologia/salud-mental/", "SNIC · fuentes sanitarias oficiales", mental.get("generated_at"), "Serie 2016–2025 · red territorial CABA"),
        ("Migraciones", "/territorio/migraciones/", "/cepoes/metodologia/migraciones/", "INDEC · IDECBA · EAH", migration.get("updated_at") or migration.get("generated"), f'{len(migration.get("communes", {}))} comunas · Censo 2022 y EAH'),
    ]
    cards = "".join(
        f'<article class="state-card"><div class="state-card-top"><span class="state-dot" aria-hidden="true"></span><span>Conjunto incorporado</span></div>'
        f'<h3><a href="{product}">{html.escape(title)}</a></h3>'
        f'<p class="state-source">{html.escape(source)}</p>'
        f'<dl><div><dt>Procesado</dt><dd>{date(processed)}</dd></div><div><dt>Cobertura</dt><dd>{html.escape(coverage)}</dd></div></dl>'
        f'<div class="state-actions"><a href="{product}">Explorar datos <span aria-hidden="true">→</span></a><a href="{method}">Ficha técnica <span aria-hidden="true">→</span></a></div></article>'
        for title, product, method, source, processed, coverage in rows
    )
    generated = datetime.now().astimezone().strftime("%Y-%m-%d")
    page = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Estado de los datos — CEPOES</title>
<meta name="description" content="Estado, cobertura y fecha de actualización de las principales fuentes de datos publicadas por CEPOES.">
<link rel="canonical" href="https://cepoes.org/datos/estado/">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&amp;family=Inter:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
<link rel="stylesheet" href="/assets/arquitectura.css">
<link rel="stylesheet" href="/assets/estado-datos.css?v=1">
<script defer src="/assets/common-r1.js?v=259"></script>
</head>
<body data-related-tags="datos-publicos,metodologia,fuentes">
<main id="contenido" class="state-page">
<header class="page-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">CEPOES</a> / <a href="/cepoes/metodologia/">Metodología y fuentes</a> / Estado de los datos</div><span class="eyebrow">Transparencia de datos</span><h1>Estado de los datos</h1><p class="state-lead">Consultá cuándo se procesó cada conjunto, qué cubre y con qué fuentes se elaboró.</p><div class="state-hero-meta"><span><strong>{len(rows)} conjuntos</strong> con información de procedencia</span><span>Página generada el <strong>{date(generated)}</strong></span></div></div></header>
<section class="section state-section" aria-labelledby="conjuntos"><div class="wrap"><div class="state-intro"><div><span class="eyebrow">Panorama de fuentes</span><h2 id="conjuntos">Conjuntos publicados</h2><p>La fecha de procesamiento indica cuándo CEPOES generó o incorporó el archivo. El período estadístico y la frecuencia de actualización de cada fuente pueden ser distintos.</p></div><a class="state-intro-link" href="/cepoes/metodologia/">Metodología y fuentes <span aria-hidden="true">→</span></a></div>
<div class="state-grid">{cards}</div>
<aside class="state-explainer" aria-labelledby="interpretar"><div><span class="eyebrow">Cómo leer estas fechas</span><h2 id="interpretar">Procesamiento y período no son lo mismo</h2></div><div><p>Una fecha reciente de procesamiento no vuelve reciente a una medición censal o anual. Revisá el período, la unidad y los límites de cada indicador en el producto y su ficha técnica.</p><p>Esta página es informativa y no monitorea la disponibilidad de las fuentes en tiempo real. Si una actualización falla, puede conservarse la última versión válida hasta completar los controles.</p></div></aside>
</div></section>
</main>
</body>
</html>
"""
    target = args.site / "datos" / "estado" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    print(f"Estado de datos generado: {len(rows)} fuentes críticas")


if __name__ == "__main__":
    main()
