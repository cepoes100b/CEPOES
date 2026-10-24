#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V34 = ROOT / 'automatizar_analisis_legislativo_v3_4.py'
WORKFLOW = ROOT / '.github/workflows/analizar-legislatura.yml'
VALIDATION = ROOT / '.github/workflows/validar-analisis-automatico.yml'

v34 = V34.read_text(encoding='utf-8')
workflow = WORKFLOW.read_text(encoding='utf-8')
validation = VALIDATION.read_text(encoding='utf-8')

for token in [
    'Una sola llamada al modelo', 'strict.run_copilot(v3.build_prompt_v3(material))',
    'apply_entity_guardrail', 'apply_numeric_guardrail', 'apply_institution_guardrail',
    'apply_external_reference_guardrail', 'neutralize_low_confidence',
    'final_assertions', 'single_pass_deterministic_guardrails', 'strict-v3.4',
    'v3.fetch_supplement = v32.fetch_supplement_resolved',
]:
    assert token in v34, f'Falta arquitectura v3.4: {token}'

# No puede volver a introducir una segunda corrección por modelo.
assert v34.count('strict.run_copilot(') == 1, 'v3.4 debe tener exactamente una llamada de inferencia'
assert 'automatizar_analisis_legislativo_v3_4.py --max-items' in workflow
assert 'cancel-in-progress: true' in workflow
assert 'automatizar_analisis_legislativo_v3_4.py --self-test' in validation
assert 'verificar_analisis_v3_4.py' in validation

print('Análisis legislativo v3.4 · validación estática OK')
print('  Inferencia: una sola llamada')
print('  Grounding: cascada determinística + control final')
