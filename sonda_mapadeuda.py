from __future__ import annotations

import json
import requests

BASE = "https://datos.mapadeladeuda.ar/"


def get(s: requests.Session, path: str):
    url = BASE + path.lstrip("/")
    r = s.get(url, timeout=60)
    print("GET", path, r.status_code, len(r.content), r.headers.get("content-type"))
    r.raise_for_status()
    return r.json()


def main() -> None:
    s = requests.Session()
    s.headers.update({"User-Agent": "CEPOES/1.0 (+https://cepoes.org)"})
    manifest = get(s, "manifest.json")
    print("MANIFEST")
    print(json.dumps(manifest, ensure_ascii=False, indent=2)[:20000])

    print("PERIODS", [(p.get("id"), p.get("index")) for p in manifest.get("periods", [])])
    print("DEFAULT", manifest.get("defaultPeriod"))
    print("DIMENSIONS", manifest.get("dimensions"))
    print("GEO", manifest.get("geo"))

    period = next((p for p in manifest.get("periods", []) if p.get("id") == "2026-06"), None)
    if not period:
        period = next((p for p in manifest.get("periods", []) if "202606" in str(p.get("id")) or "2026-06" in str(p.get("id"))), None)
    if not period:
        period = next(p for p in manifest.get("periods", []) if p.get("id") == manifest.get("defaultPeriod"))
    print("SELECTED PERIOD", period)

    index = get(s, period["index"])
    print("INDEX KEYS", list(index))
    print("AVAILABLE SLICES", len(index.get("availableSlices", [])))
    caba = []
    for sl in index.get("availableSlices", []):
        if sl.get("level") == "barrio_caba":
            caba.append(sl)
    print("CABA SLICES", len(caba))
    for sl in caba[:200]:
        print("SLICE", json.dumps(sl, ensure_ascii=False, sort_keys=True))

    all_values = {"__ALL__", "all", "ALL", "Todos", "todas", "todos", None, ""}
    candidates = [sl for sl in caba if all(v in all_values for v in (sl.get("filters") or {}).values())]
    if not candidates:
        candidates = caba
    print("CANDIDATES", len(candidates))

    for sl in candidates[:5]:
        path = sl.get("path") or sl.get("file") or sl.get("data") or sl.get("slice") or sl.get("url")
        print("CANDIDATE PATH", path, sl)
        if path:
            data = get(s, path)
            print("DATA KEYS", list(data))
            print("COLUMNS", data.get("columns"))
            print("ALIASES", data.get("aliases"))
            print("KPIS", data.get("kpis"))
            print("ROWS", len(data.get("rows", [])))
            for row in data.get("rows", [])[:60]:
                print("ROW", row)

    lookup_path = (manifest.get("geo") or {}).get("lookup")
    if lookup_path:
        lookup = get(s, lookup_path)
        feats = [x for x in lookup.get("features", []) if x.get("level") == "barrio_caba"]
        print("LOOKUP CABA", len(feats))
        for x in feats[:60]:
            print("GEO", json.dumps(x, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
