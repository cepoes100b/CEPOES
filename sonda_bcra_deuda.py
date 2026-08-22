from __future__ import annotations

import html as htmlmod
import re
import requests

PAGE = "https://www3.bcra.gob.ar/ChequesDeudoresMFT/Deudores"


def direct_url(file_id: str, name: str) -> str:
    return (
        "https://mft.bcra.gob.ar/apilink.aspx?"
        f"&username=api_user&arg01={file_id}&arg05=0/{name}"
        "&arg12=downloaddirect&quiet=true"
    )


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "CEPOES/1.0 (+https://cepoes.org)"})
    r = session.get(PAGE, timeout=30)
    r.raise_for_status()
    source = htmlmod.unescape(r.text)

    pattern = re.compile(
        r"arg01='\+'(?P<id>\d+)'\+\s*'&arg05=0/'\s*\+\s*'(?P<name>[^']+\.7Z)'",
        flags=re.I,
    )
    found = {m.group("name"): m.group("id") for m in pattern.finditer(source)}
    print("ARCHIVOS PUBLICADOS", found)

    targets = []
    for name, fid in found.items():
        if re.search(r"\d{6}DEUDORES\.7Z$", name, re.I) or re.search(r"\d{8}PADRON\.7Z$", name, re.I):
            targets.append((name, fid))

    if len(targets) != 2:
        raise SystemExit(f"Se esperaban DEUDORES + PADRON; obtenidos: {targets}")

    for name, fid in targets:
        url = direct_url(fid, name)
        print("TEST", name, url)
        with session.get(url, timeout=60, stream=True, allow_redirects=True) as resp:
            print(
                " RESPONSE",
                resp.status_code,
                "type=", resp.headers.get("content-type"),
                "length=", resp.headers.get("content-length"),
                "disposition=", resp.headers.get("content-disposition"),
                "final=", resp.url,
            )
            resp.raise_for_status()
            chunk = next(resp.iter_content(chunk_size=128), b"")
            print(" FIRST_BYTES", chunk[:32].hex(), "read=", len(chunk))
            if not chunk:
                raise SystemExit(f"Descarga vacía: {name}")


if __name__ == "__main__":
    main()
