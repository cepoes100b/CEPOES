#!/usr/bin/env python3
"""Reconstruye y valida una matriz probabilística CP4 -> barrio CABA.

La matriz se calibra exclusivamente con métricas de stock (deudores totales y
monto total) y se valida con métricas de mora que el ajuste no vio. BA Data se
usa sólo para restringir el soporte geográfico CP4-barrio; la frecuencia de
puntos/equipamientos nunca se interpreta como población.

La salida es agregada. No lee ni escribe identificadores personales.
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import numpy as np
import requests

BASE = "https://datos.mapadeladeuda.ar/"
INPUT = Path("diagnostico_universo_territorial_integral.json")
BADATA = Path("badata")
OUT_MATRIX = Path("matriz_cp_barrio_v229.json")
OUT_DIAG = Path("diagnostico_reconstruccion_cp_barrio_v229.json")

METRICS = {
    "deudores_unicos_total": "deudores",
    "deudores_unicos_mora": "personas_mora",
    "monto_total": "deuda_total_pesos",
    "monto_mora": "deuda_mora_pesos",
}
TRAIN_METRICS = {"deudores_unicos_total", "monto_total"}
VALIDATION_METRICS = {"deudores_unicos_mora", "monto_mora"}

AGES_OURS_TO_REF = {
    "le25": "<=25", "26_35": "26_35", "36_45": "36_45", "46_55": "46_55",
    "56_65": "56_65", "66_75": "66_75", "gt75": ">75",
}
AGES_REF = set(AGES_OURS_TO_REF.values())
SEXES = {"F", "M"}


def norm_text(v: Any) -> str:
    s = unicodedata.normalize("NFKD", str(v or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^A-Z0-9]+", " ", s.upper().strip())
    return re.sub(r"\s+", " ", s).strip()


def norm_barrio(v: Any) -> str:
    s = norm_text(v)
    return {"LA BOCA": "BOCA", "VILLA GRAL MITRE": "VILLA GENERAL MITRE", "PATERNAL": "LA PATERNAL"}.get(s, s)


def cp4_value(v: Any, allow_cpa: bool = True) -> int | None:
    s = str(v or "").strip().upper()
    if re.fullmatch(r"\d{4}(?:\.0+)?", s):
        n = int(float(s))
        return n if 1000 <= n <= 1499 else None
    if allow_cpa:
        m = re.search(r"(?:^|[^0-9])(1[0-4]\d{2})(?:[^0-9]|$)", s)
        if m:
            n = int(m.group(1))
            return n if 1000 <= n <= 1499 else None
    return None


def get_json(session: requests.Session, path_or_url: str) -> dict:
    url = path_or_url if path_or_url.startswith("https://") else urljoin(BASE, path_or_url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "datos.mapadeladeuda.ar":
        raise ValueError(f"Origen externo no autorizado: {url}")
    for attempt in range(3):
        try:
            r = session.get(url, timeout=60)
            r.raise_for_status()
            x = r.json()
            if not isinstance(x, dict):
                raise ValueError(f"JSON raíz no objeto: {url}")
            return x
        except Exception:
            if attempt == 2:
                raise
    raise RuntimeError("No alcanzable")


def period_key(v: Any) -> str:
    return re.sub(r"\D", "", str(v or ""))[:6]


def feature_name(x: dict) -> str:
    for k in ("name", "nombre", "label", "geo_name", "barrio", "BARRIO"):
        if x.get(k): return str(x[k])
    props = x.get("properties") if isinstance(x.get("properties"), dict) else {}
    for k in ("name", "nombre", "label", "geo_name", "barrio", "BARRIO"):
        if props.get(k): return str(props[k])
    raise ValueError(f"Feature sin nombre reconocible: {x}")


def decode_rows(layer: dict) -> list[dict]:
    cols, aliases, rows = layer.get("columns") or [], layer.get("aliases") or {}, layer.get("rows") or []
    out = []
    for row in rows:
        if not isinstance(row, list) or len(row) != len(cols):
            raise ValueError("Slice externo con fila incompatible")
        out.append({aliases.get(col, col): row[i] for i, col in enumerate(cols)})
    return out


def flatten_values(x: Any) -> list[str]:
    out: list[str] = []
    if isinstance(x, dict):
        for v in x.values(): out.extend(flatten_values(v))
    elif isinstance(x, (list, tuple)):
        for v in x: out.extend(flatten_values(v))
    elif x is not None: out.append(str(x))
    return out


def segment_from_filters(filters: Any, category_ids: set[str]):
    vals = set(flatten_values(filters or {}))
    if vals & category_ids: return None
    sex, age = sorted(vals & SEXES), sorted(vals & AGES_REF)
    if len(sex) > 1 or len(age) > 1: return None
    return (sex[0] if sex else None, age[0] if age else None)


def load_reference():
    session = requests.Session()
    session.headers.update({"User-Agent": "CEPOES-reconstruccion-territorial/2.0 (+https://cepoes.org)"})
    manifest = get_json(session, "manifest.json")
    if manifest.get("dataset") != "mapa-de-la-deuda": raise ValueError("Manifest externo inesperado")
    filters_meta = get_json(session, (manifest.get("dimensions") or {})["filters"])
    category_ids = {str(x.get("id")) for x in filters_meta.get("categorias", []) if x.get("id") not in (None, "__ALL__")}
    lookup = get_json(session, (manifest.get("geo") or {})["lookup"])
    features = [x for x in lookup.get("features", []) if x.get("level") == "barrio_caba" and str(x.get("scope")) == "02"]
    if len(features) != 48: raise ValueError(f"Referencia externa: se esperaban 48 barrios, hay {len(features)}")
    geo_to_name = {str(x["geo_id"]): feature_name(x) for x in features}
    own = json.loads(INPUT.read_text(encoding="utf-8"))
    want = period_key(own.get("periodo_deuda"))
    period = next((p for p in manifest.get("periods") or [] if period_key(p.get("id")) == want), None)
    if not period: raise ValueError(f"Referencia externa no publica el período {own.get('periodo_deuda')}")
    idx = get_json(session, period["index"])
    descriptors, duplicates = {}, Counter()
    for d in idx.get("availableSlices", []):
        if d.get("level") != "barrio_caba" or str(d.get("scope")) != "02": continue
        seg = segment_from_filters(d.get("filters"), category_ids)
        if seg is None: continue
        duplicates[seg] += 1
        prev = descriptors.get(seg)
        if prev is None or len(json.dumps(d.get("filters") or {}, sort_keys=True)) < len(json.dumps(prev.get("filters") or {}, sort_keys=True)):
            descriptors[seg] = d
    layers = {}
    for seg, d in descriptors.items():
        layer = get_json(session, d["path"])
        if len(decode_rows(layer)) == 48: layers[seg] = layer
    meta = {
        "manifest_version": manifest.get("version"), "contract": manifest.get("contract"),
        "periodo_referencia": period.get("id"), "segmentos_disponibles_sin_categoria": len(layers),
        "segmentos": [{"sexo": s[0], "edad": s[1]} for s in sorted(layers, key=str)],
        "duplicados_descriptor": {str(k): v for k, v in duplicates.items() if v > 1},
    }
    return meta, geo_to_name, layers


def point_in_ring(x: float, y: float, ring: list) -> bool:
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi, xj, yj = ring[i][0], ring[i][1], ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (yj - yi) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: inside = not inside
        j = i
    return inside


def point_in_polygon(x: float, y: float, poly: list) -> bool:
    return bool(poly) and point_in_ring(x, y, poly[0]) and not any(point_in_ring(x, y, h) for h in poly[1:])


def geometry_contains(geom: dict, x: float, y: float) -> bool:
    coords = geom.get("coordinates") or []
    if geom.get("type") == "Polygon": return point_in_polygon(x, y, coords)
    if geom.get("type") == "MultiPolygon": return any(point_in_polygon(x, y, p) for p in coords)
    return False


def load_local_polygons(official_norm_to_name: dict[str, str]):
    obj = json.loads((BADATA / "barrios.geojson").read_text(encoding="utf-8"))
    out = []
    for f in obj.get("features", []):
        name = official_norm_to_name.get(norm_barrio(feature_name(f)))
        if not name: continue
        geom, pts, stack = f.get("geometry") or {}, [], [(f.get("geometry") or {}).get("coordinates")]
        while stack:
            q = stack.pop()
            if isinstance(q, list) and len(q) >= 2 and all(isinstance(z, (int, float)) for z in q[:2]): pts.append((float(q[0]), float(q[1])))
            elif isinstance(q, list): stack.extend(q)
        if pts:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out.append((name, (min(xs), min(ys), max(xs), max(ys)), geom))
    if len(out) != 48: raise ValueError(f"BA Data local: se esperaban 48 polígonos compatibles, hay {len(out)}")
    return out


def barrio_from_point(lon: float, lat: float, polygons):
    if not (-59 < lon < -57 and -36 < lat < -33): return None
    for name, (xmin, ymin, xmax, ymax), geom in polygons:
        if xmin <= lon <= xmax and ymin <= lat <= ymax and geometry_contains(geom, lon, lat): return name
    return None


def sniff_csv(path: Path):
    with path.open("rb") as fh: raw = fh.read(32768)
    text = raw.decode("utf-8-sig", errors="replace")
    try: return csv.Sniffer().sniff(text, delimiters=",;\t|")
    except csv.Error: return csv.excel


def first_header(headers: list[str], tests: Iterable[str]):
    norm = {h: norm_text(h).replace(" ", "_") for h in headers}
    for t in tests:
        for h, n in norm.items():
            if n == t: return h
    return None


def build_support(cp_list: list[int], barrio_names: list[str]):
    target_cps = set(cp_list)
    official = {norm_barrio(x): x for x in barrio_names}
    polygons = load_local_polygons(official)
    support, sources, obs = defaultdict(set), defaultdict(set), Counter()
    files_used, rows_seen, rows_geocoded = set(), 0, 0
    for path in sorted(BADATA.glob("*.csv")):
        try:
            with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
                reader = csv.DictReader(fh, dialect=sniff_csv(path)); headers = list(reader.fieldnames or [])
                cp_col = first_header(headers, ["CODIGO_POSTAL", "COD_POSTAL", "CP", "CODIGOPOSTAL"])
                cpa_col = first_header(headers, ["CODIGO_POSTAL_ARGENTINO", "CPA", "COD_POSTAL_ARGENTINO"])
                barrio_col = first_header(headers, ["BARRIO", "NOMBRE_BARRIO", "BARRIO_NOMBRE"])
                lat_col = first_header(headers, ["LAT", "LATITUD", "LATITUDE", "Y"])
                lon_col = first_header(headers, ["LON", "LONG", "LONGITUD", "LONGITUDE", "X"])
                if not (cp_col or cpa_col) or not (barrio_col or (lat_col and lon_col)): continue
                used = False
                for row in reader:
                    rows_seen += 1
                    cp = cp4_value(row.get(cp_col)) if cp_col else None
                    if cp is None and cpa_col: cp = cp4_value(row.get(cpa_col), True)
                    if cp not in target_cps: continue
                    barrio = official.get(norm_barrio(row.get(barrio_col))) if barrio_col else None
                    if barrio is None and lat_col and lon_col:
                        try:
                            lat = float(str(row.get(lat_col, "")).replace(",", ".")); lon = float(str(row.get(lon_col, "")).replace(",", "."))
                            barrio = barrio_from_point(lon, lat, polygons)
                            if barrio: rows_geocoded += 1
                        except (TypeError, ValueError): pass
                    if barrio:
                        support[cp].add(barrio); sources[cp].add(path.name); obs[(cp, barrio)] += 1; used = True
                if used: files_used.add(path.name)
        except Exception as exc:
            print(f"WARN soporte: {path.name}: {exc}", flush=True)
    meta = {
        "datasets_usados": sorted(files_used), "cantidad_datasets": len(files_used),
        "filas_csv_examinadas": rows_seen, "filas_geocodificadas_por_poligono": rows_geocoded,
        "cp_con_soporte_observado": sum(bool(support.get(cp)) for cp in cp_list),
        "cp_sin_soporte_observado": sum(not support.get(cp) for cp in cp_list),
        "pares_cp_barrio_observados": sum(len(support.get(cp, ())) for cp in cp_list),
        "observaciones_pares": sum(obs.values()),
    }
    return support, meta


def load_cp_data():
    root = json.loads(INPUT.read_text(encoding="utf-8"))
    cp_total = {int(r["clave"]): {k: float(r.get(k, 0) or 0) for k in METRICS.values()} for r in root["agregado_cp_1000_1499"]["filas"]}
    cp_list = sorted(cp_total)
    cross = {}
    for r in root["agregado_cp_sexo_edad_1000_1499"]["filas"]:
        parts = str(r["clave"]).split("|")
        if len(parts) == 3:
            cross[(int(parts[0]), parts[1], parts[2])] = {k: float(r.get(k, 0) or 0) for k in METRICS.values()}
    segs = {(None, None): cp_total}; age_rev = {v: k for k, v in AGES_OURS_TO_REF.items()}
    for sex in [None, "F", "M"]:
        for age_ref in [None] + sorted(AGES_REF):
            if sex is None and age_ref is None: continue
            age_ours, cells = age_rev.get(age_ref) if age_ref else None, {}
            for cp in cp_list:
                ac = {k: 0.0 for k in METRICS.values()}
                for sx in ("F", "M"):
                    if sex and sx != sex: continue
                    ages = [age_ours] if age_ours else list(AGES_OURS_TO_REF) + ["desconocida"]
                    for age in ages:
                        row = cross.get((cp, sx, age))
                        if row:
                            for k in ac: ac[k] += row[k]
                cells[cp] = ac
            segs[(sex, age_ref)] = cells
    return root, cp_list, segs


def reference_targets(layer: dict, geo_to_name: dict[str, str], barrio_names: list[str]):
    by_name = {name: {} for name in barrio_names}
    for row in decode_rows(layer):
        name = geo_to_name.get(str(row.get("geo_id")))
        if name in by_name: by_name[name] = row
    if any(not by_name[n] for n in barrio_names): raise ValueError("Slice externo no cubre los mismos 48 barrios")
    return {metric: np.array([float(by_name[n].get(metric, 0) or 0) for n in barrio_names], dtype=float) for metric in METRICS}


def make_samples(cp_list, segs, layers, geo_to_name, barrio_names):
    samples = []
    for seg, layer in sorted(layers.items(), key=str):
        if seg not in segs: continue
        targets = reference_targets(layer, geo_to_name, barrio_names)
        for ref_metric, own_metric in METRICS.items():
            x = np.array([float(segs[seg].get(cp, {}).get(own_metric, 0) or 0) for cp in cp_list], dtype=float)
            y = targets[ref_metric]
            if x.sum() > 0 and y.sum() > 0:
                samples.append({"segment": seg, "metric": ref_metric, "x": x/x.sum(), "y": y/y.sum(), "own_total": float(x.sum()), "ref_total": float(y.sum())})
    return samples


def split_by_metric(samples):
    segments = sorted({s["segment"] for s in samples}, key=str)
    if len(segments) < 3: raise ValueError(f"Referencia insuficiente: sólo {len(segments)} segmentos comparables")
    train = [s for s in samples if s["metric"] in TRAIN_METRICS]
    validation = [s for s in samples if s["metric"] in VALIDATION_METRICS]
    if len(train) < 6 or len(validation) < 6:
        raise ValueError(f"Muestras insuficientes: entrenamiento={len(train)}, validación={len(validation)}")
    return segments, train, validation


def simplex_projection(v: np.ndarray) -> np.ndarray:
    if len(v) == 1: return np.array([1.0])
    u = np.sort(v)[::-1]; cssv = np.cumsum(u) - 1; ind = np.arange(1, len(v)+1); cond = u - cssv/ind > 0
    rho = ind[cond][-1]; theta = cssv[cond][-1]/rho
    return np.maximum(v-theta, 0)


def project_rows(w: np.ndarray, support_idx: list[np.ndarray]) -> np.ndarray:
    out = np.zeros_like(w)
    for i, idx in enumerate(support_idx): out[i, idx] = simplex_projection(w[i, idx])
    return out


def fit_weights(X, Y, P, support_idx, lam=0.01):
    W, n, c = P.copy(), max(1, X.shape[0]), max(1, X.shape[1])
    L = 2*float(np.linalg.norm(X, 2)**2)/n + 2*lam/c; step = 0.9/max(L, 1e-12); prev = None
    for it in range(1, 2501):
        resid = X@W-Y; grad = (2/n)*(X.T@resid) + (2*lam/c)*(W-P); W = project_rows(W-step*grad, support_idx)
        if it % 25 == 0 or it == 1:
            obj = float(np.mean((X@W-Y)**2) + lam*np.mean((W-P)**2))
            if prev is not None and abs(prev-obj) <= 1e-10*max(1.0, abs(prev)): break
            prev = obj
    return W, {"iteraciones": it, "lambda_prior": lam, "objetivo_final": prev, "paso": step}


def corr(a, b):
    return 0.0 if np.std(a) == 0 or np.std(b) == 0 else float(np.corrcoef(a, b)[0,1])


def eval_samples(samples, W, P):
    rows = []
    for sample in samples:
        y, pred, base = sample["y"], sample["x"]@W, sample["x"]@P
        def metrics(z):
            d = np.abs(z-y)
            return {"mae_share_pp": float(d.mean()*100), "max_abs_share_pp": float(d.max()*100), "tv_distance": float(0.5*d.sum()), "correlacion": corr(z,y)}
        rows.append({"segmento": {"sexo": sample["segment"][0], "edad": sample["segment"][1]}, "metrica": sample["metric"], "modelo": metrics(pred), "prior_badata": metrics(base)})
    def agg(which):
        if not rows: return {}
        return {"n": len(rows), "mae_share_pp_media": float(np.mean([r[which]["mae_share_pp"] for r in rows])), "max_abs_share_pp_media": float(np.mean([r[which]["max_abs_share_pp"] for r in rows])), "tv_distance_media": float(np.mean([r[which]["tv_distance"] for r in rows])), "correlacion_media": float(np.mean([r[which]["correlacion"] for r in rows]))}
    return {"detalle": rows, "modelo": agg("modelo"), "prior_badata": agg("prior_badata")}


def main() -> int:
    own, cp_list, segs = load_cp_data(); ref_meta, geo_to_name, layers = load_reference()
    barrio_names = sorted(geo_to_name.values(), key=norm_text); support, support_meta = build_support(cp_list, barrio_names)
    bidx, C, B = {b:i for i,b in enumerate(barrio_names)}, len(cp_list), len(barrio_names)
    P = np.zeros((C,B)); support_idx, observed = [], []
    for i, cp in enumerate(cp_list):
        cands = sorted(support.get(cp) or barrio_names, key=norm_text); idx = np.array([bidx[b] for b in cands], dtype=int)
        support_idx.append(idx); P[i,idx] = 1.0/len(idx); observed.append(bool(support.get(cp)))
    total_cells = segs[(None,None)]
    td = sum(total_cells[cp]["deudores"] for cp in cp_list); cd = sum(total_cells[cp]["deudores"] for cp,ok in zip(cp_list,observed) if ok)
    tm = sum(total_cells[cp]["deuda_total_pesos"] for cp in cp_list); cm = sum(total_cells[cp]["deuda_total_pesos"] for cp,ok in zip(cp_list,observed) if ok)
    support_meta["cobertura_deudores_pct"] = round(cd/td*100,4) if td else 0; support_meta["cobertura_deuda_pct"] = round(cm/tm*100,4) if tm else 0
    samples = make_samples(cp_list,segs,layers,geo_to_name,barrio_names); segments, train, validation = split_by_metric(samples)
    X,Y = np.vstack([s["x"] for s in train]), np.vstack([s["y"] for s in train]); W,fit_meta = fit_weights(X,Y,P,support_idx)
    train_eval,val_eval = eval_samples(train,W,P), eval_samples(validation,W,P)
    vm,vb = val_eval["modelo"],val_eval["prior_badata"]; improvement = None if not vb.get("tv_distance_media") else 1-vm.get("tv_distance_media",1)/vb["tv_distance_media"]
    checks = {
        "soporte_cubre_90pct_deudores": support_meta["cobertura_deudores_pct"] >= 90.0,
        "mora_fuera_objetivo_tv_menor_10pct": vm.get("tv_distance_media",1) <= 0.10,
        "mora_fuera_objetivo_correlacion_mayor_090": vm.get("correlacion_media",0) >= 0.90,
        "mejora_mora_vs_prior_10pct": improvement is not None and improvement >= 0.10,
        "hay_al_menos_3_segmentos_comparables": len(segments) >= 3,
        "hay_al_menos_6_muestras_mora_no_usadas": len(validation) >= 6,
    }
    status = "VALIDADA_CANDIDATA" if all(checks.values()) else "NO_VALIDADA"
    matrix_rows=[]
    for i,cp in enumerate(cp_list):
        weights=[{"barrio":barrio_names[j],"peso":round(float(W[i,j]),10)} for j in support_idx[i] if W[i,j]>1e-9]; weights.sort(key=lambda x:(-x["peso"],norm_text(x["barrio"])))
        matrix_rows.append({"cp4":cp,"soporte_badata_observado":observed[i],"barrios_candidatos":len(support_idx[i]),"pesos":weights})
    matrix={"schema":"cepoes-cp4-barrio-probabilistic-v2","generado_utc":datetime.now(timezone.utc).isoformat(),"periodo_calibracion":own.get("periodo_deuda"),"estado_validacion":status,"interpretacion":"ponderadores territoriales estimados; no geolocalizacion individual exacta","fuente_primaria_futura":"Central de Deudores BCRA + PADRON ARCA distribuido por BCRA","referencia_calibracion":"Mapa de la Deuda, capa agregada barrio_caba","restriccion_geografica":"compatibilidades CP4-barrio observadas en datasets BA Data locales; frecuencia de puntos no se usa como peso","calibracion":sorted(TRAIN_METRICS),"validacion_no_usada_en_ajuste":sorted(VALIDATION_METRICS),"barrios":barrio_names,"filas":matrix_rows}
    OUT_MATRIX.write_text(json.dumps(matrix,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    diag={"schema":"cepoes-diagnostico-reconstruccion-cp4-barrio-v2","generado_utc":datetime.now(timezone.utc).isoformat(),"estado":status,"periodo":own.get("periodo_deuda"),"referencia":ref_meta,"universo_cp":{"cantidad":C,"min":min(cp_list),"max":max(cp_list)},"soporte_geografico":support_meta,"validacion":{"diseno":"ajuste sólo con deudores totales y monto total; prueba con deudores en mora y monto en mora","segmentos_comparables":[{"sexo":s[0],"edad":s[1]} for s in segments],"metricas_entrenamiento":sorted(TRAIN_METRICS),"metricas_fuera_objetivo":sorted(VALIDATION_METRICS),"muestras_entrenamiento":len(train),"muestras_fuera_objetivo":len(validation),"segunda_etapa_requerida_si_aprueba":"validación temporal con otro período BCRA/ARCA sin recalibrar la matriz"},"ajuste":fit_meta,"resultado_entrenamiento":train_eval,"resultado_validacion":val_eval,"mejora_tv_vs_prior":improvement,"checks":checks,"criterio":{"adoptar_solo_si":"todos los checks son true","si_aprueba":"candidata únicamente; falta validación temporal antes de producción","si_falla":"no usar la matriz en producción ni relajar umbrales para forzar aprobación"},"privacidad":{"identificadores_personales":False,"microdatos":False,"salida_solo_agregada":True}}
    OUT_DIAG.write_text(json.dumps(diag,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"estado":status,"soporte":support_meta,"segmentos_comparables":len(segments),"muestras_entrenamiento":len(train),"muestras_validacion_mora":len(validation),"validacion_modelo":vm,"validacion_prior":vb,"mejora_tv_vs_prior":improvement,"checks":checks},ensure_ascii=False,indent=2),flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
