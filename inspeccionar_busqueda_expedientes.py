#!/usr/bin/env python3
"""Sonda temporal v2.26: descubre contrato y salida del buscador oficial de expedientes."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from urllib.parse import urljoin

import requests

BASE = "https://parlamentaria.legislatura.gob.ar/"
PAGE = urljoin(BASE, "pages/ExpedienteBusqueda.aspx")
WS = urljoin(BASE, "webservices/Json.asmx/")
WSDL = urljoin(BASE, "webservices/Json.asmx?WSDL")
UA = "CEPOES-legislatura-v226-probe/1.2 (+https://github.com/cepoes100b/CEPOES)"


def local(tag: str) -> str:
    return tag.split("}")[-1]


def node_dict(node: ET.Element) -> dict[str, str]:
    return {local(c.tag): re.sub(r"\s+", " ", c.text or "").strip() for c in list(node)}


def extract(root: ET.Element, local_name: str) -> list[dict[str, str]]:
    wanted = local_name.lower()
    return [node_dict(n) for n in root.iter() if local(n.tag).lower() == wanted]


def operation_params(root: ET.Element, name: str) -> list[tuple[str, str]]:
    for node in root.iter():
        if local(node.tag) == "element" and node.attrib.get("name") == name:
            out = []
            for child in node.iter():
                if child is node or local(child.tag) != "element":
                    continue
                cname = child.attrib.get("name")
                if cname:
                    out.append((cname, child.attrib.get("type", "")))
            return out
    return []


def payload_for(params: list[tuple[str, str]]) -> dict[str, str]:
    out = {}
    for name, typ in params:
        n = name.lower()
        if "limite" in n or "cantidad" in n or "cant" in n:
            out[name] = "100"
        elif "anio" in n or "ano" in n:
            out[name] = "2026"
        elif any(x in typ.lower() for x in ("int", "long", "short", "decimal")):
            out[name] = "0"
        else:
            out[name] = ""
    return out


def probe(http: requests.Session, headers: dict, method: str, payload: dict[str, str]) -> None:
    q = http.post(urljoin(WS, method), headers=headers, data=payload, timeout=90)
    print(f"\n{method} status:", q.status_code, "bytes:", len(q.content), "payload:", payload)
    q.raise_for_status()
    root = ET.fromstring(q.content)
    counts = Counter(local(n.tag) for n in root.iter())
    print("Tags repetidos:", counts.most_common(12))
    candidates = [(tag, count) for tag, count in counts.items() if count > 1 and tag not in {"string"}]
    for tag, count in sorted(candidates, key=lambda x: -x[1])[:6]:
        rows = extract(root, tag)
        if rows and rows[0]:
            print(f"Candidato {tag}: {len(rows)} filas · campos:", sorted(rows[0].keys()))
            for row in rows[:3]:
                print(" MUESTRA:", row)
            break


def main() -> None:
    http = requests.Session()
    headers = {"User-Agent": UA, "Referer": PAGE, "X-Requested-With": "XMLHttpRequest"}
    r = http.get(WSDL, headers=headers, timeout=60)
    print("WSDL status:", r.status_code, "bytes:", len(r.content))
    r.raise_for_status()
    root = ET.fromstring(r.content)

    for method in ("GetExpedienteAvanzada", "GetUltimosExpedientes"):
        params = operation_params(root, method)
        print(method, "params:", params)

    advanced_params = operation_params(root, "GetExpedienteAvanzada")
    advanced_payload = payload_for(advanced_params)
    advanced_payload.update({
        "FechaDesde": "",
        "FechaHasta": "",
        "AnioParlamentario": "2026",
        "Limite": "100",
        "SumarioExacto": "0",
    })
    probe(http, headers, "GetExpedienteAvanzada", advanced_payload)

    last_params = operation_params(root, "GetUltimosExpedientes")
    probe(http, headers, "GetUltimosExpedientes", payload_for(last_params))


if __name__ == "__main__":
    main()
