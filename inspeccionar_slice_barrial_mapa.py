#!/usr/bin/env python3
"""Inspección estructural del slice barrial público de Mapa de la Deuda.

No procesa microdatos: descarga únicamente dos JSON públicos y conserva una
copia temporal del slice agregado para poder documentar su contrato real.
La salida sirve para ajustar el parser contra la estructura vigente, sin
inferir ni fabricar correspondencias territoriales.
"""
from __future__ import annotations

import json
from pathlib import Path
import requests

DATA = "https://datos.mapadeladeuda.ar/"
PERIOD = "2026-06"
SLICE_URL = f"{DATA}periods/{PERIOD}/slices/barrio_caba/02/default.json"
LOOKUP_URL = f"{DATA}geo/lookup.json"
OUT = Path("estructura_slice_barrial_mapa.json")


def summarize(node, depth=0, max_depth=5):
    if depth > max_depth:
        return {"type": type(node).__name__}
    if isinstance(node, dict):
        items = {}
        for k, v in list(node.items())[:100]:
            items[str(k)] = summarize(v, depth + 1, max_depth)
        return {"type": "dict", "len": len(node), "items": items}
    if isinstance(node, list):
        sample = [summarize(v, depth + 1, max_depth) for v in node[:5]]
        return {"type": "list", "len": len(node), "sample": sample}
    if isinstance(node, str):
        return {"type": "str", "sample": node[:120]}
    if isinstance(node, (int, float, bool)) or node is None:
        return {"type": type(node).__name__, "sample": node}
    return {"type": type(node).__name__}


def candidates(node, path="$", depth=0, out=None):
    if out is None:
        out = []
    if depth > 8:
        return out
    if isinstance(node, list):
        if 40 <= len(node) <= 60:
            out.append({
                "path": path,
                "kind": "list",
                "len": len(node),
                "sample": node[:3],
            })
        for i, v in enumerate(node[:100]):
            if isinstance(v, (dict, list)):
                candidates(v, f"{path}[{i}]", depth + 1, out)
    elif isinstance(node, dict):
        if 40 <= len(node) <= 60:
            out.append({
                "path": path,
                "kind": "dict",
                "len": len(node),
                "keys": list(node.keys())[:60],
                "sample_values": list(node.values())[:3],
            })
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                candidates(v, f"{path}.{k}", depth + 1, out)
    return out


def main():
    s = requests.Session()
    s.headers.update({"User-Agent": "CEPOES-public-slice-inspector/1.1"})
    r = s.get(SLICE_URL, timeout=(20, 90)); r.raise_for_status()
    slice_obj = r.json()
    lr = s.get(LOOKUP_URL, timeout=(20, 90)); lr.raise_for_status()
    lookup_obj = lr.json()

    payload = {
        "schema": "cepoes-mapadeladeuda-slice-structure-v1",
        "period": PERIOD,
        "slice_url": SLICE_URL,
        "lookup_url": LOOKUP_URL,
        "slice_bytes": len(r.content),
        "slice_structure": summarize(slice_obj),
        "candidates_40_60": candidates(slice_obj),
        "slice_publico_agregado": slice_obj,
        "lookup_structure": summarize(lookup_obj, max_depth=3),
        "nota": "El slice es un agregado público; no contiene registros individuales.",
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "slice_bytes": payload["slice_bytes"],
        "top_type": type(slice_obj).__name__,
        "top_keys": list(slice_obj.keys()) if isinstance(slice_obj, dict) else None,
        "candidates_40_60": [
            {"path": x["path"], "kind": x["kind"], "len": x["len"]}
            for x in payload["candidates_40_60"]
        ],
    }, ensure_ascii=False, indent=2))
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
