#!/usr/bin/env python3
"""Validaciones estáticas del pipeline privado de análisis legislativo automático."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / 'automatizar_analisis_legislativo.py'
COPILOT = ROOT / 'automatizar_analisis_legislativo_copilot.py'
WORKFLOW = ROOT / '.github/workflows/analizar-legislatura.yml'
EDGE = ROOT / 'supabase/functions/legislative-analysis-ingest-v2/index.ts'
MIGRATION = ROOT / 'infra/supabase/004_analisis_legislativo_automatico.sql'
FOCUS_MIGRATION = ROOT / 'infra/supabase/005_focus_analisis_rls.sql'
UI = ROOT / 'deploy/site-overlay/assets/legislativa-auto-ui.js'
CONFIG = ROOT / 'deploy/site-overlay/assets/legislativa-config.js'
DOC = ROOT / 'docs/ANALISIS-LEGISLATIVO-AUTOMATICO.md'

for path in [SCRIPT, COPILOT, WORKFLOW, EDGE, MIGRATION, FOCUS_MIGRATION, UI, CONFIG, DOC]:
    assert path.is_file() and path.stat().st_size > 100, f'Falta o está vacío: {path.relative_to(ROOT)}'

script = SCRIPT.read_text(encoding='utf-8')
copilot = COPILOT.read_text(encoding='utf-8')
workflow = WORKFLOW.read_text(encoding='utf-8')
edge = EDGE.read_text(encoding='utf-8')
migration = MIGRATION.read_text(encoding='utf-8').lower()
focus_migration = FOCUS_MIGRATION.read_text(encoding='utf-8').lower()
ui = UI.read_text(encoding='utf-8')
config = CONFIG.read_text(encoding='utf-8')

# Repositorio personal: Copilot se autentica con un PAT de Copilot Requests; OIDC se usa sólo para Supabase.
assert re.search(r'^\s*id-token:\s*write\s*$', workflow, re.M), 'Falta permiso id-token: write'
assert 'models: read' not in workflow, 'GitHub Models fue retirado y no debe seguir configurado'
assert 'COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}' in workflow, 'Falta credencial Copilot de repositorio personal'
assert 'npm install -g @github/copilot@latest' in workflow, 'No se instala Copilot CLI vigente'
assert 'automatizar_analisis_legislativo_copilot.py' in workflow, 'El workflow no usa el adaptador Copilot'
assert 'legislative-analysis-ingest-v2' in workflow, 'El workflow no usa el receptor RLS vigente'
for forbidden in ['SUPABASE_SERVICE_ROLE', 'SUPABASE_SECRET_KEY', 'OPENAI_API_KEY']:
    assert forbidden not in workflow, f'Secreto/variable administrativa prohibida en workflow: {forbidden}'

# El adaptador de Copilot debe ser no interactivo, sin herramientas y exigir JSON.
assert 'COPILOT_GITHUB_TOKEN' in copilot
assert '--no-ask-user' in copilot and '--no-custom-instructions' in copilot
assert '--deny-tool=shell,write,read,url,memory' in copilot, 'Copilot podría usar herramientas externas'
assert 'Devolvé SOLAMENTE un objeto JSON válido' in copilot
assert 'recommendation debe ser "sin_definir"' in copilot
assert 'pipeline.call_model = call_copilot' in copilot

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
assert 'analysis_origin:"automatic"' in edge
assert 'review_status:"borrador"' in edge
assert 'review_required:true' in edge
assert 'is_current:true' in edge

# Evidencia: únicamente dominio legislativo oficial y hash de fuente antes de inferir.
assert 'allowed_official_url' in script, 'No se valida el dominio oficial'
assert 'legislatura.gob.ar' in script, 'No se detecta dominio oficial permitido'
assert 'source_hash' in script and 'sha256' in script, 'No se versiona evidencia con hash'
check_pos = script.find('"action": "check"')
model_pos = script.find('analysis = call_model(material)')
assert 0 <= check_pos < model_pos, 'La inferencia se ejecuta antes de deduplicar evidencia'

# La base conserva procedencia y versiones. El foco es inaccesible a clientes aunque use el schema public.
for field in [
    'analysis_origin', 'automation_source_hash', 'automation_model', 'automation_confidence',
    'review_required', 'source_evidence', 'affected_actors', 'arguments_for',
    'arguments_against', 'evidence_gaps', 'analysis_focus_commissions'
]:
    assert field in migration, f'Falta soporte de base: {field}'
assert 'enable row level security' in focus_migration
assert 'revoke all on public.analysis_focus_commissions from public, anon, authenticated' in focus_migration
assert 'grant select on public.analysis_focus_commissions to service_role' in focus_migration
for private_name in ['salud', 'discapacidad', 'asuntos constitucionales', 'educación, ciencia y tecnología']:
    assert private_name not in migration + focus_migration, 'La lista estratégica concreta no debe versionarse'

# La UI muestra sólo versiones vigentes en su capa ampliada y exige revisión visualmente.
assert ".eq('is_current', true)" in ui, 'La UI automática no filtra versiones vigentes'
assert 'REVISIÓN REQUERIDA' in ui, 'No se identifica la revisión humana obligatoria'
assert 'automation_confidence' in ui, 'No se muestra la confianza de la salida automática'
assert 'analysis-gaps' in ui and 'analysis-actors' in ui, 'Faltan campos ampliados de revisión'
assert 'legislativa-auto-ui.js' in config, 'La capa UI automática no se carga'

print('Análisis legislativo automático · validación estática OK')
print('  Copilot CLI + OIDC Supabase: verificados')
print('  Foco privado: RLS sin acceso de cliente')
print('  Revisión humana y evidencia oficial: verificadas')
