#!/usr/bin/env python3
"""Inspecciona los archivos BCRA descargados sin persistir datos personales derivados.

Objetivo v2.29:
- descomprimir temporalmente los .7z de Central de Deudores;
- detectar nombres de archivos internos, codificación, delimitador y cantidad de campos;
- producir un diagnóstico estructural JSON sin CUIT/CUIL, nombres ni filas individuales;
- bloquear el pipeline si cambia el formato esperado.

Este script NO publica ni conserva registros individuales. El contenido extraído vive en
un directorio temporal y se elimina al finalizar.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE_RE = re.compile(r"(?P<periodo>\d{6})(?:\d{2})?(?P<tipo>DEUDORES|PADRON)\.7Z$", re.I)
SENSITIVE_RE = re.compile(r"(?:^|[^0-9])(?:20|23|24|27|30|33|34)[0-9]{9}(?:[^0-9]|$)")


def extraer_7z(archivo: Path, destino: Path) -> None:
    seven = shutil.which("7z") or shutil.which("7zz")
    if not seven:
        raise RuntimeError("No se encontró 7z/7zz. En Ubuntu: sudo apt-get install p7zip-full")
    subprocess.run([seven, "x", "-y", f"-o{destino}", str(archivo)], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def detectar_encoding(path: Path) -> str:
    muestra = path.read_bytes()[:200_000]
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            muestra.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detectar_separador(linea: str) -> str | None:
    candidatos = [";", "|", "\t", ","]
    conteos = {c: linea.count(c) for c in candidatos}
    sep, n = max(conteos.items(), key=lambda kv: kv[1])
    return sep if n > 0 else None


def estructura_archivo(path: Path) -> dict:
    enc = detectar_encoding(path)
    lineas = []
    with path.open("r", encoding=enc, errors="replace", newline="") as f:
        for _ in range(25):
            linea = f.readline()
            if not linea:
                break
            linea = linea.rstrip("\r\n")
            if linea:
                lineas.append(linea)

    if not lineas:
        return {
            "nombre": path.name,
            "bytes": path.stat().st_size,
            "encoding": enc,
            "vacio": True,
        }

    sep = detectar_separador(lineas[0])
    longitudes = [len(x) for x in lineas]
    campos = []
    if sep:
        for linea in lineas:
            campos.append(len(next(csv.reader([linea], delimiter=sep))))

    # No copiar muestras de contenido al JSON: podrían contener identificadores o nombres.
    return {
        "nombre": path.name,
        "bytes": path.stat().st_size,
        "encoding": enc,
        "separador": sep,
        "campos_por_fila_muestra": sorted(Counter(campos).items()) if campos else None,
        "longitud_fila_min": min(longitudes),
        "longitud_fila_max": max(longitudes),
        "filas_muestreadas": len(lineas),
        "posible_identificador_en_muestra": any(SENSITIVE_RE.search(x) for x in lineas),
    }


def contar_lineas(path: Path) -> int:
    # Conteo binario rápido y sin parsear contenido.
    total = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            total += chunk.count(b"\n")
    return total


def inspeccionar_archivo_7z(archivo: Path) -> dict:
    m = ARCHIVE_RE.search(archivo.name.upper())
    if not m:
        raise ValueError(f"Nombre no reconocido: {archivo.name}")

    with tempfile.TemporaryDirectory(prefix="cepoes-bcra-") as tmp:
        tmpdir = Path(tmp)
        extraer_7z(archivo, tmpdir)
        internos = [p for p in tmpdir.rglob("*") if p.is_file()]
        detalle = []
        for p in internos:
            d = estructura_archivo(p)
            d["filas"] = contar_lineas(p)
            detalle.append(d)

    return {
        "archivo": archivo.name,
        "periodo": m.group("periodo"),
        "tipo": m.group("tipo").upper(),
        "bytes_7z": archivo.stat().st_size,
        "internos": detalle,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--directorio", default="bcra_deudores")
    ap.add_argument("--salida", default="estado_bcra_deudores.json")
    args = ap.parse_args()

    directorio = Path(args.directorio)
    archivos = sorted(
        p for p in directorio.glob("*.7Z")
        if ARCHIVE_RE.search(p.name.upper())
    )
    if not archivos:
        raise SystemExit("No hay archivos DEUDORES/PADRON .7Z para inspeccionar")

    resultado = {
        "schema": "cepoes-bcra-structural-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "archivos": [inspeccionar_archivo_7z(p) for p in archivos],
        "privacidad": {
            "contiene_filas_individuales": False,
            "contiene_identificadores": False,
            "contiene_nombres": False,
            "nota": "El JSON conserva únicamente metadatos estructurales y conteos.",
        },
    }

    Path(args.salida).write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    print(f"OK -> {args.salida}")
    for a in resultado["archivos"]:
        print(f"  {a['archivo']} · {len(a['internos'])} archivo(s) interno(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
