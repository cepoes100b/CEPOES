#!/usr/bin/env python3
"""Detecta hallazgos actualizados sin publicarlos como notas aprobadas."""
import json
import hashlib
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
FUNCTION_URL = os.environ.get("PRESS_DRAFT_FUNCTION_URL", "")
OIDC_AUDIENCE = "cepoes-supabase-press-drafts"

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

    raw = [
      {"slug":f"migraciones-comuna-{mvals[0][1]}-{mig['latest']['place_birth_commune_eah']}","topic":"Migraciones","title":f"La Comuna {mvals[0][1]} encabeza el peso de la migración internacional","summary":f"La EAH {mig['latest']['place_birth_commune_eah']} estima que el {mvals[0][0]:.1f}% de su población nació en otro país.","body":["La distribución territorial de la población migrante internacional presenta diferencias marcadas entre comunas. Este borrador identifica el valor máximo del último período disponible y queda sujeto a revisión editorial."],"methodology":"Encuesta Anual de Hogares de IDECBA. Las estimaciones comunales están sujetas a error muestral.","source_label":"IDECBA · Elaboración CEPOES","source_section":"/territorio/migraciones/","source_period":str(mig['latest']['place_birth_commune_eah'])},
      {"slug":f"acceso-clubes-{sport['generado']}","topic":"Deporte y salud","title":f"Más de {cov['poblacion_fuera_cobertura_estimada']:,.0f} porteños quedan a más de 800 metros caminables de un club".replace(",","."),"summary":f"La cobertura peatonal estimada alcanza al {cov['cobertura_pct']:.1f}% de la población.","body":["La medición sobre la red peatonal permite observar brechas que la distancia en línea recta no registra. El resultado no equivale a acceso efectivo y debe interpretarse junto con las limitaciones metodológicas."],"methodology":"Radios censales 2022 y recorridos estimados sobre OpenStreetMap.","source_label":"BA Data, INDEC y OpenStreetMap · Elaboración CEPOES","source_section":"/territorio/deporte-salud/","source_period":sport['generado']},
      {"slug":f"empresas-registradas-{series[-1]['anio']}","topic":"Estructura productiva","title":f"CABA registra {series[-1]['empresas']:,} empresas privadas con empleo asalariado".replace(",","."),"summary":f"Son {series[0]['empresas']-series[-1]['empresas']:,} menos que en {series[0]['anio']}.".replace(",","."),"body":["La serie permite comparar la evolución del stock de empresas privadas registradas en la Ciudad. No debe confundirse con cantidad de locales ni con el universo de trabajadores independientes."],"methodology":"Empresas privadas con empleo asalariado registrado según OEDE/SIPA.","source_label":"OEDE/SIPA · Elaboración CEPOES","source_section":"/territorio/estructura-productiva/","source_period":str(series[-1]['anio'])},
      {"slug":f"mora-maxima-{debt['periodo']}","topic":"Endeudamiento","title":f"{mora[0][1]} presenta la mayor incidencia barrial estimada de mora","summary":f"La proporción alcanza al {mora[0][0]:.1f}% de las personas deudoras en {debt['periodo']}.","body":["La estimación territorial muestra una distribución desigual de la mora entre barrios. Los resultados son agregados estadísticos y no geolocalizaciones individuales."],"methodology":"Central de Deudores del BCRA y Padrón ARCA; matriz postal-territorial de CEPOES.","source_label":"BCRA y Padrón ARCA · Elaboración CEPOES","source_section":"/territorio/endeudamiento/","source_period":debt['periodo']}
    ]
    for d in raw:
        d.update({"facts":[],"quote":""})
        d["source_hash"] = hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if not FUNCTION_URL:
        print(json.dumps({"drafts":raw},ensure_ascii=False,indent=2)); return
    base=os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL"); token=os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not base or not token: raise RuntimeError("GitHub OIDC no está disponible")
    sep="&" if "?" in base else "?"
    oidc_req=Request(f"{base}{sep}audience={OIDC_AUDIENCE}",headers={"Authorization":f"Bearer {token}"})
    with urlopen(oidc_req,timeout=30) as response: oidc=json.loads(response.read())["value"]
    ingest_req=Request(FUNCTION_URL,data=json.dumps({"drafts":raw}).encode(),headers={"Authorization":f"Bearer {oidc}","Content-Type":"application/json"},method="POST")
    with urlopen(ingest_req,timeout=30) as response: result=json.loads(response.read())
    print(f"Bandeja privada · {result}")

if __name__ == "__main__":
    main()
