#!/usr/bin/env python3
"""Sonda temporal del JavaScript oficial de sesión/votaciones."""
from __future__ import annotations

import json
import re
import requests

URL = "https://parlamentaria.legislatura.gob.ar/pages/sesion_votaciones.js"
UA = "cepoes-legislatura-sesiones/2.24 (+https://github.com/cepoes100b/CEPOES)"
NEEDLES = (
    "webservices/Json.asmx",
    "data-presentes",
    "data-votaciones",
    "data-sanciones",
    "AsuntosVotados",
    "SesionDetalleVotaciones",
    "getSanciones",
    "GetSesion",
    "GetVot",
    "GetAsuntos",
)


def clean(x: str) -> str:
    return re.sub(r"\s+", " ", x).strip()


def snippets(text: str, needle: str, radius: int = 3000) -> list[str]:
    low, target = text.casefold(), needle.casefold()
    out, start = [], 0
    while len(out) < 12:
        p = low.find(target, start)
        if p < 0:
            break
        out.append(clean(text[max(0,p-radius):min(len(text),p+len(needle)+radius)]))
        start = p + len(target)
    return out


def main() -> None:
    r = requests.get(URL, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    text = r.text
    endpoints = sorted(set(re.findall(r"(?:\.\./)?webservices/Json\.asmx/[A-Za-z0-9_]+", text)))
    matches = {n: snippets(text, n) for n in NEEDLES if n.casefold() in text.casefold()}
    print("=== JS VOTACIONES v2.24 ===")
    print(json.dumps({
        "url": URL,
        "status": r.status_code,
        "bytes": len(r.content),
        "endpoints": endpoints,
        "coincidencias": matches,
    }, ensure_ascii=False, indent=2))
    print("=== FIN JS VOTACIONES ===")


if __name__ == "__main__":
    main()
