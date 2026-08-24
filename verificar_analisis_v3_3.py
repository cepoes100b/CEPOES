#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V33 = ROOT / 'automatizar_analisis_legislativo_v3_3.py'
WORKFLOW = ROOT / '.github/workflows/analizar-legislatura.yml'
VALIDATION = ROOT / '.github/workflows/validar-analisis-automatico.yml'

v33 = V33.read_text(encoding='utf-8')
workflow = WORKFLOW.read_text(encoding='utf-8')
validation = VALIDATION.read_text(encoding='utf-8')

for token in [
    'EXTERNAL_REFERENCE_PATTERNS', 'c[oó]digo penal', 'jurisprudencia',
    'sanitize_external_references', 'unsupported_external_reference_removed',
    'strict-v3.3', 'v3.fetch_supplement = v32.fetch_supplement_resolved',
]:
    assert token in v33, f'Falta guardrail v3.3: {token}'
assert 'automatizar_analisis_legislativo_v3_3.py --max-items' in workflow
assert 'cancel-in-progress: true' in workflow
assert 'automatizar_analisis_legislativo_v3_3.py --self-test' in validation
assert 'verificar_analisis_v3_3.py' in validation

print('Análisis legislativo v3.3 · validación estática OK')
print('  Referencias jurídicas externas no evidenciadas: saneadas')
print('  Normativa actualizada v3.2: preservada')
