#!/usr/bin/env python3
"""Detecta hallazgos actualizados sin publicarlos como notas aprobadas."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "datos" / "prensa-borradores.json"

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def main():
    mig = load("deploy/site-overlay/assets/data/migraciones.json")
    sport = load("deploy/site-overlay/assets/data/deporte-accesibilidad-peatonal.json")
    prod = load("deploy/site-overlay/assets/data/estructura-productiva/actual.json")
    debt_manifest = load("datos/endeudamiento/manifest.json")
    debt = load("datos/endeudamiento/" + debt_manifest["archivos"][debt_manifest["ultimo_periodo"]])

    mvals = sorted(((v["eah"]["migracion_internacional_pct"], k) for k, v in mig["communes"].items()), reverse=True)
    cov = sport["cobertura"]["clubes"]["distancias"]["800"]["ciudad"]
    series = prod["panorama"]["empresas_registradas"]["serie"]
    base = next(x for x in debt["segmentos"] if all(v is None for v in x["filtros"].values()))
    mora = sorted(((row[1] / row[0] * 100, barrio) for barrio, row in zip(debt["barrios"], base["datos"])), reverse=True)

    drafts = [
        {"tema":"Migraciones", "hallazgo":f"Comuna {mvals[0][1]} encabeza la proporción de población migrante internacional ({mvals[0][0]:.1f}%).", "periodo":str(mig["latest"]["place_birth_commune_eah"])},
        {"tema":"Deporte y salud", "hallazgo":f"{cov['poblacion_fuera_cobertura_estimada']:,} personas quedan a más de 800 m caminables de una sede de club ({cov['cobertura_pct']:.1f}% cubierto).", "periodo":sport["generado"]},
        {"tema":"Estructura productiva", "hallazgo":f"El stock de empresas registradas pasó de {series[0]['empresas']:,} en {series[0]['anio']} a {series[-1]['empresas']:,} en {series[-1]['anio']}.", "periodo":str(series[-1]["anio"])},
        {"tema":"Endeudamiento", "hallazgo":f"{mora[0][1]} presenta la mayor incidencia barrial estimada de mora ({mora[0][0]:.1f}%).", "periodo":debt["periodo"]}
    ]
    if OUT.exists():
        previous = json.loads(OUT.read_text(encoding="utf-8"))
        if previous.get("borradores") == drafts:
            print(f"{OUT.relative_to(ROOT)} · sin nuevos hallazgos")
            return
    payload = {"schema":"cepoes-prensa-borradores-v1", "generado_utc":datetime.now(timezone.utc).isoformat(), "estado":"REQUIERE_REVISION_EDITORIAL", "borradores":drafts}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)} · {len(drafts)} borradores · no publicados")

if __name__ == "__main__":
    main()
