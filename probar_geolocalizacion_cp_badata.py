#!/usr/bin/env python3
"""Prueba territorial liviana usando puntos oficiales de Buenos Aires Data.

Objetivo: aproximar la etapa CP tradicional -> ubicación sin volver a leer PADRON ni
DEUDORES. Se usa el dataset oficial `Mobiliario Urbano`, que publica coordenadas,
barrio, código postal tradicional y CPA. Las coordenadas se intersectan contra la
misma capa `barrios_caba` del PMTiles público de Mapa de la Deuda.

Se prueban cuatro reglas:
1. barrio modal entre los puntos oficiales de cada CP;
2. barrio que contiene la media de coordenadas del CP;
3. barrio que contiene la mediana de coordenadas del CP;
4. asignación fraccional según la distribución de puntos del CP entre barrios
   (sólo diagnóstico de distribución; no implica personas fraccionarias en producto).

Los 48 agregados de Mapa de la Deuda se usan sólo como benchmark de QA.
"""
from __future__ import annotations

import csv
import io
import json
import math
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import requests

import probar_geolocalizacion_cp_mapadeladeuda as geo

INPUT = Path("diagnostico_universo_territorial_integral.json")
OUTPUT = Path("diagnostico_geolocalizacion_cp_badata.json")

BADATA_URL = (
    "https://data.buenosaires.gob.ar/dataset/mobiliario-urbano/"
    "resource/juqdkmgo-1441-resource/download"
)
BADATA_PAGE = (
    "https://data.buenosaires.gob.ar/dataset/mobiliario-urbano/"
    "resource/juqdkmgo-1441-resource"
)


def normalizar(s: str) -> str:
    x = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return "_".join(x.strip().lower().replace("-", "_").split())


def numero(v):
    if v is None:
        return None
    s = str(v).strip().replace("\u00a0", "")
    if not s:
        return None
    # Decimal comma only when no decimal point is present.
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def cp4(v):
    n = numero(v)
    if n is None:
        return None
    i = int(round(n))
    return i if 1000 <= i <= 1499 else None


def descargar_y_leer() -> tuple[list[dict], dict]:
    r = requests.get(
        BADATA_URL,
        headers={"User-Agent": "CEPOES-validacion-territorial/1.0"},
        timeout=120,
        allow_redirects=True,
    )
    r.raise_for_status()
    raw = r.content
    if len(raw) < 1000:
        raise RuntimeError(f"Mobiliario Urbano inesperadamente pequeño: {len(raw)} bytes")

    texto = None
    encoding = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            texto = raw.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        raise RuntimeError("No se pudo decodificar CSV de BA Data")

    primera = next((ln for ln in texto.splitlines() if ln.strip()), "")
    delimitador = max((";", ",", "\t"), key=lambda d: primera.count(d))
    lector = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    if not lector.fieldnames:
        raise RuntimeError("CSV sin encabezado")
    campos = {normalizar(c): c for c in lector.fieldnames if c}

    def col(*candidatos):
        for c in candidatos:
            if c in campos:
                return campos[c]
        return None

    c_cp = col("codigo_postal", "cod_postal", "cp")
    c_lon = col("long", "lng", "lon", "longitud")
    c_lat = col("lat", "latitud")
    c_barrio = col("barrio")
    if not (c_cp and c_lon and c_lat):
        raise RuntimeError(
            f"Faltan columnas CP/lon/lat. Campos normalizados={sorted(campos)}"
        )

    filas = []
    leidas = 0
    descartadas = 0
    for row in lector:
        leidas += 1
        cp = cp4(row.get(c_cp))
        lon = numero(row.get(c_lon))
        lat = numero(row.get(c_lat))
        if cp is None or lon is None or lat is None:
            descartadas += 1
            continue
        if not (-59.0 < lon < -57.5 and -35.0 < lat < -34.0):
            descartadas += 1
            continue
        filas.append({
            "cp": cp,
            "lon": lon,
            "lat": lat,
            "barrio_publicado": str(row.get(c_barrio) or "").strip() if c_barrio else "",
        })

    meta = {
        "pagina": BADATA_PAGE,
        "url_descarga": BADATA_URL,
        "url_final": r.url,
        "bytes": len(raw),
        "content_type": r.headers.get("content-type", ""),
        "encoding": encoding,
        "delimitador": delimitador,
        "campos_originales": lector.fieldnames,
        "columnas_usadas": {"cp": c_cp, "lon": c_lon, "lat": c_lat, "barrio": c_barrio},
        "filas_leidas": leidas,
        "filas_validas_cp_coord": len(filas),
        "filas_descartadas": descartadas,
        "cp_distintos": len({x["cp"] for x in filas}),
    }
    if len(filas) < 500 or meta["cp_distintos"] < 30:
        raise RuntimeError(f"Cobertura BA Data insuficiente: {meta}")
    return filas, meta


def candidato_centro(rows, metodo):
    if metodo == "media":
        return statistics.fmean(x["lon"] for x in rows), statistics.fmean(x["lat"] for x in rows)
    if metodo == "mediana":
        return statistics.median(x["lon"] for x in rows), statistics.median(x["lat"] for x in rows)
    raise ValueError(metodo)


def comparar(agg, benchmark):
    # Reutiliza exactamente el comparador del experimento anterior.
    return geo.comparar_benchmark(agg, benchmark)


def main() -> int:
    base = json.loads(INPUT.read_text(encoding="utf-8"))
    cp_rows = {int(r["clave"]): r for r in base["agregado_cp_1000_1499"]["filas"]}
    if len(cp_rows) < 300:
        raise RuntimeError(f"Agregado CP inesperado: {len(cp_rows)}")

    barrios, por_nombre, _bbox = geo.cargar_lookup()
    benchmark = geo.cargar_benchmark()
    filas, meta_badata = descargar_y_leer()
    meta_pmtiles = geo.descargar_pmtiles()

    locator = geo.BarrioLocator(por_nombre)
    por_cp = defaultdict(list)
    coincidencia_barrio_publicado = Counter()
    puntos_sin_barrio = 0
    try:
        for x in filas:
            gid, _ = locator.localizar(x["lon"], x["lat"])
            if not gid:
                puntos_sin_barrio += 1
                continue
            x = dict(x)
            x["geo_id"] = gid
            por_cp[x["cp"]].append(x)
            if x["barrio_publicado"]:
                esperado = por_nombre.get(geo.norm(x["barrio_publicado"]))
                if esperado:
                    coincidencia_barrio_publicado["comparables"] += 1
                    coincidencia_barrio_publicado["coinciden"] += int(esperado == gid)
        meta_pmtiles.update({
            "header": {k: (v.value if hasattr(v, "value") else v) for k, v in locator.header.items()},
            "metadata": locator.metadata,
            "sample_properties": locator.sample_properties,
        })

        asignaciones = {"moda_puntos_badata": {}, "media_coordenadas_badata": {}, "mediana_coordenadas_badata": {}}
        pesos = {}
        ambiguos = 0
        for cp, rr in sorted(por_cp.items()):
            conteo = Counter(x["geo_id"] for x in rr)
            if len(conteo) > 1:
                ambiguos += 1
            asignaciones["moda_puntos_badata"][cp] = sorted(conteo.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            pesos[cp] = {gid: n / len(rr) for gid, n in sorted(conteo.items())}
            for metodo, nombre in (("media", "media_coordenadas_badata"), ("mediana", "mediana_coordenadas_badata")):
                lon, lat = candidato_centro(rr, metodo)
                gid, _ = locator.localizar(lon, lat)
                if gid:
                    asignaciones[nombre][cp] = gid
    finally:
        locator.close()

    total_deudores_cp = sum(int(r["deudores"]) for r in cp_rows.values())
    resultados = {}

    for metodo, mapa in asignaciones.items():
        agg = defaultdict(lambda: defaultdict(float))
        cp_cubiertos = []
        for cp, r in cp_rows.items():
            gid = mapa.get(cp)
            if not gid:
                continue
            cp_cubiertos.append(cp)
            for f in ("deudores", "personas_mora", "deuda_total_pesos", "deuda_mora_pesos", "registros"):
                agg[gid][f] += float(r.get(f, 0) or 0)
        cub = sum(int(cp_rows[cp]["deudores"]) for cp in cp_cubiertos)
        resultados[metodo] = {
            "cp_asignados": len(cp_cubiertos),
            "cobertura_deudores_pct": round(cub / total_deudores_cp * 100, 4) if total_deudores_cp else 0,
            "barrios_con_datos": len(agg),
            "comparacion_48_barrios": comparar(dict(agg), benchmark),
            "cp_a_barrio": [{"cp": cp, "geo_id": mapa[cp], "n_puntos_badata": len(por_cp[cp])} for cp in sorted(mapa) if cp in cp_rows],
        }

    # Fraccional: útil para saber si la nube oficial contiene suficiente información
    # para recuperar la distribución territorial. No se propone como conteo final de
    # personas; es una prueba de sensibilidad/ecológica.
    agg_f = defaultdict(lambda: defaultdict(float))
    cp_frac = []
    for cp, r in cp_rows.items():
        if cp not in pesos:
            continue
        cp_frac.append(cp)
        for gid, w in pesos[cp].items():
            for f in ("deudores", "personas_mora", "deuda_total_pesos", "deuda_mora_pesos", "registros"):
                agg_f[gid][f] += float(r.get(f, 0) or 0) * w
    cub_f = sum(int(cp_rows[cp]["deudores"]) for cp in cp_frac)
    resultados["fraccional_puntos_badata_diagnostico"] = {
        "cp_asignados": len(cp_frac),
        "cobertura_deudores_pct": round(cub_f / total_deudores_cp * 100, 4) if total_deudores_cp else 0,
        "barrios_con_datos": len(agg_f),
        "comparacion_48_barrios": comparar(dict(agg_f), benchmark),
        "advertencia": "Asignación fraccional sólo para diagnóstico distributivo; no representa personas fraccionarias ni se adopta como metodología de producción.",
    }

    ranking = []
    for metodo, r in resultados.items():
        c = r["comparacion_48_barrios"]
        score = statistics.fmean([
            c["deudores"]["wape_distribucion_normalizada_pct"],
            c["personas_mora"]["wape_distribucion_normalizada_pct"],
        ])
        ranking.append({"metodo": metodo, "score_wape_promedio_deudores_mora": round(score, 3)})
    ranking.sort(key=lambda x: x["score_wape_promedio_deudores_mora"])

    comparables = coincidencia_barrio_publicado["comparables"]
    out = {
        "schema": "cepoes-geolocalizacion-cp-badata-v1",
        "periodo": "2026-06",
        "input": {"cp_agregados_bcra": len(cp_rows), "microdatos_bcra_arca": False},
        "fuentes": {
            "badata_mobiliario_urbano": meta_badata,
            "mapa_lookup": geo.LOOKUP_URL,
            "mapa_slice_benchmark": geo.SLICE_URL,
            "mapa_pmtiles": meta_pmtiles,
        },
        "controles": {
            "puntos_badata_localizados_en_barrio_mapa": sum(len(v) for v in por_cp.values()),
            "puntos_badata_sin_barrio_mapa": puntos_sin_barrio,
            "cp_badata_con_barrio_mapa": len(por_cp),
            "cp_ambiguos_multiples_barrios": ambiguos,
            "comparables_con_barrio_publicado_badata": comparables,
            "coincidencia_barrio_publicado_vs_pmtiles_pct": round(coincidencia_barrio_publicado["coinciden"] / comparables * 100, 4) if comparables else None,
        },
        "ranking_exploratorio": ranking,
        "resultados": resultados,
        "privacidad": {
            "microdatos_bcra_arca_leidos": False,
            "identificadores_personales_leidos": False,
            "solo_puntos_publicos_institucionales_y_agregados": True,
        },
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "badata": meta_badata,
        "controles": out["controles"],
        "ranking": ranking,
        "resumen": {
            m: {
                "cp": r["cp_asignados"],
                "cobertura": r["cobertura_deudores_pct"],
                "barrios": r["barrios_con_datos"],
                "deudores": r["comparacion_48_barrios"]["deudores"],
                "mora": r["comparacion_48_barrios"]["personas_mora"],
            } for m, r in resultados.items()
        },
    }, ensure_ascii=False, indent=2))

    if max(r["cp_asignados"] for r in resultados.values()) < 30:
        raise SystemExit("Cobertura CP insuficiente")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
