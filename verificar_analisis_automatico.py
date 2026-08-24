#!/usr/bin/env python3
"""Validaciones estáticas del pipeline privado de análisis legislativo automático."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / 'automatizar_analisis_legislativo.py'
WORKFLOW = ROOT / '.github/workflows/analizar-legislatura.yml'
EDGE = ROOT / 'supabase/functions/legislative-analysis-ingest/index.ts'
MIGRATION = ROOT / 'infra/supabase/004_analisis_legislativo_automatico.sql'
UI = ROOT / 'deploy/site-overlay/assets/legislativa-auto-ui.js'
CONFIG = ROOT / 'deploy/site-overlay/assets/legislativa-config.js'
DOC = ROOT / 'docs/ANALISIS-LEGISLATIVO-AUTOMATICO.md'

for path in [SCRIPT, WORKFLOW, EDGE, MIGRATION, UI, CONFIG, DOC]:
    assert path.is_file() and path.stat().st_size > 100, f'Falta o está vacío: {path.relative_to(ROOT)}'

script = SCRIPT.read_text(encoding='utf-8')
workflow = WORKFLOW.read_text(encoding='utf-8')
edge = EDGE.read_text(encoding='utf-8')
migration = MIGRATION.read_text(encoding='utf-8').lower()
ui = UI.read_text(encoding='utf-8')
config = CONFIG.read_text(encoding='utf-8')

# El workflow usa credenciales efímeras propias de GitHub, no secretos administrativos de Supabase.
assert re.search(r'^\s*models:\s*read\s*$', workflow, re.M), 'Falta permiso models: read'
assert re.search(r'^\s*id-token:\s*write\s*$', workflow, re.M), 'Falta permiso id-token: write'
for forbidden in ['SUPABASE_SERVICE_ROLE', 'SUPABASE_SECRET_KEY', 'OPENAI_API_KEY']:
    assert forbidden not in workflow, f'Secreto/variable administrativa prohibida en workflow: {forbidden}'

# El receptor debe verificar el origen exacto del token OIDC antes de tocar la base.
for required in [
    'https://token.actions.githubusercontent.com',
    'cepoes-supabase-legislative-analysis',
    'cepoes100b/CEPOES',
    'refs/heads/main',
    '.github/workflows/analizar-legislatura.yml@refs/heads/main',
    'jwtVerify',
]:
    assert required in edge, f'Falta verificación OIDC: {required}'
assert 'analysis_origin: "automatic"' in edge
assert 'review_status: "borrador"' in edge
assert 'review_required: true' in edge
assert 'is_current: true' in edge

# Evidencia: únicamente dominio legislativo oficial y hash de fuente antes de inferir.
assert 'allowed_official_url' in script, 'No se valida el dominio oficial'
assert 'legislatura.gob.ar' in script, 'No se detecta dominio oficial permitido'
assert 'source_hash' in script and 'sha256' in script, 'No se versiona evidencia con hash'
check_pos = script.find('"action": "check"')
model_pos = script.find('analysis = call_model(material)')
assert 0 <= check_pos < model_pos, 'El modelo se ejecuta antes de deduplicar evidencia'
assert 'response_format' in script and 'json_schema' in script, 'No se exige salida estructurada'
assert "recommendation='sin_definir'" in script, 'No se explicita salida prudente ante evidencia insuficiente'

# La migración conserva procedencia, revisión y versiones sin publicar el foco concreto.
for field in [
    'analysis_origin', 'automation_source_hash', 'automation_model', 'automation_confidence',
    'review_required', 'source_evidence', 'affected_actors', 'arguments_for',
    'arguments_against', 'evidence_gaps', 'analysis_focus_commissions'
]:
    assert field in migration, f'Falta soporte de base: {field}'
for private_name in ['salud', 'discapacidad', 'asuntos constitucionales', 'educación, ciencia y tecnología']:
    assert private_name not in migration, 'La lista estratégica concreta no debe versionarse'

# La UI debe mostrar sólo versiones vigentes en su capa ampliada y exigir revisión visualmente.
assert ".eq('is_current', true)" in ui, 'La UI automática no filtra versiones vigentes'
assert 'REVISIÓN REQUERIDA' in ui, 'No se identifica la revisión humana obligatoria'
assert 'automation_confidence' in ui, 'No se muestra la confianza de la salida automática'
assert 'analysis-gaps' in ui and 'analysis-actors' in ui, 'Faltan campos ampliados de revisión'
assert 'legislativa-auto-ui.js' in config, 'La capa UI automática no se carga'

print('Análisis legislativo automático · validación estática OK')
print('  GitHub Models + OIDC: verificados')
print('  Revisión humana: obligatoria')
print('  Evidencia oficial y versionada: verificada')
