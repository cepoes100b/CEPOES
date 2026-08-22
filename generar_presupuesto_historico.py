"""Construye una serie trimestral liviana del Presupuesto Ejecutado de CABA.

Descubre los CSV trimestrales oficiales en BA Data, desde 2024. Reutiliza los
períodos ya procesados si el recurso y su `last_modified` no cambiaron, de modo
que la actualización diaria normalmente sólo procesa un nuevo trimestre.
"""
from __future__ import annotations

import datetime as dt
import json
import tempfile
from pathlib import Path

import requests

from descargar_presupuesto import package_show, is_csv, parse_exec_name, resource_url
from generar_presupuesto import process_executed

BASE = Path(__file__).resolve().parent
OUT = BASE / "presupuesto_historico.json"
CURRENT = BASE / "presupuesto.json"
SINCE_YEAR = 2024
TIMEOUT = 120


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


def process(item: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="cepoes-presupuesto-") as td:
        path=Path(td)/"periodo.csv"
        download(item["resource"]["url"],path)
        total,rows,groups=process_executed(path)
    return {
        **item,
        "filas":rows,
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
        if prev and (prev.get("resource") or {}).get("id")==item["resource"].get("id") and (prev.get("resource") or {}).get("last_modified")==item["resource"].get("last_modified"):
            periods.append(prev); reused+=1
            print(f"  ↺ {item['periodo']} reutilizado")
        else:
            print(f"  ↓ {item['periodo']} {item['resource']['name']}")
            periods.append(process(item)); updated+=1
    current=json.loads(CURRENT.read_text(encoding="utf-8")) if CURRENT.exists() else {}
    output={
        "version":1,
        "generado":dt.datetime.now(dt.timezone.utc).isoformat(),
        "desde":SINCE_YEAR,
        "hasta":periods[-1]["periodo"],
        "fuente":"BA Data · Ministerio de Hacienda y Finanzas GCBA",
        "metodologia":{
            "moneda":"pesos corrientes",
            "comparacion":"Las series nominales no corrigen inflación. Las comparaciones entre ejercicios deben leerse como evolución nominal hasta incorporar una serie homogénea a precios constantes.",
            "ejecucion":"Devengado / crédito vigente, acumulado al cierre de cada trimestre.",
            "estructura":"Los cambios de estructura ministerial entre ejercicios pueden afectar la comparación nominal por jurisdicción; se conserva la denominación oficial de cada período."
        },
        "periodos":periods,
        "actual":current.get("periodo"),
    }
    OUT.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(f"presupuesto_historico.json · {OUT.stat().st_size//1024} KB · {len(periods)} períodos · {updated} procesados · {reused} reutilizados")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
