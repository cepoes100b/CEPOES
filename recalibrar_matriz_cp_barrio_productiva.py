#!/usr/bin/env python3
"""Recalibra la matriz CP4->barrio sobre la base territorial productiva.

Es una herramienta de validación, no forma parte del workflow mensual. Adapta la
salida productiva (provincia ARCA=00 + CP4 1000-1499) al estimador v2.29 y genera
una matriz candidata que luego debe congelarse para producción.
"""
from __future__ import annotations

import json
from pathlib import Path

import reconstruir_matriz_cp_barrio as estimador

SRC = Path("diagnostico_endeudamiento_productivo.json")
COMPAT = Path("diagnostico_territorial_productivo_compat.json")
OUT_MATRIX = Path("matriz_cp_barrio_productiva_candidata.json")
OUT_DIAG = Path("diagnostico_matriz_cp_barrio_productiva.json")


def main() -> int:
    src = json.loads(SRC.read_text(encoding="utf-8"))
    compat = {
        "schema": "cepoes-bcra-territorial-productivo-compat-v1",
        "periodo_deuda": src["periodo_deuda"],
        "agregado_cp_1000_1499": src["agregado_cp_caba_1000_1499"],
        "agregado_cp_sexo_edad_1000_1499": src["agregado_cp_sexo_edad_caba_1000_1499"],
        "privacidad": src["privacidad"],
    }
    COMPAT.write_text(json.dumps(compat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    estimador.INPUT = COMPAT
    estimador.OUT_MATRIX = OUT_MATRIX
    estimador.OUT_DIAG = OUT_DIAG
    rc = estimador.main()

    d = json.loads(OUT_DIAG.read_text(encoding="utf-8"))
    print(json.dumps({
        "estado": d.get("estado"),
        "periodo": d.get("periodo"),
        "soporte": d.get("soporte_geografico"),
        "validacion_mora": (d.get("resultado_validacion") or {}).get("modelo"),
        "checks": d.get("checks"),
    }, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
