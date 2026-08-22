from __future__ import annotations

import re
from urllib.parse import urljoin

import requests

PAGES = [
    "https://www3.bcra.gob.ar/ChequesDeudoresMFT/Deudores",
    "https://www5.bcra.gob.ar/ChequesyDeudores/Deudores",
]


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "CEPOES/1.0 (+https://cepoes.org)"})

    html = None
    base = None
    for url in PAGES:
        try:
            r = session.get(url, timeout=30)
            print(f"PAGE {url} -> {r.status_code} {len(r.content)} bytes")
            if r.ok:
                html = r.text
                base = r.url
                break
        except Exception as exc:
            print(f"PAGE ERROR {url}: {exc}")

    if not html or not base:
        raise SystemExit("No se pudo abrir la página pública de archivos deudores")

    hrefs = re.findall(r'href=[\"\']([^\"\']+)[\"\']', html, flags=re.I)
    links = []
    for href in hrefs:
        full = urljoin(base, href)
        if re.search(r"(?:DEUDORES|PADRON|24DSF|1DSF).*\.7z(?:\?|$)", full, flags=re.I):
            links.append(full)

    # También buscar URLs o nombres embebidos en JS/HTML.
    for name in re.findall(r"[A-Za-z0-9_./?=&%-]*(?:DEUDORES|PADRON|24DSF|1DSF)[A-Za-z0-9_./?=&%-]*\.7z", html, flags=re.I):
        links.append(urljoin(base, name))

    links = list(dict.fromkeys(links))
    print(f"ARCHIVOS ENCONTRADOS {len(links)}")
    for link in links:
        print("LINK", link)
        try:
            h = session.head(link, timeout=30, allow_redirects=True)
            print(
                "  HEAD",
                h.status_code,
                "type=", h.headers.get("content-type"),
                "length=", h.headers.get("content-length"),
                "final=", h.url,
            )
        except Exception as exc:
            print("  HEAD ERROR", exc)

    deudores = [x for x in links if re.search(r"\d{6}DEUDORES\.7z", x, flags=re.I)]
    padrones = [x for x in links if re.search(r"\d{8}PADRON\.7z", x, flags=re.I)]
    if not deudores:
        print("HTML SNIPPET DEUDORES")
        m = re.search(r".{0,500}DEUDORES.{0,500}", html, flags=re.I | re.S)
        print(m.group(0) if m else "sin coincidencia")
    if not padrones:
        print("HTML SNIPPET PADRON")
        m = re.search(r".{0,500}PADRON.{0,500}", html, flags=re.I | re.S)
        print(m.group(0) if m else "sin coincidencia")

    if not deudores or not padrones:
        raise SystemExit("No se resolvieron links directos de DEUDORES y PADRON")


if __name__ == "__main__":
    main()
