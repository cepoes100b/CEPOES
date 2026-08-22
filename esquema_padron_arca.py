#!/usr/bin/env python3
"""Diseño oficial de registro de Padron_ARCA.txt (ARCA, 220 caracteres).

Las posiciones se derivan del LEAME PADRON incluido en 20260731PADRON.7Z.
Este módulo define únicamente el layout. No registra, imprime ni persiste microdatos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CampoFijo:
    nombre: str
    inicio: int  # 0-based, inclusivo
    fin: int     # 0-based, exclusivo

    @property
    def longitud(self) -> int:
        return self.fin - self.inicio


CAMPOS = (
    CampoFijo("cuit_cuil_cdi", 0, 11),
    CampoFijo("denominacion", 11, 171),
    CampoFijo("actividad", 171, 177),
    CampoFijo("marca_baja", 177, 178),
    CampoFijo("cuit_cuil_reemplazo", 178, 189),
    CampoFijo("fecha_nacimiento_contrato", 189, 199),
    CampoFijo("sexo", 199, 200),
    CampoFijo("codigo_postal", 200, 210),
    CampoFijo("provincia", 210, 212),
    CampoFijo("fecha_fallecimiento", 212, 220),
)

LONGITUD_REGISTRO = 220
CODIGO_PROVINCIA_CABA = "00"
FECHA_NO_INFORMADA = "1901-01-01"

assert CAMPOS[-1].fin == LONGITUD_REGISTRO
assert sum(c.longitud for c in CAMPOS) == LONGITUD_REGISTRO


def cortar(linea: str, campo: CampoFijo) -> str:
    if len(linea) != LONGITUD_REGISTRO:
        raise ValueError(f"Registro ARCA inválido: {len(linea)} caracteres; se esperaban 220")
    return linea[campo.inicio:campo.fin]


def valor(linea: str, nombre: str) -> str:
    campo = next((c for c in CAMPOS if c.nombre == nombre), None)
    if campo is None:
        raise KeyError(nombre)
    return cortar(linea, campo).strip()


def es_caba(linea: str) -> bool:
    return valor(linea, "provincia") == CODIGO_PROVINCIA_CABA


def edad_al(fecha_texto: str, referencia: date) -> int | None:
    """Calcula edad sólo para fechas de nacimiento válidas; no infiere faltantes."""
    if not fecha_texto or fecha_texto == FECHA_NO_INFORMADA:
        return None
    try:
        nacimiento = date.fromisoformat(fecha_texto)
    except ValueError:
        return None
    if nacimiento > referencia:
        return None
    return referencia.year - nacimiento.year - (
        (referencia.month, referencia.day) < (nacimiento.month, nacimiento.day)
    )
