#!/usr/bin/env python3
"""Genera una página pública y verificable sobre la frescura de los datos."""

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
        ("Oferta territorial", "BA Data y fuentes oficiales primarias", date(equipment.get("generado")), f'{equipment.get("total_capas", "s/d")} capas · {equipment.get("total_registros", "s/d"):,} registros'.replace(",", "."), "Disponible"),
        ("Perfiles territoriales", "BA Data · Censo 2022", date(territory.get("generado")), f'{len(territory.get("comunas", {}))} comunas · {len(territory.get("barrios", {}))} barrios', "Disponible"),
        ("Presupuesto", "GCBA · datos presupuestarios oficiales", date(budget.get("generado")), f'Período {budget.get("periodo", "no informado")}', "Disponible"),
        ("Legislatura", "Legislatura de la Ciudad de Buenos Aires", date(legislature.get("generado")), f'{len(legislature.get("expedientes", []))} expedientes · {len(legislature.get("reuniones", []))} reuniones', "Disponible"),
        ("Salud mental", "SNIC · fuentes sanitarias oficiales", date(mental.get("generated_at")), "Serie 2016–2025 · red territorial CABA", "Disponible"),
        ("Migraciones", "INDEC · IDECBA · EAH", date(migration.get("updated_at") or migration.get("generated")), f'{len(migration.get("communes", {}))} comunas · Censo 2022 y EAH', "Disponible"),
    ]
    cells = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
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
<link rel="stylesheet" href="/assets/style.css?v=226">
<script defer src="/assets/common-r1.js?v=258"></script>
</head>
<body data-related-tags="datos-publicos,metodologia,fuentes">
<main id="contenido">
<header class="page-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">CEPOES</a> / Estado de los datos</div><span class="eyebrow">Transparencia operativa</span><h1>Estado de los datos</h1><p>Fecha, cobertura y disponibilidad de las fuentes principales que sostienen los productos públicos de CEPOES.</p><div class="meta-row"><span>Última verificación del conjunto: <b>{date(generated)}</b></span><span>Estado: <b>informativo, no monitor en tiempo real</b></span></div></div></header>
<section class="section"><div class="wrap"><div class="section-head"><div><span class="eyebrow">Fuentes críticas</span><h2>Disponibilidad y frescura</h2><p>La fecha corresponde al último conjunto generado o incorporado al repositorio. “Disponible” indica que el archivo pasó los controles del despliegue; no implica que la fuente oficial tenga una frecuencia diaria.</p></div></div>
<div class="table-wrap"><table class="data-table"><thead><tr><th>Producto</th><th>Fuente</th><th>Último conjunto</th><th>Cobertura</th><th>Estado</th></tr></thead><tbody>{cells}</tbody></table></div>
<div class="note-card" style="margin-top:24px"><h3>Cómo interpretar esta página</h3><p>CEPOES combina fuentes con frecuencias distintas: censales, anuales, trimestrales y de actualización continua. Si una fuente oficial se retrasa, la fecha se conserva y no se reemplaza por una estimación. Las incidencias que afecten una publicación completa se informarán aquí.</p><p><a class="more" href="/cepoes/metodologia/">Ver metodología y fuentes →</a></p></div>
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
