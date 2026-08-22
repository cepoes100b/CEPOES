"""Descarga las fuentes oficiales más recientes de presupuesto de CABA.

Selecciona automáticamente el último Presupuesto Ejecutado disponible en CSV y el
Presupuesto Sancionado del mismo ejercicio desde BA Data. Los CSV quedan como
archivos de trabajo y no se versionan; sólo se publican el resumen procesado y
sus metadatos de fuente.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent
WORK = BASE / "badata" / "presupuesto"
STATE = BASE / "estado_presupuesto.json"
API = "https://data.buenosaires.gob.ar/api/3/action/package_show"
BASE_URL = "https://data.buenosaires.gob.ar/"
TIMEOUT = 90

QUARTERS = {
    "primer trimestre": 1,
    "primero trimestre": 1,
    "1er trimestre": 1,
    "segundo trimestre": 2,
    "2do trimestre": 2,
    "tercer trimestre": 3,
    "3er trimestre": 3,
    "cuarto trimestre": 4,
    "4to trimestre": 4,
}


def package_show(dataset: str) -> dict:
    r = requests.get(API, params={"id": dataset}, timeout=TIMEOUT)
    r.raise_for_status()
    payload = r.json()
    if not payload.get("success"):
        raise RuntimeError(f"BA Data no devolvió el dataset {dataset}")
    return payload["result"]


def is_csv(resource: dict) -> bool:
    fmt = str(resource.get("format") or "").lower()
    mimetype = str(resource.get("mimetype") or "").lower()
    name = str(resource.get("name") or "").lower()
    return fmt == "csv" or "csv" in mimetype or "(csv)" in name


def parse_exec_name(name: str) -> tuple[int, int] | None:
    low = name.lower()
    m = re.search(r"\b(20\d{2})\b", low)
    if not m:
        return None
    year = int(m.group(1))
    quarter = None
    for label, q in QUARTERS.items():
        if label in low:
            quarter = q
            break
    if quarter is None:
        return None
    return year, quarter


def choose_executed(pkg: dict) -> tuple[dict, int, int]:
    candidates = []
    for r in pkg.get("resources") or []:
        name = str(r.get("name") or "")
        if not is_csv(r) or "presupuesto ejecutado" not in name.lower():
            continue
        parsed = parse_exec_name(name)
        if parsed:
            candidates.append((parsed[0], parsed[1], r))
    if not candidates:
        raise RuntimeError("No se encontró Presupuesto Ejecutado trimestral en CSV")
    year, quarter, resource = max(candidates, key=lambda x: (x[0], x[1]))
    return resource, year, quarter


def choose_sanctioned(pkg: dict, year: int) -> dict:
    candidates = []
    for r in pkg.get("resources") or []:
        name = str(r.get("name") or "")
        if not is_csv(r):
            continue
        if str(year) in name and "presupuesto sancionado" in name.lower():
            candidates.append(r)
    if not candidates:
        raise RuntimeError(f"No se encontró Presupuesto Sancionado {year} en CSV")
    return max(candidates, key=lambda r: str(r.get("last_modified") or r.get("metadata_modified") or ""))


def resource_url(resource: dict) -> str:
    url = str(resource.get("url") or "").strip()
    if not url:
        rid = resource.get("id")
        if not rid:
            raise RuntimeError("Recurso sin URL ni ID")
        url = f"dataset/recurso/resource/{rid}/download"
    return urljoin(BASE_URL, url)


def download(resource: dict, target: Path) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    url = resource_url(resource)
    with requests.get(url, timeout=TIMEOUT, stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        with target.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
    if target.stat().st_size < 1000:
        raise RuntimeError(f"Descarga sospechosamente pequeña: {target}")
    return target.stat().st_size


def meta(resource: dict) -> dict:
    return {
        "id": resource.get("id"),
        "name": resource.get("name"),
        "url": resource_url(resource),
        "last_modified": resource.get("last_modified") or resource.get("metadata_modified"),
        "format": resource.get("format") or resource.get("mimetype"),
    }


def main() -> int:
    executed_pkg = package_show("presupuesto-ejecutado")
    sanctioned_pkg = package_show("presupuesto-sancionado")
    executed, year, quarter = choose_executed(executed_pkg)
    sanctioned = choose_sanctioned(sanctioned_pkg, year)

    exec_path = WORK / "ejecutado.csv"
    sanc_path = WORK / "sancionado.csv"
    exec_size = download(executed, exec_path)
    sanc_size = download(sanctioned, sanc_path)

    state = {
        "version": 1,
        "descargado": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ejercicio": year,
        "trimestre": quarter,
        "fuente": "BA Data · Ministerio de Hacienda y Finanzas GCBA",
        "dataset_ejecutado": {
            "url": "https://data.buenosaires.gob.ar/dataset/presupuesto-ejecutado",
            "updated": executed_pkg.get("metadata_modified"),
            "resource": meta(executed),
            "bytes": exec_size,
        },
        "dataset_sancionado": {
            "url": "https://data.buenosaires.gob.ar/dataset/presupuesto-sancionado",
            "updated": sanctioned_pkg.get("metadata_modified"),
            "resource": meta(sanctioned),
            "bytes": sanc_size,
        },
    }
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Presupuesto · ejercicio {year} · T{quarter}")
    print(f"  ejecutado: {executed.get('name')} · {exec_size/1024/1024:.1f} MB")
    print(f"  sancionado: {sanctioned.get('name')} · {sanc_size/1024/1024:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
