#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V31 = ROOT / 'automatizar_analisis_legislativo_v3_1.py'
V32 = ROOT / 'automatizar_analisis_legislativo_v3_2.py'
V33 = ROOT / 'automatizar_analisis_legislativo_v3_3.py'
WORKFLOW = ROOT / '.github/workflows/analizar-legislatura.yml'

v31 = V31.read_text(encoding='utf-8')
v32 = V32.read_text(encoding='utf-8') if V32.exists() else ''
v33 = V33.read_text(encoding='utf-8') if V33.exists() else ''
workflow = WORKFLOW.read_text(encoding='utf-8')

# v3.1 debe seguir siendo una capa válida. Producción puede usarla directamente
# o una cadena sucesora que la importe transitivamente y conserve sus guardrails.
uses_v31 = 'automatizar_analisis_legislativo_v3_1.py --max-items' in workflow
uses_v32 = ('import automatizar_analisis_legislativo_v3_1 as v31' in v32 and
            'automatizar_analisis_legislativo_v3_2.py --max-items' in workflow)
uses_v33 = ('import automatizar_analisis_legislativo_v3_1 as v31' in v32 and
            'import automatizar_analisis_legislativo_v3_2 as v32' in v33 and
            'automatizar_analisis_legislativo_v3_3.py --max-items' in workflow)
assert uses_v31 or uses_v32 or uses_v33, 'Producción no usa v3.1 ni una capa sucesora compatible'
assert 'sanitize_unsupported_entities' in v31
assert 'unsupported_entity_removed' in v31
assert "result['recommendation'] = 'sin_definir'" in v31
assert "result['confidence'] = min" in v31
assert 'strict.unsupported_acronyms(result, material)' in v31
assert 'Persisten entidades/siglas no respaldadas tras saneamiento' in v31
assert "evidence['selection_policy'] = 'strict-v3.1'" in v31
assert "'preliminary_insufficient_evidence'" in v31
assert "result['proposed_amendments'] == ''" in v31

print('Análisis legislativo v3.1 · saneamiento conservador OK')
