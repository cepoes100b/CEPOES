#!/usr/bin/env python3
"""Inspección no destructiva del buscador oficial de sesiones del SLP.

Objetivo de v2.24: descubrir, sin adivinar IDs, endpoints ni payloads, los
controles y JavaScript reales que implementan la búsqueda de sesiones en
ExpedienteBusqueda.aspx. Este script NO publica datos ni envía formularios:
solo hace GET a recursos oficiales y muestra una sonda estructural en stdout.
"""

from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urljoin, urlparse

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
NEEDLES = (
    "advanced-search-sesiones",
    "txtFechaSesionDesde",
    "txtFechaSesionHasta",
    "sesiones-avanzado",
)
ALLOWED_HOST_SUFFIXES = ("legislatura.gob.ar",)


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def relevant(text: str) -> bool:
    low = text.casefold()
    return any(k.casefold() in low for k in KEYWORDS) or any(n.casefold() in low for n in NEEDLES)


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


def allowed_official(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_HOST_SUFFIXES)


def snippets(text: str, needle: str, radius: int = 850) -> list[str]:
    found: list[str] = []
    low = text.casefold()
    target = needle.casefold()
    start = 0
    while len(found) < 8:
        pos = low.find(target, start)
        if pos < 0:
            break
        a = max(0, pos - radius)
        b = min(len(text), pos + len(needle) + radius)
        found.append(clean(text[a:b]))
        start = pos + len(target)
    return found


def inspect_script(session: requests.Session, src: str) -> dict:
    rec: dict = {"src": src, "status": None, "bytes": 0, "coincidencias": {}}
    if not allowed_official(src):
        rec["omitido"] = "host no oficial"
        return rec
    try:
        r = session.get(src, headers={"User-Agent": UA}, timeout=45)
        rec["status"] = r.status_code
        rec["bytes"] = len(r.content)
        if r.ok:
            text = r.text
            for needle in NEEDLES:
                hits = snippets(text, needle)
                if hits:
                    rec["coincidencias"][needle] = hits
            # También capturamos líneas que nombren sesiones/Labor si este JS
            # ya resultó vinculado a alguno de los controles objetivo.
            if rec["coincidencias"]:
                extra = []
                for raw_line in text.splitlines():
                    line = clean(raw_line)
                    if line and relevant(line):
                        extra.append(line[:1800])
                rec["lineas_relevantes"] = list(dict.fromkeys(extra))[:120]
    except requests.RequestException as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"
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
        searchable = " ".join(str(rec.get(k, "")) for k in ("id", "name", "value", "contexto"))
        if relevant(searchable):
            candidates.append(rec)

    inline_scripts = []
    script_sources = []
    for script in soup.find_all("script"):
        src = clean(script.get("src", ""))
        if src:
            script_sources.append(urljoin(URL, src))
            continue
        text = script.string or script.get_text("\n", strip=False) or ""
        for raw_line in text.splitlines():
            line = clean(raw_line)
            if line and relevant(line):
                inline_scripts.append(line[:1800])
    inline_scripts = list(dict.fromkeys(inline_scripts))[:160]
    script_sources = list(dict.fromkeys(script_sources))

    inspected_scripts = [inspect_script(session, src) for src in script_sources]
    inspected_scripts = [x for x in inspected_scripts if x.get("coincidencias") or x.get("error")]

    inline_snippets = {}
    for needle in NEEDLES:
        hits = snippets(html, needle)
        if hits:
            inline_snippets[needle] = hits

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
        "script_src_totales": script_sources,
        "lineas_script_inline_candidatas": inline_scripts,
        "snippets_html_controles": inline_snippets,
        "scripts_externos_con_coincidencias": inspected_scripts,
        "links_candidatos": links,
    }

    print("=== SONDA SLP SESIONES v2.24 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=== FIN SONDA ===")


if __name__ == "__main__":
    main()
