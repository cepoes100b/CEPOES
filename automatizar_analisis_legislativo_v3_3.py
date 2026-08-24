#!/usr/bin/env python3
"""CEPOES · análisis legislativo automático v3.3.

Añade a v3.2 un guardrail determinístico para referencias jurídicas,
jurisprudenciales y comparadas que no estén presentes en la evidencia suministrada.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re

import automatizar_analisis_legislativo as pipeline
import automatizar_analisis_legislativo_v3 as v3
import automatizar_analisis_legislativo_v3_2 as v32

MODEL_LABEL = f"github-copilot-cli-v3.3:{os.getenv('COPILOT_MODEL', '').strip() or 'auto'}"

# Frases cuyo uso como afirmación exige que aparezcan en la evidencia.
EXTERNAL_REFERENCE_PATTERNS = [
    r"\bc[oó]digo penal\b",
    r"\bc[oó]digo civil(?: y comercial)?\b",
    r"\bconstituci[oó]n(?: nacional)?\b",
    r"\bjurisprudencia\b",
    r"\bdoctrina\b",
    r"\bprecedentes? (?:judiciales?|legislativos?)\b",
    r"\bmarco internacional\b",
    r"\best[aá]ndares internacionales\b",
    r"\btratados? internacionales?\b",
    r"\bderecho comparado\b",
    r"\blegislaci[oó]n comparada\b",
    r"\bcompetencia federal\b",
    r"\br[eé]gimen federal\b",
]


def unsupported_external_reference(text: str, material: str) -> bool:
    nmaterial = pipeline.norm(material)
    for pattern in EXTERNAL_REFERENCE_PATTERNS:
        match = re.search(pattern, str(text or ""), re.I)
        if not match:
            continue
        phrase = pipeline.norm(match.group(0))
        if phrase and phrase not in nmaterial:
            return True
    return False


def scrub_external_string(value: str, material: str) -> tuple[str, bool]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", str(value or ""))
    kept: list[str] = []
    removed = False
    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue
        if unsupported_external_reference(c, material):
            removed = True
            continue
        kept.append(c)
    return " ".join(kept).strip(), removed


def scrub_external_list(values, material: str, *, allow_research_target: bool) -> tuple[list[str], bool]:
    kept: list[str] = []
    removed = False
    for item in values if isinstance(values, list) else []:
        s = str(item or "").strip()
        if not s:
            continue
        # En brechas/preguntas se admite pedir evidencia genérica; no se admiten
        # referencias jurídicas concretas que el propio material nunca mencionó.
        bad = unsupported_external_reference(s, material)
        if bad and allow_research_target and re.search(r"\b(jurisprudencia|doctrina|precedentes?)\b", s, re.I):
            # Sólo se preserva si no añade un código/constitución/marco concreto.
            concrete = any(re.search(p, s, re.I) for p in EXTERNAL_REFERENCE_PATTERNS[:3] + EXTERNAL_REFERENCE_PATTERNS[5:])
            bad = concrete
        if bad:
            removed = True
            continue
        kept.append(s)
    return kept, removed


def sanitize_external_references(result: dict, material: str) -> tuple[dict, bool]:
    removed = False
    # Campos sustantivos: ninguna referencia externa factual no evidenciada.
    for key in [
        "executive_summary", "legal_impact", "fiscal_impact", "territorial_impact",
        "affected_actors", "risks", "arguments_for", "arguments_against", "rationale",
        "proposed_amendments", "intervention_arguments",
    ]:
        result[key], changed = scrub_external_string(result.get(key, ""), material)
        removed = removed or changed
    for key in ["committee_questions", "evidence_gaps"]:
        result[key], changed = scrub_external_list(result.get(key), material, allow_research_target=True)
        removed = removed or changed
    return result, removed


def collect_source_v33(project: dict) -> tuple[str, str, dict]:
    material, source_hash_v32, evidence = v32.collect_source_v32(project)
    evidence = dict(evidence)
    evidence["selection_policy"] = "strict-v3.3"
    source_hash = hashlib.sha256(json.dumps({
        "base_hash_v32": source_hash_v32,
        "selection_policy": "strict-v3.3",
    }, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    material = material.replace("CONTROL DE CALIDAD V3.2:", "CONTROL DE CALIDAD V3.3:", 1)
    return material, source_hash, evidence


def call_copilot_v33(material: str) -> dict:
    result = v32.call_copilot_v32(material)
    result, removed = sanitize_external_references(result, material)
    if removed:
        flags = list(result.get("quality_flags") or [])
        if "unsupported_external_reference_removed" not in flags:
            flags.append("unsupported_external_reference_removed")
        result["quality_flags"] = flags[:12]
        result["confidence"] = min(float(result.get("confidence") or 0), 0.69)
        result["recommendation"] = "sin_definir"
        gaps = list(result.get("evidence_gaps") or [])
        note = "Se eliminó una referencia jurídica o antecedente externo no presente en la evidencia suministrada."
        if note not in gaps:
            gaps.append(note)
        result["evidence_gaps"] = gaps[:12]
        result = v32.neutralize_low_confidence(result)
    return result


def self_test() -> None:
    material = (
        "CONTROL DE CALIDAD V3.3:\n"
        "- analysis_mode=full\n- documentos_primarios_del_expediente=1\n"
        "DOCUMENTO PRIMARIO: Proyecto que modifica una contravención local. No cita otras normas."
    )
    result = {
        "executive_summary": "Modifica una contravención local.",
        "legal_impact": "Debe coordinarse con el Código Penal federal.",
        "fiscal_impact": "No surge cuantificación.", "territorial_impact": "Aplicación local.",
        "affected_actors": "Personas alcanzadas.", "risks": "La jurisprudencia demuestra un riesgo.",
        "arguments_for": "Actualiza la figura.", "arguments_against": "Falta precisión.",
        "internal_priority": "media", "recommendation": "sin_definir",
        "rationale": "La evidencia no alcanza.", "proposed_amendments": "",
        "committee_questions": ["¿Qué normativa penal aplicable debe considerarse?"],
        "intervention_arguments": "Puntos a verificar.",
        "evidence_gaps": ["Relevar jurisprudencia pertinente."], "tags": [], "confidence": 0.69,
        "analysis_mode": "full", "quality_flags": [],
    }
    cleaned, removed = sanitize_external_references(result, material)
    assert removed
    assert "Código Penal" not in cleaned["legal_impact"]
    assert "jurisprudencia demuestra" not in cleaned["risks"].lower()
    assert cleaned["evidence_gaps"] == ["Relevar jurisprudencia pertinente."]
    print("Self-test análisis legislativo v3.3 OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-items", type=int, default=int(os.getenv("ANALYSIS_MAX_ITEMS", "3")))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    # Mantiene la resolución de normativa actualizada de v3.2.
    v3.fetch_supplement = v32.fetch_supplement_resolved
    pipeline.collect_source = collect_source_v33
    pipeline.call_model = call_copilot_v33
    pipeline.MODEL_ID = MODEL_LABEL
    if args.self_test:
        self_test()
        return
    pipeline.process(max(1, min(args.max_items, 25)))


if __name__ == "__main__":
    main()
