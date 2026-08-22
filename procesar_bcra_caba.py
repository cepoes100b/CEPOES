#!/usr/bin/env python3
"""Construye un diagnóstico agregado de endeudamiento para CABA desde BCRA + ARCA.

Privacidad por diseño:
- PADRON y DEUDORES se leen directamente desde los .7z en streaming;
- ningún archivo de microdatos se descomprime a disco;
- CUIT/CUIL/CDI sólo existen temporalmente en memoria como claves de cruce;
- la salida contiene exclusivamente estadísticas agregadas.

Esta primera etapa usa un universo conservador de personas humanas: registros del Padrón
ARCA con provincia 00 (CABA) y sexo informado M/F. No se infieren personas humanas por
prefijo de CUIT. La cobertura se contrasta luego contra referencias externas antes de publicar.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

LONG_PADRON = 220
LONG_DEUDORES = 171
MORA = {b"3", b"4", b"5"}
SITUACIONES_VALIDAS = {b"1", b"2", b"3", b"4", b"5", b"11"}

# Referencia de reconciliación: valores de la v2.28 para junio 2026.
REFERENCIA = {
    "deudores": 1_877_802,
    "personas_mora": 255_805,
    "incidencia_mora_pct": 13.62,
    "deuda_total_pesos": 13_390_000_000_000,
    "deuda_mora_pesos": 1_570_000_000_000,
    "tasa_mora_pct": 11.71,
}


def sevenzip() -> str:
    exe = shutil.which("7z") or shutil.which("7zz")
    if not exe:
        raise RuntimeError("Falta 7z/7zz")
    return exe


def internos(archivo: Path) -> list[str]:
    r = subprocess.run(
        [sevenzip(), "l", "-slt", str(archivo)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    nombres: list[str] = []
    actual: dict[str, str] = {}
    for linea in r.stdout.splitlines() + [""]:
        if not linea.strip():
            if actual.get("Path") and actual.get("Folder") != "+":
                nombres.append(actual["Path"])
            actual = {}
            continue
        if " = " in linea:
            k, v = linea.split(" = ", 1)
            actual[k.strip()] = v.strip()
    return nombres


def buscar_interno(archivo: Path, nombre: str) -> str:
    objetivo = nombre.lower()
    for item in internos(archivo):
        if Path(item).name.lower() == objetivo:
            return item
    raise RuntimeError(f"No se encontró {nombre} dentro de {archivo.name}")


def stream_lineas(archivo: Path, interno: str):
    proc = subprocess.Popen(
        [sevenzip(), "x", "-so", str(archivo), interno],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=1024 * 1024,
    )
    assert proc.stdout is not None
    try:
        for raw in proc.stdout:
            yield raw.rstrip(b"\r\n")
    finally:
        proc.stdout.close()
        rc = proc.wait()
        if rc not in (0,):
            raise RuntimeError(f"7z terminó con código {rc} leyendo {interno}")


def monto_decimas_de_miles(raw: bytes) -> int | None:
    """Devuelve el monto como décimas de miles de pesos (1 unidad = $100).

    El LEAME define once enteros y un decimal. Se tolera separador decimal explícito
    (coma/punto) o decimal implícito, sin convertir a float.
    """
    valor = raw.strip().replace(b",", b"").replace(b".", b"")
    if not valor:
        return 0
    if not valor.isdigit():
        return None
    return int(valor)


def desviacion_pct(valor: float, referencia: float) -> float | None:
    if not referencia:
        return None
    return round((valor / referencia - 1) * 100, 3)


def main() -> int:
    carpeta = Path("bcra_deudores")
    padrones = sorted(carpeta.glob("*PADRON.7Z"))
    deudores_arch = sorted(carpeta.glob("*DEUDORES.7Z"))
    if not padrones or not deudores_arch:
        raise SystemExit("Se requieren PADRON.7Z y DEUDORES.7Z en bcra_deudores/")

    padron = padrones[-1]
    deudores = deudores_arch[-1]
    interno_padron = buscar_interno(padron, "Padron_ARCA.txt")
    interno_deudores = buscar_interno(deudores, "deudores.txt")

    # 1) Universo CABA de personas humanas conservador.
    ids_caba_humanos: set[bytes] = set()
    padron_leidos = 0
    padron_longitud_invalida = 0
    caba_registros = 0
    caba_sexo = Counter()
    caba_ids_invalidos = 0

    print(f"[1/2] Leyendo {padron.name}:{interno_padron} en streaming", flush=True)
    for raw in stream_lineas(padron, interno_padron):
        if not raw:
            continue
        padron_leidos += 1
        if len(raw) != LONG_PADRON:
            padron_longitud_invalida += 1
            continue
        if raw[210:212] != b"00":
            continue
        caba_registros += 1
        sexo = raw[199:200].strip().upper()
        caba_sexo[sexo.decode("ascii", errors="replace") or "sin_informar"] += 1
        ident = raw[0:11].strip()
        if len(ident) != 11 or not ident.isdigit():
            caba_ids_invalidos += 1
            continue
        if sexo in (b"M", b"F"):
            ids_caba_humanos.add(ident)
        if padron_leidos % 5_000_000 == 0:
            print(
                f"  PADRON {padron_leidos:,} registros; "
                f"CABA humanos únicos {len(ids_caba_humanos):,}",
                flush=True,
            )

    if not ids_caba_humanos:
        raise SystemExit("No se identificaron personas humanas CABA en PADRON")

    # 2) Cruce contra CENDEU mensual y agregación.
    deudores_unicos: set[bytes] = set()
    morosos_unicos: set[bytes] = set()
    registros_leidos = 0
    registros_longitud_invalida = 0
    registros_tipo_id_no_fiscal = 0
    registros_caba = 0
    montos_invalidos = 0
    situaciones = Counter()
    deuda_total_u100 = 0
    deuda_mora_u100 = 0

    print(f"[2/2] Leyendo {deudores.name}:{interno_deudores} en streaming", flush=True)
    for raw in stream_lineas(deudores, interno_deudores):
        if not raw:
            continue
        registros_leidos += 1
        if len(raw) != LONG_DEUDORES:
            registros_longitud_invalida += 1
            continue
        if raw[11:13].strip() != b"11":
            registros_tipo_id_no_fiscal += 1
            continue
        ident = raw[13:24].strip()
        if ident not in ids_caba_humanos:
            continue
        registros_caba += 1
        deudores_unicos.add(ident)
        situacion = raw[27:29].strip()
        situaciones[situacion.decode("ascii", errors="replace") or "vacio"] += 1

        m7 = monto_decimas_de_miles(raw[29:41])
        m10 = monto_decimas_de_miles(raw[65:77])
        if m7 is None or m10 is None:
            montos_invalidos += 1
            continue
        deuda = m7 + m10
        deuda_total_u100 += deuda
        if situacion in MORA:
            morosos_unicos.add(ident)
            deuda_mora_u100 += deuda

        if registros_leidos % 5_000_000 == 0:
            print(
                f"  DEUDORES {registros_leidos:,} registros; "
                f"deudores CABA únicos {len(deudores_unicos):,}",
                flush=True,
            )

    n_deudores = len(deudores_unicos)
    n_morosos = len(morosos_unicos)
    deuda_total_pesos = deuda_total_u100 * 100
    deuda_mora_pesos = deuda_mora_u100 * 100
    incidencia = (n_morosos / n_deudores * 100) if n_deudores else 0.0
    tasa_monetaria = (deuda_mora_pesos / deuda_total_pesos * 100) if deuda_total_pesos else 0.0

    resultado = {
        "schema": "cepoes-bcra-caba-diagnostico-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "fuentes": {
            "padron": padron.name,
            "deudores": deudores.name,
            "padron_interno": interno_padron,
            "deudores_interno": interno_deudores,
        },
        "universo": {
            "criterio": "provincia ARCA=00 y sexo ARCA en M/F; tipo identificacion CENDEU=11",
            "nota": "Criterio conservador de persona humana. No se infiere por prefijo de CUIT.",
            "padron_registros_leidos": padron_leidos,
            "padron_registros_longitud_invalida": padron_longitud_invalida,
            "padron_registros_caba": caba_registros,
            "padron_caba_por_sexo": dict(sorted(caba_sexo.items())),
            "padron_caba_ids_invalidos": caba_ids_invalidos,
            "padron_caba_humanos_unicos": len(ids_caba_humanos),
        },
        "procesamiento_cendeu": {
            "registros_leidos": registros_leidos,
            "registros_longitud_invalida": registros_longitud_invalida,
            "registros_tipo_id_no_fiscal": registros_tipo_id_no_fiscal,
            "registros_caba_humanos": registros_caba,
            "montos_invalidos": montos_invalidos,
            "situaciones_registros_caba": dict(sorted(situaciones.items())),
            "mora_definida_situaciones": [3, 4, 5],
            "deuda_definida_como": "campo 7 prestamos/financiaciones + campo 10 otros conceptos",
            "unidad_origen": "miles de pesos con un decimal",
        },
        "indicadores": {
            "deudores": n_deudores,
            "personas_mora": n_morosos,
            "incidencia_mora_pct": round(incidencia, 4),
            "deuda_total_pesos": deuda_total_pesos,
            "deuda_mora_pesos": deuda_mora_pesos,
            "tasa_mora_pct": round(tasa_monetaria, 4),
        },
        "reconciliacion_v228": {
            "referencia": REFERENCIA,
            "desviacion_pct": {
                "deudores": desviacion_pct(n_deudores, REFERENCIA["deudores"]),
                "personas_mora": desviacion_pct(n_morosos, REFERENCIA["personas_mora"]),
                "incidencia_mora": desviacion_pct(incidencia, REFERENCIA["incidencia_mora_pct"]),
                "deuda_total": desviacion_pct(deuda_total_pesos, REFERENCIA["deuda_total_pesos"]),
                "deuda_mora": desviacion_pct(deuda_mora_pesos, REFERENCIA["deuda_mora_pesos"]),
                "tasa_mora": desviacion_pct(tasa_monetaria, REFERENCIA["tasa_mora_pct"]),
            },
            "nota": "La referencia v2.28 se usa sólo como benchmark de reconciliación, no como fuente del nuevo dataset.",
        },
        "privacidad": {
            "microdatos_publicados": False,
            "identificadores_en_salida": False,
            "nombres_en_salida": False,
            "microdatos_descomprimidos_en_disco": False,
            "identificadores_solo_en_memoria": True,
        },
    }

    Path("diagnostico_bcra_caba.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"indicadores": resultado["indicadores"],
                      "reconciliacion_v228": resultado["reconciliacion_v228"]},
                     ensure_ascii=False, indent=2))
    print("OK -> diagnostico_bcra_caba.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
