#!/usr/bin/env python3
"""CEPOES · análisis legislativo automático v3.1.

Hace tolerante el último guardrail de v3: después de un reintento de Copilot,
una sigla no respaldada ya no descarta toda la ficha. Se elimina la unidad textual
que la contiene, se registra el saneamiento, se reduce la confianza y se fuerza
la recomendación a sin_definir. Ninguna entidad no respaldada llega a Supabase.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re

import automatizar_analisis_legislativo as pipeline
import automatizar_analisis_legislativo_hardened as strict
import automatizar_analisis_legislativo_v3 as v3

MODEL_LABEL = f"github-copilot-cli-v3.1:{os.getenv('COPILOT_MODEL', '').strip() or 'auto'}"


def contains_bad_acronym(text: str, bad: list[str]) -> bool:
    upper = str(text or '').upper()
    return any(re.search(rf"\b{re.escape(token)}\b", upper) for token in bad)


def scrub_acronyms_string(value: str, bad: list[str]) -> str:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", str(value or ''))
    return ' '.join(
        chunk.strip() for chunk in chunks
        if chunk.strip() and not contains_bad_acronym(chunk, bad)
    ).strip()


def scrub_acronyms_list(values, bad: list[str]) -> list[str]:
    return [
        str(item).strip() for item in (values if isinstance(values, list) else [])
        if str(item or '').strip() and not contains_bad_acronym(str(item), bad)
    ]


def sanitize_unsupported_entities(result: dict, material: str) -> tuple[dict, bool]:
    bad = strict.unsupported_acronyms(result, material)
    if not bad:
        return result, False

    string_fields = [
        'executive_summary', 'legal_impact', 'fiscal_impact', 'territorial_impact',
        'affected_actors', 'risks', 'arguments_for', 'arguments_against', 'rationale',
        'proposed_amendments', 'intervention_arguments',
    ]
    for key in string_fields:
        result[key] = scrub_acronyms_string(result.get(key, ''), bad)
    for key in ['committee_questions', 'evidence_gaps', 'tags']:
        result[key] = scrub_acronyms_list(result.get(key), bad)

    # El control final debe quedar vacío: ninguna sigla no respaldada se persiste.
    remaining = strict.unsupported_acronyms(result, material)
    if remaining:
        raise RuntimeError(f"Persisten entidades/siglas no respaldadas tras saneamiento: {remaining}")
    return result, True


def collect_source_v31(project: dict) -> tuple[str, str, dict]:
    material, source_hash_v3, evidence = v3.collect_source_v3(project)
    evidence = dict(evidence)
    evidence['selection_policy'] = 'strict-v3.1'
    hash_input = json.dumps({
        'base_hash_v3': source_hash_v3,
        'selection_policy': 'strict-v3.1',
    }, ensure_ascii=False, sort_keys=True)
    source_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    material = material.replace('CONTROL DE CALIDAD V3:', 'CONTROL DE CALIDAD V3.1:', 1)
    return material, source_hash, evidence


def call_copilot_v31(material: str) -> dict:
    result = strict.run_copilot(v3.build_prompt_v3(material))
    bad_acronyms = strict.unsupported_acronyms(result, material)
    textual = {k: val for k, val in result.items() if k != 'confidence'}
    output = json.dumps(textual, ensure_ascii=False)
    numbers = set(re.findall(r"(?<![A-Za-z])\d{2,}(?:[.,]\d+)?%?", output))
    bad_numbers = sorted(n for n in numbers if n not in material)
    placeholders = bool(v3.PLACEHOLDER_RE.search(output))

    if bad_acronyms or bad_numbers or placeholders:
        correction = (
            'CORRECCIÓN OBLIGATORIA: eliminá todo elemento no respaldado. '
            f"Siglas/entidades no verificadas: {bad_acronyms or 'ninguna'}. "
            f"Cifras/umbrales no verificados: {bad_numbers or 'ninguno'}. "
            'No reemplaces cifras por placeholders. Reformulá naturalmente indicando que el dato no surge de la evidencia. '
            'Si recommendation debe quedar sin_definir, evitá cualquier frase de apoyo, rechazo o acompañamiento.'
        )
        result = strict.run_copilot(v3.build_prompt_v3(material, correction))

    result, entity_scrubbed = sanitize_unsupported_entities(result, material)
    result = v3.normalize_v3(result, material)
    if entity_scrubbed:
        flags = list(result.get('quality_flags') or [])
        if 'unsupported_entity_removed' not in flags:
            flags.append('unsupported_entity_removed')
        result['quality_flags'] = flags[:12]
        result['confidence'] = min(float(result.get('confidence') or 0), 0.69)
        result['recommendation'] = 'sin_definir'
        gaps = list(result.get('evidence_gaps') or [])
        note = 'La salida inicial contenía una entidad o sigla no respaldada; la unidad textual afectada fue eliminada y debe revisarse.'
        if note not in gaps:
            gaps.append(note)
        result['evidence_gaps'] = gaps[:12]
    return result


def self_test() -> None:
    material = (
        'CONTROL DE CALIDAD V3.1:\n'
        '- analysis_mode=preliminary_insufficient_evidence\n'
        '- documentos_primarios_del_expediente=0\n'
        '- normativa_complementaria_recuperada=0\n'
        'FICHA PÚBLICA ESTRUCTURADA: Expediente TEST-2026. Sumario: homologación administrativa. '
        'No se incorpora texto del proyecto ni monto ni plazo.'
    )
    result = call_copilot_v31(material)
    assert result['analysis_mode'] == 'preliminary_insufficient_evidence'
    assert result['recommendation'] == 'sin_definir'
    assert result['arguments_for'] == '' and result['arguments_against'] == ''
    assert result['proposed_amendments'] == '' and result['intervention_arguments'] == ''
    assert not v3.PLACEHOLDER_RE.search(json.dumps(result, ensure_ascii=False))
    assert not strict.unsupported_acronyms(result, material)
    print('Self-test Copilot v3.1 OK')
    print(json.dumps({
        'analysis_mode': result['analysis_mode'],
        'recommendation': result['recommendation'],
        'confidence': result['confidence'],
        'quality_flags': result['quality_flags'],
    }, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-items', type=int, default=int(os.getenv('ANALYSIS_MAX_ITEMS', '3')))
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()

    pipeline.collect_source = collect_source_v31
    pipeline.call_model = call_copilot_v31
    pipeline.MODEL_ID = MODEL_LABEL
    if args.self_test:
        self_test()
        return
    pipeline.process(max(1, min(args.max_items, 25)))


if __name__ == '__main__':
    main()
