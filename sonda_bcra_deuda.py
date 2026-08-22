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

    targets = [(name, fid) for name, fid in found.items() if re.search(r"\d{6}DEUDORES\.7Z$", name, re.I)]
    if not targets:
        raise SystemExit("No se encontró DEUDORES")

    name, fid = targets[0]
    url = direct_url(fid, name)
    resp = session.get(url, timeout=60, allow_redirects=True)
    print("RESPONSE", resp.status_code, resp.url, resp.headers.get("content-type"), len(resp.content))
    resp.raise_for_status()

    if "human.aspx" not in resp.url.lower():
        raise SystemExit("El control anti-bot esperado no apareció")

    human = htmlmod.unescape(resp.text)
    print("HUMAN TITLE", re.findall(r"<title[^>]*>(.*?)</title>", human, flags=re.I | re.S))
    print("FORMS")
    for form in re.findall(r"<form\b.*?</form>", human, flags=re.I | re.S):
        action = re.search(r"action=[\"']([^\"']*)[\"']", form, flags=re.I)
        method = re.search(r"method=[\"']([^\"']*)[\"']", form, flags=re.I)
        print(" FORM", "action=", action.group(1) if action else "", "method=", method.group(1) if method else "")
        for inp in re.findall(r"<input\b[^>]*>", form, flags=re.I):
            typ = re.search(r"type=[\"']([^\"']*)[\"']", inp, flags=re.I)
            nam = re.search(r"name=[\"']([^\"']*)[\"']", inp, flags=re.I)
            val = re.search(r"value=[\"']([^\"']*)[\"']", inp, flags=re.I)
            print("  INPUT", "type=", typ.group(1) if typ else "", "name=", nam.group(1) if nam else "", "value=", (val.group(1)[:120] if val else ""))

    print("SCRIPTS / CAPTCHA SIGNALS")
    for line in human.splitlines():
        low = line.lower()
        if any(token in low for token in ("captcha", "recaptcha", "hcaptcha", "turnstile", "cloudflare", "human", "verify", "challenge", "robot")):
            print(line.strip()[:1000])

    print("PAGE TEXT")
    text = re.sub(r"<script\b.*?</script>", " ", human, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    print(text[:2500])


if __name__ == "__main__":
    main()
