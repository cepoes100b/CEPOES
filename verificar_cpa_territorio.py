from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

CPA_RE = re.compile(r"^C\d{4}[A-Z]{3}$")


def fail(msg: str) -> None:
    raise ValueError(msg)


def main() -> None:
    csv_path = Path(sys.argv[1] if len(sys.argv) > 1 else "cpa_territorio.csv")
    estado_path = Path(sys.argv[2] if len(sys.argv) > 2 else "estado_cpa_territorio.json")
    territorio_path = Path(sys.argv[3] if len(sys.argv) > 3 else "territorio.json")

    territorio = json.loads(territorio_path.read_text(encoding="utf-8"))
    canonical = {
        item["nombre"]: int(item["comuna"])
        for item in (territorio.get("barrios") or {}).values()
    }
    if len(canonical) != 48:
        fail(f"territorio.json no contiene 48 barrios: {len(canonical)}")

    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8", newline="")))
    if not rows:
        fail("cruce CPA vacío")
    if set(rows[0]) != {"cpa", "barrio", "comuna", "fuentes_n", "observaciones", "fuentes"}:
        fail(f"columnas inesperadas: {list(rows[0])}")

    seen: set[str] = set()
    barrios: set[str] = set()
    for row in rows:
        cpa = row["cpa"].strip().upper()
        barrio = row["barrio"].strip()
        if not CPA_RE.fullmatch(cpa):
            fail(f"CPA inválido: {cpa!r}")
        if cpa in seen:
            fail(f"CPA duplicado: {cpa}")
        seen.add(cpa)
        if barrio not in canonical:
            fail(f"barrio no canónico: {barrio!r}")
        comuna = int(row["comuna"])
        if comuna != canonical[barrio]:
            fail(f"comuna inconsistente para {barrio}: {comuna} vs {canonical[barrio]}")
        if int(row["fuentes_n"]) < 1 or int(row["observaciones"]) < 1:
            fail(f"proveniencia inválida para {cpa}")
        sources = [s for s in row["fuentes"].split("|") if s]
        if len(set(sources)) != int(row["fuentes_n"]):
            fail(f"fuentes_n inconsistente para {cpa}")
        barrios.add(barrio)

    estado = json.loads(estado_path.read_text(encoding="utf-8"))
    if estado.get("schema") != 1 or estado.get("producto") != "cruce_cpa_barrio_gcba_observado":
        fail("estado CPA con schema/producto inesperado")
    if estado.get("cpa_utilizables") != len(rows):
        fail("cpa_utilizables no coincide con CSV")
    if estado.get("barrios_cubiertos") != len(barrios):
        fail("barrios_cubiertos no coincide con CSV")
    if estado.get("barrios_canonicos_total") != 48:
        fail("barrios_canonicos_total debe ser 48")
    if estado.get("cpa_observados") != estado.get("cpa_utilizables") + estado.get("cpa_conflictivos"):
        fail("CPA observados != utilizables + conflictivos")

    conflictivos = {str(x.get("cpa", "")).upper() for x in estado.get("conflictos") or []}
    if len(conflictivos) != estado.get("cpa_conflictivos"):
        fail("detalle de conflictos no coincide con cpa_conflictivos")
    if seen & conflictivos:
        fail("un CPA conflictivo fue incluido en el cruce utilizable")

    faltantes = set(estado.get("barrios_sin_cpa_observado") or [])
    if faltantes != set(canonical) - barrios:
        fail("barrios_sin_cpa_observado inconsistente")

    print(
        f"✔ cruce CPA verificado · {len(rows)} CPA utilizables · "
        f"{len(conflictivos)} conflictivos excluidos · {len(barrios)}/48 barrios"
    )


if __name__ == "__main__":
    main()
