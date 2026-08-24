#!/usr/bin/env python3
"""CEPOES · análisis legislativo automático v3.4.

Arquitectura estable de generación:
1. una única inferencia de Copilot sobre evidencia suministrada;
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
import re

import automatizar_analisis_legislativo as pipeline
import automatizar_analisis_legislativo_hardened as strict
import automatizar_analisis_legislativo_v3 as v3
import automatizar_analisis_legislativo_v3_1 as v31
import automatizar_analisis_legislativo_v3_2 as v32
import automatizar_analisis_legislativo_v3_3 as v33

MODEL_LABEL = f"github-copilot-cli-v3.4:{os.getenv('COPILOT_MODEL', '').strip() or 'auto'}"
STRING_FIELDS = [
    "executive_summary", "legal_impact", "fiscal_impact", "territorial_impact",
    "affected_actors", "risks", "arguments_for", "arguments_against", "rationale",
    "proposed_amendments", "intervention_arguments",
]
LIST_FIELDS = ["committee_questions", "evidence_gaps", "tags"]


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
    # normalize_v3 elimina unidades textuales con cifras/placeholders no respaldados,
    # fija el modo preliminar cuando corresponde y aplica el umbral 0,75.
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

    # Ninguna referencia jurídica externa concreta puede sobrevivir en campos sustantivos.
    for key in STRING_FIELDS:
        if v33.unsupported_external_reference(str(result.get(key) or ""), material):
            raise RuntimeError(f"Control final: referencia jurídica externa no respaldada en {key}")

    # Ninguna referencia institucional no evidenciada puede sobrevivir.
    for key in STRING_FIELDS:
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


def call_copilot_v34(material: str) -> dict:
    # Una sola llamada al modelo. Todo lo posterior es determinístico.
    result = strict.run_copilot(v3.build_prompt_v3(material))
    result = apply_entity_guardrail(result, material)
    result = apply_numeric_guardrail(result, material)
    result = apply_institution_guardrail(result, material)
    result = v32.neutralize_low_confidence(result)
    result = apply_external_reference_guardrail(result, material)
    result = v32.neutralize_low_confidence(result)
    add_flag(result, "single_pass_deterministic_guardrails")
    final_assertions(result, material)
    return result


def self_test() -> None:
    material = (
        "CONTROL DE CALIDAD V3.4:\n"
        "- analysis_mode=full\n- documentos_primarios_del_expediente=1\n"
        "- normativa_complementaria_recuperada=0\n"
        "DOCUMENTO PRIMARIO: Proyecto que crea un registro administrativo bajo el Ministerio de Educación. "
        "No informa costo fiscal ni plazo de implementación."
    )
    result = call_copilot_v34(material)
    assert "single_pass_deterministic_guardrails" in result.get("quality_flags", [])
    final_assertions(result, material)
    print("Self-test Copilot v3.4 OK")
    print(json.dumps({
        "analysis_mode": result.get("analysis_mode"),
        "recommendation": result.get("recommendation"),
        "confidence": result.get("confidence"),
        "quality_flags": result.get("quality_flags"),
    }, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-items", type=int, default=int(os.getenv("ANALYSIS_MAX_ITEMS", "3")))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    # Conserva la resolución de NormativaBA → texto actualizado/PDF implementada en v3.2.
    v3.fetch_supplement = v32.fetch_supplement_resolved
    pipeline.collect_source = collect_source_v34
    pipeline.call_model = call_copilot_v34
    pipeline.MODEL_ID = MODEL_LABEL
    if args.self_test:
        self_test()
        return
    pipeline.process(max(1, min(args.max_items, 25)))


if __name__ == "__main__":
    main()
