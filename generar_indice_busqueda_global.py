#!/usr/bin/env python3
"""Fusiona el índice heredado de producción con el registro canónico versionado."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "deploy" / "search-registry.json"
CANONICAL = {
    "/observatorio/presupuesto/": "/presupuesto/ejecucion/",
    "/territorio/presupuesto/": "/presupuesto/territorio/",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    target = args.site / "assets" / "data" / "search-index.json"
    current = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else []
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    merged: dict[str, dict] = {}
    for item in current + registry["entries"]:
        item = {key: value for key, value in item.items() if key != "query"}
        url = CANONICAL.get(item.get("url"), item.get("url"))
        if not url:
            continue
        item["url"] = url
        previous = merged.get(url, {})
        merged[url] = {**previous, **item}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(list(merged.values()), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Índice global generado: {len(merged)} URLs canónicas")


if __name__ == "__main__":
    main()

