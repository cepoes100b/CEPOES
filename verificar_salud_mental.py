#!/usr/bin/env python3
import json
from pathlib import Path

p = Path("salud_mental.json")
if not p.is_file(): raise SystemExit("✘ falta salud_mental.json")
d = json.loads(p.read_text(encoding="utf-8"))
problems=[]
if d.get("status") != "VALIDADO": problems.append("status no VALIDADO")
s=d.get("series",[])
if len(s) != 20: problems.append(f"serie esperada 20 años, recibidos {len(s)}")
years=[x.get("anio") for x in s]
if years != list(range(2005,2025)): problems.append("años no cubren exactamente 2005-2024")
for x in s:
    n=x.get("caba",{}).get("defunciones",0)
    if not isinstance(n,(int,float)) or n <= 0: problems.append(f"CABA sin casos válidos en {x.get('anio')}")
for x in s:
    if x["anio"] >= 2010 and x.get("caba",{}).get("tasa_100k") is None: problems.append(f"falta tasa CABA {x['anio']}")
if s and not (20 <= s[-1]["caba"]["defunciones"] <= 1000): problems.append("último conteo CABA fuera de rango de control")
if problems:
    print("✘ salud mental inválida")
    for x in problems: print("  ·",x)
    raise SystemExit(1)
print(f"✓ Salud mental validada · {len(s)} años · último {s[-1]['anio']} · CABA {s[-1]['caba']['defunciones']} · tasa {s[-1]['caba']['tasa_100k']}")
