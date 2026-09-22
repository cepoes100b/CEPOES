"""Genera el índice ciudadano compacto usado por la búsqueda transversal."""
from __future__ import annotations

import datetime
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "equipamientos"
PUBLIC = BASE / "deploy" / "site-overlay" / "assets" / "data" / "equipamientos-busqueda.json"
EXCLUDED = {"vados", "rampas-accesibilidad-2016"}
KEEP = (
    "id", "nombre", "comuna", "barrio", "direccion", "ubicacion", "tipo",
    "clasificacion", "sector", "coord", "telefono", "web", "especialidad",
    "especialidades", "atencion", "oferta", "detalle", "detalle2",
)


def main() -> int:
    catalog = json.loads((OUT / "catalogo.json").read_text(encoding="utf-8"))
    records = []
    for layer in catalog.get("layers") or []:
        if layer.get("id") in EXCLUDED:
            continue
        path = OUT / str(layer.get("file") or f"{layer['id']}.json")
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for source in doc.get("items") or []:
            item = {key: source[key] for key in KEEP if source.get(key) not in (None, "", [], {})}
            item["layer"] = layer["id"]
            records.append(item)
    payload = {
        "version": 1,
        "generado": datetime.date.today().isoformat(),
        "excluded": sorted(EXCLUDED),
        "total": len(records),
        "items": records,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    (OUT / "busqueda.json").write_text(encoded, encoding="utf-8")
    PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC.write_text(encoded, encoding="utf-8")
    print(f"Índice ciudadano: {len(records)} registros de {len(set(x['layer'] for x in records))} fuentes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
