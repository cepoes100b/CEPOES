"""Control de calidad de territorio.json antes de publicarlo."""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "territorio.json"


def main() -> int:
    if not OUT.exists():
        print("✘ no existe territorio.json")
        return 1
    d = json.loads(OUT.read_text(encoding="utf-8"))
    errors, notices = [], []
    try:
        g = datetime.date.fromisoformat(d["generado"])
        if abs((datetime.date.today() - g).days) > 2:
            errors.append(f"fecha de generación vieja: {g}")
    except Exception as e:
        errors.append(f"generado inválido: {e}")

    comunas = d.get("comunas") or {}
    barrios = d.get("barrios") or {}
    if set(comunas) != {str(i) for i in range(1, 16)}:
        errors.append(f"comunas: {len(comunas)}, esperaba exactamente 15")
    if len(barrios) != 48:
        errors.append(f"barrios: {len(barrios)}, esperaba 48")

    totals = {
        "educacion": sum((c.get("educacion") or {}).get("establecimientos", 0) for c in comunas.values()),
        "cesac": sum((c.get("salud") or {}).get("cesac", 0) for c in comunas.values()),
        "hospitales": sum((c.get("salud") or {}).get("hospitales", 0) for c in comunas.values()),
        "espacios": sum((c.get("espacio_verde") or {}).get("espacios", 0) for c in comunas.values()),
        "verde_m2": sum((c.get("espacio_verde") or {}).get("m2", 0) for c in comunas.values()),
    }
    # Umbrales deliberadamente amplios: detectan parser roto, no cambios reales de padrón.
    checks = {
        "educacion": (500, 5000),
        "cesac": (20, 200),
        "hospitales": (15, 100),
        "espacios": (100, 5000),
        "verde_m2": (1_000_000, 200_000_000),
    }
    for k, (lo, hi) in checks.items():
        v = totals[k]
        if not lo <= v <= hi:
            errors.append(f"{k}: total {v:g} fuera de rango [{lo:g}, {hi:g}]")
        else:
            notices.append(f"{k}: {v:g}")

    if d.get("errores"):
        errors.extend([f"generador informó {x}" for x in d["errores"]])

    # Consistencia: sumas barriales no pueden superar mucho las comunales.
    for cid, c in comunas.items():
        bs = [b for b in barrios.values() if str(b.get("comuna")) == cid]
        for section, key in [("educacion", "establecimientos"), ("salud", "cesac"), ("salud", "hospitales")]:
            bc = sum((b.get(section) or {}).get(key, 0) for b in bs)
            cc = (c.get(section) or {}).get(key, 0)
            if bc > cc:
                errors.append(f"comuna {cid}: barrios suman {bc} en {section}.{key}, comuna dice {cc}")

    print(f"territorio.json · {OUT.stat().st_size//1024} KB")
    for n in notices:
        print("  ·", n)
    if errors:
        print(f"\n✘ {len(errors)} problema(s) — NO se publica")
        for e in errors:
            print("   ·", e)
        return 1
    print("\n✔ verificación territorial superada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
