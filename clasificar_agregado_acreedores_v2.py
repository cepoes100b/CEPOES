#!/usr/bin/env python3
"""Wrapper robusto para la clasificación agregada de acreedores.

El BCRA publica la nómina general de entidades financieras mediante una página que
no expone sus filas al runner de GitHub Actions, aun después de renderizar con
Chromium. Como fallback se usa la unión EXACTA de las tres nóminas oficiales
vigentes a abril de 2026 que componen ese universo:

- Bancos públicos: tipo=2
- Bancos privados: tipo=3
- Compañías financieras: tipo=5

No se infiere ningún código por rango ni por denominación. El resto de registros
continúa leyéndose desde las páginas oficiales en tiempo de ejecución.
"""
from __future__ import annotations

import clasificar_agregado_acreedores as base

# Fuente BCRA, información actualizada a abril de 2026.
# Públicos: https://www.bcra.gob.ar/sistema-financiero-nomina-de-entidades/?bco=AAA10&tipo=2
PUBLICOS = {
    "00011", "00014", "00020", "00029", "00065", "00083", "00093",
    "00094", "00097", "00268", "00300", "00309", "00311", "00315",
}

# Privados: https://www.bcra.gob.ar/sistema-financiero-nomina-de-entidades/?bco=AAA20&tipo=3
PRIVADOS = {
    "00007", "00015", "00016", "00017", "00027", "00034", "00044",
    "00045", "00072", "00086", "00131", "00143", "00147", "00165",
    "00191", "00198", "00247", "00254", "00266", "00269", "00277",
    "00281", "00285", "00299", "00301", "00305", "00310", "00312",
    "00319", "00321", "00322", "00330", "00331", "00332", "00338",
    "00339", "00340", "00341", "00384", "00386", "00389", "00426",
    "00431", "00432", "00435", "00448",
}

# Compañías financieras: https://www.bcra.gob.ar/sistema-financiero-nomina-de-entidades/?bco=AAA30&tipo=5
COMPANIAS_FINANCIERAS = {
    "44077", "44088", "44092", "44093", "44094", "44095", "44096",
    "44098", "44099", "45030", "45056", "45072", "65203",
}

ENTIDADES_FINANCIERAS_OFICIALES = PUBLICOS | PRIVADOS | COMPANIAS_FINANCIERAS

_original = base.cargar_registro


def cargar_registro_robusto(categoria: str, url: str) -> dict:
    try:
        return _original(categoria, url)
    except RuntimeError:
        if categoria != "entidad_financiera":
            raise
        codigos = sorted(ENTIDADES_FINANCIERAS_OFICIALES)
        assert len(codigos) == 73, len(codigos)
        return {
            "url": url,
            "metodo": "fallback_union_nominas_oficiales_bcra_abril_2026",
            "cantidad_codigos": len(codigos),
            "codigos": codigos,
            "error_requests": "La nómina general no expone filas al runner; se usa unión exacta tipo 2 + tipo 3 + tipo 5.",
        }


base.cargar_registro = cargar_registro_robusto

if __name__ == "__main__":
    raise SystemExit(base.main())
