#!/usr/bin/env python3
"""Sonda temporal de la respuesta oficial de sesiones y página de votaciones.

Sólo consulta fuentes públicas oficiales. Se eliminará o dejará manual una vez
fijado el colector estable de v2.24.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

BASE = "https://parlamentaria.legislatura.gob.ar/"
ENDPOINT = urljoin(BASE, "webservices/Json.asmx/GetSesionesAvanzado")
UA = "cepoes-legislatura-sesiones/2.24 (+https://github.com/cepoes100b/CEPOES)"


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def node_dict(node: ET.Element) -> dict[str, str]:
    return {child.tag.split("}")[-1]: clean(child.text) for child in list(node)}


def table_summaries(soup: BeautifulSoup) -> list[dict]:
    out = []
    for i, table in enumerate(soup.find_all("table"), start=1):
        headers = [clean(x.get_text(" ", strip=True)) for x in table.find_all("th")]
        rows = table.find_all("tr")
        if headers or len(rows) > 1:
            out.append({
                "n": i,
                "id": clean(table.get("id", "")),
                "class": " ".join(table.get("class", [])),
                "headers": headers[:30],
                "filas": max(0, len(rows) - (1 if headers else 0)),
                "muestra_texto": clean(table.get_text(" ", strip=True))[:1200],
            })
    return out[:40]


def main() -> None:
    now = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    desde = f"01/01/{now.year}"
    hasta = now.strftime("%d/%m/%Y")

    s = requests.Session()
    headers = {
        "User-Agent": UA,
        "Referer": urljoin(BASE, "pages/ExpedienteBusqueda.aspx#sesiones-avanzado"),
        "X-Requested-With": "XMLHttpRequest",
    }
    r = s.post(ENDPOINT, headers=headers, data={"FechaDesde": desde, "FechaHasta": hasta}, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    nodes = [n for n in root.iter() if n.tag.split("}")[-1].lower() == "sesiones"]
    rows = [node_dict(n) for n in nodes]

    all_fields = sorted({k for row in rows for k in row})
    sample = []
    if rows:
        sample.extend(rows[:2])
        if len(rows) > 2:
            sample.extend(rows[-2:])

    # Preferimos la sesión más reciente con id y documento de Labor, que es
    # la señal que la propia UI usa para indicar una sesión realizada.
    realized = [x for x in rows if x.get("id_sesion_lp") and x.get("labor_documento") not in ("", "0")]
    chosen = realized[-1] if realized else (rows[-1] if rows else {})
    id_sesion = chosen.get("id_sesion_lp", "")

    vote_probe = {}
    if id_sesion:
        vote_url = urljoin(BASE, f"pages/sesion_votaciones.aspx?IdSesion={id_sesion}")
        vr = s.get(vote_url, headers={"User-Agent": UA, "Referer": r.url}, timeout=60)
        vote_probe = {
            "url": vote_url,
            "status": vr.status_code,
            "content_type": vr.headers.get("Content-Type", ""),
            "bytes": len(vr.content),
        }
        if vr.ok:
            soup = BeautifulSoup(vr.text, "html.parser")
            vote_probe.update({
                "titulo": clean(soup.title.get_text(" ", strip=True)) if soup.title else "",
                "tablas": table_summaries(soup),
                "scripts": [urljoin(vote_url, x.get("src")) for x in soup.find_all("script", src=True)],
                "links_relevantes": [
                    {"texto": clean(a.get_text(" ", strip=True)), "href": urljoin(vote_url, a.get("href"))}
                    for a in soup.find_all("a", href=True)
                    if any(k in clean(a.get_text(" ", strip=True)).casefold() for k in ("voto", "sesion", "sancion", "asunto", "presente", "bloque"))
                ][:80],
                "ids_relevantes": [
                    t.get("id") for t in soup.find_all(id=True)
                    if any(k in str(t.get("id", "")).casefold() for k in ("vot", "ses", "asunt", "sanc", "present", "bloq"))
                ][:120],
            })

    result = {
        "endpoint": ENDPOINT,
        "periodo": {"desde": desde, "hasta": hasta},
        "status": r.status_code,
        "content_type": r.headers.get("Content-Type", ""),
        "bytes": len(r.content),
        "cantidad_sesiones": len(rows),
        "campos_detectados": all_fields,
        "muestra_sesiones": sample,
        "sesion_elegida_para_votaciones": chosen,
        "sonda_votaciones": vote_probe,
    }
    print("=== DATOS SLP SESIONES v2.24 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=== FIN DATOS ===")


if __name__ == "__main__":
    main()
