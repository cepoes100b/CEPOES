#!/usr/bin/env python3
"""CEPOES · análisis legislativo automático v3.4.

Arquitectura estable de generación:
1. una única inferencia sobre la evidencia suministrada, independiente del proveedor;
2. saneamiento determinístico de siglas, cifras/placeholders, instituciones y
   referencias jurídicas externas;
3. neutralización determinística cuando la confianza queda por debajo de 0,75;
4. verificación final antes de persistir.

No se vuelve a consultar al modelo para "corregir" su primera salida.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

import automatizar_analisis_legislativo as pipeline
import automatizar_analisis_legislativo_hardened as strict
import automatizar_analisis_legislativo_v3 as v3
import automatizar_analisis_legislativo_v3_1 as v31
import automatizar_analisis_legislativo_v3_2 as v32
import automatizar_analisis_legislativo_v3_3 as v33
import proveedor_modelo_legislativo as provider

STRING_FIELDS = [
    "executive_summary", "legal_impact", "fiscal_impact", "territorial_impact",
    "affected_actors", "risks", "arguments_for", "arguments_against", "rationale",
    "proposed_amendments", "intervention_arguments",
]


def model_label() -> str:
    p = provider.provider_name()
    if p == "openai":
        return f"openai-v3.4:{provider.OPENAI_MODEL}"
    return f"github-copilot-cli-v3.4:{os.getenv('COPILOT_MODEL', '').strip() or 'auto'}"


def add_flag(result: dict, flag: str) -> None:
    flags = list(result.get("quality_flags") or [])
    if flag not in flags:
        flags.append(flag)
    result["quality_flags"] = flags[:12]


def add_gap(result: dict, note: str) -> None:
    gaps = [str(x).strip() for x in (result.get("evidence_gaps") or []) if str(x).strip()]
    if note not in gaps:
        gaps.append(note)
    result["evidence_gaps"] = gaps[:12]


def collect_source_v34(project: dict) -> tuple[str, str, dict]:
    material, source_hash_v33, evidence = v33.collect_source_v33(project)
    evidence = dict(evidence)
    evidence["selection_policy"] = "strict-v3.4"
    source_hash = hashlib.sha256(json.dumps({
        "base_hash_v33": source_hash_v33,
        "selection_policy": "strict-v3.4",
    }, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    material = material.replace("CONTROL DE CALIDAD V3.3:", "CONTROL DE CALIDAD V3.4:", 1)
    return material, source_hash, evidence


def apply_entity_guardrail(result: dict, material: str) -> dict:
    result, changed = v31.sanitize_unsupported_entities(result, material)
    if changed:
        add_flag(result, "unsupported_entity_removed")
        result["confidence"] = min(float(result.get("confidence") or 0), 0.69)
        result["recommendation"] = "sin_definir"
        add_gap(result, "Se eliminó una entidad o sigla no respaldada por la evidencia suministrada.")
    return result


def apply_numeric_guardrail(result: dict, material: str) -> dict:
    return v3.normalize_v3(result, material)


def apply_institution_guardrail(result: dict, material: str) -> dict:
    result, changed = v32.sanitize_institutions(result, material)
    if changed:
        add_flag(result, "unsupported_institution_removed")
        result["confidence"] = min(float(result.get("confidence") or 0), 0.69)
        result["recommendation"] = "sin_definir"
        add_gap(result, "Se eliminó una referencia institucional no presente en la evidencia suministrada.")
    return result


def apply_external_reference_guardrail(result: dict, material: str) -> dict:
    result, changed = v33.sanitize_external_references(result, material)
    if changed:
        add_flag(result, "unsupported_external_reference_removed")
        result["confidence"] = min(float(result.get("confidence") or 0), 0.69)
        result["recommendation"] = "sin_definir"
        add_gap(result, "Se eliminó una referencia jurídica o antecedente externo no presente en la evidencia suministrada.")
    return result


def final_assertions(result: dict, material: str) -> None:
    acronyms = strict.unsupported_acronyms(result, material)
    if acronyms:
        raise RuntimeError(f"Control final: persisten siglas no respaldadas: {acronyms}")

    rendered = json.dumps({k: v for k, v in result.items() if k != "confidence"}, ensure_ascii=False)
    if v3.PLACEHOLDER_RE.search(rendered):
        raise RuntimeError("Control final: persiste placeholder 'a definir'")

    for key in STRING_FIELDS:
        if v33.unsupported_external_reference(str(result.get(key) or ""), material):
            raise RuntimeError(f"Control final: referencia jurídica externa no respaldada en {key}")
        if v32.has_unsupported_institution(str(result.get(key) or ""), material):
            raise RuntimeError(f"Control final: institución no respaldada en {key}")

    confidence = float(result.get("confidence") or 0)
    if result.get("analysis_mode") == "preliminary_insufficient_evidence":
        if result.get("recommendation") != "sin_definir":
            raise RuntimeError("Control final: ficha preliminar con recomendación")
        if any(str(result.get(k) or "").strip() for k in ["arguments_for", "arguments_against", "proposed_amendments", "intervention_arguments"]):
            raise RuntimeError("Control final: ficha preliminar contiene campos sustantivos prohibidos")
    elif confidence < 0.75 or result.get("recommendation") == "sin_definir":
        if str(result.get("proposed_amendments") or "").strip():
            raise RuntimeError("Control final: confianza baja conserva enmiendas")


def guardrail_cascade(result: dict, material: str) -> dict:
    result = apply_entity_guardrail(result, material)
    result = apply_numeric_guardrail(result, material)
    result = apply_institution_guardrail(result, material)
    result = v32.neutralize_low_confidence(result)
    result = apply_external_reference_guardrail(result, material)
    result = v32.neutralize_low_confidence(result)
    add_flag(result, "single_pass_deterministic_guardrails")
    final_assertions(result, material)
    return result


def call_model_v34(material: str) -> dict:
    # Una sola llamada al proveedor. Todo lo posterior es determinístico.
    result, _provider_label = provider.call_provider(v3.build_prompt_v3(material))
    return guardrail_cascade(result, material)


def self_test() -> None:
    """Prueba determinística: no consume créditos de ningún proveedor."""
    material = (
        "CONTROL DE CALIDAD V3.4:\n"
        "- analysis_mode=full\n- documentos_primarios_del_expediente=1\n"
        "- normativa_complementaria_recuperada=0\n"
        "DOCUMENTO PRIMARIO: Proyecto que crea un registro administrativo bajo el Ministerio de Educación. "
        "No informa costo fiscal ni plazo de implementación."
    )
    synthetic = {
        "executive_summary": "El proyecto crea un registro administrativo.",
        "legal_impact": "Requiere implementación administrativa.",
        "fiscal_impact": "No surge cuantificación fiscal de la evidencia suministrada.",
        "territorial_impact": "No surge de la evidencia suministrada.",
        "affected_actors": "Ministerio de Educación.",
        "risks": "La evidencia no precisa el procedimiento de implementación.",
        "arguments_for": "Ordena el registro.",
        "arguments_against": "Falta detalle de implementación.",
        "internal_priority": "media",
        "recommendation": "sin_definir",
        "rationale": "La evidencia disponible no alcanza para formular una posición técnica preliminar.",
        "proposed_amendments": "Agregar un plazo de 30 días.",
        "committee_questions": ["¿Cuál es el procedimiento de implementación?"],
        "intervention_arguments": "Conviene acompañar con cambios.",
        "evidence_gaps": ["No surge el plazo de implementación."],
        "tags": ["educacion"],
        "confidence": 0.68,
    }
    result = guardrail_cascade(synthetic, material)
    assert "single_pass_deterministic_guardrails" in result.get("quality_flags", [])
    assert result["recommendation"] == "sin_definir"
    assert result["proposed_amendments"] == ""
    final_assertions(result, material)
    provider.static_self_test()
    print("Self-test determinístico v3.4 OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-items", type=int, default=int(os.getenv("ANALYSIS_MAX_ITEMS", "3")))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    v3.fetch_supplement = v32.fetch_supplement_resolved
    pipeline.collect_source = collect_source_v34
    pipeline.call_model = call_model_v34
    pipeline.MODEL_ID = model_label()
    if args.self_test:
        self_test()
        return
    pipeline.process(max(1, min(args.max_items, 25)))


if __name__ == "__main__":
    main()
