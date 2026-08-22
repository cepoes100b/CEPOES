#!/usr/bin/env python3
"""Prueba reglas de CP -> coordenada -> barrio usando sólo agregados CEPOES.

Entrada: diagnostico_universo_territorial_integral.json, que contiene agregados por
código postal y ningún identificador personal.

Hipótesis geográfica: GeoNames AR (CP tradicional de 4 dígitos) aporta coordenadas
estimadas. Las coordenadas se intersectan contra la MISMA capa `barrios_caba`
publicada por Mapa de la Deuda dentro de su PMTiles. Los 48 valores públicos de
junio 2026 se usan sólo como benchmark de validación.

Se prueban varias reglas sin seleccionar a priori la que mejor coincida:
- media de coordenadas GeoNames del CP dentro del bbox CABA;
- mediana de coordenadas;
- media entre observaciones de máxima accuracy GeoNames;
- moda del barrio obtenido al geolocalizar todas las observaciones del CP.

No se descargan ni procesan microdatos BCRA/ARCA.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import math
import statistics
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import mapbox_vector_tile
import requests
from pmtiles.reader import Reader, MmapSource
from pmtiles.tile import Compression
from shapely.geometry import Point, shape

INPUT = Path("diagnostico_universo_territorial_integral.json")
PMTILES = Path("geo_admin_argentina.pmtiles")
OUTPUT = Path("diagnostico_geolocalizacion_cp_mapadeladeuda.json")

GEONAMES_URL = "https://download.geonames.org/export/zip/AR.zip"
PMTILES_URL = "https://datos.mapadeladeuda.ar/tiles/geo_admin_argentina.pmtiles"
LOOKUP_URL = "https://datos.mapadeladeuda.ar/geo/lookup.json"
SLICE_URL = "https://datos.mapadeladeuda.ar/periods/2026-06/slices/barrio_caba/02/default.json"


def get(url: str, *, timeout: int = 120) -> requests.Response:
    r = requests.get(url, headers={"User-Agent": "CEPOES-validacion-territorial/1.0"}, timeout=timeout)
    r.raise_for_status()
    return r


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.upper().replace("-", " ").split())


def cargar_lookup() -> tuple[dict, dict[str, str], tuple[float, float, float, float]]:
    obj = get(LOOKUP_URL).json()
    barrios: dict[str, dict] = {}
    caba_bbox = None
    for f in obj.get("features", []):
        if f.get("level") == "barrio_caba" and str(f.get("scope")) == "02":
            barrios[str(f["geo_id"])] = f
        if f.get("level") == "provincia" and str(f.get("geo_id")) == "02":
            caba_bbox = tuple(float(x) for x in f["bbox"])
    if len(barrios) != 48 or not caba_bbox:
        raise RuntimeError(f"Lookup inesperado: {len(barrios)} barrios; bbox={caba_bbox}")
    por_nombre = {norm(v["nombre"]): k for k, v in barrios.items()}
    return barrios, por_nombre, caba_bbox


def cargar_benchmark() -> dict[str, dict]:
    obj = get(SLICE_URL).json()
    if obj.get("contract") != "mobile-slices-v2":
        raise RuntimeError(f"Contrato slice inesperado: {obj.get('contract')}")
    cols = obj["columns"]
    aliases = obj.get("aliases", {})
    out = {}
    for raw in obj["rows"]:
        row = raw if isinstance(raw, dict) else dict(zip(cols, raw))
        gid = str(row["geo_id"])
        out[gid] = {aliases.get(k, k): v for k, v in row.items() if k != "geo_id"}
    if len(out) != 48:
        raise RuntimeError(f"Benchmark inesperado: {len(out)} barrios")
    return out


def cargar_geonames(caba_bbox) -> tuple[dict[int, list[dict]], dict]:
    data = get(GEONAMES_URL).content
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".txt")]
        if not names:
            raise RuntimeError("AR.zip de GeoNames no contiene .txt")
        text = z.read(names[0]).decode("utf-8", errors="replace")
    west, south, east, north = caba_bbox
    por_cp = defaultdict(list)
    leidas = 0
    rango = 0
    bbox = 0
    for row in csv.reader(io.StringIO(text), delimiter="\t"):
        if len(row) < 12:
            continue
        leidas += 1
        cp_s = row[1].strip()
        if len(cp_s) != 4 or not cp_s.isdigit():
            continue
        cp = int(cp_s)
        if not 1000 <= cp <= 1499:
            continue
        rango += 1
        try:
            lat = float(row[9]); lon = float(row[10])
        except ValueError:
            continue
        # Filtrar por la envolvente exacta CABA publicada por Mapa. Se conserva
        # admin1 sólo como metadato diagnóstico, no como criterio de selección.
        if not (west <= lon <= east and south <= lat <= north):
            continue
        bbox += 1
        try:
            accuracy = int(row[11]) if row[11].strip() else 0
        except ValueError:
            accuracy = 0
        por_cp[cp].append({
            "place": row[2], "admin1": row[3], "lat": lat, "lon": lon, "accuracy": accuracy,
        })
    return dict(por_cp), {
        "url": GEONAMES_URL,
        "bytes_zip": len(data),
        "filas_leidas": leidas,
        "filas_cp_1000_1499": rango,
        "filas_dentro_bbox_caba": bbox,
        "cp_con_observaciones_caba": len(por_cp),
    }


def descargar_pmtiles() -> dict:
    r = get(PMTILES_URL, timeout=240)
    PMTILES.write_bytes(r.content)
    if PMTILES.stat().st_size < 1000:
        raise RuntimeError("PMTiles inesperadamente pequeño")
    return {"url": PMTILES_URL, "bytes": PMTILES.stat().st_size}


def xy_float(lon: float, lat: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    xf = (lon + 180.0) / 360.0 * n
    lat = max(min(lat, 85.05112878), -85.05112878)
    yf = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return xf, yf


class BarrioLocator:
    def __init__(self, por_nombre: dict[str, str]):
        self.fh = open(PMTILES, "rb")
        self.reader = Reader(MmapSource(self.fh))
        self.header = self.reader.header()
        self.metadata = self.reader.metadata()
        self.por_nombre = por_nombre
        self.cache = {}
        self.sample_properties = []

    def close(self):
        self.fh.close()

    def _decode_tile(self, z: int, x: int, y: int):
        key = (z, x, y)
        if key in self.cache:
            return self.cache[key]
        raw = self.reader.get(z, x, y)
        if raw is None:
            self.cache[key] = None
            return None
        comp = self.header.get("tile_compression")
        if comp == Compression.GZIP or getattr(comp, "value", None) == Compression.GZIP.value or comp == Compression.GZIP.value:
            raw = gzip.decompress(raw)
        decoded = mapbox_vector_tile.decode(raw, default_options={"y_coord_down": True})
        self.cache[key] = decoded
        return decoded

    def localizar(self, lon: float, lat: float):
        maxz = int(self.header["max_zoom"])
        minz = int(self.header["min_zoom"])
        # Descender desde el mayor detalle hasta encontrar la capa. La capa puede
        # no estar presente en todos los zooms de un PMTiles multicapas.
        for z in range(maxz, minz - 1, -1):
            xf, yf = xy_float(lon, lat, z)
            x = int(math.floor(xf)); y = int(math.floor(yf))
            dec = self._decode_tile(z, x, y)
            if not dec or "barrios_caba" not in dec:
                continue
            layer = dec["barrios_caba"]
            extent = float(layer.get("extent", 4096))
            p = Point((xf - x) * extent, (yf - y) * extent)
            for feat in layer.get("features", []):
                try:
                    if not shape(feat["geometry"]).covers(p):
                        continue
                except Exception:
                    continue
                props = feat.get("properties") or {}
                if len(self.sample_properties) < 5:
                    self.sample_properties.append(props)
                for k in ("geo_id", "id", "GEO_ID"):
                    if props.get(k) and str(props[k]).startswith("BARRIO_"):
                        return str(props[k]), z
                for k in ("nombre", "name", "barrio", "BARRIO"):
                    if props.get(k):
                        gid = self.por_nombre.get(norm(props[k]))
                        if gid:
                            return gid, z
                # Algunos tiles usan source_id como nombre/ID estable.
                sid = props.get("source_id")
                if sid:
                    gid = self.por_nombre.get(norm(sid))
                    if gid:
                        return gid, z
        return None, None


def punto_candidato(rows: list[dict], metodo: str):
    if metodo == "media":
        return statistics.fmean(r["lon"] for r in rows), statistics.fmean(r["lat"] for r in rows)
    if metodo == "mediana":
        return statistics.median(r["lon"] for r in rows), statistics.median(r["lat"] for r in rows)
    if metodo == "max_accuracy_media":
        mx = max(r["accuracy"] for r in rows)
        rr = [r for r in rows if r["accuracy"] == mx]
        return statistics.fmean(r["lon"] for r in rr), statistics.fmean(r["lat"] for r in rr)
    raise ValueError(metodo)


def asignaciones(por_cp: dict[int, list[dict]], locator: BarrioLocator) -> tuple[dict[str, dict[int, str]], dict]:
    metodos = {"media": {}, "mediana": {}, "max_accuracy_media": {}, "moda_barrio_puntos": {}}
    diag = {"puntos_geonames_localizados": 0, "puntos_geonames_sin_barrio": 0, "cp_ambiguos_por_puntos": 0}
    for cp, rows in sorted(por_cp.items()):
        barrios_puntos = []
        for r in rows:
            gid, _ = locator.localizar(r["lon"], r["lat"])
            if gid:
                barrios_puntos.append(gid); diag["puntos_geonames_localizados"] += 1
            else:
                diag["puntos_geonames_sin_barrio"] += 1
        if len(set(barrios_puntos)) > 1:
            diag["cp_ambiguos_por_puntos"] += 1
        if barrios_puntos:
            c = Counter(barrios_puntos)
            # desempate determinista: mayor frecuencia y luego geo_id
            gid = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            metodos["moda_barrio_puntos"][cp] = gid
        for metodo in ("media", "mediana", "max_accuracy_media"):
            lon, lat = punto_candidato(rows, metodo)
            gid, _ = locator.localizar(lon, lat)
            if gid:
                metodos[metodo][cp] = gid
    return metodos, diag


def pearson(a, b):
    if len(a) < 2:
        return None
    ma = statistics.fmean(a); mb = statistics.fmean(b)
    num = sum((x-ma)*(y-mb) for x,y in zip(a,b))
    da = math.sqrt(sum((x-ma)**2 for x in a)); db = math.sqrt(sum((y-mb)**2 for y in b))
    return num/(da*db) if da and db else None


def comparar_benchmark(agg_barrio: dict[str, dict], benchmark: dict[str, dict]) -> dict:
    pares = {
        "deudores": ("deudores", "deudores_unicos_total", 1.0),
        "personas_mora": ("personas_mora", "deudores_unicos_mora", 1.0),
        # Mapa publica montos en miles de pesos; nuestro agregado está en pesos.
        "deuda_total": ("deuda_total_pesos", "monto_total", 1/1000),
        "deuda_mora": ("deuda_mora_pesos", "monto_mora", 1/1000),
    }
    out = {}
    for etiqueta, (nuestro, ref, escala) in pares.items():
        ours = [float(agg_barrio.get(g, {}).get(nuestro, 0))*escala for g in sorted(benchmark)]
        refs = [float(benchmark[g].get(ref, 0) or 0) for g in sorted(benchmark)]
        so = sum(ours); sr = sum(refs)
        wape_raw = sum(abs(x-y) for x,y in zip(ours, refs))/sr*100 if sr else None
        factor = sr/so if so else 0
        normed = [x*factor for x in ours]
        wape_norm = sum(abs(x-y) for x,y in zip(normed, refs))/sr*100 if sr else None
        out[etiqueta] = {
            "nuestro_total_asignado": round(so, 3),
            "benchmark_total_48": round(sr, 3),
            "wape_raw_pct": round(wape_raw, 3) if wape_raw is not None else None,
            "wape_distribucion_normalizada_pct": round(wape_norm, 3) if wape_norm is not None else None,
            "correlacion_pearson": round(pearson(ours, refs), 4) if pearson(ours, refs) is not None else None,
        }
    return out


def main() -> int:
    base = json.loads(INPUT.read_text(encoding="utf-8"))
    cp_rows = {int(r["clave"]): r for r in base["agregado_cp_1000_1499"]["filas"]}
    if len(cp_rows) < 300:
        raise RuntimeError(f"Agregado CP inesperadamente corto: {len(cp_rows)}")

    barrios, por_nombre, caba_bbox = cargar_lookup()
    benchmark = cargar_benchmark()
    geonames, meta_geonames = cargar_geonames(caba_bbox)
    meta_pmtiles = descargar_pmtiles()

    locator = BarrioLocator(por_nombre)
    try:
        metodos, diag = asignaciones(geonames, locator)
        meta_pmtiles.update({
            "header": {k: (v.value if hasattr(v, "value") else v) for k, v in locator.header.items()},
            "metadata": locator.metadata,
            "sample_properties": locator.sample_properties,
        })
    finally:
        locator.close()

    resultados = {}
    for metodo, mapa_cp in metodos.items():
        agg = defaultdict(lambda: {
            "deudores": 0, "personas_mora": 0, "deuda_total_pesos": 0,
            "deuda_mora_pesos": 0, "registros": 0,
        })
        cp_asignados = []
        for cp, row in cp_rows.items():
            gid = mapa_cp.get(cp)
            if not gid:
                continue
            cp_asignados.append(cp)
            for f in ("deudores", "personas_mora", "deuda_total_pesos", "deuda_mora_pesos", "registros"):
                agg[gid][f] += int(row.get(f, 0) or 0)
        total_deudores = sum(r["deudores"] for r in cp_rows.values())
        cubiertos = sum(cp_rows[c]["deudores"] for c in cp_asignados)
        resultados[metodo] = {
            "cp_asignados": len(cp_asignados),
            "cp_sin_asignar": sorted(set(cp_rows) - set(cp_asignados)),
            "cobertura_deudores_pct": round(cubiertos/total_deudores*100, 4) if total_deudores else 0,
            "barrios_con_datos": len(agg),
            "comparacion_48_barrios": comparar_benchmark(dict(agg), benchmark),
            "agregado_barrial": [
                {"geo_id": gid, "nombre": barrios[gid]["nombre"], **agg.get(gid, {})}
                for gid in sorted(barrios)
            ],
            "cp_a_barrio": [{"cp": cp, "geo_id": mapa_cp[cp]} for cp in sorted(mapa_cp) if cp in cp_rows],
        }

    # Ranking no fuerza coincidencia: usa sólo el error distributivo normalizado de
    # deudores y mora para orientar la siguiente auditoría.
    ranking = []
    for metodo, r in resultados.items():
        c = r["comparacion_48_barrios"]
        score = statistics.fmean([
            c["deudores"]["wape_distribucion_normalizada_pct"],
            c["personas_mora"]["wape_distribucion_normalizada_pct"],
        ])
        ranking.append({"metodo": metodo, "score_wape_promedio_deudores_mora": round(score, 3)})
    ranking.sort(key=lambda x: x["score_wape_promedio_deudores_mora"])

    out = {
        "schema": "cepoes-geolocalizacion-cp-mapadeladeuda-v1",
        "periodo": "2026-06",
        "input": {
            "schema": base.get("schema"),
            "cp_agregados": len(cp_rows),
            "microdatos_personales": False,
            "nota": "El agregado CP de la corrida integral se usa como insumo; no se reabre PADRON/DEUDORES.",
        },
        "fuentes": {
            "geonames": meta_geonames,
            "geonames_documentacion": "https://www.geonames.org/export/zip/",
            "mapa_lookup": LOOKUP_URL,
            "mapa_slice_benchmark": SLICE_URL,
            "mapa_pmtiles": meta_pmtiles,
        },
        "criterio": {
            "bbox_caba_mapa": caba_bbox,
            "geometria_barrios": "capa barrios_caba del PMTiles público de Mapa de la Deuda",
            "benchmark": "48 agregados públicos de junio 2026; sólo QA, no fuente de producción",
            "advertencia_geonames": "GeoNames declara coordenadas estimadas y datos AR de CP tradicionales; se prueba como hipótesis, no se presume que sea la fuente usada por Mapa de la Deuda.",
        },
        "diagnostico_geografico": diag,
        "ranking_exploratorio": ranking,
        "resultados": resultados,
        "privacidad": {
            "microdatos_bcra_arca_leidos": False,
            "identificadores_personales_leidos": False,
            "salida_solo_agregada": True,
        },
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "geonames": meta_geonames,
        "pmtiles_bytes": meta_pmtiles["bytes"],
        "diag": diag,
        "ranking": ranking,
        "resumen": {
            m: {
                "cp": r["cp_asignados"],
                "cobertura_deudores_pct": r["cobertura_deudores_pct"],
                "barrios": r["barrios_con_datos"],
                "deudores": r["comparacion_48_barrios"]["deudores"],
                "mora": r["comparacion_48_barrios"]["personas_mora"],
            } for m, r in resultados.items()
        }
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
