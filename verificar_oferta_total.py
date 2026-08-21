"""Verifica todas las capas del catálogo total, no sólo las 29 originales."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DIR = BASE / "equipamientos"
CAT = DIR / "catalogo.json"
MIN_LAYERS = 55


def main() -> int:
    errors = []
    if not CAT.exists():
        print("✘ no existe equipamientos/catalogo.json")
        return 1
    cat = json.loads(CAT.read_text(encoding="utf-8"))
    layers = {x.get("id"): x for x in cat.get("layers") or [] if x.get("id")}
    if cat.get("errores"):
        errors.extend(["generador: " + str(x) for x in cat["errores"]])
    if len(layers) < MIN_LAYERS:
        errors.append(f"catálogo tiene {len(layers)} capas; esperaba al menos {MIN_LAYERS}")

    print(f"Oferta territorial total · {len(layers)} capas")
    total = 0
    for lid in sorted(layers):
        meta = layers[lid]
        fn = meta.get("file") or f"{lid}.json"
        p = DIR / fn
        if not p.exists():
            errors.append(f"{lid}: falta {fn}")
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8")); items = d.get("items") or []
        except Exception as e:
            errors.append(f"{lid}: JSON inválido: {e}"); continue
        n = len(items); total += n
        if n < 1:
            errors.append(f"{lid}: sin registros"); continue
        if meta.get("total") != n:
            errors.append(f"{lid}: catálogo={meta.get('total')} archivo={n}")
        ids = [str(x.get("id") or "") for x in items]
        if any(not x for x in ids): errors.append(f"{lid}: registros sin id")
        if len(ids) != len(set(ids)): errors.append(f"{lid}: IDs duplicados")
        invalid = []
        for x in items:
            c = x.get("comuna")
            if c is not None:
                try:
                    if not 1 <= int(c) <= 15: invalid.append(x)
                except Exception: invalid.append(x)
        if invalid: errors.append(f"{lid}: {len(invalid)} comunas inválidas")
        named = sum(bool(str(x.get("nombre") or "").strip()) for x in items)
        scoped = sum(bool(x.get("comuna") or x.get("barrio")) for x in items)
        coords = sum(bool(x.get("coord")) for x in items)
        coverage = scoped / n
        if coverage < .50:
            errors.append(f"{lid}: cobertura territorial baja ({coverage:.0%})")
        if named != n:
            errors.append(f"{lid}: {n-named} registros sin etiqueta visible")
        print(f"  · {lid:32} {n:6} · territorio {coverage:5.0%} · coord {coords/n:5.0%}")

    print(f"\nTotal de registros explorables: {total}")
    if errors:
        print(f"\n✘ {len(errors)} problema(s) — NO se publica")
        for e in errors: print("   ·", e)
        return 1
    print("\n✔ verificación de Oferta territorial total superada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
