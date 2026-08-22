#!/usr/bin/env python3
"""Sonda temporal v2.26: descubre el contrato oficial de búsqueda de expedientes."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://parlamentaria.legislatura.gob.ar/"
PAGE = urljoin(BASE, "pages/ExpedienteBusqueda.aspx")
WSDL = urljoin(BASE, "webservices/Json.asmx?WSDL")
UA = "CEPOES-legislatura-v226-probe/1.0 (+https://github.com/cepoes100b/CEPOES)"


def main() -> None:
    http = requests.Session()
    headers = {"User-Agent": UA, "Referer": PAGE}

    r = http.get(WSDL, headers=headers, timeout=60)
    print("WSDL status:", r.status_code, "bytes:", len(r.content))
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ops = sorted({
        node.attrib.get("name", "")
        for node in root.iter()
        if node.tag.split("}")[-1] == "operation" and node.attrib.get("name")
    })
    exp_ops = [x for x in ops if "exped" in x.lower()]
    print("Operaciones con expediente:")
    for op in exp_ops:
        print("  -", op)

    p = http.get(PAGE, headers=headers, timeout=60)
    print("Página status:", p.status_code, "bytes:", len(p.content))
    p.raise_for_status()
    soup = BeautifulSoup(p.text, "html.parser")
    scripts = [urljoin(PAGE, s.get("src")) for s in soup.find_all("script", src=True)]
    print("Scripts:")
    for src in scripts:
        print("  -", src)

    pattern = re.compile(r".{0,240}(?:Get[A-Za-z0-9_]*Exped[A-Za-z0-9_]*|ExpedienteBusqueda|FechaDesde|FechaHasta).{0,360}", re.I | re.S)
    hits = 0
    for src in scripts:
        try:
            js = http.get(src, headers=headers, timeout=60)
            if js.status_code != 200:
                continue
            text = js.text
            matches = pattern.findall(text)
            if not matches:
                continue
            print("\n###", src)
            for match in matches[:30]:
                print(re.sub(r"\s+", " ", match).strip())
                hits += 1
        except requests.RequestException as exc:
            print("ERROR script", src, type(exc).__name__, exc)
    print("Snippets relevantes:", hits)


if __name__ == "__main__":
    main()
