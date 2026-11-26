#!/usr/bin/env python3
import json
import re
import unicodedata
from pathlib import Path
from datetime import datetime

P = Path('estructura_legislativa.json')

def norm(v):
    s=unicodedata.normalize('NFKD',str(v or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

def public_structure_status(x):
    status = x.get("control_actualizacion")
    if status is None:
        return None
    if not isinstance(status, dict) or status != {
        "estado": "degradada",
        "motivo": "salud_14_de_15",
        "intentado_en": status.get("intentado_en"),
        "fuente": "https://www.legislatura.gob.ar/comision/salud",
        "integrantes_observados": 14,
        "integrantes_normativos": 15,
    }:
        raise ValueError("Estado de degradación institucional inválido")
    validated_at = x.get("actualizado_en")
    attempted_at = datetime.fromisoformat(status["intentado_en"])
    updated_at = datetime.fromisoformat(validated_at)
    if attempted_at.tzinfo is None or updated_at.tzinfo is None or attempted_at < updated_at:
        raise ValueError("Fechas de degradación institucional inválidas")
    return {**status, "ultimo_validado_en": validated_at}


def validate_structure(x):
    assert x.get('schema') == 'cepoes-estructura-legislativa-v1'
    cs=x.get('comisiones') or []
    assert len(cs) == 27, len(cs)
    assert len({norm(c.get('nombre')) for c in cs}) == 27
    for c in cs:
        expected=int(c['integrantes_normativos'])
        members=c.get('integrantes') or []
        assert len(members) == expected, (c['nombre'],len(members),expected)
        assert len({norm(m.get('nombre')) for m in members}) == expected, c['nombre']
        assert any(norm(m.get('cargo'))=='presidente' for m in members), c['nombre']
        assert all(m.get('nombre') and m.get('bloque') and m.get('cargo') for m in members), c['nombre']

    salud=next(c for c in cs if norm(c.get('nombre'))=='salud')
    negri=[m for m in salud['integrantes'] if 'negri' in norm(m.get('nombre')) and 'claudia' in norm(m.get('nombre'))]
    assert len(negri)==1, negri
    assert 'vicepresidente 1' in norm(negri[0].get('cargo')), negri[0]

    fpba=x['bloques']['fuerza_por_buenos_aires']
    assert len(fpba['integrantes']) == fpba['integrantes_informados'], (len(fpba['integrantes']),fpba['integrantes_informados'])
    assert len(fpba['integrantes']) >= 15
    assert any('negri' in norm(m['nombre']) and 'claudia' in norm(m['nombre']) for m in fpba['integrantes'])
    ref=x['referentes']['claudia_negri']
    assert any(norm(r.get('comision'))=='salud' and 'vicepresidente 1' in norm(r.get('cargo')) for r in ref['comisiones'])
    public_structure_status(x)
    return len(cs), len(fpba['integrantes'])


def main():
    x = json.loads(P.read_text(encoding='utf-8'))
    commissions, members = validate_structure(x)
    print('OK estructura legislativa:', commissions, 'comisiones · FPBA', members, '· Salud/Negri verificado')


if __name__ == '__main__':
    main()
