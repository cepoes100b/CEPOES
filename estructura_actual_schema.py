#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

P = Path("deploy/site-overlay/assets/data/estructura-productiva/actual.json")
GEO = Path("deploy/site-overlay/assets/data/estructura-productiva/comunas.geojson")
EXPECTED_2026Q1 = {"1":-0.5,"2":-4.6,"3":-1.1,"4":-0.3,"5":-2.0,"6":0.0,"7":-0.4,"8":-1.7,"9":0.7,"10":-2.5,"11":0.8,"12":-1.0,"13":-3.3,"14":-2.1,"15":-3.5}


def fail(msg: str):
    raise ValueError(msg)


def validate(d, geo):
    if d.get("schema") != 1:
        fail("schema inesperado")

    pan = d.get("panorama") or {}
    oede = pan.get("empresas_registradas") or {}
    ejes = pan.get("ejes_comerciales") or {}

    if int(oede.get("periodo", 0)) < 2024:
        fail("OEDE anterior a 2024")
    empresas = int(oede.get("empresas", 0))
    if not 50000 <= empresas <= 250000:
        fail(f"total OEDE improbable: {empresas}")
    sectores = oede.get("sectores") or []
    if len(sectores) < 8:
        fail("pocos sectores OEDE")
    serie = oede.get("serie") or []
    if len(serie) < 8 or serie[-1].get("anio") != oede.get("periodo"):
        fail("serie OEDE inconsistente")

    periodo = ejes.get("periodo") or {}
    if periodo.get("cuatrimestre") not in (1, 2, 3):
        fail("cuatrimestre IDECBA inválido")
    if int(periodo.get("anio", 0)) < 2026:
        fail("IDECBA anterior a 2026")
    if any(type(ejes.get(key)) is not int for key in ("locales_relevados", "locales_ocupados")):
        fail("totales IDECBA deben ser conteos enteros")
    relevados = int(ejes.get("locales_relevados", 0))
    ocupados = int(ejes.get("locales_ocupados", 0))
    tasa = float(ejes.get("tasa_ocupacion", 0))
    if relevados < 10000 or ocupados < 9000 or ocupados >= relevados:
        fail(f"totales IDECBA improbables: {ocupados}/{relevados}")
    if not 70 <= tasa <= 100:
        fail(f"tasa IDECBA improbable: {tasa}")
    if tasa != round(100 * ocupados / relevados, 1):
        fail("tasa IDECBA no coincide con conteos")
    if ejes.get("provisorio") is not True:
        fail("falta carácter provisorio IDECBA")

    comunas = ejes.get("comunas") or {}
    if set(comunas) != {str(i) for i in range(1, 16)}:
        fail(f"comunas IDECBA inválidas: {sorted(comunas)}")
    if sum(int(x.get("ocupados", 0)) for x in comunas.values()) != ocupados:
        fail("ocupados por comuna no suman el total")
    if sum(int(x.get("relevados", 0)) for x in comunas.values()) != relevados:
        fail("relevados por comuna no suman el total")

    rubros = ejes.get("rubros") or []
    if len(rubros) != 19 or len({x.get("rubro", "").strip().lower() for x in rubros}) != 19:
        fail("se requieren 19 rubros IDECBA únicos")
    if sum(int(x.get("total", 0)) for x in rubros) != ocupados:
        fail("rubros IDECBA no suman los locales ocupados")

    expected_ids = {str(i) for i in range(1, 16)}
    for c, entry in comunas.items():
        for key in ("relevados", "ocupados"):
            if type(entry.get(key)) is not int or entry[key] < 0:
                fail(f"conteo inválido comuna {c}")
        if entry["relevados"] <= 0 or entry["ocupados"] > entry["relevados"]:
            fail(f"conteos improbables comuna {c}")
        if entry.get("tasa_ocupacion") != round(100 * entry["ocupados"] / entry["relevados"], 1):
            fail(f"tasa no coincide con conteos comuna {c}")
    for rubro in rubros:
        counts = rubro.get("comunas") or {}
        if set(counts) != expected_ids or any(type(x) is not int or x < 0 for x in counts.values()):
            fail("comunas/conteos inválidos en rubro")
        if type(rubro.get("total")) is not int or sum(counts.values()) != rubro["total"]:
            fail("rubro no suma su total")
    if any(sum(x["comunas"][c] for x in rubros) != comunas[c]["ocupados"] for c in expected_ids):
        fail("rubros no suman los ocupados de cada comuna")

    if int(periodo.get("anio", 0)) >= 2026:
        missing = [c for c, x in comunas.items() if "variacion_interanual_pp" not in x or "tasa_ocupacion_anterior" not in x]
        if missing:
            fail(f"faltan variaciones interanuales por comuna: {missing}")
        for c, x in comunas.items():
            delta = float(x["variacion_interanual_pp"])
            prev = float(x["tasa_ocupacion_anterior"])
            if not -15 <= delta <= 15 or not 70 <= prev <= 100:
                fail(f"interanual improbable comuna {c}: {prev=} {delta=}")
            if abs((prev + delta) - float(x["tasa_ocupacion"])) > 0.11:
                fail(f"interanual inconsistente comuna {c}")
        comp = ejes.get("comparacion_interanual") or {}
        if comp.get("desde") != {"anio": periodo["anio"] - 1, "cuatrimestre": periodo["cuatrimestre"]} or comp.get("hasta") != periodo:
            fail("período interanual inválido")
        prev_total = comp.get("tasa_ocupacion_desde")
        delta_total = comp.get("variacion_total_pp")
        if not isinstance(prev_total, (int, float)) or isinstance(prev_total, bool) or not 70 <= prev_total <= 100:
            fail("tasa total interanual ausente/improbable")
        if not isinstance(delta_total, (int, float)) or isinstance(delta_total, bool) or not -10 <= delta_total <= 10:
            fail("variación total interanual ausente/improbable")
        # Three independently rounded values can differ by at most 0.1 p.p.
        if abs(prev_total + delta_total - tasa) > 0.100000001:
            fail("comparación total interanual inconsistente")
        if int(periodo.get("anio",0)) == 2026 and int(periodo.get("cuatrimestre",0)) == 1:
            got={c: round(float(x["variacion_interanual_pp"]),1) for c,x in comunas.items()}
            if got != EXPECTED_2026Q1:
                fail(f"variación interanual 2026-C1 no coincide con informe IDECBA: {got}")

    feats=geo.get("features") or []
    ids={str(int((f.get("properties") or {}).get("comuna"))) for f in feats}
    if geo.get("type") != "FeatureCollection" or len(feats) != 15 or ids != {str(i) for i in range(1,16)}:
        fail("GeoJSON oficial de comunas inválido")

    fuentes = d.get("fuentes") or {}
    for key in ("idecba_rubros", "idecba_indicadores", "idecba_informe"):
        source = fuentes.get(key) or {}
        if source.get("periodo") != periodo:
            fail(f"fuente/período IDECBA incoherente: {key}")
        url = urlparse(source.get("url", ""))
        if url.scheme != "https" or url.netloc != "www.estadisticaciudad.gob.ar":
            fail(f"fuente IDECBA no oficial: {key}")
        if not re.fullmatch(r"[0-9a-f]{64}", source.get("sha256", "")):
            fail(f"falta huella de fuente: {key}")
        try:
            stamp = datetime.fromisoformat(source.get("extraido", ""))
            if stamp.tzinfo is None:
                fail(f"fecha de extracción sin zona: {key}")
        except (TypeError, ValueError):
            fail(f"fecha de extracción inválida: {key}")
    report = fuentes["idecba_informe"]
    ordinal = {1: "1er", 2: "2do", 3: "3er"}[periodo["cuatrimestre"]]
    expected_page = f"https://www.estadisticaciudad.gob.ar/eyc/publicaciones/ejes-comerciales-ciudad-de-buenos-aires-{ordinal}-cuatrimestre-de-{periodo['anio']}/"
    if report.get("pagina") != expected_page or report.get("periodo_verificado") != periodo:
        fail("publicación/informe no verificado para el período")
    if type(report.get("numero")) is not int or not re.search(rf"/ir_\d{{4}}_{report['numero']}\.pdf(?:\?|$)", report.get("url", "")):
        fail("URL de informe inválida")

    criterio = d.get("criterio") or {}
    if "2017" not in str(criterio.get("historico", "")):
        fail("falta advertencia histórica RUS 2017")
    if "48 ejes" not in str(criterio.get("territorial", "")):
        fail("falta alcance territorial de los 48 ejes")

    return f"✔ panorama analítico válido · OEDE {oede['periodo']}: {empresas:,} empresas · IDECBA {periodo.get('anio')} C{periodo.get('cuatrimestre')}: {ocupados:,}/{relevados:,} locales · {tasa:.1f}% · 15 comunas con comparación interanual"


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail(f"clave JSON duplicada: {key}")
        result[key] = value
    return result


def main():
    try:
        d = json.loads(P.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        geo = json.loads(GEO.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        print(validate(d, geo))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(f"✘ {exc}") from exc


if __name__ == "__main__":
    main()
