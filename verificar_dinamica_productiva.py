#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

P = Path("deploy/site-overlay/assets/data/estructura-productiva/dinamica.json")


def main() -> None:
    assert P.is_file() and P.stat().st_size > 1000, f"Falta {P}"
    d = json.loads(P.read_text(encoding="utf-8"))
    assert d.get("schema") == 1
    assert d.get("lectura") == "flujo_administrativo"
    years = d.get("anios", {})
    for y in ("2024", "2025", "2026"):
        assert y in years, y
        assert int(years[y].get("total", 0)) >= 50, (y, years[y])
        p = float(years[y].get("precision_manzana", 0))
        assert 0 <= p <= 1, (y, p)
    blocks = d.get("manzanas", {})
    assert len(blocks) >= 500, len(blocks)
    assert len(d.get("comunas", [])) == 15
    for sm, b in list(blocks.items())[:200]:
        assert sm and int(b.get("t", 0)) > 0
        assert sum(int(n) for n in b.get("y", {}).values()) == int(b["t"])
        assert isinstance(b.get("e"), list)
        for e in b["e"][:10]:
            assert len(e) == 5
    # El detalle público se limita a año/fecha/rubro/subrubro/dirección.
    # No debe aparecer estructura de datos de titulares o identificadores fiscales.
    forbidden_keys = {"titulares", "titular", "cuits", "cuit", "telefono", "razon_social"}
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                assert str(k).lower() not in forbidden_keys, k
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(d)
    total = sum(int(x["total"]) for x in years.values())
    print(f"OK dinámica productiva: {total:,} habilitaciones · {len(blocks):,} manzanas exactas")


if __name__ == "__main__":
    main()
