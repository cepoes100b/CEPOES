#!/usr/bin/env python3
"""Inspección no destructiva del buscador oficial de sesiones del SLP.

Objetivo de v2.24: descubrir, sin adivinar IDs ni parámetros ASP.NET, los
controles reales que implementan la búsqueda de sesiones en
ExpedienteBusqueda.aspx. Este script NO publica datos ni envía formularios:
solo hace GET a la fuente oficial y muestra una sonda estructural en stdout.
"""

from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = "https://parlamentaria.legislatura.gob.ar/pages/ExpedienteBusqueda.aspx"
UA = "cepoes-legislatura-sesiones/2.24 (+https://github.com/cepoes100b/CEPOES)"
KEYWORDS = (
    "sesion",
    "sesión",
    "labor",
    "taquig",
    "asuntos considerados",
    "informacion",
    "información",
    "presente",
    "sanciones de la sesion",
    "sanciones de la sesión",
)


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def relevant(text: str) -> bool:
    low = text.casefold()
    return any(k.casefold() in low for k in KEYWORDS)


def context_text(tag) -> str:
    """Texto cercano al control, limitado para no volcar toda la página."""
    node = tag
    pieces: list[str] = []
    for _ in range(4):
        if node is None:
            break
        txt = clean(node.get_text(" ", strip=True)) if hasattr(node, "get_text") else ""
        if txt and txt not in pieces:
            pieces.append(txt)
        if relevant(" ".join(pieces)):
            break
        node = getattr(node, "parent", None)
    return clean(" | ".join(pieces))[:500]


def control_record(tag) -> dict:
    attrs = tag.attrs
    value = attrs.get("value", "")
    if isinstance(value, list):
        value = " ".join(value)
    rec = {
        "tag": tag.name,
        "type": clean(attrs.get("type", "")),
        "id": clean(attrs.get("id", "")),
        "name": clean(attrs.get("name", "")),
        "value": clean(str(value)),
        "contexto": context_text(tag),
    }
    if tag.name == "select":
        rec["opciones"] = [
            {
                "value": clean(opt.get("value", "")),
                "text": clean(opt.get_text(" ", strip=True)),
            }
            for opt in tag.find_all("option")[:30]
        ]
    return rec


def main() -> None:
    session = requests.Session()
    r = session.get(URL, headers={"User-Agent": UA}, timeout=45)
    r.raise_for_status()
    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    forms = []
    for idx, form in enumerate(soup.find_all("form"), start=1):
        forms.append(
            {
                "n": idx,
                "id": clean(form.get("id", "")),
                "name": clean(form.get("name", "")),
                "method": clean(form.get("method", "GET")).upper(),
                "action": urljoin(URL, clean(form.get("action", "")) or URL),
            }
        )

    controls = [control_record(t) for t in soup.find_all(["input", "button", "select", "textarea"])]
    candidates = []
    for rec in controls:
        searchable = " ".join(
            str(rec.get(k, "")) for k in ("id", "name", "value", "contexto")
        )
        if relevant(searchable):
            candidates.append(rec)

    scripts = []
    for script in soup.find_all("script"):
        text = script.string or script.get_text("\n", strip=False) or ""
        for raw_line in text.splitlines():
            line = clean(raw_line)
            if line and relevant(line):
                scripts.append(line[:1000])
    scripts = list(dict.fromkeys(scripts))[:120]

    links = []
    for a in soup.find_all("a", href=True):
        label = clean(a.get_text(" ", strip=True))
        href = urljoin(URL, a.get("href"))
        if relevant(f"{label} {href}"):
            links.append({"texto": label, "href": href})
    links = list({json.dumps(x, ensure_ascii=False, sort_keys=True): x for x in links}.values())[:80]

    result = {
        "fuente": URL,
        "status": r.status_code,
        "content_type": r.headers.get("Content-Type", ""),
        "bytes": len(r.content),
        "sha256_html": hashlib.sha256(r.content).hexdigest(),
        "titulo": clean(soup.title.get_text(" ", strip=True)) if soup.title else "",
        "formularios": forms,
        "controles_totales": len(controls),
        "controles_candidatos_sesiones": candidates,
        "lineas_script_candidatas": scripts,
        "links_candidatos": links,
    }

    print("=== SONDA SLP SESIONES v2.24 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=== FIN SONDA ===")


if __name__ == "__main__":
    main()
