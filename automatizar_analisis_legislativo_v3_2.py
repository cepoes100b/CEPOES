#!/usr/bin/env python3
"""CEPOES · análisis legislativo automático v3.2.

Sobre v3.1 agrega:
- resolución de la ficha NormativaBA hacia el texto actualizado oficial (incluido PDF);
- saneamiento de referencias institucionales no presentes en la evidencia;
- salida estrictamente neutral cuando la confianza no alcanza 0,75;
- supresión de enmiendas redactadas cuando la confianza es baja.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import automatizar_analisis_legislativo as pipeline
import automatizar_analisis_legislativo_hardened as strict
import automatizar_analisis_legislativo_v3 as v3
import automatizar_analisis_legislativo_v3_1 as v31

MODEL_LABEL = f"github-copilot-cli-v3.2:{os.getenv('COPILOT_MODEL', '').strip() or 'auto'}"
SUPPLEMENTARY_HOSTS = set(v3.SUPPLEMENTARY_HOSTS) | {"boletinoficialpdf.buenosaires.gob.ar"}
RISK_INSTITUTION_TOKENS = {
    "ministerio", "defensoria", "procuracion", "fiscalia", "secretaria",
    "agencia", "consejo", "juzgado", "juzgados", "tribunal", "tribunales",
}
FIXED_RISK_PHRASES = {
    "fuerzas de seguridad", "autoridad de datos", "autoridad de proteccion de datos",
    "organismos internacionales", "procuracion penal federal",
}


def allowed_supplementary_url(url: str) -> bool:
    try:
        return (urlparse(url).hostname or "").lower() in SUPPLEMENTARY_HOSTS
    except Exception:
        return False


def _extract_response_text(response) -> tuple[str, str]:
    data = response.content
    ctype = (response.headers.get("content-type") or "").lower()
    if data[:4] == b"%PDF" or "pdf" in ctype:
        return v3.extract_pdf(data), "pdf"
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer"]):
        tag.decompose()
    return pipeline.clean(soup.get_text("\n", strip=True), 60000), "html"


def _updated_text_target(response) -> str:
    """Busca el enlace al texto actualizado dentro de una ficha NormativaBA."""
    try:
        soup = BeautifulSoup(response.text, "html.parser")
        candidates: list[tuple[int, str]] = []
        for a in soup.find_all("a", href=True):
            label = pipeline.norm(a.get_text(" ", strip=True))
            absolute = urljoin(response.url, a["href"])
            if not allowed_supplementary_url(absolute):
                continue
            host = (urlparse(absolute).hostname or "").lower()
            if "texto actualizado" in label:
                score = 20
                if host == "boletinoficialpdf.buenosaires.gob.ar":
                    score += 20
                if absolute.lower().endswith(".pdf") or "imagen.php" in absolute.lower():
                    score += 10
                candidates.append((score, absolute))
        return max(candidates, default=(0, ""))[1]
    except Exception:
        return ""


def fetch_supplement_resolved(url: str) -> tuple[str, dict] | None:
    """Recupera el texto normativo real, no sólo la ficha descriptiva."""
    if not allowed_supplementary_url(url):
        return None
    try:
        first = pipeline.SESSION.get(url, timeout=pipeline.TIMEOUT, allow_redirects=True)
        if first.status_code != 200 or len(first.content) > 12_000_000 or not allowed_supplementary_url(first.url):
            return None

        response = first
        resolved_from = ""
        ctype = (first.headers.get("content-type") or "").lower()
        if "html" in ctype and (urlparse(first.url).hostname or "").lower() == "boletinoficial.buenosaires.gob.ar":
            target = _updated_text_target(first)
            if target and target != first.url:
                second = pipeline.SESSION.get(target, timeout=pipeline.TIMEOUT, allow_redirects=True)
                if second.status_code == 200 and len(second.content) <= 12_000_000 and allowed_supplementary_url(second.url):
                    resolved_from = first.url
                    response = second

        text, kind = _extract_response_text(response)
        if not text:
            return None
        return text, {
            "url": response.url,
            "resolved_from": resolved_from or None,
            "kind": kind,
            "role": "normativa_vigente_complementaria",
            "source_scope": "supplementary",
            "sha256": hashlib.sha256(response.content).hexdigest(),
            "characters": len(text),
        }
    except Exception as exc:
        print(f"  · normativa complementaria no disponible: {url} ({exc})")
        return None


def _institution_candidates(text: str) -> list[str]:
    tokens = pipeline.norm(text).split()
    out: list[str] = []
    for phrase in FIXED_RISK_PHRASES:
        if phrase in " ".join(tokens):
            out.append(phrase)
    for i, token in enumerate(tokens):
        if token not in RISK_INSTITUTION_TOKENS:
            continue
        if i + 2 < len(tokens) and tokens[i + 1] in {"de", "del", "general", "penal"}:
            out.append(" ".join(tokens[i:i + 3]))
        elif i + 1 < len(tokens):
            out.append(" ".join(tokens[i:i + 2]))
        else:
            out.append(token)
    return list(dict.fromkeys(out))


def has_unsupported_institution(text: str, material: str) -> bool:
    norm_material = pipeline.norm(material)
    return any(candidate and candidate not in norm_material for candidate in _institution_candidates(text))


def scrub_institutions_string(value: str, material: str) -> tuple[str, bool]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", str(value or ""))
    kept: list[str] = []
    removed = False
    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue
        if has_unsupported_institution(c, material):
            removed = True
            continue
        kept.append(c)
    return " ".join(kept).strip(), removed


def scrub_institutions_list(values, material: str) -> tuple[list[str], bool]:
    kept: list[str] = []
    removed = False
    for item in values if isinstance(values, list) else []:
        s = str(item or "").strip()
        if not s:
            continue
        if has_unsupported_institution(s, material):
            removed = True
            continue
        kept.append(s)
    return kept, removed


def sanitize_institutions(result: dict, material: str) -> tuple[dict, bool]:
    removed = False
    for key in [
        "executive_summary", "legal_impact", "fiscal_impact", "territorial_impact",
        "affected_actors", "risks", "arguments_for", "arguments_against", "rationale",
        "proposed_amendments", "intervention_arguments",
    ]:
        result[key], changed = scrub_institutions_string(result.get(key, ""), material)
        removed = removed or changed
    for key in ["committee_questions", "evidence_gaps", "tags"]:
        result[key], changed = scrub_institutions_list(result.get(key), material)
        removed = removed or changed
    return result, removed


def neutralize_low_confidence(result: dict) -> dict:
    confidence = float(result.get("confidence") or 0)
    if result.get("analysis_mode") == "preliminary_insufficient_evidence":
        return result
    if confidence >= 0.75 and result.get("recommendation") != "sin_definir":
        return result

    result["recommendation"] = "sin_definir"
    flags = list(result.get("quality_flags") or [])
    if "low_confidence_neutralized" not in flags:
        flags.append("low_confidence_neutralized")

    gaps = [str(x).strip() for x in (result.get("evidence_gaps") or []) if str(x).strip()]
    reason = "La evidencia disponible no alcanza el umbral de confianza para formular una posición técnica preliminar."
    if gaps:
        reason += " Antes de adoptar una posición deben resolverse, entre otras, estas brechas: " + "; ".join(gaps[:3]) + "."
    result["rationale"] = reason

    questions = [str(x).strip() for x in (result.get("committee_questions") or []) if str(x).strip()]
    if questions:
        result["intervention_arguments"] = "Puntos a verificar antes de adoptar una posición técnica: " + " ".join(f"{i+1}) {q}" for i, q in enumerate(questions[:4]))
    else:
        result["intervention_arguments"] = "No se consolidan argumentos de intervención hasta completar la revisión de evidencia."

    if result.get("proposed_amendments"):
        result["proposed_amendments"] = ""
        if "amendments_suppressed_low_confidence" not in flags:
            flags.append("amendments_suppressed_low_confidence")
    result["quality_flags"] = flags[:12]
    return result


def collect_source_v32(project: dict) -> tuple[str, str, dict]:
    material, source_hash_v31, evidence = v31.collect_source_v31(project)
    evidence = dict(evidence)
    evidence["selection_policy"] = "strict-v3.2"
    source_hash = hashlib.sha256(json.dumps({
        "base_hash_v31": source_hash_v31,
        "selection_policy": "strict-v3.2",
    }, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    material = material.replace("CONTROL DE CALIDAD V3.1:", "CONTROL DE CALIDAD V3.2:", 1)
    return material, source_hash, evidence


def call_copilot_v32(material: str) -> dict:
    result = v31.call_copilot_v31(material)
    result, institution_removed = sanitize_institutions(result, material)
    if institution_removed:
        flags = list(result.get("quality_flags") or [])
        if "unsupported_institution_removed" not in flags:
            flags.append("unsupported_institution_removed")
        result["quality_flags"] = flags[:12]
        result["confidence"] = min(float(result.get("confidence") or 0), 0.69)
        result["recommendation"] = "sin_definir"
        gaps = list(result.get("evidence_gaps") or [])
        note = "Se eliminó una referencia institucional no presente en la evidencia y debe revisarse manualmente."
        if note not in gaps:
            gaps.append(note)
        result["evidence_gaps"] = gaps[:12]
    return neutralize_low_confidence(result)


def self_test() -> None:
    material = (
        "CONTROL DE CALIDAD V3.2:\n"
        "- analysis_mode=full\n"
        "- documentos_primarios_del_expediente=1\n"
        "- normativa_complementaria_recuperada=0\n"
        "DOCUMENTO PRIMARIO DEL EXPEDIENTE: Proyecto que crea un registro bajo el Ministerio de Educación. "
        "No se informa costo fiscal ni plazo."
    )
    raw = {
        "executive_summary": "El proyecto crea un registro.",
        "legal_impact": "Requiere implementación administrativa.",
        "fiscal_impact": "No surge cuantificación fiscal.",
        "territorial_impact": "No surge de la evidencia.",
        "affected_actors": "Ministerio de Educación.",
        "risks": "Requiere precisión operativa.",
        "arguments_for": "Ordena el registro.",
        "arguments_against": "Falta detalle de implementación.",
        "internal_priority": "media",
        "recommendation": "sin_definir",
        "rationale": "Podría acompañarse si se modifica.",
        "proposed_amendments": "Agregar un plazo de implementación.",
        "committee_questions": ["¿Cuál es el costo fiscal?"],
        "intervention_arguments": "Conviene acompañar con cambios.",
        "evidence_gaps": ["No surge el costo fiscal."],
        "tags": ["educacion"],
        "confidence": 0.68,
        "analysis_mode": "full",
        "quality_flags": [],
    }
    cleaned, removed = sanitize_institutions(raw, material)
    assert not removed
    cleaned = neutralize_low_confidence(cleaned)
    assert cleaned["recommendation"] == "sin_definir"
    assert cleaned["proposed_amendments"] == ""
    assert "acompañ" not in pipeline.norm(cleaned["rationale"])
    assert "Puntos a verificar" in cleaned["intervention_arguments"]

    bad = dict(raw)
    bad["evidence_gaps"] = ["Consultar a Procuración Penal federal."]
    bad, removed = sanitize_institutions(bad, material)
    assert removed and bad["evidence_gaps"] == []
    print("Self-test análisis legislativo v3.2 OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-items", type=int, default=int(os.getenv("ANALYSIS_MAX_ITEMS", "3")))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    # v3.collect_source_v3 resuelve la normativa mediante esta función global.
    v3.fetch_supplement = fetch_supplement_resolved
    pipeline.collect_source = collect_source_v32
    pipeline.call_model = call_copilot_v32
    pipeline.MODEL_ID = MODEL_LABEL
    if args.self_test:
        self_test()
        return
    pipeline.process(max(1, min(args.max_items, 25)))


if __name__ == "__main__":
    main()
