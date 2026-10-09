#!/usr/bin/env python3
"""Explicitly download the two public geometry snapshots; verify before replacing."""
import argparse
import gzip
import hashlib
import json
import urllib.request
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sources", type=Path, default=Path(__file__).with_name("sources.json"))
    p.add_argument("--output", type=Path, default=Path(__file__).with_name("raw"))
    args = p.parse_args()
    meta = json.loads(args.sources.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    for sid, filename, hashkey in [("ba-educacion-geometria", "educacion.geojson.gz", "education_geometry_sha256"),
                                    ("ba-verdes-geometria", "verdes.geojson.gz", "green_geometry_sha256")]:
        source = next(s for s in meta["sources"] if s["id"] == sid)
        request = urllib.request.Request(source["resource_url"], headers={"User-Agent": "CEPOES-map-research/1.0 (+https://cepoes.org)"})
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read(64 * 1024 * 1024 + 1)
        if len(data) > 64 * 1024 * 1024:
            raise ValueError("Official resource exceeds the reviewed size limit; previous snapshot preserved")
        if hashlib.sha256(data).hexdigest() != meta[hashkey]:
            raise ValueError(f"{sid} changed; review the new official snapshot before updating hashes. Previous snapshot preserved")
        payload = json.loads(data)
        if payload.get("type") != "FeatureCollection" or not payload.get("features"):
            raise ValueError(f"Invalid official GeoJSON for {sid}")
        target = args.output / filename
        tmp = target.with_suffix(".tmp")
        tmp.write_bytes(gzip.compress(data, mtime=0))
        tmp.replace(target)
        print(f"Verified {sid}: {len(payload['features'])} features, {len(data)} source bytes")


if __name__ == "__main__":
    main()
