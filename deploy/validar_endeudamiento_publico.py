#!/usr/bin/env python3
"""Valida exclusivamente los agregados públicos de endeudamiento, sin crudos.

API: validate_manifest, validate_period y validate_public_aggregates(root).
La última devuelve manifest, latest y staging_paths. El CLI --staging-paths
imprime únicamente manifest y último período, después de validar TODO el historial
referido. No enumera directorios, copia archivos ni consulta la matriz territorial.
Los cambios de esquema requieren revisión explícita: no se aceptan campos libres.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timedelta
import json
import math
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).absolute().parents[1]
PUBLIC_DIR = "datos/endeudamiento"
MANIFEST_SCHEMA = "cepoes-endeudamiento-manifest-v1"
PERIOD_SCHEMA = "cepoes-endeudamiento-barrios-v2-compact"
SOURCE = "BCRA / Padrón ARCA — elaboración CEPOES"
METRICS = ("deudores", "personas_mora", "deuda_total_pesos", "deuda_mora_pesos")
SEXES = ("F", "M")
AGES = ("le25", "26_35", "36_45", "46_55", "56_65", "66_75", "gt75", "desconocida")
CREDITORS = ("entidad_financiera", "emisora_tarjeta", "otro_pnfc")
BARRIOS = (
    "Agronomia", "Almagro", "Balvanera", "Barracas", "Belgrano", "Boca", "Boedo",
    "Caballito", "Chacarita", "Coghlan", "Colegiales", "Constitucion", "Flores",
    "Floresta", "Liniers", "Mataderos", "Monserrat", "Monte Castro", "Nueva Pompeya",
    "Nunez", "Palermo", "Parque Avellaneda", "Parque Chacabuco", "Parque Chas",
    "Parque Patricios", "Paternal", "Puerto Madero", "Recoleta", "Retiro", "Saavedra",
    "San Cristobal", "San Nicolas", "San Telmo", "Velez Sarsfield", "Versalles",
    "Villa Crespo", "Villa Del Parque", "Villa Devoto", "Villa Gral. Mitre",
    "Villa Lugano", "Villa Luro", "Villa Ortuzar", "Villa Pueyrredon", "Villa Real",
    "Villa Riachuelo", "Villa Santa Rita", "Villa Soldati", "Villa Urquiza",
)
PERIOD_RE = re.compile(r"[0-9]{4}-(?:0[1-9]|1[0-2])\Z")
TIMESTAMP_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:\+00:00|Z)\Z")
METHOD_FIXED = {
    "nivel": "barrio",
    "naturaleza": "estimacion territorial agregada",
    "regla": "distribucion probabilistica de agregados BCRA/ARCA por CP4 entre barrios mediante matriz fija CP4-barrio",
    "no_es": "geolocalizacion individual ni conteo domiciliario exacto",
    "matriz_schema": "cepoes-cp4-barrio-probabilistic-v2",
    "tratamiento_sin_soporte": "los CP4 sin soporte geografico observado no se imputan a barrios; permanecen incluidos en el total CABA",
    "actualizacion_mensual": "la matriz territorial permanece fija; cada período incorpora exclusivamente nuevos agregados BCRA/ARCA",
    "supresion": "las celdas demograficas o por acreedor con menos de 10 deudores se omiten antes de la territorializacion",
}
SOURCE_FIELDS = {
    "principal": "Banco Central de la República Argentina — Central de Deudores",
    "padron": "Padrón ARCA distribuido por BCRA",
    "elaboracion": "CEPOES",
}
COVERAGE_METRICS = ("deudores_pct", "personas_mora_pct", "deuda_total_pct", "deuda_mora_pct")


class ValidationError(ValueError):
    """La entrada no cumple el contrato agregado público; no publicar."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _object(value, keys, context: str) -> None:
    # No imprimir claves ni valores desconocidos: podrían contener datos privados.
    _require(type(value) is dict and set(value) == set(keys),
             f"{context}: se requiere un objeto con exactamente los campos públicos esperados")


def _period(value, context: str) -> None:
    _require(type(value) is str and PERIOD_RE.fullmatch(value) is not None
             and not value.startswith("0000"), f"{context}: período YYYY-MM inválido")


def _timestamp(value, context: str) -> None:
    _require(type(value) is str and TIMESTAMP_RE.fullmatch(value) is not None,
             f"{context}: fecha UTC inválida")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValidationError(f"{context}: fecha UTC inválida") from None
    _require(parsed.utcoffset() == timedelta(0), f"{context}: fecha sin UTC")


def _number(value, context: str, *, integer: bool = False, percentage: bool = False) -> None:
    _require(type(value) in ((int,) if integer else (int, float)), f"{context}: número inválido")
    try:
        valid = math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    _require(valid, f"{context}: valor no finito o negativo")
    if percentage:
        _require(value <= 100, f"{context}: porcentaje fuera de rango")


def validate_manifest(obj: dict) -> dict:
    """Valida el esquema del índice sin abrir ninguna ruta referida."""
    _object(obj, ("schema", "actualizado_utc", "ultimo_periodo", "periodos", "archivos", "fuente"), "manifest")
    _require(obj["schema"] == MANIFEST_SCHEMA and obj["fuente"] == SOURCE, "manifest: metadatos no admitidos")
    _timestamp(obj["actualizado_utc"], "manifest.actualizado_utc")
    periods = obj["periodos"]
    _require(type(periods) is list and bool(periods), "manifest.periodos: lista vacía o inválida")
    for period in periods:
        _period(period, "manifest.periodos")
    _require(periods == sorted(set(periods)), "manifest.periodos: períodos duplicados o desordenados")
    _period(obj["ultimo_periodo"], "manifest.ultimo_periodo")
    _require(obj["ultimo_periodo"] == periods[-1], "manifest: último período inconsistente")
    _object(obj["archivos"], periods, "manifest.archivos")
    for period in periods:
        _require(obj["archivos"][period] == f"{period}.json", "manifest.archivos: ruta no admitida")
    return obj


def _summary(obj, *, records: bool, context: str) -> None:
    keys = (*METRICS, "incidencia_mora_pct", "tasa_mora_pct")
    _object(obj, (*keys, "registros_incluidos") if records else keys, context)
    for key in keys:
        _number(obj[key], f"{context}.{key}", percentage=key.endswith("_pct"))
    if records:
        _number(obj["registros_incluidos"], f"{context}.registros_incluidos", integer=True)
    _require(obj["personas_mora"] <= obj["deudores"] and obj["deuda_mora_pesos"] <= obj["deuda_total_pesos"],
             f"{context}: mora superior al total")
    for numerator, denominator, percentage in (
        ("personas_mora", "deudores", "incidencia_mora_pct"),
        ("deuda_mora_pesos", "deuda_total_pesos", "tasa_mora_pct"),
    ):
        expected = round(obj[numerator] / obj[denominator] * 100, 4) if obj[denominator] else 0
        _require(abs(obj[percentage] - expected) <= 0.00011, f"{context}: porcentaje inconsistente")


def validate_period(obj: dict, expected_period: str) -> dict:
    """Valida un agregado compacto; no acepta campos extra ni valores personales."""
    _period(expected_period, "período esperado")
    _object(obj, ("schema", "generado_utc", "periodo", "padron_fecha", "titulo", "fuente", "caba",
                  "filtros", "barrios", "metricas_segmento", "metodologia", "segmentos"), "período")
    _require(obj["schema"] == PERIOD_SCHEMA and obj["periodo"] == expected_period
             and obj["titulo"] == "Endeudamiento por barrio", "período: metadatos no admitidos")
    _timestamp(obj["generado_utc"], "generado_utc")
    padron = obj["padron_fecha"]
    _require(type(padron) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", padron) is not None,
             "padron_fecha: fecha inválida")
    try:
        date.fromisoformat(padron)
    except ValueError:
        raise ValidationError("padron_fecha: fecha inválida") from None
    _object(obj["fuente"], SOURCE_FIELDS, "fuente")
    _require(obj["fuente"] == SOURCE_FIELDS, "fuente: metadatos no admitidos")
    _object(obj["filtros"], ("sexos", "edades", "acreedores"), "filtros")
    _require(obj["filtros"] == {"sexos": list(SEXES), "edades": list(AGES), "acreedores": list(CREDITORS)},
             "filtros: dominios no admitidos")
    _require(obj["metricas_segmento"] == list(METRICS), "metricas_segmento: orden o métricas inválidas")
    barrios = obj["barrios"]
    _require(type(barrios) is list and len(barrios) == 48 and all(type(b) is str for b in barrios),
             "barrios: se requieren 48 nombres públicos")
    _require(set(barrios) == set(BARRIOS), "barrios: nombres no admitidos o duplicados")

    method = obj["metodologia"]
    _object(method, (*METHOD_FIXED, "matriz_periodo_calibracion", "matriz_estado_validacion", "soporte_cp4"), "metodologia")
    _require(all(method[key] == value for key, value in METHOD_FIXED.items()), "metodologia: metadatos no admitidos")
    _period(method["matriz_periodo_calibracion"], "metodologia.matriz_periodo_calibracion")
    _require(method["matriz_periodo_calibracion"] <= expected_period, "metodologia: calibración posterior al período")
    _require(method["matriz_estado_validacion"] in ("VALIDADA", "VALIDADA_TEMPORAL"),
             "metodologia: estado de matriz no admitido")
    support = method["soporte_cp4"]
    _object(support, ("cp4_matriz", "cp4_con_soporte", "cp4_sin_soporte"), "metodologia.soporte_cp4")
    for key, value in support.items():
        _number(value, f"metodologia.soporte_cp4.{key}", integer=True)
    _require(support["cp4_con_soporte"] >= 250
             and support["cp4_matriz"] == support["cp4_con_soporte"] + support["cp4_sin_soporte"],
             "metodologia: conteo de soporte inconsistente")

    caba = obj["caba"]
    _object(caba, ("total", "base_territorial_cp4", "base_barrial_con_soporte",
                   "cobertura_territorial_cp4_sobre_caba", "cobertura_mapa_sobre_caba"), "caba")
    for key in ("total", "base_territorial_cp4", "base_barrial_con_soporte"):
        _summary(caba[key], records=key != "base_barrial_con_soporte", context=f"caba.{key}")
    for name, base in (("cobertura_territorial_cp4_sobre_caba", "base_territorial_cp4"),
                       ("cobertura_mapa_sobre_caba", "base_barrial_con_soporte")):
        coverage = caba[name]
        _object(coverage, COVERAGE_METRICS, f"caba.{name}")
        for key, metric in zip(COVERAGE_METRICS, METRICS):
            _number(coverage[key], f"caba.{name}.{key}", percentage=True)
            numerator, denominator = caba[base][metric], caba["total"][metric]
            expected = round(numerator / denominator * 100, 4) if denominator else 0
            _require(numerator <= denominator and abs(coverage[key] - expected) <= 0.00011,
                     f"caba.{name}: cobertura inconsistente")
    _require(all(caba["base_barrial_con_soporte"][m] <= caba["base_territorial_cp4"][m] for m in METRICS),
             "caba: base barrial superior a base territorial")
    _require(caba["cobertura_mapa_sobre_caba"]["deudores_pct"] >= 90
             and caba["cobertura_mapa_sobre_caba"]["deuda_total_pct"] >= 90, "caba: cobertura del mapa insuficiente")

    segments = obj["segmentos"]
    _require(type(segments) is list and 1 <= len(segments) <= 108, "segmentos: lista vacía o tamaño inválido")
    seen = set()
    for index, segment in enumerate(segments):
        context = f"segmentos[{index}]"
        _object(segment, ("filtros", "datos"), context)
        filters = segment["filtros"]
        _object(filters, ("sexo", "edad", "acreedor"), f"{context}.filtros")
        for key, allowed in (("sexo", SEXES), ("edad", AGES), ("acreedor", CREDITORS)):
            _require(filters[key] is None or type(filters[key]) is str and filters[key] in allowed,
                     f"{context}.filtros: valor no admitido")
        identity = (filters["sexo"], filters["edad"], filters["acreedor"])
        _require(identity not in seen, "segmentos: filtros duplicados")
        seen.add(identity)
        if index == 0:
            _require(identity == (None, None, None), "segmentos: falta el total inicial sin filtros")
        rows = segment["datos"]
        _require(type(rows) is list and len(rows) == 48, f"{context}.datos: se requieren 48 filas")
        for barrio_index, row in enumerate(rows):
            _require(type(row) is list and len(row) == 4, f"{context}.datos: cada fila debe contener cuatro métricas")
            for value in row:
                _number(value, f"{context}.datos")
            _require(row[1] <= row[0] and row[3] <= row[2], f"{context}.datos: mora superior al total")
            if index:
                total_row = segments[0]["datos"][barrio_index]
                for metric_index, value in enumerate(row):
                    tolerance = 0.00011 if metric_index < 2 else 1.0
                    _require(value <= total_row[metric_index] + tolerance,
                             f"{context}.datos: subgrupo superior al total del barrio")
    # El generador redondea cada barrio a 4 decimales / pesos enteros.
    for index, metric in enumerate(METRICS):
        try:
            actual = math.fsum(row[index] for row in segments[0]["datos"])
        except OverflowError:
            raise ValidationError("segmentos: suma barrial no finita") from None
        tolerance = 0.0025 if index < 2 else 24.5
        _require(abs(actual - caba["base_barrial_con_soporte"][metric]) <= tolerance,
                 "segmentos: total barrial inconsistente con el resumen agregado")
    return obj


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "JSON: campos duplicados no admitidos")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ValidationError("JSON: constantes no finitas no admitidas")


@contextmanager
def _aggregate_directory(root):
    """Ancla cada componente mediante openat/O_NOFOLLOW, incluso los ancestros."""
    path = Path(root)
    _require(".." not in path.parts, "Ruta raíz: traversal no admitido")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = None
    try:
        absolute = path.absolute()
        fd = os.open(absolute.anchor, flags)
        for part in (*absolute.parts[1:], "datos", "endeudamiento"):
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    except OSError:
        raise ValidationError("No se pudo abrir la ruta pública: falta, no es directorio o contiene enlaces simbólicos") from None
    finally:
        if fd is not None:
            os.close(fd)


def _read_json(directory_fd: int, filename: str, limit: int):
    _require(filename == "manifest.json" or re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])\.json", filename) is not None,
             "Archivo no permitido")
    try:
        fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        with os.fdopen(fd, "rb") as handle:
            _require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode), "Entrada pública no regular")
            raw = handle.read(limit + 1)
    except OSError:
        raise ValidationError("No se pudo leer un agregado referido: falta o contiene enlaces simbólicos") from None
    _require(len(raw) <= limit, "JSON agregado excede el tamaño permitido")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        if isinstance(error, ValidationError):
            raise
        raise ValidationError("JSON agregado inválido") from None


def validate_public_aggregates(root=ROOT) -> dict:
    """Abre sólo manifest.json y los meses canónicos que éste declara.

    No sigue enlaces, no admite rutas externas y no inspecciona otros archivos.
    staging_paths es una lista explícita de dos rutas relativas, apta para git add.
    """
    with _aggregate_directory(root) as directory_fd:
        manifest = validate_manifest(_read_json(directory_fd, "manifest.json", 65536))
        latest = None
        for period in manifest["periodos"]:
            aggregate = validate_period(_read_json(directory_fd, manifest["archivos"][period], 2 * 1024 * 1024), period)
            if period == manifest["ultimo_periodo"]:
                latest = aggregate
        _require(manifest["actualizado_utc"] == latest["generado_utc"], "manifest: actualización no coincide con el último agregado")
    return {"manifest": manifest, "latest": latest,
            "staging_paths": [f"{PUBLIC_DIR}/manifest.json", f"{PUBLIC_DIR}/{manifest['ultimo_periodo']}.json"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="raíz del repositorio")
    parser.add_argument("--staging-paths", "--print-paths", action="store_true", help="sólo rutas explícitas para staging")
    args = parser.parse_args(argv)
    try:
        result = validate_public_aggregates(args.root)
    except ValidationError as error:
        print(f"Endeudamiento público rechazado: {error}", file=sys.stderr)
        return 1
    if args.staging_paths:
        print("\n".join(result["staging_paths"]))
    else:
        print(f"Endeudamiento público válido: {len(result['manifest']['periodos'])} períodos; último {result['manifest']['ultimo_periodo']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
