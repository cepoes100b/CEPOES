#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V32 = ROOT / 'automatizar_analisis_legislativo_v3_2.py'
v32 = V32.read_text(encoding='utf-8')

for token in [
    'boletinoficialpdf.buenosaires.gob.ar', '_updated_text_target', 'texto actualizado',
    'fetch_supplement_resolved', 'resolved_from', 'neutralize_low_confidence',
    'low_confidence_neutralized', 'amendments_suppressed_low_confidence',
    'Puntos a verificar antes de adoptar una posición técnica',
    'result["proposed_amendments"] = ""', 'sanitize_institutions',
    'unsupported_institution_removed', 'procuracion penal federal', 'has_unsupported_institution',
]:
    assert token in v32, f'Falta guardrail histórico v3.2: {token}'

print('Análisis legislativo v3.2 · normativa actualizada y neutralización OK')
