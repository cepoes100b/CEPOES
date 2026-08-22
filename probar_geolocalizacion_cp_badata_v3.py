#!/usr/bin/env python3
"""Ejecuta la prueba BA Data con el CSV oficial del Registro Acumulado APH 2018.

El recurso `juqdkmgo-94-resource` documenta explícitamente barrio, código postal
tradicional, CPA, latitud y longitud. Se reutiliza el parser y comparador del
experimento BA Data base; no se leen microdatos BCRA/ARCA.
"""
import json
import probar_geolocalizacion_cp_badata as base

APH_PAGE = (
    "https://data.buenosaires.gob.ar/dataset/areas-proteccion-historica/"
    "resource/juqdkmgo-94-resource"
)
APH_URL = APH_PAGE + "/download"

base.BADATA_PAGE = APH_PAGE
base.BADATA_URL = APH_URL
rc = base.main()

out = json.load(open(base.OUTPUT, encoding="utf-8"))
meta = out["fuentes"]["badata_mobiliario_urbano"]
meta["dataset_identificado"] = "Registro Acumulado de Áreas de Protección Histórica 2018"
meta["resource_id"] = "juqdkmgo-94-resource"
# Persistir metadatos corregidos en el diagnóstico.
with open(base.OUTPUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
    f.write("\n")

if meta.get("filas_validas_cp_coord", 0) < 1000:
    raise SystemExit(f"APH CSV con pocas filas válidas: {meta}")
if meta.get("cp_distintos", 0) < 30:
    raise SystemExit(f"APH CSV con pocos CP: {meta}")
raise SystemExit(rc)
