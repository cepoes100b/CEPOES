#!/usr/bin/env python3
import json
from pathlib import Path
p=Path("descentralizacion_comunas.json")
if not p.is_file():raise SystemExit("✘ falta descentralizacion_comunas.json")
d=json.loads(p.read_text(encoding="utf-8"));problems=[]
if d.get("status")!="VALIDADO":problems.append("status")
cs=d.get("comunas",[])
if len(cs)!=15:problems.append(f"comunas={len(cs)}")
if sorted(x.get("comuna") for x in cs)!=list(range(1,16)):problems.append("IDs de comunas incompletos")
for x in cs:
    a=x.get("administrado",{})
    if a.get("vigente",0)<=0:problems.append(f"Comuna {x.get('comuna')}: vigente administrado <=0")
    if a.get("devengado",0)<0:problems.append(f"Comuna {x.get('comuna')}: devengado negativo")
    if a.get("ejecucion_pct") is None:problems.append(f"Comuna {x.get('comuna')}: sin ejecución")
# Guardarraíl conceptual: el JSON debe mantener ambos conceptos separados.
if not all("gasto_localizado" in x and "administrado" in x for x in cs):problems.append("no separa administrado de localizado")
if d.get("quality",{}).get("admin_rows",0)<=0:problems.append("sin filas administrativas")
if problems:
 print("✘ descentralización inválida")
 for x in problems:print("  ·",x)
 raise SystemExit(1)
print(f"✓ Descentralización validada · T{d['quarter']} 2026 · 15 comunas · peso GCBA {d['headline']['participacion_presupuesto_gcba_pct']}%")
