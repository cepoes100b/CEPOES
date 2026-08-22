#!/usr/bin/env python3
"""Valida de forma segura el layout histórico CENDEU contra el DEUDORES vigente.

No imprime ni persiste filas, CUIT/CUIL ni valores individuales. Sólo produce métricas
estructurales agregadas sobre una muestra acotada leída en streaming desde el .7z.

El candidato de 24 campos proviene del diseño oficial histórico de la Central de
Deudores del BCRA. Debe considerarse confirmado sólo si este control pasa sobre el
archivo mensual vigente.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

LONGITUD_CANDIDATA = 138
MAX_FILAS = 500

# (nombre, inicio 0-based, fin exclusivo)
CAMPOS = (
    ("entidad", 0, 5),
    ("periodo", 5, 11),
    ("tipo_identificacion", 11, 13),
    ("identificacion", 13, 24),
    ("actividad", 24, 27),
    ("situacion", 27, 29),
    ("prestamos", 29, 38),
    ("participaciones", 38, 47),
    ("garantias_otorgadas", 47, 56),
    ("otros_conceptos", 56, 65),
    ("garantias_pref_a", 65, 74),
    ("garantias_pref_b", 74, 83),
    ("sin_garantias_pref", 83, 92),
    ("contragarantias_pref_a", 92, 101),
    ("contragarantias_pref_b", 101, 110),
    ("sin_contragarantias_pref", 110, 119),
    ("previsiones", 119, 128),
    ("deuda_cubierta", 128, 129),
    ("proceso_judicial_revision", 129, 130),
    ("refinanciaciones", 130, 131),
    ("recategorizacion_obligatoria", 131, 132),
    ("situacion_juridica", 132, 133),
    ("irrecuperable_disposicion_tecnica", 133, 134),
    ("dias_atraso", 134, 138),
)

assert CAMPOS[-1][2] == LONGITUD_CANDIDATA


def sevenzip() -> str:
    exe = shutil.which("7z") or shutil.which("7zz")
    if not exe:
        raise RuntimeError("Falta 7z/7zz")
    return exe


def primer_interno_datos(archivo: Path) -> str:
    r = subprocess.run([sevenzip(), "l", "-slt", str(archivo)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, errors="replace")
    candidatos: list[tuple[int, str]] = []
    actual: dict[str, str] = {}
    for linea in r.stdout.splitlines() + [""]:
        if not linea.strip():
            if actual.get("Path") and actual.get("Folder") != "+":
                try:
                    tam = int(actual.get("Size", "0") or 0)
                except ValueError:
                    tam = 0
                nombre = actual["Path"]
                if nombre.lower().endswith((".txt", ".dat", ".csv")):
                    candidatos.append((tam, nombre))
            actual = {}
            continue
        if " = " in linea:
            k, v = linea.split(" = ", 1)
            actual[k.strip()] = v.strip()
    if not candidatos:
        raise RuntimeError("No se encontró archivo de datos interno")
    # El fichero principal de datos será, por diseño, el mayor archivo de texto.
    return max(candidatos)[1]


def leer_lineas(archivo: Path, interno: str) -> list[str]:
    proc = subprocess.Popen([sevenzip(), "x", "-so", str(archivo), interno],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdout is not None
    lineas: list[str] = []
    try:
        for raw in proc.stdout:
            if not raw.strip():
                continue
            linea = raw.rstrip(b"\r\n").decode("cp1252", errors="replace")
            lineas.append(linea)
            if len(lineas) >= MAX_FILAS:
                break
    finally:
        proc.stdout.close()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=5)
    return lineas


def es_digitos(s: str) -> bool:
    return bool(s) and s.isdigit()


def main() -> int:
    archivos = sorted(Path("bcra_deudores").glob("*DEUDORES.7Z"))
    if not archivos:
        raise SystemExit("No hay *DEUDORES.7Z")
    archivo = archivos[-1]
    interno = primer_interno_datos(archivo)
    lineas = leer_lineas(archivo, interno)
    if not lineas:
        raise SystemExit("No se pudo obtener muestra")

    largos: dict[int, int] = {}
    for x in lineas:
        largos[len(x)] = largos.get(len(x), 0) + 1

    validas_longitud = [x for x in lineas if len(x) == LONGITUD_CANDIDATA]
    controles = {
        "entidad_5_digitos": 0,
        "periodo_6_digitos": 0,
        "tipo_id_2_digitos": 0,
        "identificacion_11_digitos": 0,
        "situacion_2_digitos": 0,
        "dias_atraso_4_digitos": 0,
    }
    for x in validas_longitud:
        controles["entidad_5_digitos"] += es_digitos(x[0:5])
        controles["periodo_6_digitos"] += bool(re.fullmatch(r"20\d{4}", x[5:11]))
        controles["tipo_id_2_digitos"] += es_digitos(x[11:13])
        controles["identificacion_11_digitos"] += es_digitos(x[13:24])
        controles["situacion_2_digitos"] += es_digitos(x[27:29])
        controles["dias_atraso_4_digitos"] += es_digitos(x[134:138])

    n = len(validas_longitud)
    ratios = {k: (v / n if n else 0.0) for k, v in controles.items()}
    confirmado = (
        n == len(lineas)
        and n > 0
        and all(v >= 0.98 for v in ratios.values())
    )
    salida = {
        "schema": "cepoes-cendeu-layout-check-v1",
        "archivo": archivo.name,
        "archivo_interno": interno,
        "filas_muestreadas": len(lineas),
        "longitudes": {str(k): v for k, v in sorted(largos.items())},
        "longitud_candidata": LONGITUD_CANDIDATA,
        "campos_candidatos": len(CAMPOS),
        "ratios_controles": ratios,
        "layout_historico_24_campos_confirmado": confirmado,
        "privacidad": {
            "filas_publicadas": False,
            "identificadores_publicados": False,
            "valores_individuales_publicados": False,
        },
    }
    Path("diagnostico_layout_cendeu.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(salida, ensure_ascii=False, indent=2))
    return 0 if confirmado else 2


if __name__ == "__main__":
    raise SystemExit(main())
