#!/usr/bin/env python3
import json
from pathlib import Path

p = Path("salud_mental.json")
if not p.is_file():
    raise SystemExit("✘ falta salud_mental.json")

d = json.loads(p.read_text(encoding="utf-8"))
problems = []

if d.get("schema") != "cepoes-salud-mental-v2":
    problems.append(f"schema inesperado: {d.get('schema')}")
if d.get("status") != "VALIDADO":
    problems.append("status no VALIDADO")

series = d.get("series", {})
arg = series.get("argentina_deis", [])
caba = series.get("caba_snic_sat", [])
deis_caba = series.get("caba_deis_diagnostico", [])

arg_by_year = {x.get("anio"): x for x in arg}
caba_by_year = {x.get("anio"): x for x in caba}

if not arg or min(arg_by_year) > 2005 or max(arg_by_year) < 2024:
    problems.append("DEIS nacional no cubre 2005-2024 como mínimo")

for y, expected in {2023: 3488, 2024: 3614}.items():
    actual = arg_by_year.get(y, {}).get("defunciones")
    if actual != expected:
        problems.append(f"DEIS nacional {y}: {actual} != {expected}")

if not caba or min(caba_by_year) > 2017 or max(caba_by_year) < 2024:
    problems.append("SNIC CABA no cubre 2017-2024 como mínimo")

for y, expected in {2022: 242, 2023: 184, 2024: 171}.items():
    actual = caba_by_year.get(y, {}).get("suicidios")
    if actual != expected:
        problems.append(f"SNIC CABA {y}: {actual} != {expected}")

for y, expected_rate in {2022: 8.4, 2023: 6.4, 2024: 5.9}.items():
    actual = caba_by_year.get(y, {}).get("tasa_100k_mayores_5")
    if actual != expected_rate:
        problems.append(f"tasa oficial SNIC CABA {y}: {actual} != {expected_rate}")

quality = d.get("quality", {})
if quality.get("deis_caba_recent_quality") != "NO_VALIDO_PARA_INDICADOR":
    problems.append("DEIS-CABA reciente no está marcado como diagnóstico no válido")

if not quality.get("snic_method"):
    problems.append("falta método de conteo SNIC validado")

headline = d.get("headline", {})
if headline.get("caba", {}).get("suicidios_snic_sat") != caba_by_year[max(caba_by_year)]["suicidios"]:
    problems.append("headline CABA no coincide con última observación SNIC")

if problems:
    print("✘ salud mental inválida")
    for x in problems:
        print("  ·", x)
    raise SystemExit(1)

latest = max(caba_by_year)
print(
    f"✓ Salud mental V2 validada · DEIS nacional 2024={arg_by_year[2024]['defunciones']} · "
    f"CABA SNIC {latest}={caba_by_year[latest]['suicidios']} · "
    f"método={quality['snic_method']}"
)
