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
    assert m.get("schema") in {1, 2}
    assert m.get("periodo_rus") == "2022-2024"
    total = int(m.get("total", 0))
    blocks = int(m.get("manzanas_actividad", 0))
    ratio = float(m.get("join_cartografia", 0))
    assert total >= 10000, total
    assert blocks >= 1000, blocks
    assert ratio >= .75, ratio
    assert len(m.get("comunas", [])) == 15
    assert len(m.get("sectores", [])) >= 8

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

    assert sum_total == total, (sum_total, total)
    assert sum_blocks == blocks, (sum_blocks, blocks)
    print(f"OK estructura productiva: {total:,} registros · {blocks:,} manzanas · join {ratio:.1%}")


if __name__ == "__main__":
    main()
