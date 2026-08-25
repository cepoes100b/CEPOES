#!/usr/bin/env python3
"""Genera el dataset público de accesibilidad peatonal deportiva V3.

Reutiliza el motor diagnóstico validado con malla 8x8 y publica solamente datos
agregados por Ciudad/comuna y controles metodológicos; nunca publica las muestras
intraradio ni coordenadas auxiliares.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
PUBLIC = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-accesibilidad-peatonal.json"
EUCLIDEAN = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-accesibilidad.json"
TMP = BASE / "diagnostico_accesibilidad_peatonal_publicacion.json"
GRAPH_REPORT = BASE / "diagnostico_red_peatonal.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    # Importar después de fijar el entorno porque el motor lee GRID_N al cargar.
    os.environ["GRID_N"] = "8"
    os.environ["OUT_FILE"] = TMP.name
    import diagnosticar_accesibilidad_peatonal as calc

    calc.main()
    diag = load(TMP)
    euclid = load(EUCLIDEAN)
    graph_report = load(GRAPH_REPORT) if GRAPH_REPORT.exists() else {}

    coverage = {}
    for key, obj in diag["cobertura"].items():
        distances = {}
        for distance, block in obj["distancias"].items():
            distances[distance] = {
                "ciudad": block["ciudad"],
                "comunas": block["comunas"],
                "comparacion_geometrica": block["comparacion_v2"],
            }
        coverage[key] = {
            "label": euclid["cobertura"][key]["label"],
            "puntos_georreferenciados": obj["puntos_georreferenciados"],
            "tramos_destino_unicos": obj.get("tramos_destino_unicos"),
            "distancia_fuera_red_equipamiento": obj.get("distancia_fuera_red_equipamiento"),
            "distancias": distances,
        }

    base = dict(euclid["base_poblacional"])
    base.update(
        {
            "malla_intraradio": "8x8",
            "muestras_ponderadas": diag["muestreo"]["muestras"],
            "poblacion_reconstruida": diag["muestreo"]["poblacion_reconstruida"],
        }
    )

    off_audit = {
        "estadisticos_m": diag["distancia_fuera_red_muestras"],
        "umbrales": diag["auditoria_fuera_red"]["umbrales"],
    }
    public = {
        "version": 1,
        "generado": datetime.now(timezone.utc).date().isoformat(),
        "titulo": "Accesibilidad peatonal estimada a la red deportiva de CABA",
        "metodologia": {
            **diag["metodologia"],
            "universo": euclid["metodologia"].get("universo"),
            "seleccion_malla": "Se utiliza 8x8. En la auditoría inicial 4x4→8x8 la red total varió 0,16 pp a 800 m y 0,05 pp a 1.000 m; la máxima variación comunal fue 0,69 pp.",
            "limitacion": "Es una estimación de distancia caminable sobre la red peatonal registrada en OpenStreetMap. No mide tiempo real, pendiente, estado de veredas, cruces demorados, seguridad, capacidad, costo, horarios ni acceso efectivo al equipamiento.",
        },
        "base_poblacional": base,
        "grafo_peatonal": {
            **diag["grafo"],
            "generado": graph_report.get("grafo_generado"),
            "edad_dias_al_calculo": graph_report.get("grafo_edad_dias"),
            "margen_m": graph_report.get("margen_m", 1200),
            "longitud_aristas_km": graph_report.get("longitud_aristas_km"),
            "max_edad_dias": graph_report.get("max_edad_dias", 28),
        },
        "control_conexion_red": off_audit,
        "fuentes": [
            {
                "nombre": "OpenStreetMap contributors",
                "url": "https://www.openstreetmap.org/copyright",
                "detalle": "Red caminable descargada y procesada con OSMnx; se conserva en caché y se intenta refrescar cuando supera 28 días.",
            },
            *euclid.get("fuentes", []),
        ],
        "cobertura": coverage,
    }

    PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC.write_text(json.dumps(public, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    TMP.unlink(missing_ok=True)

    red = public["cobertura"]["red_deportiva"]["distancias"]
    print(
        f"{PUBLIC.name} · {PUBLIC.stat().st_size // 1024} KB · "
        f"red 800 m {red['800']['ciudad']['cobertura_pct']}% · "
        f"1000 m {red['1000']['ciudad']['cobertura_pct']}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
