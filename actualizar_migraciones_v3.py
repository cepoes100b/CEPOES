#!/usr/bin/env python3
"""Entrada de producción para el actualizador de Migraciones CEPOES."""
import actualizar_migraciones as base
import actualizar_migraciones_v2 as m01

# Algunas pantallas de IDECBA requieren declarar el corte para que el HTML
# exponga el tabulado completo y no sólo los selectores de la interfaz.
base.INDICATORS['schooling'] = (
    'https://www.estadisticaciudad.gob.ar/si/demog/principal-indicador?'
    'cortante=%7B%22annio%22%3Atrue%2C%22lu_nac%22%3Atrue%7D&indicador=b29b'
)
base.parse_commune_eah = m01.parse_commune_eah

if __name__ == '__main__':
    base.main()
