#!/usr/bin/env python3
"""Sonda temporal v2.26: descubre contrato y salida del buscador oficial de expedientes."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://parlamentaria.legislatura.gob.ar/"
PAGE = urljoin(BASE, "pages/ExpedienteBusqueda.aspx")
WS = urljoin(BASE, "webservices/Json.asmx/")
WSDL = urljoin(BASE, "webservices/Json.asmx?WSDL")
UA = "CEPOES-legislatura-v226-probe/1.1 (+https://github.com/cepoes100b/CEPOES)"


def node_dict(node: ET.Element) -> dict[str, str]:
    return {c.tag.split("}")[-1]: re.sub(r"\s+", " ", c.text or "").strip() for c in list(node)}


def extract(root: ET.Element, local_name: str) -> list[dict[str, str]]:
    wanted = local_name.lower()
    return [node_dict(n) for n in root.iter() if n.tag.split("}")[-1].lower() == wanted]


def main() -> None:
    http = requests.Session()
    headers = {"User-Agent": UA, "Referer": PAGE, "X-Requested-With": "XMLHttpRequest"}

    r = http.get(WSDL, headers=headers, timeout=60)
    print("WSDL status:", r.status_code, "bytes:", len(r.content))
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ops = sorted({n.attrib.get("name", "") for n in root.iter() if n.tag.split("}")[-1] == "operation" and n.attrib.get("name")})
    print("Operaciones avanzadas:", [x for x in ops if "expedienteavanzada" in x.lower()])

    p = http.get(PAGE, headers=headers, timeout=60)
    p.raise_for_status()
    soup = BeautifulSoup(p.text, "html.parser")
    js_url = next((urljoin(PAGE, s.get("src")) for s in soup.find_all("script", src=True) if "ExpedienteBusqueda.js" in s.get("src", "")), "")
    print("JS buscador:", js_url)
    if js_url:
        js = http.get(js_url, headers=headers, timeout=60)
        print("JS status:", js.status_code, "bytes:", len(js.content))
        m = re.search(r"GetExpedienteAvanzada.{0,1200}", js.text, re.I | re.S)
        if m:
            print("Contrato JS:", re.sub(r"\s+", " ", m.group(0))[:1500])

    payload = {
        "IdProyectoTipo": "",
        "IdAutoresInternos": "",
        "IdUbicacion": "",
        "IdEstado": "",
        "Sumario": "",
        "SumarioExacto": "0",
        "FechaDesde": "08/08/2026",
        "FechaHasta": "22/08/2026",
        "AnioParlamentario": "2026",
        "Limite": "",
    }
    q = http.post(urljoin(WS, "GetExpedienteAvanzada"), headers=headers, data=payload, timeout=90)
    print("Búsqueda status:", q.status_code, "bytes:", len(q.content))
    q.raise_for_status()
    qroot = ET.fromstring(q.content)
    rows = extract(qroot, "expedienteAvanzado")
    print("Expedientes 08/08–22/08:", len(rows))
    if rows:
        print("Campos:", sorted(rows[0].keys()))
        for row in rows[:8]:
            print("MUESTRA:", row)


if __name__ == "__main__":
    main()
