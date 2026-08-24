#!/usr/bin/env python3
"""Capa final de grounding para el análisis legislativo automático CEPOES.

Extiende strict-v2: las cifras no respaldadas se reemplazan por "a definir";
las entidades/siglas no presentes en la evidencia siguen siendo un error duro.
"""
from __future__ import annotations

import argparse
import json
import os
import re

import automatizar_analisis_legislativo as pipeline
import automatizar_analisis_legislativo_hardened as strict

MODEL_LABEL = f"github-copilot-cli-grounded:{os.getenv('COPILOT_MODEL', '').strip() or 'auto'}"


def unsupported_numbers(result: dict, material: str) -> list[str]:
    # No inspecciona confidence: 0.75 no es una afirmación sobre el expediente.
    textual = {k: v for k, v in result.items() if k != "confidence"}
    output = json.dumps(textual, ensure_ascii=False)
    numbers = set(re.findall(r"(?<![A-Za-z])\d{2,}(?:[.,]\d+)?%?", output))
    return sorted(n for n in numbers if n not in material)


def sanitize_value(value, bad_numbers: list[str]):
    if isinstance(value, str):
        out = value
        for number in sorted(bad_numbers, key=len, reverse=True):
            out = re.sub(rf"(?<!\d){re.escape(number)}(?!\d)", "a definir", out)
        return out
    if isinstance(value, list):
        return [sanitize_value(x, bad_numbers) for x in value]
    return value


def normalize_grounding(result: dict, material: str) -> dict:
    bad_acronyms = strict.unsupported_acronyms(result, material)
    bad_numbers = unsupported_numbers(result, material)
    if bad_acronyms:
        raise RuntimeError(f"Salida con entidades/siglas no respaldadas: {bad_acronyms}")
    if bad_numbers:
        result = {k: sanitize_value(v, bad_numbers) for k, v in result.items()}
        gaps = list(result.get("evidence_gaps") or [])
        gaps.append(
            "La salida inicial propuso parámetros numéricos no presentes en la evidencia; fueron reemplazados por 'a definir'."
        )
        result["evidence_gaps"] = gaps[:12]
        result["confidence"] = min(float(result.get("confidence") or 0), 0.69)
        result["recommendation"] = "sin_definir"
    return result


def call_copilot_grounded(material: str) -> dict:
    result = strict.run_copilot(strict.build_prompt(material))
    bad_acronyms = strict.unsupported_acronyms(result, material)
    bad_numbers = unsupported_numbers(result, material)

    if bad_acronyms or bad_numbers:
        correction = (
            "CORRECCIÓN OBLIGATORIA: la salida anterior introdujo elementos no presentes en la evidencia. "
            f"Siglas/entidades no verificadas: {bad_acronyms or 'ninguna'}. "
            f"Cifras/umbrales no verificados: {bad_numbers or 'ninguno'}. "
            "Regenerá el JSON sin esos elementos. Si necesitás proponer un parámetro no documentado, escribí 'a definir'."
        )
        result = strict.run_copilot(strict.build_prompt(material, correction))

    result = normalize_grounding(result, material)

    primary_match = re.search(r"documentos_primarios_del_expediente=(\d+)", material)
    primary_count = int(primary_match.group(1)) if primary_match else 0
    confidence = float(result.get("confidence") or 0)
    if primary_count < 1:
        confidence = min(confidence, 0.45)
    if len(result.get("evidence_gaps") or []) >= 8:
        confidence = min(confidence, 0.69)
    result["confidence"] = confidence
    if confidence < 0.75 or primary_count < 1:
        result["recommendation"] = "sin_definir"

    fiscal = str(result.get("fiscal_impact") or "")
    if re.search(r"\b(presupuesto|costo|financiamiento).{0,30}\b(cero|inexistente|no existe)\b", fiscal, re.I):
        result["fiscal_impact"] = (
            "No surge de la evidencia suministrada una estimación fiscal cuantificada. "
            "La revisión humana debe determinar si las obligaciones expresas del proyecto generan necesidades de recursos y, en su caso, cuantificarlas."
        )
        result["recommendation"] = "sin_definir"
        result["confidence"] = min(result["confidence"], 0.69)
    return result


def self_test() -> None:
    material = (
        "CONTROL DE EVIDENCIA:\n- documentos_primarios_del_expediente=1\n"
        "FICHA PÚBLICA ESTRUCTURADA: Expediente TEST-2026. Proyecto hipotético que crea un registro administrativo. "
        "La evidencia no informa costo fiscal, partida presupuestaria ni plazo de reglamentación."
    )
    result = call_copilot_grounded(material)
    assert result["recommendation"] == "sin_definir" or result["confidence"] >= 0.75
    assert not unsupported_numbers(result, material), "Persisten cifras no respaldadas después del saneamiento"
    assert not strict.unsupported_acronyms(result, material), "Persisten entidades no respaldadas"
    print("Self-test Copilot grounded-v2 OK")
    print(json.dumps({
        "internal_priority": result["internal_priority"],
        "recommendation": result["recommendation"],
        "confidence": result["confidence"],
    }, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-items", type=int, default=int(os.getenv("ANALYSIS_MAX_ITEMS", "3")))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    pipeline.collect_source = strict.collect_source_strict
    pipeline.call_model = call_copilot_grounded
    pipeline.MODEL_ID = MODEL_LABEL
    if args.self_test:
        self_test()
        return
    pipeline.process(max(1, min(args.max_items, 25)))


if __name__ == "__main__":
    main()
