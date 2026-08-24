#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("deploy/site-overlay/assets/data/estructura-productiva")


def load(name: str):
    p = ROOT / name
    assert p.is_file() and p.stat().st_size > 10, f"Falta {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    m = load("manifest.json")
    assert int(m.get("schema", 0)) >= 3, m.get("schema")
    assert m.get("periodo_rus") == "2017", m.get("periodo_rus")
    assert m.get("clasificacion_economica") == "ClaNAE 2004", m.get("clasificacion_economica")
    total = int(m.get("total", 0))
    blocks = int(m.get("manzanas_actividad", 0))
    ratio = float(m.get("join_cartografia", 0))
    excluded = int(m.get("registros_excluidos_sin_actividad_clanae", 0))
    assert total >= 50000, total
    assert blocks >= 1000, blocks
    assert ratio >= .75, ratio
    assert excluded > 0, excluded
    assert len(m.get("comunas", [])) == 15
    assert len(m.get("sectores", [])) >= 8

    # La categoría residual no puede volver a absorber edificios, lotes o
    # locales cerrados: esos códigos 00/0 se excluyen antes de clasificar.
    sector_z = next((int(x.get("total", 0)) for x in m.get("sectores", []) if x.get("id") == "Z"), 0)
    assert sector_z < total * .10, (sector_z, total)

    geo = load("mapa.json")
    feats = geo.get("features", [])
    assert geo.get("type") == "FeatureCollection"
    assert len(feats) == blocks, (len(feats), blocks)
    for f in feats[:100]:
        p = f.get("properties", {})
        assert p.get("sm") and 1 <= int(p.get("c", 0)) <= 15 and int(p.get("t", 0)) > 0
        assert f.get("geometry", {}).get("type") in {"Polygon", "MultiPolygon"}

    sum_total = 0
    sum_blocks = 0
    for c in range(1, 16):
        d = load(f"comuna-{c:02d}.json")
        assert d.get("comuna") == c
        assert isinstance(d.get("manzanas"), dict)
        sum_total += int(d.get("total", 0))
        sum_blocks += len(d["manzanas"])
        for sm, b in list(d["manzanas"].items())[:50]:
            assert sm and int(b.get("t", 0)) > 0
            assert isinstance(b.get("e"), list)
            assert sum(int(v) for v in b.get("s", {}).values()) == int(b.get("t", 0))
            # Todos los registros publicados deben tener una división ClaNAE
            # económica real; 00/0 no debe reaparecer en el detalle.
            for e in b.get("e", [])[:25]:
                assert str(e[3]).strip() not in {"", "0", "00"}, (sm, e[3])

    assert sum_total == total, (sum_total, total)
    assert sum_blocks == blocks, (sum_blocks, blocks)
    print(
        f"OK estructura productiva: {total:,} actividades ClaNAE 2004 · "
        f"{blocks:,} manzanas · join {ratio:.1%} · excluidos {excluded:,} usos no económicos"
    )


if __name__ == "__main__":
    main()
