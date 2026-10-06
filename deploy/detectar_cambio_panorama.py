#!/usr/bin/env python3
"""Evita commits por fecha de lectura; conserva bytes previos si los datos no cambian."""
from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path


def substantive(document: dict) -> dict:
    result = copy.deepcopy(document)
    result.pop("generado", None)
    # Sólo estos timestamps de extracción son volátiles. Hash, URL, período,
    # cobertura, metodología y cualquier otra fecha permanecen comparables.
    for source in result.get("fuentes", {}).values():
        if isinstance(source, dict):
            source.pop("extraido", None)
    return result


def detect(current: Path, previous: Path, current_geo: Path, previous_geo: Path) -> bool:
    new = json.loads(current.read_text(encoding="utf-8"))
    new_geo = json.loads(current_geo.read_text(encoding="utf-8"))
    if not previous.exists() or not previous_geo.exists():
        return True
    old = json.loads(previous.read_text(encoding="utf-8"))
    old_geo = json.loads(previous_geo.read_text(encoding="utf-8"))
    changed = substantive(old) != substantive(new) or old_geo != new_geo
    if not changed:
        shutil.copyfile(previous, current)
        shutil.copyfile(previous_geo, current_geo)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", type=Path, default=Path("deploy/site-overlay/assets/data/estructura-productiva/actual.json"))
    parser.add_argument("--previous", type=Path, default=Path("/tmp/estructura-actual-prev.json"))
    parser.add_argument("--current-geo", type=Path, default=Path("deploy/site-overlay/assets/data/estructura-productiva/comunas.geojson"))
    parser.add_argument("--previous-geo", type=Path, default=Path("/tmp/estructura-comunas-prev.geojson"))
    args = parser.parse_args()
    changed = detect(args.current, args.previous, args.current_geo, args.previous_geo)
    print("changed=" + str(changed).lower())


if __name__ == "__main__":
    main()
