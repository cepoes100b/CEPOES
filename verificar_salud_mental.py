#!/usr/bin/env python3
import json
from pathlib import Path

p = Path("salud_mental.json")
if not p.is_file():
    raise SystemExit("✘ falta salud_mental.json")

d = json.loads(p.read_text(encoding="utf-8"))
problems = []

if d.get("schema") != "cepoes-salud-mental-v3":
    problems.append(f"schema inesperado: {d.get('schema')}")
if d.get("status") != "VALIDADO":
    problems.append("status no VALIDADO")

series = d.get("series", {})
arg = series.get("argentina_snic", [])
caba = series.get("caba_snic", [])
arg_by_year = {x.get("anio"): x for x in arg}
caba_by_year = {x.get("anio"): x for x in caba}

expected_arg = {
    2016: 2897, 2017: 3304, 2018: 3903, 2019: 3647, 2020: 3262,
    2021: 3648, 2022: 3959, 2023: 4205, 2024: 4249, 2025: 5209,
}
for y, expected in expected_arg.items():
    actual = arg_by_year.get(y, {}).get("suicidios")
    if actual != expected:
        problems.append(f"SNIC Argentina {y}: {actual} != {expected}")

arg_rate = arg_by_year.get(2025, {}).get("tasa_100k_mayores_5")
if arg_rate is None or abs(float(arg_rate) - 11.84) > 0.06:
    problems.append(f"SNIC Argentina 2025 tasa incompatible: {arg_rate}")

if caba_by_year.get(2024, {}).get("suicidios") != 171:
    problems.append(f"SNIC CABA 2024: {caba_by_year.get(2024)}")
if caba_by_year.get(2025, {}).get("suicidios") != 236:
    problems.append(f"SNIC CABA 2025: {caba_by_year.get(2025)}")

caba_rate = caba_by_year.get(2025, {}).get("tasa_100k_mayores_5")
if caba_rate is None or abs(float(caba_rate) - 7.97) > 0.06:
    problems.append(f"SNIC CABA 2025 tasa incompatible: {caba_rate}")

headline = d.get("headline", {})
caba_var = headline.get("caba", {}).get("variacion_anual_pct")
if caba_var != 38.0:
    problems.append(f"CABA variación 2025/2024: {caba_var} != 38.0")

jur = d.get("jurisdicciones_2025", [])
if len(jur) != 24:
    problems.append(f"jurisdicciones 2025: {len(jur)} != 24")
jur_sum = sum(int(x.get("suicidios_2025") or 0) for x in jur)
if jur_sum != 5209:
    problems.append(f"suma jurisdicciones 2025: {jur_sum} != 5209")

comp = d.get("comparabilidad", {}).get("buenos_aires", {})
if comp.get("estado") != "RUPTURA_DE_SERIE_2025" or not comp.get("advertencia"):
    problems.append("falta advertencia metodológica de ruptura de serie en Buenos Aires")

red = d.get("red_atencion_caba", {})
cesac = red.get("cesac_con_salud_mental", [])
if len(cesac) < 43:
    problems.append(f"CeSAC con salud mental: {len(cesac)} < 43")
effectors = red.get("efectores_especializados", [])
if len(effectors) != 5:
    problems.append(f"efectores especializados: {len(effectors)} != 5")

attempts = d.get("intentos_suicidio", {})
if attempts.get("publicado") is not False:
    problems.append("intentos de suicidio no están marcados como panel separado no publicado")

phones = {x.get("telefono") for x in d.get("asistencia", [])}
for phone in ("0800-999-0091", "107"):
    if phone not in phones:
        problems.append(f"falta información de asistencia: {phone}")

deis = d.get("contraste_deis", {})
if deis.get("estado") not in {"ACTUALIZADO", "ULTIMO_DATO_VALIDADO"}:
    problems.append(f"estado DEIS inválido: {deis.get('estado')}")
deis_series = deis.get("serie_nacional", [])
if not deis_series or max(int(x.get("anio") or 0) for x in deis_series) < 2024:
    problems.append("contraste DEIS no conserva al menos el último dato validado 2024")

if problems:
    print("✘ salud mental V3 inválida")
    for x in problems:
        print("  ·", x)
    raise SystemExit(1)

print(
    "✓ Salud Mental V3 validada · "
    f"Argentina 2025={arg_by_year[2025]['suicidios']} tasa={arg_by_year[2025]['tasa_100k_mayores_5']} · "
    f"CABA 2025={caba_by_year[2025]['suicidios']} tasa={caba_by_year[2025]['tasa_100k_mayores_5']} "
    f"var={caba_var:+.1f}% · jurisdicciones={len(jur)} suma={jur_sum} · "
    f"CeSAC={len(cesac)} · efectores={len(effectors)} · DEIS={deis['estado']}"
)
