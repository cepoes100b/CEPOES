#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V31 = ROOT / 'automatizar_analisis_legislativo_v3_1.py'
v31 = V31.read_text(encoding='utf-8')

for token in [
    'sanitize_unsupported_entities', 'unsupported_entity_removed',
    "result['recommendation'] = 'sin_definir'", "result['confidence'] = min",
    'strict.unsupported_acronyms(result, material)',
    'Persisten entidades/siglas no respaldadas tras saneamiento',
    "evidence['selection_policy'] = 'strict-v3.1'",
    "'preliminary_insufficient_evidence'", "result['proposed_amendments'] == ''",
]:
    assert token in v31, f'Falta guardrail histórico v3.1: {token}'

print('Análisis legislativo v3.1 · saneamiento conservador OK')
