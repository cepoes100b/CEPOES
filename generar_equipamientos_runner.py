"""Ejecuta el generador de equipamientos y normaliza espacios sin nombre oficial.

La fuente de Espacios Verdes Públicos de BA Data contiene registros válidos
(canteros, plazoletas, jardines, etc.) sin denominación propia. Para que el
explorador no publique títulos vacíos, se conserva el registro y se le asigna
una etiqueta descriptiva explícita, sin presentarla como nombre oficial.
"""
from __future__ import annotations

import json
from pathlib import Path

import generar_equipamientos as E

BASE = Path(__file__).resolve().parent
ESPACIOS = BASE / "equipamientos" / "espacios-verdes.json"


def etiqueta_sin_denominacion(item: dict) -> str:
    clase = str(item.get("clasificacion") or "").strip()
    if clase:
        clase = clase.lower().capitalize()
        return f"{clase} sin denominación"
    return "Espacio verde sin denominación"


def main() -> int:
    rc = E.main()
    if rc:
        return rc

    d = json.loads(ESPACIOS.read_text(encoding="utf-8"))
    n = 0
    for item in d.get("items") or []:
        if not str(item.get("nombre") or "").strip():
            item["nombre"] = etiqueta_sin_denominacion(item)
            item["sin_denominacion"] = True
            n += 1
        else:
            item["sin_denominacion"] = False

    ESPACIOS.write_text(
        json.dumps(d, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"  · espacios verdes sin denominación oficial: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
