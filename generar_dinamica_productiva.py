#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

OUT = Path("deploy/site-overlay/assets/data/estructura-productiva/dinamica.json")
TIMEOUT = 180
RESOURCES = {
    2024: "af7cb21d-3c26-4227-8271-a898442bf99b",
    2025: "00cab09a-06fa-43d0-b000-e6b2364a3082",
    2026: "1ee0b29d-058b-4b02-941f-59e9136da759",
}


def clean(v: Any) -> str:
    if v is None:
        return ""
    s = re.sub(r"\s+", " ", str(v).strip())
    return "" if s.lower() in {"", "nan", "none", "null", "-"} else s


def key(v: Any) -> str:
    s = str(v or "").strip().lower()
    s = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    return re.sub(r"[^a-z0-9]+", "", s)


def value(row: dict[str, Any], *names: str) -> str:
    d = {key(k): v for k, v in row.items() if k is not None}
    for n in names:
        if key(n) in d:
            s = clean(d[key(n)])
            if s:
                return s
    return ""


def manzana_norm(v: str) -> str:
    s = re.sub(r"\s+", "", clean(v).upper())
    m = re.fullmatch(r"0*(\d+)([A-Z]*)", s)
    return f"{int(m.group(1)):03d}{m.group(2)}" if m else s


def sm_norm(sec: str, man: str) -> str:
    sec = clean(sec)
    man = clean(man)
    if not sec or not man:
        return ""
    m = re.search(r"\d+", sec)
    return f"{int(m.group()):03d}-{manzana_norm(man)}" if m else ""


def rows(raw: bytes):
    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            pass
    if text is None:
        raise RuntimeError("No pude decodificar habilitaciones")
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return
    first = lines[0]
    counts = {d: first.count(d) for d in (",", ";", "\t", "|")}
    delim = max(counts, key=counts.get)
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delim)
    print(f"Campos habilitaciones: {reader.fieldnames}")
    yield from reader


def download(year: int) -> bytes:
    rid = RESOURCES[year]
    url = f"https://data.buenosaires.gob.ar/dataset/habilitaciones-aprobadas/resource/{rid}/download"
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "CEPOES-data/1.0"})
    r.raise_for_status()
    print(f"{year}: {len(r.content)/1024/1024:.1f} MB · {r.headers.get('content-type')}")
    return r.content


def top(c: Counter, n: int = 12):
    return [[k, v] for k, v in c.most_common(n) if k]


def main() -> None:
    blocks: dict[str, dict[str, Any]] = {}
    years = {}
    comuna_year = defaultdict(Counter)
    comuna_rubros = defaultdict(Counter)
    exact = Counter()
    no_exact = Counter()

    for year in sorted(RESOURCES):
        raw = download(year)
        total = 0
        exact_year = 0
        rubros = Counter()
        comunas = Counter()
        for row in rows(raw):
            rubro = value(row, "DescripcionRubro", "rubro", "descripcion_rubro")
            subrubro = value(row, "DescripcionSubRubro", "subrubro", "descripcion_subrubro")
            direccion = value(row, "Calles", "domicilio", "direccion")
            fecha = value(row, "FechaHabilitacion", "fecha_habilitacion", "fecha")
            comuna_s = value(row, "comuna")
            cm = re.search(r"\d+", comuna_s)
            comuna = int(cm.group()) if cm and 1 <= int(cm.group()) <= 15 else 0
            sm = sm_norm(value(row, "Seccion", "seccion"), value(row, "Manzana", "manzana"))

            # No publicamos titulares, CUIT ni teléfonos. La capa muestra sólo
            # información administrativa de la habilitación y su localización.
            if not rubro and not direccion:
                continue
            total += 1
            if rubro:
                rubros[rubro] += 1
            if comuna:
                comunas[comuna] += 1
                comuna_year[comuna][year] += 1
                if rubro:
                    comuna_rubros[comuna][rubro] += 1

            if sm:
                exact_year += 1
                exact[year] += 1
                b = blocks.setdefault(sm, {"t": 0, "y": Counter(), "r": Counter(), "e": []})
                b["t"] += 1
                b["y"][year] += 1
                if rubro:
                    b["r"][rubro] += 1
                # año, fecha, rubro, subrubro, dirección. Sin datos del titular.
                b["e"].append([year, fecha, rubro, subrubro, direccion])
            else:
                no_exact[year] += 1

        if total < 50:
            raise RuntimeError(f"Habilitaciones {year} inesperadamente pequeñas: {total}")
        years[str(year)] = {
            "total": total,
            "manzana_exacta": exact_year,
            "precision_manzana": round(exact_year / total, 5),
            "rubros": top(rubros, 25),
            "comunas": [[c, n] for c, n in sorted(comunas.items())],
            "resource_id": RESOURCES[year],
        }

    compact = {}
    for sm, b in blocks.items():
        compact[sm] = {
            "t": b["t"],
            "y": {str(k): v for k, v in sorted(b["y"].items())},
            "r": top(b["r"], 15),
            "e": b["e"],
        }

    if len(compact) < 500:
        raise RuntimeError(f"Muy pocas manzanas con habilitaciones recientes: {len(compact)}")

    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    out = {
        "schema": 1,
        "generado": generated,
        "unidad": "habilitaciones aprobadas",
        "lectura": "flujo_administrativo",
        "nota": "Las habilitaciones son un flujo de altas administrativas y no equivalen al stock de establecimientos activos. Se publican separadas del RUS estructural. No se incluyen CUIT, titulares ni teléfonos.",
        "anios": years,
        "manzanas": compact,
        "comunas": [
            {
                "comuna": c,
                "anios": {str(y): n for y, n in sorted(comuna_year[c].items())},
                "rubros": top(comuna_rubros[c], 20),
            }
            for c in range(1, 16)
        ],
        "fuente": {
            "nombre": "Habilitaciones Aprobadas · Agencia Gubernamental de Control · Buenos Aires Data",
            "url": "https://data.buenosaires.gob.ar/dataset/habilitaciones-aprobadas",
            "frecuencia": "trimestral",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"OK dinámica: {sum(x['total'] for x in years.values()):,} registros · {len(compact):,} manzanas con precisión exacta")
    print("Precisión por año:", {y: x['precision_manzana'] for y, x in years.items()})


if __name__ == "__main__":
    main()
