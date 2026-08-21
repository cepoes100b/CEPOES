"""Control de calidad del resumen territorial usado por radiografias y mapas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
P = BASE / "equipamientos" / "resumen-territorial.json"


def main() -> int:
    errors = []
    if not P.exists():
        print("✘ no existe equipamientos/resumen-territorial.json")
        return 1
    d = json.loads(P.read_text(encoding="utf-8"))
    comunas = d.get("comunas") or {}
    barrios = d.get("barrios") or {}
    layers = d.get("layers") or {}
    if set(comunas) != {str(i) for i in range(1,16)}:
        errors.append(f"comunas inválidas: {sorted(comunas)}")
    if len(barrios) != 48:
        errors.append(f"barrios={len(barrios)}; esperaba 48")
    if len(layers) < 62:
        errors.append(f"capas={len(layers)}; esperaba al menos 62")
    if int(d.get("total_registros") or 0) < 100000:
        errors.append(f"total_registros demasiado bajo: {d.get('total_registros')}")

    required = {"educacion","salud","mayores","infancias","cultura","deporte","seguridad","movilidad","servicios","ambiente"}
    for label, scopes in (("comuna", comunas), ("barrio", barrios)):
        for sid, scope in scopes.items():
            pop = int(scope.get("poblacion") or 0)
            if pop <= 0:
                errors.append(f"{label} {sid}: población inválida")
            featured = scope.get("destacados") or {}
            miss = required - set(featured)
            if miss:
                errors.append(f"{label} {sid}: faltan destacados {sorted(miss)}")
            for fid, item in featured.items():
                val = item.get("valor")
                if val is not None and int(val) < 0:
                    errors.append(f"{label} {sid}: {fid} negativo")
                rate = item.get("tasa_10k")
                if rate is not None and float(rate) < 0:
                    errors.append(f"{label} {sid}: {fid} tasa negativa")

    # Todo conteo barrial debe estar contenido en el conteo de su comuna.
    for bkey, b in barrios.items():
        cid = str(b.get("comuna") or "")
        c = comunas.get(cid)
        if not c:
            errors.append(f"barrio {bkey}: comuna inexistente {cid}")
            continue
        for lid, n in (b.get("capas") or {}).items():
            if int(n) > int((c.get("capas") or {}).get(lid, 0)):
                errors.append(f"barrio {bkey}: {lid}={n} supera comuna {cid}")

    print(f"Resumen territorial · {len(comunas)} comunas · {len(barrios)} barrios · {len(layers)} capas · {d.get('total_registros')} registros")
    if errors:
        print(f"✘ {len(errors)} problema(s) — NO se publica")
        for e in errors[:50]:
            print("  ·", e)
        return 1
    print("✔ verificación del resumen territorial superada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
