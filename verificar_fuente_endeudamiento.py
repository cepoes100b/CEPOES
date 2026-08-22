from __future__ import annotations

import math
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests

BASE = "https://datos.mapadeladeuda.ar/"
REQUIRED_ALIASES = {
    "du": "deudores_unicos_total",
    "dm": "deudores_unicos_mora",
    "mt": "monto_total",
    "mm": "monto_mora",
    "tmo": "tasa_mora",
}
EXPECTED_CATEGORIES = {
    "Banco_Privado",
    "Banco_Publico",
    "Compania_Financiera",
    "Empresa_No_Financiera_Emisora_de_Tarjetas_de_Credito_o_Compra",
    "Neobanco",
    "Proveedor_No_Financiero_de_Credito",
}
EXPECTED_AGES = {"<=25", "26_35", "36_45", "46_55", "56_65", "66_75", ">75"}
EXPECTED_SEX = {"F", "M"}


def fail(msg: str) -> None:
    raise ValueError(msg)


def get_json(session: requests.Session, path: str) -> tuple[dict, requests.Response]:
    url = urljoin(BASE, path)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "datos.mapadeladeuda.ar":
        fail(f"ruta fuera del origen autorizado: {url}")
    response = session.get(url, timeout=60, headers={"Origin": "https://cepoes.org"})
    response.raise_for_status()
    if "json" not in (response.headers.get("content-type") or "").lower() and not path.endswith(".json"):
        fail(f"contenido inesperado: {path}")
    data = response.json()
    if not isinstance(data, dict):
        fail(f"JSON raíz no es objeto: {path}")
    return data, response


def pct(num: float, den: float) -> float:
    return (num / den * 100.0) if den else 0.0


def close(a: float, b: float, tol: float = 1e-4) -> bool:
    return math.isclose(float(a), float(b), rel_tol=0, abs_tol=tol)


def decode_rows(layer: dict) -> list[dict]:
    cols = layer.get("columns") or []
    aliases = layer.get("aliases") or {}
    rows = layer.get("rows") or []
    if not isinstance(cols, list) or not isinstance(aliases, dict) or not isinstance(rows, list):
        fail("estructura de slice inválida")
    for short, long_name in REQUIRED_ALIASES.items():
        if aliases.get(short) != long_name:
            fail(f"alias requerido cambió: {short} -> {aliases.get(short)!r}")
    out = []
    for row in rows:
        if not isinstance(row, list) or len(row) != len(cols):
            fail("fila de slice no coincide con columnas")
        item = {}
        for i, col in enumerate(cols):
            item[aliases.get(col, col)] = row[i]
        out.append(item)
    return out


def verify_layer(layer: dict, period: str, geo_ids: set[str]) -> dict:
    if layer.get("period") != period:
        fail(f"slice {period}: período inconsistente")
    if layer.get("level") != "barrio_caba" or str(layer.get("scope")) != "02":
        fail(f"slice {period}: nivel/scope inesperado")
    if layer.get("filters") not in ({}, None):
        fail(f"slice {period}: se esperaba capa sin filtros")
    rows = decode_rows(layer)
    if len(rows) != 48:
        fail(f"slice {period}: se esperaban 48 barrios y hay {len(rows)}")
    row_ids = {str(r.get("geo_id")) for r in rows}
    if len(row_ids) != 48 or row_ids != geo_ids:
        fail(f"slice {period}: universo geográfico no coincide con lookup")

    sums = {"deudores_unicos_total": 0, "deudores_unicos_mora": 0, "monto_total": 0, "monto_mora": 0}
    for row in rows:
        du = int(row["deudores_unicos_total"])
        dm = int(row["deudores_unicos_mora"])
        mt = float(row["monto_total"])
        mm = float(row["monto_mora"])
        tmo = float(row["tasa_mora"])
        if min(du, dm, mt, mm) < 0 or dm > du or mm > mt:
            fail(f"slice {period}: métricas inválidas en {row.get('geo_id')}")
        if not close(tmo, pct(mm, mt), tol=1e-3):
            fail(f"slice {period}: tasa de mora inconsistente en {row.get('geo_id')}")
        for key in sums:
            sums[key] += row[key]

    kpis = layer.get("kpis") or {}
    for key, total in sums.items():
        if not close(kpis.get(key, -1), total, tol=1e-3):
            fail(f"slice {period}: KPI {key} no coincide con suma barrial")
    if not close(kpis.get("tasa_mora", -1), pct(kpis["monto_mora"], kpis["monto_total"]), tol=1e-3):
        fail(f"slice {period}: KPI tasa_mora inconsistente")

    return {
        "periodo": period,
        "barrios": len(rows),
        "deudores": int(kpis["deudores_unicos_total"]),
        "deudores_mora": int(kpis["deudores_unicos_mora"]),
        "personas_mora_pct": round(pct(kpis["deudores_unicos_mora"], kpis["deudores_unicos_total"]), 4),
        "tasa_mora": round(float(kpis["tasa_mora"]), 4),
    }


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "CEPOES/1.0 (+https://cepoes.org)"})

    manifest, manifest_response = get_json(session, "manifest.json")
    if manifest.get("dataset") != "mapa-de-la-deuda":
        fail("dataset inesperado")
    if manifest.get("contract") != "mobile-slices-v2":
        fail("contrato de fuente cambió")
    if "barrio_caba" not in (manifest.get("levels") or []):
        fail("manifest ya no declara barrio_caba")
    if manifest_response.headers.get("access-control-allow-origin") != "*":
        fail("la fuente dejó de permitir lectura cross-origin desde cepoes.org")

    filters, _ = get_json(session, manifest["dimensions"]["filters"])
    categories = {x["id"] for x in filters.get("categorias", []) if x.get("id") != "__ALL__"}
    ages = {x["id"] for x in filters.get("rangos_edad", []) if x.get("id") != "__ALL__"}
    sex = {x["id"] for x in filters.get("sexos", []) if x.get("id") != "__ALL__"}
    if categories != EXPECTED_CATEGORIES:
        fail(f"categorías cambiaron: {sorted(categories)}")
    if ages != EXPECTED_AGES:
        fail(f"rangos de edad cambiaron: {sorted(ages)}")
    if sex != EXPECTED_SEX:
        fail(f"categorías de sexo cambiaron: {sorted(sex)}")

    metrics, _ = get_json(session, manifest["dimensions"]["metrics"])
    metric_ids = {x.get("id") for x in metrics.get("metrics", [])}
    required_metrics = {"tasa_mora", "monto_total", "monto_mora", "deudores_unicos_total", "deudores_unicos_mora"}
    if not required_metrics.issubset(metric_ids):
        fail(f"faltan métricas: {sorted(required_metrics - metric_ids)}")

    lookup, _ = get_json(session, manifest["geo"]["lookup"])
    caba_geo = [x for x in lookup.get("features", []) if x.get("level") == "barrio_caba" and str(x.get("scope")) == "02"]
    geo_ids = {str(x.get("geo_id")) for x in caba_geo}
    if len(caba_geo) != 48 or len(geo_ids) != 48:
        fail(f"lookup CABA debe tener 48 barrios; tiene {len(caba_geo)}")
    if any(x.get("source") != "IGN" for x in caba_geo):
        fail("la fuente geográfica dejó de declararse IGN")

    periods = manifest.get("periods") or []
    if len(periods) < 3:
        fail("se esperaban al menos tres períodos públicos")
    results = []
    for p in periods:
        period = str(p.get("id"))
        index, _ = get_json(session, p["index"])
        candidates = [
            x for x in index.get("availableSlices", [])
            if x.get("level") == "barrio_caba" and str(x.get("scope")) == "02" and (x.get("filters") or {}) == {}
        ]
        if len(candidates) != 1:
            fail(f"{period}: se esperaba un único slice CABA sin filtros; hay {len(candidates)}")
        descriptor = candidates[0]
        if descriptor.get("geographies") != 48:
            fail(f"{period}: descriptor no declara 48 barrios")
        layer, response = get_json(session, descriptor["path"])
        if response.headers.get("access-control-allow-origin") != "*":
            fail(f"{period}: slice dejó de ser legible cross-origin")
        results.append(verify_layer(layer, period, geo_ids))

    default_period = manifest.get("defaultPeriod")
    if default_period != periods[0].get("id"):
        fail("defaultPeriod no coincide con el período más reciente publicado")

    print("✔ fuente agregada de endeudamiento verificada")
    print(f"  fuente: {BASE} · contrato {manifest['contract']} · versión {manifest.get('version')}")
    print(f"  geografía: 48 barrios CABA · IGN · CORS abierto")
    print(f"  filtros: {len(categories)} categorías · {len(ages)} edades · {len(sex)} sexos")
    for r in results:
        print(
            f"  {r['periodo']}: {r['deudores']:,} deudores · {r['deudores_mora']:,} en mora · "
            f"personas en mora {r['personas_mora_pct']:.2f}% · tasa monto mora {r['tasa_mora']:.2f}%"
        )
    print("  modo CEPOES: referencia externa en tiempo de lectura; no se replica la base completa")


if __name__ == "__main__":
    main()
