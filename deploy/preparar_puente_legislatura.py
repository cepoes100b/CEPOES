#!/usr/bin/env python3
"""Integra el puente público en todos los HTML legislativos del sitio construido."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BRIDGE_PATH = "/assets/legislatura-public-bridge.js"
BRIDGE_TAG = f'<script src="{BRIDGE_PATH}?v=20260827-2"></script>'
BRIDGE_PATTERN = re.compile(
    r'<script\b[^>]*src=["\']/assets/legislatura-public-bridge\.js'
    r'(?:\?[^"\']*)?["\'][^>]*></script>',
    flags=re.I,
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

    for path in pages:
        relative = path.relative_to(site).as_posix()
        source = path.read_text(encoding="utf-8")
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
