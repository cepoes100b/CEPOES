"""Ejecuta la generación ampliada y asegura IDs únicos por capa.

Algunas fuentes oficiales reutilizan un mismo identificador para más de una
actividad o sede. Para el explorador web necesitamos una clave de fila estable y
única; si hay colisiones se conserva el identificador original como prefijo y se
agrega un sufijo ordinal, sin alterar ningún dato sustantivo de la fuente.
"""
from __future__ import annotations

import json
from pathlib import Path

import generar_oferta_ampliada as E

BASE = Path(__file__).resolve().parent
DIR = BASE / "equipamientos"


def unique_ids(path: Path) -> int:
    d = json.loads(path.read_text(encoding="utf-8"))
    used = set(); changed = 0
    for i, item in enumerate(d.get("items") or [], 1):
        base = str(item.get("id") or f"registro-{i}")
        candidate = base; n = 2
        while candidate in used:
            candidate = f"{base}-{n}"; n += 1
        if candidate != item.get("id"):
            item["id"] = candidate; changed += 1
        used.add(candidate)
    if changed:
        path.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return changed


def main() -> int:
    rc = E.main()
    if rc:
        return rc
    changed = 0
    for cfg in E.LAYERS:
        p = DIR / f"{cfg['id']}.json"
        if p.exists():
            changed += unique_ids(p)
    print(f"  · IDs duplicados normalizados: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
