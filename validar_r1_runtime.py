#!/usr/bin/env python3
"""Controles de confianza y robustez incorporados en R1."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path)
    args = parser.parse_args()

    thematic = (ROOT / "deploy/site-overlay/assets/thematic-map.js").read_text(encoding="utf-8")
    gaps = (ROOT / "deploy/site-overlay/assets/brechas.js").read_text(encoding="utf-8")
    migration = (ROOT / "deploy/site-overlay/assets/migraciones.js").read_text(encoding="utf-8")
    related = (ROOT / "deploy/site-overlay/assets/related.js").read_text(encoding="utf-8")
    publications = (ROOT / "deploy/site-overlay/publicaciones/index.html").read_text(encoding="utf-8")

    for name, source in (("Mapa temático", thematic), ("Brechas", gaps)):
        assert "S?.generado" in source and "data-date" in source, f"{name} no resuelve la fecha"
        assert "Fecha no informada" in source, f"{name} no tiene fallback de fecha"
        assert "Probá nuevamente más tarde" in source, f"{name} no ofrece salida ante una falla"
    assert "}).catch(" not in migration, "Migraciones conserva el catch aplicado a addEventListener"
    assert "async()=>{try{" in migration and "}catch(e){" in migration
    assert "generic=new Set" in related and "if(!tags.length)return" in related
    assert "Último boletín" in publications and "Última publicación" not in publications

    if args.site:
        site = args.site
        checks = {
            "territorio/mapa-tematico/index.html": "/assets/thematic-map.js?v=258",
            "territorio/brechas/index.html": "/assets/brechas.js?v=258",
            "territorio/migraciones/index.html": "/assets/migraciones.js?v=258",
            "publicaciones/index.html": "Último boletín",
            "datos/estado/index.html": "Estado de los datos",
        }
        for rel, token in checks.items():
            path = site / rel
            assert path.is_file(), f"Falta {rel}"
            assert token in path.read_text(encoding="utf-8"), f"Falta {token} en {rel}"
        status = (site / "datos/estado/index.html").read_text(encoding="utf-8")
        for token in ("Fuente", "Último conjunto", "Cobertura", "Estado", "Disponible"):
            assert token in status, f"Estado de datos incompleto: {token}"
        assert "/assets/common-r1.js?v=258" in status, "Estado de datos no carga la interacción global"

    print("R1 runtime: fechas, fallbacks, Migraciones, relacionados, rótulo y estado de datos válidos")


if __name__ == "__main__":
    main()
