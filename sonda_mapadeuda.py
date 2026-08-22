from __future__ import annotations

import re
from urllib.parse import urljoin

import requests

URLS = ["https://mapadeladeuda.ar/", "https://mapadeladeuda.ar/informe/"]


def contexts(text: str, needle: str, radius: int = 1400) -> None:
    start = 0
    count = 0
    while True:
        pos = text.find(needle, start)
        if pos < 0:
            break
        count += 1
        print(f"CONTEXT {needle!r} #{count} @ {pos}")
        print(text[max(0, pos-radius):pos+radius])
        start = pos + len(needle)
        if count >= 8:
            break


def main() -> None:
    s = requests.Session()
    s.headers.update({"User-Agent": "CEPOES/1.0 (+https://cepoes.org)"})
    assets = []
    for page in URLS:
        r = s.get(page, timeout=30)
        print("PAGE", page, r.status_code, len(r.content))
        r.raise_for_status()
        for m in re.findall(r'(?:src|href)=[\"\']([^\"\']+)[\"\']', r.text, flags=re.I):
            full = urljoin(r.url, m)
            if ".js" in full:
                assets.append(full)
    assets = list(dict.fromkeys(assets))
    print("JS ASSETS", assets)

    for a in assets:
        r = s.get(a, timeout=60)
        print("FETCH", a, r.status_code, len(r.content))
        r.raise_for_status()
        text = r.text

        print("JSON-LIKE STRING LITERALS")
        vals = set()
        for token in re.findall(r'[\"\']([^\"\']{1,500})[\"\']', text):
            low = token.lower()
            if any(k in low for k in (".json", ".geojson", ".csv", "data/", "datos/", "assets/data", "barrio_caba")):
                vals.add(token)
        for v in sorted(vals):
            print(" STRING", v[:1000])

        for needle in ["async function $d", "function $d", "async function Bv", "barrio_caba", "deudores_unicos_total", "monto_mora", "source_geojson", "periodos"]:
            contexts(text, needle)


if __name__ == "__main__":
    main()
