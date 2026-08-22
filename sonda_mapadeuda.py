from __future__ import annotations

import re
from urllib.parse import urljoin

import requests

URLS = ["https://mapadeladeuda.ar/", "https://mapadeladeuda.ar/informe/"]

PATTERNS = [
    re.compile(r"https?://[^\"'\\)\s]+", re.I),
    re.compile(r"(?:/|https?://)[A-Za-z0-9_./?=&%+-]*(?:api|json|csv|geojson|topojson|data|dataset)[A-Za-z0-9_./?=&%+-]*", re.I),
]


def main() -> None:
    s = requests.Session()
    s.headers.update({"User-Agent": "CEPOES/1.0 (+https://cepoes.org)"})
    all_assets: list[str] = []
    for page in URLS:
        r = s.get(page, timeout=30)
        print("PAGE", page, r.status_code, r.url, len(r.content), r.headers.get("content-type"))
        r.raise_for_status()
        src = r.text
        for attr in ("src", "href"):
            for m in re.findall(rf'{attr}=[\"\']([^\"\']+)[\"\']', src, flags=re.I):
                full = urljoin(r.url, m)
                if any(x in full for x in (".js", "_next", "assets/")):
                    all_assets.append(full)
        print("HTML SIGNALS")
        for pat in PATTERNS:
            for x in sorted(set(pat.findall(src))):
                if "mapadeladeuda" in x.lower() or any(k in x.lower() for k in ("api", "json", "csv", "geojson", "data")):
                    print(" ", x[:1000])

    assets = list(dict.fromkeys(all_assets))
    print("ASSETS", len(assets))
    for a in assets:
        print("ASSET", a)

    for a in assets:
        try:
            r = s.get(a, timeout=45)
            print("FETCH", a, r.status_code, len(r.content), r.headers.get("content-type"))
            if not r.ok or len(r.content) > 15_000_000:
                continue
            text = r.text
            hits = set()
            for pat in PATTERNS:
                hits.update(pat.findall(text))
            for token in re.findall(r'[\"\']([^\"\']{4,300})[\"\']', text):
                low = token.lower()
                if any(k in low for k in ("supabase", "firebase", "api/", "/api", ".json", ".csv", "geojson", "topojson", "periodo", "deudores", "mora", "localidad", "barrio")):
                    hits.add(token)
            for h in sorted(hits):
                low = h.lower()
                if any(k in low for k in ("api", "json", "csv", "geojson", "topojson", "supabase", "firebase", "periodo", "deudores", "mora", "localidad", "barrio")):
                    print(" HIT", h[:1200])
        except Exception as exc:
            print("ERROR", a, repr(exc))


if __name__ == "__main__":
    main()
