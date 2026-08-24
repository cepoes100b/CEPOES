#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# El workflow normaliza el recurso descargable RUS 2017 y reemplaza esta URL
# por un servidor local temporal antes de ejecutar el generador.
RUS_URL = "https://data.buenosaires.gob.ar/es_AR/dataset/relevamiento-usos-suelo/resource/3c7e5f10-577a-44ea-b614-82cc05f842aa/download"
MANZANAS_URL = "https://data.buenosaires.gob.ar/es_AR/dataset/manzanas/resource/78a97854-6930-4d1c-b345-deb43168d88d/download"
OUT = Path("deploy/site-overlay/assets/data/estructura-productiva")
TIMEOUT = 180

# El RUS 2017 clasifica actividad con ClaNAE 2004. Estos rangos siguen las
# secciones/ramas de esa versión del clasificador, no los rangos de ClaNAE 2010.
# Fuente metodológica: INDEC, Clasificador Nacional de Actividades Económicas 2004.
SECTORES = [
    ("A", "Agricultura, ganadería, silvicultura y pesca", [(1, 5)]),
    ("C", "Explotación de minas y canteras", [(10, 14)]),
    ("D", "Industria manufacturera", [(15, 38)]),
    ("E", "Electricidad, gas y agua", [(40, 41)]),
    ("F", "Construcción", [(45, 45)]),
    ("G", "Comercio y reparación", [(50, 52)]),
    ("H", "Hoteles y restaurantes", [(55, 55)]),
    ("I", "Transporte, almacenamiento y comunicaciones", [(60, 64)]),
    ("J", "Intermediación financiera", [(65, 67)]),
    ("K", "Servicios inmobiliarios, empresariales y alquiler", [(70, 74)]),
    ("L", "Administración pública", [(75, 75)]),
    ("X", "Obras sociales", [(77, 77)]),
    ("M", "Enseñanza", [(80, 80)]),
    ("N", "Salud y servicios sociales", [(85, 85)]),
    ("O", "Servicios comunitarios, sociales y personales", [(90, 93)]),
    ("P", "Hogares privados con servicio doméstico", [(95, 95)]),
    ("Q", "Organizaciones extraterritoriales", [(99, 99)]),
]
SECTOR_NAME = {k: n for k, n, _ in SECTORES}
SECTOR_NAME["Z"] = "Otra actividad clasificada"


def d21_number(v: str) -> int | None:
    m = re.search(r"\d+", v or "")
    return int(m.group()) if m else None


def sector_for(d21: str) -> str:
    n = d21_number(d21)
    if n is None:
        return "Z"
    for code, _, ranges in SECTORES:
        if any(a <= n <= b for a, b in ranges):
            return code
    return "Z"


def clean(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() in {"nan", "none", "null", "s/d", "sd", "-"}:
        return ""
    return re.sub(r"\s+", " ", s)


def manzana_norm(v: str) -> str:
    s = re.sub(r"\s+", "", clean(v).upper())
    m = re.fullmatch(r"0*(\d+)([A-Z]*)", s)
    if not m:
        return s
    return f"{int(m.group(1)):03d}{m.group(2)}"


def sm_norm(v: str, seccion: str = "", manzana: str = "") -> str:
    s = clean(v).upper().replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", "", s)
    m = re.fullmatch(r"0*(\d+)-(.+)", s)
    if m:
        return f"{int(m.group(1)):03d}-{manzana_norm(m.group(2))}"
    sec = clean(seccion)
    man = clean(manzana)
    if sec and man and re.fullmatch(r"\d+", sec):
        return f"{int(sec):03d}-{manzana_norm(man)}"
    return s


def header_key(v: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "", str(v or "").strip().lower())


def first_value(row: dict[str, Any], *names: str) -> str:
    lower = {header_key(k): v for k, v in row.items()}
    for name in names:
        key = header_key(name)
        if key in lower:
            val = clean(lower[key])
            if val:
                return val
    return ""


def csv_rows(content: bytes):
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise RuntimeError("No pude decodificar el CSV RUS")

    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        raise RuntimeError("El CSV RUS está vacío")
    first = lines[0].strip()
    if first.lower().startswith("sep=") and len(first) >= 5:
        delimiter = first[4]
        text = "\n".join(lines[1:])
    else:
        counts = {d: first.count(d) for d in (",", ";", "\t", "|")}
        delimiter = max(counts, key=counts.get)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fields = [header_key(x) for x in (reader.fieldnames or [])]
    print(f"RUS: separador {delimiter!r} · {len(fields)} columnas · {fields[:24]}")
    if "d21" not in set(fields):
        raise RuntimeError(f"El RUS normalizado no contiene d21: {reader.fieldnames}")
    yield from reader


def get_bytes(url: str) -> bytes:
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "CEPOES-data/1.0"})
    r.raise_for_status()
    return r.content


def top(counter: Counter, n: int = 6):
    return [[k, v] for k, v in counter.most_common(n) if k]


def dump_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    print("Descargando base RUS normalizada…")
    rus_raw = get_bytes(RUS_URL)
    print(f"RUS: {len(rus_raw)/1024/1024:.1f} MB")
    print("Descargando manzanas oficiales…")
    manz_raw = get_bytes(MANZANAS_URL)
    print(f"Manzanas: {len(manz_raw)/1024/1024:.1f} MB")

    geo = json.loads(manz_raw.decode("utf-8-sig"))
    geometries: dict[str, dict[str, Any]] = {}
    for f in geo.get("features", []):
        props = f.get("properties") or {}
        key = sm_norm(str(props.get("sm", "")))
        geom = f.get("geometry")
        if key and geom:
            geometries[key] = geom
    if len(geometries) < 8000:
        raise RuntimeError(f"Cartografía insuficiente: {len(geometries)} manzanas")

    blocks: dict[str, dict[str, Any]] = {}
    sector_global = Counter()
    ramas_global = Counter()
    d21_global = Counter()
    comuna_total = Counter()
    comuna_sector = defaultdict(Counter)
    barrio_total = Counter()
    rows_total = 0
    rows_non_economic = 0
    skipped = 0

    for row in csv_rows(rus_raw):
        d21 = first_value(row, "d21")
        code2 = d21_number(d21)
        # d21=00/0 y d21 vacío corresponden a usos sin actividad económica
        # clasificada (p.ej. edificios, lotes o locales cerrados). No forman parte
        # del stock productivo que se presenta en este módulo.
        if code2 is None or code2 <= 0:
            rows_non_economic += 1
            continue

        rama = first_value(row, "rama")
        subrama = first_value(row, "subrama")
        ss_rama = first_value(row, "ss_rama")
        d51 = first_value(row, "d51")
        sm = sm_norm(first_value(row, "sm"), first_value(row, "seccion"), first_value(row, "manzana"))
        comuna_s = first_value(row, "comuna")
        cm = re.search(r"\d+", comuna_s)
        comuna = int(cm.group()) if cm else 0
        if not sm or not (1 <= comuna <= 15):
            skipped += 1
            continue

        barrio = first_value(row, "barrio").title()
        sector = sector_for(d21)
        nombre = first_value(row, "nombre")
        calle = first_value(row, "calle").title()
        numero = first_value(row, "numero")
        tipo = first_value(row, "tipo2_16")

        b = blocks.setdefault(sm, {
            "comuna": comuna,
            "barrio": barrio,
            "total": 0,
            "sectores": Counter(),
            "ramas": Counter(),
            "d21": Counter(),
            "establecimientos": [],
        })
        if not b["barrio"] and barrio:
            b["barrio"] = barrio
        b["total"] += 1
        b["sectores"][sector] += 1
        if rama:
            b["ramas"][rama] += 1
            ramas_global[rama] += 1
        b["d21"][d21] += 1
        d21_global[d21] += 1
        # nombre, calle, número, d21, sector, rama, subrama, sub-subrama,
        # tipo general y d51. No se incluyen identificadores personales/fiscales.
        b["establecimientos"].append([
            nombre, calle, numero, d21, sector, rama, subrama, ss_rama, tipo, d51
        ])

        rows_total += 1
        sector_global[sector] += 1
        comuna_total[comuna] += 1
        comuna_sector[comuna][sector] += 1
        if barrio:
            barrio_total[(comuna, barrio)] += 1

    if rows_total < 10000:
        raise RuntimeError(f"RUS económico inesperadamente pequeño: {rows_total}")

    matched = 0
    map_features = []
    comuna_blocks: dict[int, dict[str, Any]] = defaultdict(dict)
    for sm, b in blocks.items():
        geom = geometries.get(sm)
        if not geom:
            continue
        matched += 1
        top_sector = b["sectores"].most_common(1)[0][0]
        top_rama = b["ramas"].most_common(1)[0][0] if b["ramas"] else ""
        map_features.append({
            "type": "Feature",
            "properties": {
                "sm": sm,
                "c": b["comuna"],
                "b": b["barrio"],
                "t": b["total"],
                "s": top_sector,
                "r": top_rama,
                "sc": dict(b["sectores"]),
                "rc": dict(b["ramas"]),
            },
            "geometry": geom,
        })
        comuna_blocks[b["comuna"]][sm] = {
            "b": b["barrio"],
            "t": b["total"],
            "s": dict(b["sectores"]),
            "r": top(b["ramas"], 12),
            "d": top(b["d21"], 25),
            "e": b["establecimientos"],
        }

    ratio = matched / max(1, len(blocks))
    if matched < 1000 or ratio < 0.75:
        raise RuntimeError(f"Join RUS↔manzanas insuficiente: {matched}/{len(blocks)} ({ratio:.1%})")

    OUT.mkdir(parents=True, exist_ok=True)
    # Limpiar sólo los JSON gestionados por el stock. dinamica.json pertenece a
    # otro pipeline y debe sobrevivir a cada regeneración de la base estructural.
    for name in ("manifest.json", "mapa.json"):
        p=OUT/name
        if p.exists(): p.unlink()
    for p in OUT.glob("comuna-*.json"):
        p.unlink()

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    sector_ids=[x[0] for x in SECTORES]+["Z"]
    sectors=[{"id":k,"nombre":SECTOR_NAME[k],"total":sector_global.get(k,0)} for k in sector_ids]
    sectors=[x for x in sectors if x["total"]]
    barrios=[
        {"comuna": c, "barrio": b, "total": n}
        for (c, b), n in sorted(barrio_total.items(), key=lambda x: (x[0][0], x[0][1]))
    ]
    comunas=[
        {"comuna":c,"total":comuna_total.get(c,0),"manzanas":len(comuna_blocks.get(c,{})),"sectores":dict(comuna_sector.get(c,{}))}
        for c in range(1,16)
    ]
    manifest={
        "schema": 2,
        "generado": generated_at,
        "periodo_rus": "2017",
        "base_tipo": "stock_estructural",
        "clanae_version": "2004",
        "unidad": "usos y establecimientos con actividad económica clasificada",
        "total": rows_total,
        "registros_no_economicos_excluidos": rows_non_economic,
        "manzanas_actividad": matched,
        "manzanas_rus": len(blocks),
        "join_cartografia": round(ratio,5),
        "registros_omitidos_sin_clave": skipped,
        "comunas": comunas,
        "barrios": barrios,
        "sectores": sectors,
        "ramas": [[k,v] for k,v in ramas_global.most_common()],
        "clanae_2": [[k,v] for k,v in sorted(d21_global.items(),key=lambda kv:(-kv[1],kv[0]))],
        "fuentes": {
            "rus": {"nombre":"Relevamiento de Usos del Suelo 2017 · Buenos Aires Data","url":"https://data.buenosaires.gob.ar/dataset/relevamiento-usos-suelo/resource/juqdkmgo-1807-resource"},
            "manzanas": {"nombre":"Manzanas Catastrales · Buenos Aires Data","url":MANZANAS_URL},
            "clanae": {"nombre":"Clasificador Nacional de Actividades Económicas 2004 · INDEC","url":"https://www.indec.gob.ar/indec/web/Institucional-Indec-Clasificadores"},
        },
        "nota": "Base estructural RUS 2017. Se incluyen sólo usos con d21 ClaNAE mayor que cero; edificios, lotes, locales cerrados y otros usos sin actividad económica clasificada quedan fuera. Las habilitaciones recientes se publican como flujo separado.",
        "hash_fuentes": {"rus_sha256":hashlib.sha256(rus_raw).hexdigest(),"manzanas_sha256":hashlib.sha256(manz_raw).hexdigest()},
    }
    dump_json(OUT/"manifest.json",manifest)
    dump_json(OUT/"mapa.json",{"type":"FeatureCollection","features":map_features})
    for c in range(1,16):
        dump_json(OUT/f"comuna-{c:02d}.json",{"comuna":c,"total":comuna_total.get(c,0),"manzanas":comuna_blocks.get(c,{})})

    print(f"OK: {rows_total:,} registros económicos · {rows_non_economic:,} usos no económicos excluidos · {matched:,} manzanas · join {ratio:.1%}")
    print(f"Salida: {OUT}")


if __name__ == "__main__":
    main()
