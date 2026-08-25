#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

P = Path("deploy/site-overlay/assets/data/estructura-productiva/actual.json")


def fail(msg: str):
    raise SystemExit(f"✘ {msg}")


def main():
    if not P.exists():
        fail(f"falta {P}")
    d = json.loads(P.read_text(encoding="utf-8"))
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
    if int(periodo.get("anio", 0)) < 2026:
        fail("IDECBA anterior a 2026")
    relevados = int(ejes.get("locales_relevados", 0))
    ocupados = int(ejes.get("locales_ocupados", 0))
    tasa = float(ejes.get("tasa_ocupacion", 0))
    if relevados < 10000 or ocupados < 9000 or ocupados >= relevados:
        fail(f"totales IDECBA improbables: {ocupados}/{relevados}")
    if not 70 <= tasa <= 100:
        fail(f"tasa IDECBA improbable: {tasa}")

    comunas = ejes.get("comunas") or {}
    if set(comunas) != {str(i) for i in range(1, 16)}:
        fail(f"comunas IDECBA inválidas: {sorted(comunas)}")
    if sum(int(x.get("ocupados", 0)) for x in comunas.values()) != ocupados:
        fail("ocupados por comuna no suman el total")
    if sum(int(x.get("relevados", 0)) for x in comunas.values()) != relevados:
        fail("relevados por comuna no suman el total")

    rubros = ejes.get("rubros") or []
    if len(rubros) < 8:
        fail("pocos rubros IDECBA")
    if sum(int(x.get("total", 0)) for x in rubros) != ocupados:
        fail("rubros IDECBA no suman los locales ocupados")

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
        if int((comp.get("desde") or {}).get("anio", 0)) != int(periodo.get("anio")) - 1:
            fail("período interanual inválido")

    criterio = d.get("criterio") or {}
    if "2017" not in str(criterio.get("historico", "")):
        fail("falta advertencia histórica RUS 2017")
    if "48 ejes" not in str(criterio.get("territorial", "")):
        fail("falta alcance territorial de los 48 ejes")

    print(f"✔ panorama analítico válido · OEDE {oede['periodo']}: {empresas:,} empresas · IDECBA {periodo.get('anio')} C{periodo.get('cuatrimestre')}: {ocupados:,}/{relevados:,} locales · {tasa:.1f}% · 15 comunas con comparación interanual")


if __name__ == "__main__":
    main()
