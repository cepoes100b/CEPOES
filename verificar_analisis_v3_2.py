#!/usr/bin/env python3
"""Validaciones estáticas específicas del endurecimiento v3.2."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V32 = ROOT / 'automatizar_analisis_legislativo_v3_2.py'
V33 = ROOT / 'automatizar_analisis_legislativo_v3_3.py'
WORKFLOW = ROOT / '.github/workflows/analizar-legislatura.yml'
VALIDATION = ROOT / '.github/workflows/validar-analisis-automatico.yml'

for path in [V32, WORKFLOW, VALIDATION]:
    assert path.is_file() and path.stat().st_size > 200, f'Falta {path.name}'

v32 = V32.read_text(encoding='utf-8')
v33 = V33.read_text(encoding='utf-8') if V33.exists() else ''
workflow = WORKFLOW.read_text(encoding='utf-8')
validation = VALIDATION.read_text(encoding='utf-8')

for token in [
    'boletinoficialpdf.buenosaires.gob.ar', '_updated_text_target', 'texto actualizado',
    'fetch_supplement_resolved', 'resolved_from', 'neutralize_low_confidence',
    'low_confidence_neutralized', 'amendments_suppressed_low_confidence',
    'Puntos a verificar antes de adoptar una posición técnica',
    'result["proposed_amendments"] = ""', 'sanitize_institutions',
    'unsupported_institution_removed', 'procuracion penal federal', 'has_unsupported_institution',
]:
    assert token in v32, f'Falta guardrail v3.2: {token}'

uses_v32 = 'automatizar_analisis_legislativo_v3_2.py --max-items' in workflow
uses_v33 = ('import automatizar_analisis_legislativo_v3_2 as v32' in v33 and
            'automatizar_analisis_legislativo_v3_3.py --max-items' in workflow)
assert uses_v32 or uses_v33, 'Producción no usa v3.2 ni un sucesor compatible'
assert 'cancel-in-progress: true' in workflow
assert ('automatizar_analisis_legislativo_v3_2.py --self-test' in validation or
        'automatizar_analisis_legislativo_v3_3.py --self-test' in validation)
assert 'verificar_analisis_v3_2.py' in validation

print('Análisis legislativo v3.2 · validación estática OK')
print('  Normativa: ficha oficial → texto actualizado/PDF')
print('  Confianza baja: posición neutral + enmiendas suprimidas')
print('  Instituciones no respaldadas: unidad textual eliminada')
