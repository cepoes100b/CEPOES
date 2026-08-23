#!/usr/bin/env python3
"""Genera la capa pública mensual compacta de Endeudamiento por barrio.

Los indicadores mensuales provienen de BCRA/ARCA. La matriz territorial se mantiene
fija entre actualizaciones. Los CP4 sin soporte geográfico observado permanecen en
el total CABA pero no se imputan artificialmente a barrios.
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
PUBLIC_METRICS = ("deudores", "personas_mora", "deuda_total_pesos", "deuda_mora_pesos")
AGES = ("le25", "26_35", "36_45", "46_55", "56_65", "66_75", "gt75", "desconocida")
SEXES = ("F", "M")
CATEGORIES = ("entidad_financiera", "emisora_tarjeta", "otro_pnfc")


def empty_metrics() -> dict[str, float]:
    return {k: 0.0 for k in METRICS}


def ratio_pct(n: float, d: float) -> float:
    return round(n / d * 100, 4) if d else 0.0


def summary(v: dict[str, float]) -> dict[str, Any]:
    d = float(v.get("deudores", 0.0))
    m = float(v.get("personas_mora", 0.0))
    dt = float(v.get("deuda_total_pesos", 0.0))
    dm = float(v.get("deuda_mora_pesos", 0.0))
    return {
        "deudores": round(d, 4),
        "personas_mora": round(m, 4),
        "incidencia_mora_pct": ratio_pct(m, d),
        "deuda_total_pesos": round(dt),
        "deuda_mora_pesos": round(dm),
        "tasa_mora_pct": ratio_pct(dm, dt),
    }


def load_matrix() -> tuple[list[str], dict[int, list[tuple[str, float]]], dict, dict[str, int]]:
    obj = json.loads(MATRIX.read_text(encoding="utf-8"))
    status = obj.get("estado_validacion")
    if status not in {"VALIDADA", "VALIDADA_TEMPORAL", "VALIDADA_CANDIDATA"}:
        raise SystemExit(f"Matriz no habilitada para generación: {status!r}")

    barrios = list(obj.get("barrios") or [])
    if len(barrios) != 48 or len(set(barrios)) != 48:
        raise SystemExit(f"La matriz debe contener 48 barrios únicos; contiene {len(barrios)}")

    by_cp: dict[int, list[tuple[str, float]]] = {}
    total = soportados = 0
    for row in obj.get("filas") or []:
        total += 1
        cp = int(row["cp4"])
        if row.get("soporte_badata_observado") is not True:
            continue
        pesos = [(str(x["barrio"]), float(x["peso"])) for x in row.get("pesos") or []]
        if not pesos:
            raise SystemExit(f"CP {cp} con soporte geográfico pero sin ponderadores")
        s = sum(w for _, w in pesos)
        if abs(s - 1.0) > 1e-6:
            raise SystemExit(f"CP {cp}: ponderadores suman {s}, no 1")
        if any(b not in barrios or w < 0 for b, w in pesos):
            raise SystemExit(f"CP {cp}: ponderador inválido")
        by_cp[cp] = pesos
        soportados += 1

    if soportados < 250:
        raise SystemExit(f"Soporte geográfico insuficiente: sólo {soportados} CP4")
    return barrios, by_cp, obj, {
        "cp4_matriz": total,
        "cp4_con_soporte": soportados,
        "cp4_sin_soporte": total - soportados,
    }


def distribute(rows: list[dict], by_cp: dict[int, list[tuple[str, float]]], key_parts: int) -> dict[tuple[str, ...], dict[str, dict[str, float]]]:
    out: dict[tuple[str, ...], dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(empty_metrics))
    for row in rows:
        parts = str(row["clave"]).split("|")
        if len(parts) != key_parts:
            raise SystemExit(f"Clave inesperada: {row['clave']!r}")
        cp = int(parts[0])
        pesos = by_cp.get(cp)
        if not pesos:
            continue
        seg = tuple(parts[1:])
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


def compact_segment(filters: dict[str, str | None], barrio_names: list[str], data: dict[str, dict[str, float]]) -> dict:
    filas = []
    for barrio in barrio_names:
        v = data.get(barrio, empty_metrics())
        filas.append([
            round(float(v["deudores"]), 4),
            round(float(v["personas_mora"]), 4),
            round(float(v["deuda_total_pesos"])),
            round(float(v["deuda_mora_pesos"])),
        ])
    return {"filtros": filters, "datos": filas}


def sum_supported_total(rows: list[dict], by_cp: dict[int, list[tuple[str, float]]]) -> dict[str, float]:
    out = empty_metrics()
    for r in rows:
        cp = int(str(r["clave"]).split("|")[0])
        if cp not in by_cp:
            continue
        for metric in METRICS:
            out[metric] += float(r.get(metric, 0) or 0)
    return out


def main() -> int:
    src = json.loads(INPUT.read_text(encoding="utf-8"))
    periodo = str(src["periodo_deuda"])
    barrios, by_cp, matrix_obj, soporte_meta = load_matrix()

    total_rows = src["agregado_cp_caba_1000_1499"]["filas"]
    cross_rows = src["agregado_cp_sexo_edad_caba_1000_1499"]["filas"]
    cat_cross_rows = src["agregado_cp_sexo_edad_categoria_caba_1000_1499"]["filas"]

    total_raw = []
    for r in total_rows:
        x = dict(r)
        x["clave"] = f"{r['clave']}|TOTAL"
        total_raw.append(x)
    total_dist = distribute(total_raw, by_cp, 2)[("TOTAL",)]
    cross = distribute(cross_rows, by_cp, 3)
    cat_cross = distribute(cat_cross_rows, by_cp, 4)

    segmentos: list[dict] = [compact_segment({"sexo": None, "edad": None, "acreedor": None}, barrios, total_dist)]

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
                segmentos.append(compact_segment({"sexo": sexo, "edad": edad, "acreedor": None}, barrios, data))

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
                    segmentos.append(compact_segment({"sexo": sexo, "edad": edad, "acreedor": cat}, barrios, data))

    caba = src["escenarios"]["A_eeff_pnfc_prov00"]["indicadores"]
    territorial = src["escenarios"]["C_eeff_pnfc_prov00_y_cp1000_1499"]["indicadores"]
    supported_raw = sum_supported_total(total_rows, by_cp)
    cobertura_mapa = {
        "deudores_pct": ratio_pct(supported_raw["deudores"], caba["deudores"]),
        "personas_mora_pct": ratio_pct(supported_raw["personas_mora"], caba["personas_mora"]),
        "deuda_total_pct": ratio_pct(supported_raw["deuda_total_pesos"], caba["deuda_total_pesos"]),
        "deuda_mora_pct": ratio_pct(supported_raw["deuda_mora_pesos"], caba["deuda_mora_pesos"]),
    }

    out = {
        "schema": "cepoes-endeudamiento-barrios-v2-compact",
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
            "base_barrial_con_soporte": summary(supported_raw),
            "cobertura_territorial_cp4_sobre_caba": src.get("cobertura_territorial_cp4_sobre_caba"),
            "cobertura_mapa_sobre_caba": cobertura_mapa,
        },
        "filtros": {
            "sexos": list(SEXES),
            "edades": list(AGES),
            "acreedores": list(CATEGORIES),
        },
        "barrios": barrios,
        "metricas_segmento": list(PUBLIC_METRICS),
        "metodologia": {
            "nivel": "barrio",
            "naturaleza": "estimacion territorial agregada",
            "regla": "distribucion probabilistica de agregados BCRA/ARCA por CP4 entre barrios mediante matriz fija CP4-barrio",
            "no_es": "geolocalizacion individual ni conteo domiciliario exacto",
            "matriz_schema": matrix_obj.get("schema"),
            "matriz_periodo_calibracion": matrix_obj.get("periodo_calibracion"),
            "matriz_estado_validacion": matrix_obj.get("estado_validacion"),
            "soporte_cp4": soporte_meta,
            "tratamiento_sin_soporte": "los CP4 sin soporte geografico observado no se imputan a barrios; permanecen incluidos en el total CABA",
            "actualizacion_mensual": "la matriz territorial permanece fija; cada período incorpora exclusivamente nuevos agregados BCRA/ARCA",
            "supresion": "las celdas demograficas o por acreedor con menos de 10 deudores se omiten antes de la territorializacion",
        },
        "segmentos": segmentos,
    }

    if len(barrios) != 48 or len(segmentos[0]["datos"]) != 48:
        raise SystemExit("La salida total no contiene 48 barrios")
    if cobertura_mapa["deudores_pct"] < 90 or cobertura_mapa["deuda_total_pct"] < 90:
        raise SystemExit(f"Cobertura efectiva del mapa insuficiente: {cobertura_mapa}")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    month_path = OUTDIR / f"{periodo}.json"
    month_path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

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
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({
        "periodo": periodo,
        "barrios": 48,
        "segmentos": len(segmentos),
        "cobertura_mapa_sobre_caba": cobertura_mapa,
        "bytes": month_path.stat().st_size,
        "archivo": str(month_path),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
