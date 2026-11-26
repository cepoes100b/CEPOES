#!/usr/bin/env python3
"""Integra el puente público en todos los HTML legislativos del sitio construido."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from datetime import datetime


BRIDGE_PATH = "/assets/legislatura-public-bridge.js"
BRIDGE_TAG = f'<script src="{BRIDGE_PATH}?v=20260827-2"></script>'
BRIDGE_PATTERN = re.compile(
    r'<script\b[^>]*src=["\']/assets/legislatura-public-bridge\.js'
    r'(?:\?[^"\']*)?["\'][^>]*></script>',
    flags=re.I,
)


STATUS_BEGIN = "<!-- cepoes-estado-estructura:inicio -->"
STATUS_END = "<!-- cepoes-estado-estructura:fin -->"
STATUS_PATTERN = re.compile(re.escape(STATUS_BEGIN) + r".*?" + re.escape(STATUS_END), re.S)


def inject_structure_status(source: str, status: dict | None) -> str:
    # El build parte del sitio anterior: borrar siempre la versión previa, también al recuperarse.
    cleaned = STATUS_PATTERN.sub("", source)
    if status is None:
        return cleaned
    if status.get("estado") != "degradada" or status.get("motivo") != "omisiones_verificadas_comisiones":
        raise ValueError("Estado público de estructura institucional inválido")
    validated = datetime.fromisoformat(status["ultimo_validado_en"]).strftime("%d/%m/%Y")
    rows = "; ".join(
        f'{html.escape(c["comision"])} ({int(c["integrantes_observados"])} de {int(c["integrantes_normativos"])})'
        for c in status["comisiones"]
    )
    block = status["bloque_fuerza_por_buenos_aires"]
    observed, last = int(block["integrantes_observados"]), int(block["integrantes_ultimo_validado"])
    block_note = f' El bloque Fuerza por Buenos Aires informó {observed} integrantes; el registro validado conserva {last}.' if observed != last else ""
    notice = (
        STATUS_BEGIN + '<aside class="wrap" aria-label="Estado de la estructura institucional">'
        '<p><strong>Estructura institucional con actualización parcial.</strong> '
        f'Las nóminas oficiales mostraron menos integrantes que los previstos: {rows}.{block_note} '
        f'Se conserva la última estructura validada, del {validated}. '
        'Este aviso no acredita cambios formales de integración. '
        'La agenda, las sesiones y los expedientes se actualizan por separado. '
        '<a href="/datos/estado/">Ver estado de los datos</a>.</p></aside>' + STATUS_END
    )
    opening_tag = next(
        (tag for tag in ("main", "body") if re.search(fr"<{tag}\b[^>]*>", cleaned, re.I)),
        None,
    )
    if opening_tag is None:
        raise ValueError("No se encontró un lugar para la advertencia en /legislatura/")
    return re.sub(
        fr"(<{opening_tag}\b[^>]*>)", lambda match: match[0] + notice,
        cleaned, count=1, flags=re.I,
    )


def inject(source: str, relative_path: str) -> str:
    """Quita versiones anteriores e inyecta exactamente un puente en ``head``."""
    cleaned = BRIDGE_PATTERN.sub("", source)
    updated, count = re.subn(
        r"(<head\b[^>]*>)",
        r"\1" + BRIDGE_TAG,
        cleaned,
        count=1,
        flags=re.I,
    )
    if count != 1:
        raise ValueError(f"No se encontró <head> en {relative_path}")
    if len(BRIDGE_PATTERN.findall(updated)) != 1:
        raise ValueError(f"Puente duplicado o ausente en {relative_path}")
    return updated


def prepare(site: Path) -> int:
    legislature = site / "legislatura"
    asset = site / BRIDGE_PATH.lstrip("/")
    if not legislature.is_dir():
        raise SystemExit(f"No existe el módulo legislativo: {legislature}")
    if not asset.is_file() or "__CEPOES_LEGISLATURA_PUBLIC_BRIDGE__" not in asset.read_text(
        encoding="utf-8"
    ):
        raise SystemExit(f"Puente JS ausente o inválido: {asset}")

    pages = sorted(legislature.rglob("*.html"))
    if not pages:
        raise SystemExit("No se encontraron HTML bajo /legislatura/")

    payload = site / "legislatura_publica.json"
    status = json.loads(payload.read_text(encoding="utf-8")).get("estado_estructura_institucional")
    if status is not None and not (legislature / "index.html").is_file():
        raise ValueError("No está la entrada pública /legislatura/ para mostrar la advertencia")

    for path in pages:
        relative = path.relative_to(site).as_posix()
        source = path.read_text(encoding="utf-8")
        if relative == "legislatura/index.html":
            source = inject_structure_status(source, status)
        path.write_text(inject(source, relative), encoding="utf-8")

    print(f"Legislatura: puente público integrado en {len(pages)} HTML")
    return len(pages)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    prepare(args.site.resolve())


if __name__ == "__main__":
    main()
