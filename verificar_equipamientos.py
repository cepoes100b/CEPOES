"""Control de calidad de los listados de equipamientos antes de publicarlos."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
DIR = BASE / "equipamientos"
TERR = BASE / "territorio.json"

FILES = {
    "educacion": ("educacion.json", 500, 5000),
    "salud": ("salud.json", 30, 250),
    "espacios": ("espacios-verdes.json", 100, 5000),
}


def load(name):
    return json.loads((DIR / name).read_text(encoding="utf-8"))


def main() -> int:
    errors = []
    terr = json.loads(TERR.read_text(encoding="utf-8"))
    docs = {}
    for key, (name, lo, hi) in FILES.items():
        try:
            d = load(name); docs[key] = d
            n = len(d.get("items") or [])
            if d.get("total") != n:
                errors.append(f"{name}: total declarado {d.get('total')} != {n}")
            if not lo <= n <= hi:
                errors.append(f"{name}: {n} registros fuera de rango [{lo},{hi}]")
            ids = [str(x.get("id")) for x in d.get("items") or []]
            if len(ids) != len(set(ids)):
                errors.append(f"{name}: hay identificadores duplicados")
            invalid = [x for x in d.get("items") or [] if not x.get("nombre") or not (1 <= int(x.get("comuna") or 0) <= 15)]
            if invalid:
                errors.append(f"{name}: {len(invalid)} registros sin nombre o comuna válida")
        except Exception as e:
            errors.append(f"{name}: {e}")

    if not errors:
        edu = Counter(x["comuna"] for x in docs["educacion"]["items"])
        hosp = Counter(x["comuna"] for x in docs["salud"]["items"] if x.get("tipo") == "Hospital")
        cesac = Counter(x["comuna"] for x in docs["salud"]["items"] if x.get("tipo") == "CeSAC")
        ev = Counter(x["comuna"] for x in docs["espacios"]["items"])
        for cid, c in terr["comunas"].items():
            i = int(cid)
            pairs = [
                ("educacion", edu[i], c["educacion"]["establecimientos"]),
                ("hospitales", hosp[i], c["salud"]["hospitales"]),
                ("cesac", cesac[i], c["salud"]["cesac"]),
                ("espacios", ev[i], c["espacio_verde"]["espacios"]),
            ]
            for label, detail, agg in pairs:
                if detail != agg:
                    errors.append(f"comuna {cid}: {label} detalle={detail}, territorio={agg}")

        for key, items in [("educacion", docs["educacion"]["items"]), ("salud", docs["salud"]["items"]), ("espacios", docs["espacios"]["items"])]:
            missing = [x for x in items if not x.get("barrio")]
            if missing:
                errors.append(f"{key}: {len(missing)} registros sin barrio")

    print("Equipamientos:")
    for key, d in docs.items():
        print(f"  · {key}: {len(d.get('items') or [])}")
    if errors:
        print(f"\n✘ {len(errors)} problema(s) — NO se publica")
        for e in errors:
            print("   ·", e)
        return 1
    print("\n✔ verificación de equipamientos superada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
