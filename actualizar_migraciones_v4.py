#!/usr/bin/env python3
"""Entrada definitiva: actualiza sólo ante cambios sustantivos en datos oficiales."""
from copy import deepcopy
import actualizar_migraciones as base
import actualizar_migraciones_v2 as m01

base.INDICATORS['schooling'] = (
    'https://www.estadisticaciudad.gob.ar/si/demog/principal-indicador?'
    'cortante=%7B%22annio%22%3Atrue%2C%22lu_nac%22%3Atrue%7D&indicador=b29b'
)
base.parse_commune_eah = m01.parse_commune_eah
_original_build = base.build


def stable_build(previous, session):
    out = _original_build(previous, session)
    semantic_keys = ['headline', 'communes', 'countries', 'recent_migration', 'socioeconomic', 'latest']
    changed = any(out.get(k) != previous.get(k) for k in semantic_keys)
    if not changed:
        # El chequeo diario no debe generar commits/deploys por una mera marca temporal.
        out['generated'] = previous.get('generated', out.get('generated'))
        out['updated_at'] = previous.get('updated_at', out.get('updated_at'))
        out['automation'] = deepcopy(previous.get('automation', out.get('automation', {})))
    return out


base.build = stable_build

if __name__ == '__main__':
    base.main()
