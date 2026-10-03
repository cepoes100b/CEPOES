#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V33 = ROOT / 'automatizar_analisis_legislativo_v3_3.py'
v33 = V33.read_text(encoding='utf-8')

for token in [
    'EXTERNAL_REFERENCE_PATTERNS', 'c[oó]digo penal', 'jurisprudencia',
    'sanitize_external_references', 'unsupported_external_reference_removed',
    'strict-v3.3', 'v3.fetch_supplement = v32.fetch_supplement_resolved',
]:
    assert token in v33, f'Falta guardrail histórico v3.3: {token}'

print('Análisis legislativo v3.3 · referencias jurídicas externas saneadas')
