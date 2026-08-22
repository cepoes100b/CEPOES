"""Construye una serie trimestral liviana del Presupuesto Ejecutado de CABA.

Descubre los CSV trimestrales oficiales en BA Data, desde 2024. Reutiliza los
períodos ya procesados si el recurso y su `last_modified` no cambiaron, de modo
que la actualización diaria normalmente sólo procesa un nuevo trimestre.

Algunos recursos históricos fueron exportados desde tablas dinámicas y contienen
filas sintéticas de subtotal con la jurisdicción vacía. Esas filas duplican
agregados que ya están presentes al máximo nivel de desagregación. Antes de
procesar cada período se eliminan únicamente esas filas sin jurisdicción cuando
el archivo contiene, a la vez, filas detalladas con jurisdicción informada.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import tempfile
from pathlib import Path

import requests

from descargar_presupuesto import package_show, is_csv, parse_exec_name, resource_url
from generar_presupuesto import decode_csv, norm, process_executed

BASE = Path(__file__).resolve().parent
OUT = BASE / "presupuesto_historico.json"
CURRENT = BASE / "presupuesto.json"
SINCE_YEAR = 2024
TIMEOUT = 120
PARSER_REV = 2


def discover() -> list[dict]:
    pkg = package_show("presupuesto-ejecutado")
    out=[]
    for r in pkg.get("resources") or []:
        name=str(r.get("name") or "")
        if not is_csv(r) or "presupuesto ejecutado" not in name.lower():
            continue
        parsed=parse_exec_name(name)
        if not parsed or parsed[0] < SINCE_YEAR:
            continue
        y,q=parsed
        out.append({
            "ejercicio":y,"trimestre":q,"periodo":f"{y}-T{q}",
            "resource":{"id":r.get("id"),"name":name,"url":resource_url(r),
                        "last_modified":r.get("last_modified") or r.get("metadata_modified")}
        })
    unique={}
    for x in out:
        key=x["periodo"]
        if key not in unique or str(x["resource"].get("last_modified") or "") > str(unique[key]["resource"].get("last_modified") or ""):
            unique[key]=x
    return sorted(unique.values(), key=lambda x:(x["ejercicio"],x["trimestre"]))


def download(url: str, path: Path) -> None:
    with requests.get(url, timeout=TIMEOUT, stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        with path.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: fh.write(chunk)
    if path.stat().st_size < 1000:
        raise RuntimeError(f"descarga demasiado pequeña: {url}")


def existing_map() -> dict[str,dict]:
    if not OUT.exists(): return {}
    try:
        old=json.loads(OUT.read_text(encoding="utf-8"))
        return {x["periodo"]:x for x in old.get("periodos") or []}
    except Exception:
        return {}


def remove_synthetic_subtotals(path: Path) -> int:
    """Quita subtotales de exportaciones históricas con `jur` vacío.

    Sólo actúa cuando el CSV tiene una columna jurisdicción y coexistencia real
    de filas con y sin jurisdicción. Las partidas detalladas del presupuesto
    siempre están asignadas a una jurisdicción; las filas vacías observadas en
    recursos 2024 son agregados de tabla dinámica y no nuevas partidas.
    """
    text=decode_csv(path)
    sample=text[:65536]
    try:
        dialect=csv.Sniffer().sniff(sample,delimiters=",;\t|")
        delim=dialect.delimiter
    except csv.Error:
        delim=","
    reader=csv.DictReader(io.StringIO(text),delimiter=delim)
    if not reader.fieldnames:
        return 0
    jur_field=None
    for f in reader.fieldnames:
        if norm(f)=="jur":
            jur_field=f; break
    if not jur_field:
        return 0
    rows=list(reader)
    has_detail=any(str(r.get(jur_field) or "").strip() for r in rows)
    has_blank=any(not str(r.get(jur_field) or "").strip() for r in rows)
    if not (has_detail and has_blank):
        return 0
    kept=[r for r in rows if str(r.get(jur_field) or "").strip()]
    removed=len(rows)-len(kept)
    if not removed:
        return 0
    with path.open("w",encoding="utf-8",newline="") as fh:
        writer=csv.DictWriter(fh,fieldnames=reader.fieldnames,delimiter=delim,extrasaction="ignore")
        writer.writeheader(); writer.writerows(kept)
    return removed


def process(item: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="cepoes-presupuesto-") as td:
        path=Path(td)/"periodo.csv"
        download(item["resource"]["url"],path)
        removed=remove_synthetic_subtotals(path)
        total,rows,groups=process_executed(path)
    if removed:
        print(f"     depuración: {removed:,} fila(s) sintética(s) sin jurisdicción descartadas")
    return {
        **item,
        "parser_rev":PARSER_REV,
        "filas":rows,
        "filas_sinteticas_descartadas":removed,
        "total":total,
        "jurisdicciones":groups["jurisdicciones"],
        "finalidades":groups["finalidades"],
        "funciones":groups["funciones"],
        "incisos":groups["incisos"],
        "programas_top":groups["programas_top"],
        "programas_total":groups["programas_total"],
    }


def main() -> int:
    resources=discover(); old=existing_map(); periods=[]; reused=0; updated=0
    if not resources:
        raise RuntimeError("No se descubrieron recursos trimestrales")
    for item in resources:
        prev=old.get(item["periodo"])
        if (prev and prev.get("parser_rev")==PARSER_REV
                and (prev.get("resource") or {}).get("id")==item["resource"].get("id")
                and (prev.get("resource") or {}).get("last_modified")==item["resource"].get("last_modified")):
            periods.append(prev); reused+=1
            print(f"  ↺ {item['periodo']} reutilizado")
        else:
            print(f"  ↓ {item['periodo']} {item['resource']['name']}")
            periods.append(process(item)); updated+=1
    current=json.loads(CURRENT.read_text(encoding="utf-8")) if CURRENT.exists() else {}
    output={
        "version":2,
        "parser_rev":PARSER_REV,
        "generado":dt.datetime.now(dt.timezone.utc).isoformat(),
        "desde":SINCE_YEAR,
        "hasta":periods[-1]["periodo"],
        "fuente":"BA Data · Ministerio de Hacienda y Finanzas GCBA",
        "metodologia":{
            "moneda":"pesos corrientes",
            "comparacion":"Las series nominales no corrigen inflación. Las comparaciones entre ejercicios deben leerse como evolución nominal hasta incorporar una serie homogénea a precios constantes.",
            "ejecucion":"Devengado / crédito vigente, acumulado al cierre de cada trimestre.",
            "estructura":"Los cambios de estructura ministerial entre ejercicios pueden afectar la comparación nominal por jurisdicción; se conserva la denominación oficial de cada período.",
            "depuracion":"En recursos históricos que incluyen subtotales sintéticos de tabla dinámica con jurisdicción vacía, CEPOES excluye esas filas para evitar doble contabilización y conserva las partidas detalladas con jurisdicción informada."
        },
        "periodos":periods,
        "actual":current.get("periodo"),
    }
    OUT.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(f"presupuesto_historico.json · {OUT.stat().st_size//1024} KB · {len(periods)} períodos · {updated} procesados · {reused} reutilizados")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
