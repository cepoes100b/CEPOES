#!/usr/bin/env python3
"""Pruebas canónicas del buscador global de CEPOES."""

from __future__ import annotations

import json
import re
import unicodedata
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "deploy" / "search-registry.json"
COMMON = ROOT / "deploy" / "site-overlay" / "assets" / "common.js"
PREP = ROOT / "deploy" / "preparar_sitio_publico.py"


def norm(value: str) -> str:
    value = unicodedata.normalize("NFD", value or "")
    return "".join(c for c in value if unicodedata.category(c) != "Mn").lower()


def score(item: dict, query: str) -> int:
    q = norm(query.strip())
    title = norm(item.get("title", ""))
    hay = norm(" ".join([
        item.get("title", ""),
        item.get("summary", ""),
        " ".join(item.get("tags", [])),
    ]))
    words = [word for word in re.split(r"\s+", q) if word]
    matches = sum(word in hay for word in words)
    return (1000 if title == q else 200 if q in title else 0) + matches * 10 + (
        item.get("priority", 0) if matches else 0
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path)
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entries = registry["entries"]
    assert len(entries) >= 30, "Se requieren al menos 30 consultas canónicas"
    assert len({item["url"] for item in entries}) == len(entries), "Hay URLs duplicadas en el registro"
    for expected in entries:
        ranked = sorted(entries, key=lambda item: (-score(item, expected["query"]), norm(item["title"])))
        assert ranked[0]["url"] == expected["url"], (
            f'{expected["query"]!r} devolvió {ranked[0]["url"]} antes que {expected["url"]}'
        )
    common = COMMON.read_text(encoding="utf-8")
    prep = PREP.read_text(encoding="utf-8")
    for token in ("title===q?1000", "dedupe=", "search-index.json?v=258", "const esc="):
        assert token in common, f"Falta control de búsqueda: {token}"
    assert 'aria-live="polite"' in prep and 'id="site-search-results"' in prep
    assert "common-r1.js?v=258" in prep
    if args.site:
        pages = [path for path in args.site.rglob("*.html") if "privado" not in path.parts]
        assert pages, "No se encontraron páginas públicas para validar"
        for path in pages:
            source = path.read_text(encoding="utf-8")
            if "/assets/common" in source:
                assert "/assets/common-r1.js?v=258" in source, f"Referencia obsoleta a common.js en {path}"
        assert (args.site / "assets/common-r1.js").is_file(), "Falta el activo common-r1.js"
    print(f"Búsqueda global: {len(entries)}/{len(entries)} consultas canónicas correctas")


if __name__ == "__main__":
    main()
