#!/usr/bin/env python3
"""Genera la capa pública mensual de Endeudamiento por barrio.

Entrada:
- diagnostico_endeudamiento_productivo.json: agregados propios BCRA/ARCA por CP4;
- datos/endeudamiento/matriz_cp_barrio.json: matriz CP4->barrio previamente validada y congelada.

Salida:
- datos/endeudamiento/AAAA-MM.json
- datos/endeudamiento/manifest.json

No accede a microdatos ni a fuentes territoriales externas durante la actualización mensual.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INPUT = Path("diagnostico_endeudamiento_productivo.json")
MATRIX = Path("datos/endeudamiento/matriz_cp_barrio.json")
OUTDIR = Path("datos/endeudamiento")

METRICS = ("deudores", "personas_mora", "deuda_total_pesos", "deuda_mora_pesos", "registros")
AGES = ("le25", "26_35", "36_45", "46_55", "56_65", "66_75", "gt75", "desconocida")
SEXES = ("F", "M")
CATEGORIES = ("entidad_financiera", "emisora_tarjeta", "otro_pnfc")


def empty_metrics() -> dict[str, float]:
    return {k: 0.0 for k in METRICS}


def derived(v: dict[str, float]) -> dict[str, Any]:
    d = float(v.get("deudores", 0.0))
    m = float(v.get("personas_mora", 0.0))
    dt = float(v.get("deuda_total_pesos", 0.0))
    dm = float(v.get("deuda_mora_pesos", 0.0))
    return {
        "deudores": round(d, 4),
        "personas_mora": round(m, 4),
        "incidencia_mora_pct": round(m / d * 100, 4) if d else 0.0,
        "deuda_total_pesos": round(dt),
        "deuda_mora_pesos": round(dm),
        "tasa_mora_pct": round(dm / dt * 100, 4) if dt else 0.0,
        "registros": round(float(v.get("registros", 0.0)), 4),
    }


def load_matrix() -> tuple[list[str], dict[int, list[tuple[str, float]]], dict]:
    obj = json.loads(MATRIX.read_text(encoding="utf-8"))
    status = obj.get("estado_validacion")
    if status not in {"VALIDADA", "VALIDADA_TEMPORAL", "VALIDADA_CANDIDATA"}:
        raise SystemExit(f"Matriz no habilitada para generación: {status!r}")
    barrios = list(obj.get("barrios") or [])
    if len(barrios) != 48 or len(set(barrios)) != 48:
        raise SystemExit(f"La matriz debe contener 48 barrios únicos; contiene {len(barrios)}")
    by_cp: dict[int, list[tuple[str, float]]] = {}
    for row in obj.get("filas") or []:
        cp = int(row["cp4"])
        pesos = [(str(x["barrio"]), float(x["peso"])) for x in row.get("pesos") or []]
        if not pesos:
            raise SystemExit(f"CP {cp} sin ponderadores")
        s = sum(w for _, w in pesos)
        if abs(s - 1.0) > 1e-6:
            raise SystemExit(f"CP {cp}: ponderadores suman {s}, no 1")
        if any(b not in barrios or w < 0 for b, w in pesos):
            raise SystemExit(f"CP {cp}: ponderador inválido")
        by_cp[cp] = pesos
    return barrios, by_cp, obj


def distribute(rows: list[dict], by_cp: dict[int, list[tuple[str, float]]], key_parts: int) -> dict[tuple[str, ...], dict[str, dict[str, float]]]:
    out: dict[tuple[str, ...], dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(empty_metrics))
    for row in rows:
        parts = str(row["clave"]).split("|")
        if len(parts) != key_parts:
            raise SystemExit(f"Clave inesperada: {row['clave']!r}")
        cp = int(parts[0])
        seg = tuple(parts[1:])
        pesos = by_cp.get(cp)
        if not pesos:
            raise SystemExit(f"CP {cp} presente en BCRA pero ausente de la matriz")
        for barrio, w in pesos:
            ac = out[seg][barrio]
            for metric in METRICS:
                ac[metric] += float(row.get(metric, 0) or 0) * w
    return out


def add_segment(dst: dict, key: tuple, source: dict[str, dict[str, float]]) -> None:
    target = dst.setdefault(key, defaultdict(empty_metrics))
    for barrio, vals in source.items():
        ac = target[barrio]
        for metric in METRICS:
            ac[metric] += vals[metric]


def finalize_segment(filters: dict[str, str | None], barrio_names: list[str], data: dict[str, dict[str, float]]) -> dict:
    return {
        "filtros": filters,
        "barrios": [{"barrio": b, **derived(data.get(b, empty_metrics()))} for b in barrio_names],
    }


def main() -> int:
    src = json.loads(INPUT.read_text(encoding="utf-8"))
    periodo = str(src["periodo_deuda"])
    barrios, by_cp, matrix_obj = load_matrix()

    total_rows = src["agregado_cp_caba_1000_1499"]["filas"]
    cross_rows = src["agregado_cp_sexo_edad_caba_1000_1499"]["filas"]
    cat_cross_rows = src["agregado_cp_sexo_edad_categoria_caba_1000_1499"]["filas"]

    # Total: claves sólo CP.
    total_raw = []
    for r in total_rows:
        x = dict(r)
        x["clave"] = f"{r['clave']}|TOTAL"
        total_raw.append(x)
    total_dist = distribute(total_raw, by_cp, 2)[("TOTAL",)]

    # Cubos primitivos. Sexo y edad son mutuamente excluyentes, por lo que pueden sumarse sin duplicar personas.
    cross = distribute(cross_rows, by_cp, 3)  # (sexo, edad)
    cat_cross = distribute(cat_cross_rows, by_cp, 4)  # (sexo, edad, categoria)

    segmentos: list[dict] = []
    segmentos.append(finalize_segment({"sexo": None, "edad": None, "acreedor": None}, barrios, total_dist))

    # Sin filtro de acreedor.
    agg: dict[tuple, dict] = {}
    for (sexo, edad), data in cross.items():
        add_segment(agg, (sexo, edad), data)
        add_segment(agg, (sexo, None), data)
        add_segment(agg, (None, edad), data)
    for sexo in (None,) + SEXES:
        for edad in (None,) + AGES:
            if sexo is None and edad is None:
                continue
            data = agg.get((sexo, edad))
            if data is not None:
                segmentos.append(finalize_segment({"sexo": sexo, "edad": edad, "acreedor": None}, barrios, data))

    # Con filtro de acreedor. Cada categoría conserva unicidad de personas dentro de esa categoría.
    cagg: dict[tuple, dict] = {}
    for (sexo, edad, cat), data in cat_cross.items():
        add_segment(cagg, (sexo, edad, cat), data)
        add_segment(cagg, (sexo, None, cat), data)
        add_segment(cagg, (None, edad, cat), data)
        add_segment(cagg, (None, None, cat), data)
    for cat in CATEGORIES:
        for sexo in (None,) + SEXES:
            for edad in (None,) + AGES:
                data = cagg.get((sexo, edad, cat))
                if data is not None:
                    segmentos.append(finalize_segment({"sexo": sexo, "edad": edad, "acreedor": cat}, barrios, data))

    caba = src["escenarios"]["A_eeff_pnfc_prov00"]["indicadores"]
    territorial = src["escenarios"]["C_eeff_pnfc_prov00_y_cp1000_1499"]["indicadores"]

    out = {
        "schema": "cepoes-endeudamiento-barrios-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "periodo": periodo,
        "padron_fecha": src.get("padron_fecha"),
        "titulo": "Endeudamiento por barrio",
        "fuente": {
            "principal": "Banco Central de la República Argentina — Central de Deudores",
            "padron": "Padrón ARCA distribuido por BCRA",
            "elaboracion": "CEPOES",
        },
        "caba": {
            "total": caba,
            "base_territorial_cp4": territorial,
            "cobertura_territorial_cp4_sobre_caba": src.get("cobertura_territorial_cp4_sobre_caba"),
        },
        "filtros": {
            "sexos": list(SEXES),
            "edades": list(AGES),
            "acreedores": list(CATEGORIES),
        },
        "metodologia": {
            "nivel": "barrio",
            "naturaleza": "estimacion territorial agregada",
            "regla": "distribucion probabilistica de agregados BCRA/ARCA por CP4 entre barrios mediante matriz fija CP4-barrio",
            "no_es": "geolocalizacion individual ni conteo domiciliario exacto",
            "matriz_schema": matrix_obj.get("schema"),
            "matriz_periodo_calibracion": matrix_obj.get("periodo_calibracion"),
            "matriz_estado_validacion": matrix_obj.get("estado_validacion"),
            "actualizacion_mensual": "la matriz territorial permanece fija; cada período incorpora exclusivamente nuevos agregados BCRA/ARCA",
            "supresion": "las celdas demograficas o por acreedor con menos de 10 deudores se omiten antes de la territorializacion",
        },
        "segmentos": segmentos,
    }

    if len(segmentos[0]["barrios"]) != 48:
        raise SystemExit("La salida total no contiene 48 barrios")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    month_path = OUTDIR / f"{periodo}.json"
    month_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_path = OUTDIR / "manifest.json"
    prev = {}
    if manifest_path.exists():
        prev = json.loads(manifest_path.read_text(encoding="utf-8"))
    periods = sorted(set((prev.get("periodos") or []) + [periodo]))
    manifest = {
        "schema": "cepoes-endeudamiento-manifest-v1",
        "actualizado_utc": out["generado_utc"],
        "ultimo_periodo": max(periods),
        "periodos": periods,
        "archivos": {p: f"{p}.json" for p in periods},
        "fuente": "BCRA / Padrón ARCA — elaboración CEPOES",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"periodo": periodo, "barrios": 48, "segmentos": len(segmentos), "archivo": str(month_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
