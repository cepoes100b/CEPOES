#!/usr/bin/env python3
"""Validaciones estáticas del pipeline privado de análisis legislativo automático v3."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / 'automatizar_analisis_legislativo.py'
COPILOT = ROOT / 'automatizar_analisis_legislativo_copilot.py'
HARDENED = ROOT / 'automatizar_analisis_legislativo_hardened.py'
V2 = ROOT / 'automatizar_analisis_legislativo_hardened_v2.py'
V3 = ROOT / 'automatizar_analisis_legislativo_v3.py'
REGISTRY = ROOT / 'normativa_referencia_caba.json'
WORKFLOW = ROOT / '.github/workflows/analizar-legislatura.yml'
EDGE = ROOT / 'supabase/functions/legislative-analysis-ingest-v2/index.ts'
MIGRATION = ROOT / 'infra/supabase/004_analisis_legislativo_automatico.sql'
FOCUS_MIGRATION = ROOT / 'infra/supabase/005_focus_analisis_rls.sql'
GUARD_MIGRATION = ROOT / 'infra/supabase/006_guardrails_analisis_automatico.sql'
V3_MIGRATION = ROOT / 'infra/supabase/007_analisis_legislativo_v3.sql'
UI = ROOT / 'deploy/site-overlay/assets/legislativa-auto-ui.js'
CONFIG = ROOT / 'deploy/site-overlay/assets/legislativa-config.js'
DOC = ROOT / 'docs/ANALISIS-LEGISLATIVO-AUTOMATICO.md'

required = [SCRIPT, COPILOT, HARDENED, V2, V3, REGISTRY, WORKFLOW, EDGE, MIGRATION, FOCUS_MIGRATION, GUARD_MIGRATION, V3_MIGRATION, UI, CONFIG, DOC]
for path in required:
    assert path.is_file() and path.stat().st_size > 100, f'Falta o está vacío: {path.relative_to(ROOT)}'

script = SCRIPT.read_text(encoding='utf-8')
hardened = HARDENED.read_text(encoding='utf-8')
v3 = V3.read_text(encoding='utf-8')
workflow = WORKFLOW.read_text(encoding='utf-8')
edge = EDGE.read_text(encoding='utf-8')
migration = MIGRATION.read_text(encoding='utf-8').lower()
focus_migration = FOCUS_MIGRATION.read_text(encoding='utf-8').lower()
v3_migration = V3_MIGRATION.read_text(encoding='utf-8').lower()
ui = UI.read_text(encoding='utf-8')
config = CONFIG.read_text(encoding='utf-8')
registry = json.loads(REGISTRY.read_text(encoding='utf-8'))

# Autenticación y ejecución.
assert re.search(r'^\s*id-token:\s*write\s*$', workflow, re.M)
assert 'models: read' not in workflow
assert 'COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}' in workflow
assert 'npm install -g @github/copilot@latest' in workflow
assert 'automatizar_analisis_legislativo_v3.py' in workflow, 'Producción no usa v3'
assert 'legislative-analysis-ingest-v2' in workflow
for forbidden in ['SUPABASE_SERVICE_ROLE', 'SUPABASE_SECRET_KEY', 'OPENAI_API_KEY']:
    assert forbidden not in workflow, f'Secreto prohibido en workflow: {forbidden}'

# Copilot no puede usar herramientas externas.
assert '--no-ask-user' in hardened and '--no-custom-instructions' in hardened
assert '--deny-tool=shell,write,read,url,memory' in hardened
assert 'No uses memoria, conocimiento general ni web' in hardened

# Selección primaria strict-v2 conservada.
for token in ['BANNED_ASSET_TERMS', 'strict-v2', 'documentos_primarios_del_expediente', 'download.aspx', 'document_relevance']:
    assert token in hardened, f'Falta guardrail primario: {token}'
assert 'p.path == base.path and p.query == base.query' in hardened
assert 'relevance < 2' in hardened

# v3: sin placeholders, modo preliminar y normativa complementaria separada.
for token in [
    'preliminary_insufficient_evidence', 'strict-v3', 'supplementary_normative_evidence',
    'NORMATIVA VIGENTE COMPLEMENTARIA', 'No uses placeholders como "a definir"',
    'recommendation="sin_definir"', 'arguments_for=""', 'proposed_amendments=""',
    'boletinoficial.buenosaires.gob.ar', 'normativa_referencia_caba.json',
    'cited_articles_for_law', 'article_excerpt', 'quality_flags'
]:
    assert token in v3, f'Falta regla v3: {token}'
assert 'PLACEHOLDER_RE' in v3 and 'ADVOCACY_RE' in v3
assert 'unsupported_numeric_removed' in v3 and 'placeholder_removed' in v3
assert 'confidence < 0.75' in v3
assert 'pipeline.collect_source = collect_source_v3' in v3
assert 'pipeline.call_model = call_copilot_v3' in v3

# Registro de normativa complementaria sólo con fuentes oficiales de CABA.
assert {'114','1472','1845'}.issubset(registry.keys())
for item in registry.values():
    url = str(item.get('url') or '')
    assert url.startswith('https://boletinoficial.buenosaires.gob.ar/normativaba/norma/')

# OIDC del receptor exacto.
for required_token in [
    'https://token.actions.githubusercontent.com', 'cepoes-supabase-legislative-analysis',
    'cepoes100b/CEPOES', 'refs/heads/main',
    '.github/workflows/analizar-legislatura.yml@refs/heads/main', 'jwtVerify'
]:
    assert required_token in edge, f'Falta verificación OIDC: {required_token}'
assert 'analysis_origin:"automatic"' in edge
assert 'review_status:"borrador"' in edge
assert 'review_required:true' in edge

# Deduplicación antes de inferencia.
assert 'allowed_official_url' in script and 'legislatura.gob.ar' in script
check_pos = script.find('"action": "check"')
model_pos = script.find('analysis = call_model(material)')
assert 0 <= check_pos < model_pos

# Base privada y guardrails server-side v3.
for field in ['analysis_origin', 'automation_source_hash', 'automation_confidence', 'source_evidence', 'evidence_gaps']:
    assert field in migration
assert 'enable row level security' in focus_migration
assert 'revoke all on public.analysis_focus_commissions from public, anon, authenticated' in focus_migration
assert 'analysis_mode' in v3_migration and 'quality_flags' in v3_migration
assert 'preliminary_insufficient_evidence' in v3_migration
assert "new.recommendation := 'sin_definir'" in v3_migration
assert "new.proposed_amendments := ''" in v3_migration
assert "new.arguments_for := ''" in v3_migration
assert "new.intervention_arguments := ''" in v3_migration
assert '0.20' in v3_migration and '0.75' in v3_migration

for private_name in ['salud', 'discapacidad', 'asuntos constitucionales', 'educación, ciencia y tecnología']:
    assert private_name not in (migration + focus_migration + v3_migration), 'El foco concreto no debe versionarse'

# UI privada: sólo versiones vigentes y estado de revisión visible.
assert ".eq('is_current', true)" in ui
assert 'REVISIÓN REQUERIDA' in ui
assert 'automation_confidence' in ui
assert 'analysis-gaps' in ui and 'analysis-actors' in ui
assert 'legislativa-auto-ui.js' in config

print('Análisis legislativo automático · validación estática v3 OK')
print('  Primarios: strict-v2; normativa complementaria: strict-v3')
print('  Sin documento primario: ficha preliminar, sin posición ni enmiendas')
print('  Sin placeholders numéricos y con coherencia de recomendación')
print('  Copilot CLI + OIDC Supabase: verificados')
