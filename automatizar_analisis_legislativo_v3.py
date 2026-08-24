#!/usr/bin/env python3
"""CEPOES · análisis legislativo automático v3.

Sobre grounded-v2 agrega:
- coherencia obligatoria entre recomendación, rationale e intervención;
- modo preliminar cuando no existe documento primario;
- saneamiento natural de números/umbrales no respaldados (sin artefactos "a definir");
- recuperación de normativa oficial complementaria citada por el proyecto;
- comparación normativa cuando la evidencia permite localizar el artículo vigente.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader

import automatizar_analisis_legislativo as pipeline
import automatizar_analisis_legislativo_hardened as strict

BASE = Path(__file__).resolve().parent
REGISTRY_PATH = BASE / "normativa_referencia_caba.json"
MODEL_LABEL = f"github-copilot-cli-v3:{os.getenv('COPILOT_MODEL', '').strip() or 'auto'}"

SUPPLEMENTARY_HOSTS = {
    "boletinoficial.buenosaires.gob.ar",
    "digesto.buenosaires.gob.ar",
}
ADVOCACY_RE = re.compile(
    r"\b(recomend(?:ar|acion|ación|amos|ado|ada)|acompañ(?:ar|amiento|amos)|apoy(?:ar|o|amos)|"
    r"rechaz(?:ar|o|amos)|absten(?:er|cion|ción)|vot(?:ar|o|amos)|posición favorable|posición negativa)\b",
    re.I,
)
PLACEHOLDER_RE = re.compile(r"\ba definir\b", re.I)


def _norm_law_number(value: str) -> str:
    return re.sub(r"\D", "", value or "").lstrip("0") or "0"


def load_registry() -> dict[str, dict]:
    try:
        raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return {str(k): v for k, v in raw.items() if isinstance(v, dict)}
    except Exception:
        return {}


def cited_laws(material: str) -> list[str]:
    found: list[str] = []
    patterns = [
        r"\bLey\s+(?:N[°º.]?\s*)?([0-9][0-9.]{1,8})\b",
        r"\bLEY\s+(?:N[°º.]?\s*)?([0-9][0-9.]{1,8})\b",
    ]
    for pat in patterns:
        for m in re.finditer(pat, material, re.I):
            n = _norm_law_number(m.group(1))
            if n and n not in found:
                found.append(n)
    return found[:12]


def cited_articles_for_law(material: str, law_number: str) -> list[str]:
    target = re.sub(r"\B(?=(\d{3})+(?!\d))", ".", law_number)
    variants = {law_number, target}
    out: list[str] = []
    for m in re.finditer(r"art[íi]culo\s+([0-9]{1,3}(?:\s*(?:bis|ter|qu[aá]ter))?)", material, re.I):
        start = max(0, m.start() - 260)
        end = min(len(material), m.end() + 260)
        window = material[start:end]
        if any(re.search(rf"\b{re.escape(v)}\b", window) for v in variants):
            article = re.sub(r"\s+", " ", m.group(1).strip()).lower()
            if article not in out:
                out.append(article)
    return out[:6]


def allowed_supplementary_url(url: str) -> bool:
    try:
        return (urlparse(url).hostname or "").lower() in SUPPLEMENTARY_HOSTS
    except Exception:
        return False


def extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    chunks: list[str] = []
    for page in reader.pages[:80]:
        chunks.append(page.extract_text() or "")
        if sum(map(len, chunks)) > 60000:
            break
    return pipeline.clean("\n".join(chunks), 60000)


def fetch_supplement(url: str) -> tuple[str, dict] | None:
    if not allowed_supplementary_url(url):
        return None
    try:
        r = pipeline.SESSION.get(url, timeout=pipeline.TIMEOUT, allow_redirects=True)
        if r.status_code != 200 or len(r.content) > 12_000_000 or not allowed_supplementary_url(r.url):
            return None
        data = r.content
        ctype = (r.headers.get("content-type") or "").lower()
        if data[:4] == b"%PDF" or "pdf" in ctype:
            kind = "pdf"
            text = extract_pdf(data)
        else:
            kind = "html"
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "noscript", "nav", "footer"]):
                tag.decompose()
            text = pipeline.clean(soup.get_text("\n", strip=True), 60000)
        if not text:
            return None
        return text, {
            "url": r.url,
            "kind": kind,
            "role": "normativa_vigente_complementaria",
            "source_scope": "supplementary",
            "sha256": hashlib.sha256(data).hexdigest(),
            "characters": len(text),
        }
    except Exception as exc:
        print(f"  · normativa complementaria no disponible: {url} ({exc})")
        return None


def article_excerpt(text: str, articles: list[str]) -> str:
    if not articles:
        return pipeline.clean(text, 6500)
    pieces: list[str] = []
    for article in articles:
        token = article.replace(" ", r"\s+")
        m = re.search(rf"art[íi]culo\s+{token}\b", text, re.I)
        if not m:
            continue
        start = max(0, m.start() - 220)
        nxt = re.search(r"\bart[íi]culo\s+[0-9]{1,3}(?:\s*(?:bis|ter|qu[aá]ter))?\b", text[m.end() + 80 :], re.I)
        end = m.end() + 80 + (nxt.start() if nxt else 4500)
        pieces.append(pipeline.clean(text[start:min(len(text), end)], 5000))
    return pipeline.clean("\n\n".join(pieces), 12000) if pieces else pipeline.clean(text, 6500)


def collect_source_v3(project: dict) -> tuple[str, str, dict]:
    base_material, base_hash, evidence = strict.collect_source_strict(project)
    registry = load_registry()
    law_refs = cited_laws(base_material)
    supplements: list[dict] = []
    supplement_materials: list[str] = []

    for law in law_refs:
        entry = registry.get(law)
        if not entry:
            continue
        url = pipeline.clean(entry.get("url"), 2000)
        fetched = fetch_supplement(url)
        if not fetched:
            continue
        text, meta = fetched
        articles = cited_articles_for_law(base_material, law)
        excerpt = article_excerpt(text, articles)
        meta = {
            **meta,
            "law_number": law,
            "label": pipeline.clean(entry.get("label"), 300),
            "authority": pipeline.clean(entry.get("authority"), 300),
            "articles_requested": articles,
            "excerpt_characters": len(excerpt),
        }
        supplements.append(meta)
        supplement_materials.append(
            "NORMATIVA VIGENTE COMPLEMENTARIA · "
            f"{meta['label']} · fuente {meta['url']}"
            + (f" · artículos buscados: {', '.join(articles)}" if articles else "")
            + ":\n" + excerpt
        )
        if len(supplements) >= 3:
            break

    primary_count = int(evidence.get("primary_document_count") or 0)
    mode = "full" if primary_count >= 1 else "preliminary_insufficient_evidence"
    quality_header = (
        "CONTROL DE CALIDAD V3:\n"
        f"- analysis_mode={mode}\n"
        f"- documentos_primarios_del_expediente={primary_count}\n"
        f"- normativa_complementaria_recuperada={len(supplements)}\n"
        "- la normativa complementaria sirve para contraste jurídico; NO reemplaza el texto del proyecto.\n"
        "- una omisión en las fuentes NO prueba inexistencia ni valor cero.\n"
    )
    material = quality_header + "\n" + base_material
    if supplement_materials:
        material += "\n\n" + "\n\n".join(supplement_materials)
    material = material[:pipeline.MAX_MATERIAL]

    evidence = dict(evidence)
    evidence["selection_policy"] = "strict-v3"
    evidence["analysis_mode"] = mode
    evidence["cited_laws"] = law_refs
    evidence["supplementary_documents"] = supplements
    evidence["retrieved_at_v3"] = dt.datetime.now(dt.timezone.utc).isoformat()

    hash_input = json.dumps({
        "base_hash": base_hash,
        "selection_policy": "strict-v3",
        "mode": mode,
        "supplements": [
            {"url": s.get("url"), "sha256": s.get("sha256"), "law_number": s.get("law_number"), "articles": s.get("articles_requested")}
            for s in supplements
        ],
    }, ensure_ascii=False, sort_keys=True)
    source_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return material, source_hash, evidence


def primary_count(material: str) -> int:
    m = re.search(r"documentos_primarios_del_expediente=(\d+)", material)
    return int(m.group(1)) if m else 0


def build_prompt_v3(material: str, correction: str = "") -> str:
    pcount = primary_count(material)
    mode = "full" if pcount >= 1 else "preliminary_insufficient_evidence"
    return f"""
Actuá como analista legislativo técnico del CEPOES para la Ciudad Autónoma de Buenos Aires.
Usá EXCLUSIVAMENTE la evidencia incluida al final. No uses memoria, conocimiento general ni web.

MODO DE TRABAJO: {mode}

REGLAS OBLIGATORIAS:
1. Toda afirmación factual sobre normas, artículos, organismos, competencias, actores, fechas, montos, plazos, estadísticas o antecedentes debe estar expresamente respaldada por la evidencia.
2. El silencio de la evidencia NO equivale a inexistencia. Escribí "No surge de la evidencia suministrada..." cuando corresponda.
3. No introduzcas siglas, organismos, marcos jurídicos, jurisdicciones, montos, porcentajes, plazos ni umbrales que no aparezcan en la evidencia.
4. No uses placeholders como "a definir". Si un parámetro no está en la evidencia, describí naturalmente la brecha: "el proyecto no precisa el plazo", "no surge el monto", etc.
5. Diferenciá siempre: (a) contenido explícito del proyecto, (b) inferencia técnica, (c) normativa vigente complementaria.
6. Cuando exista NORMATIVA VIGENTE COMPLEMENTARIA y el proyecto modifique un artículo identificable, compará texto vigente y texto propuesto. No atribuyas al texto vigente algo que no figure en esa evidencia complementaria.
7. La normativa complementaria NO convierte una ficha sin documento primario en análisis completo.
8. Si documentos_primarios_del_expediente=0: recommendation="sin_definir"; arguments_for=""; arguments_against=""; proposed_amendments=""; intervention_arguments="". La ficha debe limitarse a lo que sabemos, qué falta y preguntas para obtener evidencia. No hagas análisis 360° sustantivo.
9. recommendation sólo puede ser distinta de "sin_definir" cuando documentos_primarios_del_expediente>=1 Y confidence>=0.75.
10. Si recommendation="sin_definir", rationale debe explicar por qué la evidencia no alcanza o qué debe revisarse. No puede contener frases de apoyo, rechazo, abstención, voto ni "acompañamiento condicionado". intervention_arguments tampoco puede insinuar una posición.
11. En impacto fiscal, si no hay cuantificación, decilo. No conviertas obligaciones del proyecto en costos comprobados.
12. Las preguntas de comisión no deben asumir como hecho aquello que buscan verificar.
13. Las enmiendas sólo son admisibles con documento primario. No inventes texto normativo ajeno al expediente.
14. Devolvé SOLAMENTE un objeto JSON válido ajustado exactamente al esquema; sin markdown ni claves extra.

ESQUEMA JSON:
{strict.copilot.schema_instruction()}

{correction}

EVIDENCIA OFICIAL Y COMPLEMENTARIA:
{material}
""".strip()


def _contains_bad_number(text: str, bad_numbers: list[str]) -> bool:
    return any(re.search(rf"(?<!\d){re.escape(n)}(?!\d)", text) for n in bad_numbers)


def scrub_string(value: str, bad_numbers: list[str], remove_advocacy: bool = False) -> str:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", str(value or ""))
    kept: list[str] = []
    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue
        if PLACEHOLDER_RE.search(c) or _contains_bad_number(c, bad_numbers):
            continue
        if remove_advocacy and ADVOCACY_RE.search(c):
            continue
        kept.append(c)
    return " ".join(kept).strip()


def scrub_list(values, bad_numbers: list[str], remove_advocacy: bool = False) -> list[str]:
    out: list[str] = []
    for item in values if isinstance(values, list) else []:
        s = str(item or "").strip()
        if not s or PLACEHOLDER_RE.search(s) or _contains_bad_number(s, bad_numbers):
            continue
        if remove_advocacy and ADVOCACY_RE.search(s):
            continue
        out.append(s)
    return out


def normalize_v3(result: dict, material: str) -> dict:
    pcount = primary_count(material)
    flags: list[str] = []

    bad_acronyms = strict.unsupported_acronyms(result, material)
    if bad_acronyms:
        raise RuntimeError(f"Salida con entidades/siglas no respaldadas: {bad_acronyms}")

    bad_numbers = []
    try:
        textual = {k: v for k, v in result.items() if k != "confidence"}
        output = json.dumps(textual, ensure_ascii=False)
        numbers = set(re.findall(r"(?<![A-Za-z])\d{2,}(?:[.,]\d+)?%?", output))
        bad_numbers = sorted(n for n in numbers if n not in material)
    except Exception:
        bad_numbers = []

    placeholder_found = PLACEHOLDER_RE.search(json.dumps(result, ensure_ascii=False)) is not None
    if bad_numbers:
        flags.append("unsupported_numeric_removed")
    if placeholder_found:
        flags.append("placeholder_removed")

    string_fields = [
        "executive_summary", "legal_impact", "fiscal_impact", "territorial_impact",
        "affected_actors", "risks", "arguments_for", "arguments_against", "rationale",
        "proposed_amendments", "intervention_arguments",
    ]
    for key in string_fields:
        result[key] = scrub_string(result.get(key, ""), bad_numbers)
    result["committee_questions"] = scrub_list(result.get("committee_questions"), bad_numbers)
    result["evidence_gaps"] = scrub_list(result.get("evidence_gaps"), bad_numbers)
    result["tags"] = scrub_list(result.get("tags"), bad_numbers)

    if bad_numbers or placeholder_found:
        gaps = list(result.get("evidence_gaps") or [])
        note = "La salida inicial contenía parámetros no respaldados por la evidencia; fueron eliminados y deben verificarse en revisión."
        if note not in gaps:
            gaps.append(note)
        result["evidence_gaps"] = gaps[:12]
        result["confidence"] = min(float(result.get("confidence") or 0), 0.69)
        result["recommendation"] = "sin_definir"

    confidence = float(result.get("confidence") or 0)
    if pcount < 1:
        result["analysis_mode"] = "preliminary_insufficient_evidence"
        result["confidence"] = min(confidence, 0.20)
        result["recommendation"] = "sin_definir"
        result["arguments_for"] = ""
        result["arguments_against"] = ""
        result["proposed_amendments"] = ""
        result["intervention_arguments"] = ""
        result["rationale"] = (
            "No corresponde formular una posición ni proponer modificaciones sin el texto primario del expediente. "
            "La ficha se limita a identificar la información disponible y las brechas que deben resolverse antes del análisis sustantivo."
        )
        flags.append("no_primary_document")
    else:
        result["analysis_mode"] = "full"
        if len(result.get("evidence_gaps") or []) >= 8:
            confidence = min(float(result.get("confidence") or 0), 0.69)
            result["confidence"] = confidence
        if confidence < 0.75:
            result["recommendation"] = "sin_definir"
            flags.append("recommendation_suppressed")

    if result.get("recommendation") == "sin_definir":
        result["rationale"] = scrub_string(result.get("rationale", ""), [], remove_advocacy=True)
        result["intervention_arguments"] = scrub_string(result.get("intervention_arguments", ""), [], remove_advocacy=True)
        if not result["rationale"]:
            gaps = list(result.get("evidence_gaps") or [])[:3]
            suffix = " ".join(gaps)
            result["rationale"] = (
                "La evidencia disponible no alcanza el umbral para formular una posición técnica preliminar. "
                + (f"Deben resolverse estas brechas: {suffix}" if suffix else "Se requiere revisión humana de la evidencia y del encuadre jurídico.")
            )

    if "NORMATIVA VIGENTE COMPLEMENTARIA" in material:
        flags.append("supplementary_normative_evidence")

    result["quality_flags"] = list(dict.fromkeys(flags))[:12]
    return result


def call_copilot_v3(material: str) -> dict:
    result = strict.run_copilot(build_prompt_v3(material))
    bad_acronyms = strict.unsupported_acronyms(result, material)
    textual = {k: v for k, v in result.items() if k != "confidence"}
    output = json.dumps(textual, ensure_ascii=False)
    nums = set(re.findall(r"(?<![A-Za-z])\d{2,}(?:[.,]\d+)?%?", output))
    bad_numbers = sorted(n for n in nums if n not in material)
    placeholders = bool(PLACEHOLDER_RE.search(output))

    if bad_acronyms or bad_numbers or placeholders:
        correction = (
            "CORRECCIÓN OBLIGATORIA: eliminá todo elemento no respaldado. "
            f"Siglas/entidades no verificadas: {bad_acronyms or 'ninguna'}. "
            f"Cifras/umbrales no verificados: {bad_numbers or 'ninguno'}. "
            "No reemplaces cifras por placeholders. Reformulá naturalmente indicando que el dato no surge de la evidencia. "
            "Si recommendation debe quedar sin_definir, evitá cualquier frase de apoyo, rechazo o acompañamiento."
        )
        result = strict.run_copilot(build_prompt_v3(material, correction))

    return normalize_v3(result, material)


def self_test() -> None:
    material = (
        "CONTROL DE CALIDAD V3:\n"
        "- analysis_mode=preliminary_insufficient_evidence\n"
        "- documentos_primarios_del_expediente=0\n"
        "- normativa_complementaria_recuperada=0\n"
        "FICHA PÚBLICA ESTRUCTURADA: Expediente TEST-2026. Sumario: homologación administrativa. "
        "No se incorpora texto del proyecto ni monto ni plazo."
    )
    result = call_copilot_v3(material)
    assert result["analysis_mode"] == "preliminary_insufficient_evidence"
    assert result["recommendation"] == "sin_definir"
    assert result["arguments_for"] == "" and result["arguments_against"] == ""
    assert result["proposed_amendments"] == "" and result["intervention_arguments"] == ""
    assert not PLACEHOLDER_RE.search(json.dumps(result, ensure_ascii=False))
    assert not strict.unsupported_acronyms(result, material)
    print("Self-test Copilot v3 OK")
    print(json.dumps({
        "analysis_mode": result["analysis_mode"],
        "recommendation": result["recommendation"],
        "confidence": result["confidence"],
        "quality_flags": result["quality_flags"],
    }, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-items", type=int, default=int(os.getenv("ANALYSIS_MAX_ITEMS", "3")))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    pipeline.collect_source = collect_source_v3
    pipeline.call_model = call_copilot_v3
    pipeline.MODEL_ID = MODEL_LABEL
    if args.self_test:
        self_test()
        return
    pipeline.process(max(1, min(args.max_items, 25)))


if __name__ == "__main__":
    main()
