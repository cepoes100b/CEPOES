#!/usr/bin/env python3
"""Inspecciona archivos masivos del BCRA sin extraer ni persistir microdatos.

Objetivo v2.29:
- listar el contenido interno del .7z;
- leer únicamente una muestra acotada en streaming;
- detectar codificación, delimitador y cantidad de campos;
- producir un diagnóstico estructural JSON sin CUIT/CUIL, nombres ni filas individuales.

Nunca se escribe el contenido descomprimido a disco. La muestra sólo existe en memoria y el
JSON resultante conserva exclusivamente metadatos derivados.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE_RE = re.compile(r"(?P<periodo>\d{6})(?:\d{2})?(?P<tipo>DEUDORES|PADRON)\.7Z$", re.I)
SENSITIVE_RE = re.compile(r"(?:^|[^0-9])(?:20|23|24|27|30|33|34)[0-9]{9}(?:[^0-9]|$)")
MAX_SAMPLE_BYTES = 256_000
MAX_SAMPLE_LINES = 40


def sevenzip() -> str:
    exe = shutil.which("7z") or shutil.which("7zz")
    if not exe:
        raise RuntimeError("No se encontró 7z/7zz. En Ubuntu: sudo apt-get install p7zip-full")
    return exe


def listar_internos(archivo: Path) -> list[dict]:
    """Obtiene nombres y tamaños declarados por 7z sin descomprimir."""
    r = subprocess.run(
        [sevenzip(), "l", "-slt", str(archivo)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    bloques: list[dict] = []
    actual: dict[str, str] = {}
    for linea in r.stdout.splitlines() + [""]:
        if not linea.strip():
            if actual:
                bloques.append(actual)
                actual = {}
            continue
        if " = " in linea:
            k, v = linea.split(" = ", 1)
            actual[k.strip()] = v.strip()

    internos = []
    for b in bloques:
        nombre = b.get("Path")
        if not nombre or b.get("Type") == "7z" or b.get("Folder") == "+":
            continue
        try:
            size = int(b.get("Size", "0") or 0)
        except ValueError:
            size = 0
        internos.append({"nombre": nombre, "bytes_declarados": size})
    return internos


def muestra_stream(archivo: Path, interno: str) -> bytes:
    """Lee sólo MAX_SAMPLE_BYTES del archivo interno y corta 7z inmediatamente."""
    proc = subprocess.Popen(
        [sevenzip(), "x", "-so", str(archivo), interno],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert proc.stdout is not None
    try:
        data = proc.stdout.read(MAX_SAMPLE_BYTES)
    finally:
        proc.stdout.close()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    return data


def detectar_encoding_bytes(muestra: bytes) -> str:
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


def estructura_muestra(nombre: str, bytes_declarados: int, muestra: bytes) -> dict:
    enc = detectar_encoding_bytes(muestra)
    texto = muestra.decode(enc, errors="replace")
    lineas = [x.rstrip("\r") for x in texto.split("\n") if x.strip()][:MAX_SAMPLE_LINES]
    if not lineas:
        return {
            "nombre": nombre,
            "bytes_declarados": bytes_declarados,
            "encoding": enc,
            "vacio_en_muestra": True,
        }

    sep = detectar_separador(lineas[0])
    longitudes = [len(x) for x in lineas]
    campos = []
    if sep:
        for linea in lineas:
            try:
                campos.append(len(next(csv.reader([linea], delimiter=sep))))
            except csv.Error:
                pass

    return {
        "nombre": nombre,
        "bytes_declarados": bytes_declarados,
        "encoding": enc,
        "separador": sep,
        "campos_por_fila_muestra": sorted(Counter(campos).items()) if campos else None,
        "longitud_fila_min": min(longitudes),
        "longitud_fila_max": max(longitudes),
        "filas_muestreadas": len(lineas),
        "bytes_muestreados_max": MAX_SAMPLE_BYTES,
        "posible_identificador_en_muestra": any(SENSITIVE_RE.search(x) for x in lineas),
    }


def inspeccionar_archivo_7z(archivo: Path) -> dict:
    m = ARCHIVE_RE.search(archivo.name.upper())
    if not m:
        raise ValueError(f"Nombre no reconocido: {archivo.name}")

    internos = listar_internos(archivo)
    detalle = []
    for item in internos:
        muestra = muestra_stream(archivo, item["nombre"])
        detalle.append(estructura_muestra(item["nombre"], item["bytes_declarados"], muestra))

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
    archivos = sorted(p for p in directorio.glob("*.7Z") if ARCHIVE_RE.search(p.name.upper()))
    if not archivos:
        raise SystemExit("No hay archivos DEUDORES/PADRON .7Z para inspeccionar")

    resultado = {
        "schema": "cepoes-bcra-structural-v2",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "archivos": [inspeccionar_archivo_7z(p) for p in archivos],
        "privacidad": {
            "contiene_filas_individuales": False,
            "contiene_identificadores": False,
            "contiene_nombres": False,
            "microdatos_descomprimidos_en_disco": False,
            "nota": "El JSON conserva sólo metadatos derivados de una muestra en memoria.",
        },
    }

    Path(args.salida).write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK -> {args.salida}")
    for a in resultado["archivos"]:
        print(f"  {a['archivo']} · {len(a['internos'])} archivo(s) interno(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
