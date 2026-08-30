#!/usr/bin/env python3
import json
from pathlib import Path

OFFICIAL = {
    1:23551207677, 2:10847320551, 3:7876703258, 4:26178123318,
    5:7637166074, 6:11425728078, 7:18239541768, 8:21459182556,
    9:20255786777, 10:17349785329, 11:15960028917, 12:26112219721,
    13:32423246607, 14:34681461509, 15:16407869924,
}

p = Path("descentralizacion_comunas.json")
if not p.is_file():
    raise SystemExit("✘ falta descentralizacion_comunas.json")

d = json.loads(p.read_text(encoding="utf-8"))
problems = []

if d.get("schema") != "cepoes-descentralizacion-comunas-v2":
    problems.append(f"schema={d.get('schema')}")
if d.get("status") != "VALIDADO":
    problems.append("status no VALIDADO")
if d.get("year") != 2026:
    problems.append(f"year={d.get('year')}")
if d.get("quarter") not in (1, 2, 3, 4):
    problems.append(f"quarter={d.get('quarter')}")

cs = d.get("comunas", [])
if len(cs) != 15:
    problems.append(f"comunas={len(cs)}")
if sorted(x.get("comuna") for x in cs) != list(range(1, 16)):
    problems.append("IDs de comunas incompletos")

by_c = {x["comuna"]: x for x in cs if isinstance(x.get("comuna"), int)}
for c in range(1, 16):
    x = by_c.get(c)
    if not x:
        continue
    a = x.get("administrado", {})
    if a.get("sancionado", 0) <= 0:
        problems.append(f"Comuna {c}: sancionado <=0")
    if a.get("vigente", 0) <= 0:
        problems.append(f"Comuna {c}: vigente <=0")
    if a.get("devengado", 0) < 0:
        problems.append(f"Comuna {c}: devengado negativo")
    if a.get("ejecucion_pct") is None:
        problems.append(f"Comuna {c}: sin ejecución")
    if "gasto_localizado" not in x:
        problems.append(f"Comuna {c}: falta gasto_localizado")

    actual = a.get("sancionado", 0)
    expected = OFFICIAL[c]
    diff_pct = abs(actual / expected - 1) * 100 if expected else 0
    if diff_pct > 0.05:
        problems.append(
            f"Comuna {c}: sancionado {actual} difiere del oficial "
            f"{expected} en {diff_pct:.4f}%"
        )

q = d.get("quality", {})
if q.get("admin_rows", 0) <= 0:
    problems.append("sin filas administrativas")
checkpoint = q.get("sancionado_checkpoint_total", {})
if checkpoint.get("ok") is not True:
    problems.append("checkpoint total Decreto Distributivo no validado")

headline = d.get("headline", {})
if headline.get("presupuesto_administrado_comunas_vigente", 0) <= 0:
    problems.append("headline vigente comunas <=0")
if headline.get("ejecucion_comunas_pct") is None:
    problems.append("headline sin ejecución")

if problems:
    print("✘ descentralización inválida")
    for x in problems:
        print("  ·", x)
    raise SystemExit(1)

print(
    f"✓ Descentralización V2 validada · T{d['quarter']} 2026 · "
    f"15 comunas · sancionado="
    f"{headline['presupuesto_administrado_comunas_sancionado']:.0f} · "
    f"vigente={headline['presupuesto_administrado_comunas_vigente']:.0f} · "
    f"ejecución={headline['ejecucion_comunas_pct']}% · "
    f"peso GCBA={headline['participacion_presupuesto_gcba_pct']}%"
)
