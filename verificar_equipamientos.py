"""Control de calidad de los listados de equipamientos antes de publicarlos."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
DIR = BASE / "equipamientos"
TERR = BASE / "territorio.json"
EQUIPMENT_HTML = BASE / "deploy/site-overlay/territorio/equipamientos/index.html"
EQUIPMENT_JS = BASE / "deploy/site-overlay/assets/equipamientos.js"
ARCHITECTURE_CSS = BASE / "deploy/site-overlay/assets/arquitectura.css"

FILES = {
    "educacion": ("educacion.json", 500, 5000),
    "salud": ("salud.json", 30, 250),
    "espacios": ("espacios-verdes.json", 100, 5000),
}


def load(name):
    return json.loads((DIR / name).read_text(encoding="utf-8"))


def main() -> int:
    errors, notices = [], []
    terr = json.loads(TERR.read_text(encoding="utf-8"))

    # El nivel educativo es un filtro exclusivo de la capa de establecimientos
    # educativos. Estas comprobaciones evitan que una regla visual vuelva a
    # convertirlo accidentalmente en un filtro general del catálogo.
    html = EQUIPMENT_HTML.read_text(encoding="utf-8")
    javascript = EQUIPMENT_JS.read_text(encoding="utf-8")
    css = ARCHITECTURE_CSS.read_text(encoding="utf-8")
    if 'class="equipment-level-control" hidden' not in html:
        errors.append("interfaz: Nivel educativo debe estar oculto por defecto")
    if "const active=type==='educacion'" not in javascript:
        errors.append("interfaz: Nivel educativo debe activarse sólo en la capa educacion")
    if ".equipment-tools .equipment-level-control[hidden]{display:none}" not in css:
        errors.append("interfaz: falta proteger el estado hidden del filtro Nivel educativo")
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

        # Un registro oficial puede traer comuna pero no barrio. Eso no invalida
        # el listado comunal: se informa como aviso y simplemente no aparece al
        # filtrar por barrio. Nunca se imputa a un barrio por aproximación.
        for key, items in [("educacion", docs["educacion"]["items"]), ("salud", docs["salud"]["items"]), ("espacios", docs["espacios"]["items"])]:
            missing = [x for x in items if not x.get("barrio")]
            if missing:
                notices.append(f"{key}: {len(missing)} registros oficiales sin barrio")

    print("Equipamientos:")
    for key, d in docs.items():
        print(f"  · {key}: {len(d.get('items') or [])}")
    for n in notices:
        print("  ~", n)
    if errors:
        print(f"\n✘ {len(errors)} problema(s) — NO se publica")
        for e in errors:
            print("   ·", e)
        return 1
    print("\n✔ verificación de equipamientos superada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
