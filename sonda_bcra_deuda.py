from __future__ import annotations

import html as htmlmod
import re
from urllib.parse import urljoin

import requests

PAGE = "https://www3.bcra.gob.ar/ChequesDeudoresMFT/Deudores"


def direct_url(file_id: str, name: str) -> str:
    return (
        "https://mft.bcra.gob.ar/apilink.aspx?"
        f"&username=api_user&arg01={file_id}&arg05=0/{name}"
        "&arg12=downloaddirect&quiet=true"
    )


def clean_text(source: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", source, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", htmlmod.unescape(text)).strip()


def inspect(label: str, resp: requests.Response) -> None:
    print(label, resp.status_code, resp.url, resp.headers.get("content-type"), len(resp.content))
    print(" TEXT", clean_text(resp.text)[:3000])
    print(" FORMS")
    for form in re.findall(r"<form\b.*?</form>", resp.text, flags=re.I | re.S):
        action = re.search(r"action=[\"']([^\"']*)[\"']", form, flags=re.I)
        method = re.search(r"method=[\"']([^\"']*)[\"']", form, flags=re.I)
        print("  FORM", action.group(1) if action else "", method.group(1) if method else "")
        for inp in re.findall(r"<input\b[^>]*>", form, flags=re.I):
            typ = re.search(r"type=[\"']([^\"']*)[\"']", inp, flags=re.I)
            nam = re.search(r"name=[\"']([^\"']*)[\"']", inp, flags=re.I)
            val = re.search(r"value=[\"']([^\"']*)[\"']", inp, flags=re.I)
            src = re.search(r"src=[\"']([^\"']*)[\"']", inp, flags=re.I)
            print("   INPUT", typ.group(1) if typ else "", nam.group(1) if nam else "", (val.group(1)[:100] if val else ""), (src.group(1) if src else ""))
    print(" SIGNALS")
    for line in resp.text.splitlines():
        low = line.lower()
        if any(k in low for k in ("captcha", "recaptcha", "hcaptcha", "turnstile", "cloudflare", "challenge", "robot", "verification", "verify", "human")):
            print("  ", line.strip()[:1200])


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "CEPOES/1.0 (+https://cepoes.org)"})
    listing = session.get(PAGE, timeout=30)
    listing.raise_for_status()
    source = htmlmod.unescape(listing.text)

    pattern = re.compile(
        r"arg01='\+'(?P<id>\d+)'\+\s*'&arg05=0/'\s*\+\s*'(?P<name>[^']+\.7Z)'",
        flags=re.I,
    )
    found = {m.group("name"): m.group("id") for m in pattern.finditer(source)}
    print("ARCHIVOS PUBLICADOS", found)
    name, fid = next((n, i) for n, i in found.items() if re.search(r"\d{6}DEUDORES\.7Z$", n, re.I))

    first = session.get(direct_url(fid, name), timeout=60, allow_redirects=True)
    first.raise_for_status()
    inspect("STEP1", first)

    m = re.search(r'''href=["']([^"']*human\.aspx[^"']*language=es[^"']*)["']''', first.text, flags=re.I)
    if not m:
        raise SystemExit("No se encontró enlace de idioma español")
    es_url = urljoin(first.url, htmlmod.unescape(m.group(1)))
    print("SPANISH URL", es_url)
    second = session.get(es_url, timeout=60, allow_redirects=True)
    second.raise_for_status()
    inspect("STEP2", second)


if __name__ == "__main__":
    main()
