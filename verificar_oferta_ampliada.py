"""Control de calidad del catálogo ampliado de Oferta territorial."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DIR = BASE / "equipamientos"
CAT = DIR / "catalogo.json"

REQUIRED = {
    "educacion","salud","espacios-verdes",
    "centros-medicos-barriales","salud-privada","estaciones-saludables",
    "bibliotecas","espacios-culturales","instituciones-colectividades",
    "polideportivos","programas-deportivos","clubes","estadios",
    "centros-primera-infancia","centros-accion-familiar","casas-nnya","hogares-paradores",
    "comisarias","bomberos",
    "subte-bocas","ecobici","ferrocarril","paradas-taxis","bicicleteros",
    "puntos-verdes","fiab","mercados","sedes-comunales","centros-integracion-laboral",
}


def main() -> int:
    errors = []
    if not CAT.exists():
        print("✘ no existe equipamientos/catalogo.json")
        return 1
    cat = json.loads(CAT.read_text(encoding="utf-8"))
    layers = {x.get("id"): x for x in cat.get("layers") or [] if x.get("id")}
    missing = sorted(REQUIRED - set(layers))
    extra_errors = cat.get("errores") or []
    if missing:
        errors.append("faltan capas: " + ", ".join(missing))
    if extra_errors:
        errors.extend(["generador: " + str(x) for x in extra_errors])
    if len(layers) < 29:
        errors.append(f"catálogo tiene {len(layers)} capas; esperaba al menos 29")

    print(f"Oferta territorial · {len(layers)} capas")
    total_all = 0
    for lid in sorted(REQUIRED & set(layers)):
        meta = layers[lid]
        fn = meta.get("file") or f"{lid}.json"
        p = DIR / fn
        if not p.exists():
            errors.append(f"{lid}: no existe {fn}")
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            items = d.get("items") or []
        except Exception as e:
            errors.append(f"{lid}: JSON inválido: {e}")
            continue
        n = len(items); total_all += n
        if n < 1:
            errors.append(f"{lid}: sin registros")
            continue
        if meta.get("total") != n:
            errors.append(f"{lid}: catálogo={meta.get('total')} archivo={n}")
        ids = [str(x.get("id") or "") for x in items]
        if any(not x for x in ids):
            errors.append(f"{lid}: registros sin id")
        if len(ids) != len(set(ids)):
            errors.append(f"{lid}: identificadores duplicados")
        bad_c = [x for x in items if x.get("comuna") is not None and not (1 <= int(x.get("comuna")) <= 15)]
        if bad_c:
            errors.append(f"{lid}: {len(bad_c)} registros con comuna inválida")
        named = sum(bool(str(x.get("nombre") or "").strip()) for x in items)
        scoped = sum(bool(x.get("comuna") or x.get("barrio")) for x in items)
        coords = sum(bool(x.get("coord")) for x in items)
        coverage = scoped / n if n else 0
        # Las capas deben poder usarse territorialmente. Se admite que una parte
        # de los registros oficiales carezca de barrio/comuna, pero no la mayoría.
        if lid not in {"programas-deportivos"} and coverage < .50:
            errors.append(f"{lid}: cobertura territorial baja ({coverage:.0%})")
        if named != n:
            errors.append(f"{lid}: {n-named} registros sin etiqueta visible")
        print(f"  · {lid:30} {n:5} · territorio {coverage:5.0%} · coord {coords/n:5.0%}")

    print(f"\nTotal de registros explorables: {total_all}")
    if errors:
        print(f"\n✘ {len(errors)} problema(s) — NO se publica")
        for e in errors:
            print("   ·", e)
        return 1
    print("\n✔ verificación de Oferta territorial ampliada superada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
