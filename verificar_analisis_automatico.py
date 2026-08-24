#!/usr/bin/env python3
"""Validaciones estáticas del pipeline privado de análisis legislativo automático."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / 'automatizar_analisis_legislativo.py'
COPILOT = ROOT / 'automatizar_analisis_legislativo_copilot.py'
HARDENED = ROOT / 'automatizar_analisis_legislativo_hardened.py'
GROUNDED = ROOT / 'automatizar_analisis_legislativo_hardened_v2.py'
WORKFLOW = ROOT / '.github/workflows/analizar-legislatura.yml'
EDGE = ROOT / 'supabase/functions/legislative-analysis-ingest-v2/index.ts'
MIGRATION = ROOT / 'infra/supabase/004_analisis_legislativo_automatico.sql'
FOCUS_MIGRATION = ROOT / 'infra/supabase/005_focus_analisis_rls.sql'
GUARD_MIGRATION = ROOT / 'infra/supabase/006_guardrails_analisis_automatico.sql'
UI = ROOT / 'deploy/site-overlay/assets/legislativa-auto-ui.js'
CONFIG = ROOT / 'deploy/site-overlay/assets/legislativa-config.js'
DOC = ROOT / 'docs/ANALISIS-LEGISLATIVO-AUTOMATICO.md'

required = [SCRIPT, COPILOT, HARDENED, GROUNDED, WORKFLOW, EDGE, MIGRATION, FOCUS_MIGRATION, GUARD_MIGRATION, UI, CONFIG, DOC]
for path in required:
    assert path.is_file() and path.stat().st_size > 100, f'Falta o está vacío: {path.relative_to(ROOT)}'

script = SCRIPT.read_text(encoding='utf-8')
copilot = COPILOT.read_text(encoding='utf-8')
hardened = HARDENED.read_text(encoding='utf-8')
grounded = GROUNDED.read_text(encoding='utf-8')
workflow = WORKFLOW.read_text(encoding='utf-8')
edge = EDGE.read_text(encoding='utf-8')
migration = MIGRATION.read_text(encoding='utf-8').lower()
focus_migration = FOCUS_MIGRATION.read_text(encoding='utf-8').lower()
guard_migration = GUARD_MIGRATION.read_text(encoding='utf-8').lower()
ui = UI.read_text(encoding='utf-8')
config = CONFIG.read_text(encoding='utf-8')

# Autenticación: Copilot usa PAT de Copilot Requests; Supabase recibe OIDC efímero.
assert re.search(r'^\s*id-token:\s*write\s*$', workflow, re.M), 'Falta permiso id-token: write'
assert 'models: read' not in workflow, 'GitHub Models fue retirado y no debe configurarse'
assert 'COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}' in workflow
assert 'npm install -g @github/copilot@latest' in workflow
assert 'automatizar_analisis_legislativo_hardened_v2.py' in workflow, 'Producción no usa grounded-v2'
assert 'legislative-analysis-ingest-v2' in workflow
for forbidden in ['SUPABASE_SERVICE_ROLE', 'SUPABASE_SECRET_KEY', 'OPENAI_API_KEY']:
    assert forbidden not in workflow, f'Secreto prohibido en workflow: {forbidden}'

# Copilot no puede usar herramientas externas.
for text in [copilot, hardened, grounded]:
    assert 'COPILOT_GITHUB_TOKEN' in text
assert '--no-ask-user' in hardened and '--no-custom-instructions' in hardened
assert '--deny-tool=shell,write,read,url,memory' in hardened
assert 'No uses memoria, conocimiento general ni web' in hardened

# Selección estricta: sin manuales, guías ni anchors de la propia ficha.
for token in ['BANNED_ASSET_TERMS', 'strict-v2', 'documentos_primarios_del_expediente', 'download.aspx', 'document_relevance']:
    assert token in hardened, f'Falta guardrail de evidencia: {token}'
assert 'p.path == base.path and p.query == base.query' in hardened, 'No se excluyen anchors de la ficha'
assert 'relevance < 2' in hardened, 'No se descartan adjuntos de baja relevancia'
assert 'unsupported_acronyms' in hardened

# Grounded-v2: cifras no sustentadas se sanejan y bajan la confianza; entidades siguen siendo error duro.
assert 'unsupported_numbers' in grounded
assert 'sanitize_value' in grounded
assert '"a definir"' in grounded
assert 'Salida con entidades/siglas no respaldadas' in grounded
assert 'result["confidence"] = min' in grounded
assert 'result["recommendation"] = "sin_definir"' in grounded
assert 'confidence < 0.75' in grounded

# OIDC del receptor exacto.
for required_token in [
    'https://token.actions.githubusercontent.com',
    'cepoes-supabase-legislative-analysis',
    'cepoes100b/CEPOES',
    'refs/heads/main',
    '.github/workflows/analizar-legislatura.yml@refs/heads/main',
    'jwtVerify',
]:
    assert required_token in edge, f'Falta verificación OIDC: {required_token}'
assert 'analysis_origin:"automatic"' in edge
assert 'review_status:"borrador"' in edge
assert 'review_required:true' in edge
assert 'is_current:true' in edge

# Deduplicación antes de inferencia y fuentes oficiales.
assert 'allowed_official_url' in script and 'legislatura.gob.ar' in script
assert 'source_hash' in script and 'sha256' in script
check_pos = script.find('"action": "check"')
model_pos = script.find('analysis = call_model(material)')
assert 0 <= check_pos < model_pos, 'La inferencia ocurre antes de deduplicar evidencia'

# Base privada, foco protegido y guardrail server-side.
for field in [
    'analysis_origin', 'automation_source_hash', 'automation_model', 'automation_confidence',
    'review_required', 'source_evidence', 'affected_actors', 'arguments_for',
    'arguments_against', 'evidence_gaps', 'analysis_focus_commissions'
]:
    assert field in migration, f'Falta soporte de base: {field}'
assert 'enable row level security' in focus_migration
assert 'revoke all on public.analysis_focus_commissions from public, anon, authenticated' in focus_migration
assert 'grant select on public.analysis_focus_commissions to service_role' in focus_migration
assert 'guard_automatic_analysis_insert' in guard_migration
assert "new.review_status := 'borrador'" in guard_migration
assert 'new.review_required := true' in guard_migration
assert "new.recommendation := 'sin_definir'" in guard_migration
assert '< 0.75' in guard_migration
assert 'primary_document_count' in guard_migration

for private_name in ['salud', 'discapacidad', 'asuntos constitucionales', 'educación, ciencia y tecnología']:
    assert private_name not in migration + focus_migration + guard_migration, 'El foco concreto no debe versionarse'

# UI privada: sólo versión vigente, origen y revisión visibles.
assert ".eq('is_current', true)" in ui
assert 'REVISIÓN REQUERIDA' in ui
assert 'automation_confidence' in ui
assert 'analysis-gaps' in ui and 'analysis-actors' in ui
assert 'legislativa-auto-ui.js' in config

print('Análisis legislativo automático · validación estática OK')
print('  Evidencia: selector strict-v2 + grounded-v2')
print('  Cifras no sustentadas: saneadas a “a definir”')
print('  Recomendación: umbral 0.75 + documento primario')
print('  Copilot CLI + OIDC Supabase: verificados')
