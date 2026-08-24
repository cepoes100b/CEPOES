#!/usr/bin/env python3
"""Pipeline endurecido de análisis legislativo automático CEPOES.

Objetivos de esta capa:
- seleccionar sólo documentos realmente vinculados al expediente;
- evitar manuales/guías/navegación del portal como evidencia material;
- exigir grounding estricto a Copilot CLI;
- impedir recomendaciones automáticas cuando la evidencia o la confianza son insuficientes.

Reutiliza la captura, priorización, hash, deduplicación y escritura segura del
pipeline base. No persiste material interno en GitHub.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

import automatizar_analisis_legislativo as pipeline
import automatizar_analisis_legislativo_copilot as copilot

MODEL_LABEL = f"github-copilot-cli-strict:{os.getenv('COPILOT_MODEL', '').strip() or 'auto'}"

BANNED_ASSET_TERMS = {
    "guia", "manual", "reglamento", "ayuda", "instructivo", "tutorial",
    "consultas parlamentarias", "consultas_parlamentarias", "como usar",
}
DOCUMENT_WORDS = {"proyecto", "dictamen", "despacho", "documento", "texto", "descargar"}
STOPWORDS = {
    "para", "sobre", "entre", "desde", "hasta", "como", "esta", "este", "estos", "estas",
    "modifica", "modificase", "ley", "codigo", "articulo", "anexo", "ciudad", "buenos", "aires",
    "regimen", "creacion", "declarase", "establece", "referido", "referidos", "proyecto",
}
SAFE_ACRONYMS = {"CABA", "IA", "CEPOES", "UF"}


def canonical_url(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, p.query, ""))


def is_banned_asset(url: str, anchor_text: str = "") -> bool:
    text = pipeline.norm(f"{urlparse(url).path} {anchor_text}")
    return any(term in text for term in BANNED_ASSET_TERMS)


def is_discovered_document(page_url: str, absolute: str, anchor_text: str) -> bool:
    if not pipeline.allowed_official_url(absolute) or is_banned_asset(absolute, anchor_text):
        return False
    p = urlparse(absolute)
    base = urlparse(page_url)
    path = p.path.lower()

    # Los anchors del propio expediente (#docu, #expte, etc.) no son documentos.
    if p.path == base.path and p.query == base.query:
        return False

    # El SLP sirve los documentos reales principalmente mediante download.aspx?IdDoc=...
    if "download.aspx" in path and (parse_qs(p.query).get("IdDoc") or parse_qs(p.query).get("iddoc")):
        return True

    # Para archivos directos exigimos una etiqueta semánticamente vinculada al expediente.
    if path.endswith((".pdf", ".docx")):
        label = pipeline.norm(anchor_text)
        return any(word in label for word in DOCUMENT_WORDS)
    return False


def role_from_anchor(anchor_text: str) -> str:
    t = pipeline.norm(anchor_text)
    if "dictamen" in t:
        return "dictamen"
    if "despacho" in t:
        return "despacho"
    return "proyecto"


def page_and_links_strict(url: str) -> tuple[str, list[dict], dict | None]:
    if not url or not pipeline.allowed_official_url(url):
        return "", [], None
    try:
        r = pipeline.SESSION.get(url, timeout=pipeline.TIMEOUT, allow_redirects=True)
        if r.status_code != 200 or not pipeline.allowed_official_url(r.url):
            return "", [], None
        soup = BeautifulSoup(r.text, "html.parser")
        links: list[dict] = []
        for a in soup.find_all("a", href=True):
            label = pipeline.clean(a.get_text(" ", strip=True), 300)
            absolute = canonical_url(urljoin(r.url, a["href"]))
            if is_discovered_document(r.url, absolute, label):
                links.append({"url": absolute, "role": role_from_anchor(label), "anchor": label})

        # La ficha oficial sí es evidencia, pero se eliminan elementos de navegación/ayuda.
        for tag in soup(["script", "style", "noscript", "nav", "footer"]):
            tag.decompose()
        for a in soup.find_all("a", href=True):
            href = canonical_url(urljoin(r.url, a["href"]))
            if is_banned_asset(href, a.get_text(" ", strip=True)):
                a.decompose()
        page_text = pipeline.clean(soup.get_text("\n", strip=True), 30000)
        meta = {
            "url": canonical_url(r.url),
            "kind": "official_page",
            "role": "official_page",
            "sha256": hashlib.sha256(r.content).hexdigest(),
            "characters": len(page_text),
        }
        unique: dict[str, dict] = {}
        for item in links:
            unique.setdefault(item["url"], item)
        return page_text, list(unique.values()), meta
    except Exception as exc:
        print(f"  · ficha oficial no disponible: {exc}")
        return "", [], None


def title_terms(project: dict) -> set[str]:
    terms = set()
    for token in pipeline.norm(project.get("sumario")).split():
        if len(token) >= 5 and token not in STOPWORDS and not token.isdigit():
            terms.add(token)
    return terms


def document_relevance(text: str, project: dict) -> int:
    ntext = pipeline.norm(text[:30000])
    score = 0
    numero = pipeline.clean(project.get("numero"), 120)
    nums = re.findall(r"\d+", numero)
    if nums and all(n in ntext for n in nums[-2:]):
        score += 3
    for term in title_terms(project):
        if term in ntext:
            score += 1
    return score


def collect_source_strict(project: dict) -> tuple[str, str, dict]:
    snapshot = pipeline.compact_snapshot(project)
    source_url = pipeline.clean(project.get("url_expediente"), 2000)
    page_text, discovered, page_meta = page_and_links_strict(source_url)

    candidates: list[dict] = []
    for d in project.get("dictamenes") or []:
        if isinstance(d, dict) and pipeline.clean(d.get("documento_url")):
            candidates.append({"url": canonical_url(pipeline.clean(d.get("documento_url"), 2000)), "role": "dictamen", "anchor": "dictamen estructurado"})
    for s in project.get("sanciones") or []:
        if isinstance(s, dict) and pipeline.clean(s.get("documento_url")):
            candidates.append({"url": canonical_url(pipeline.clean(s.get("documento_url"), 2000)), "role": "sancion", "anchor": "sanción estructurada"})
    candidates.extend(discovered)

    unique: dict[str, dict] = {}
    for item in candidates:
        url = item.get("url") or ""
        if pipeline.allowed_official_url(url) and not is_banned_asset(url, item.get("anchor") or ""):
            unique.setdefault(url, item)

    materials = ["FICHA PÚBLICA ESTRUCTURADA:\n" + json.dumps(snapshot, ensure_ascii=False, sort_keys=True)]
    evidence_docs: list[dict] = []
    if page_text:
        materials.append("FICHA OFICIAL DEL EXPEDIENTE - TEXTO VISIBLE:\n" + page_text)
    if page_meta:
        evidence_docs.append(page_meta)

    primary_count = 0
    for item in list(unique.values())[:6]:
        if primary_count >= 3:
            break
        result = pipeline.fetch_document(item["url"])
        if not result:
            continue
        text, meta = result
        relevance = document_relevance(text, project)
        explicit = item["role"] in {"dictamen", "sancion"}
        if not explicit and relevance < 2:
            print(f"  · descartado por baja relevancia: {item['url']}")
            continue
        meta = {**meta, "role": item["role"], "anchor": item.get("anchor") or "", "relevance_score": relevance}
        materials.append(
            f"DOCUMENTO PRIMARIO DEL EXPEDIENTE · {item['role'].upper()} · {meta['url']}:\n{text}"
        )
        evidence_docs.append(meta)
        primary_count += 1

    quality_header = (
        "CONTROL DE EVIDENCIA:\n"
        f"- documentos_primarios_del_expediente={primary_count}\n"
        "- politica_seleccion=strict-v2\n"
        "- una omisión en las fuentes NO prueba inexistencia ni valor cero.\n"
    )
    material = (quality_header + "\n" + "\n\n".join(materials))[:pipeline.MAX_MATERIAL]
    hash_input = json.dumps(
        {
            "selection_policy": "strict-v2",
            "snapshot": snapshot,
            "documents": [
                {"url": x.get("url"), "sha256": x.get("sha256"), "role": x.get("role")}
                for x in evidence_docs
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    source_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    evidence = {
        "selection_policy": "strict-v2",
        "primary_document_count": primary_count,
        "public_snapshot": snapshot,
        "documents": evidence_docs,
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    return material, source_hash, evidence


def unsupported_acronyms(result: dict, material: str) -> list[str]:
    output = json.dumps(result, ensure_ascii=False)
    material_upper = material.upper()
    acronyms = set(re.findall(r"\b[A-ZÁÉÍÓÚÑ]{2,10}\b", output))
    return sorted(a for a in acronyms if a not in SAFE_ACRONYMS and a not in material_upper)


def unsupported_numbers(result: dict, material: str) -> list[str]:
    # Evita umbrales, multas, plazos o cifras inventadas. Ignora enumeraciones de un dígito.
    output = json.dumps(result, ensure_ascii=False)
    numbers = set(re.findall(r"(?<![A-Za-z])\d{2,}(?:[.,]\d+)?%?", output))
    return sorted(n for n in numbers if n not in material)


def run_copilot(prompt: str) -> dict:
    if not os.getenv("COPILOT_GITHUB_TOKEN"):
        raise RuntimeError("Falta COPILOT_GITHUB_TOKEN")
    cmd = [
        "copilot", "-p", prompt, "-s",
        "--no-ask-user", "--no-custom-instructions", "--no-auto-update",
        "--no-remote", "--no-remote-export", "--no-color",
        "--deny-tool=shell,write,read,url,memory",
    ]
    model = os.getenv("COPILOT_MODEL", "").strip()
    if model:
        cmd.extend(["--model", model])
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=180, env=os.environ.copy())
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "Error sin detalle").strip()[-1200:]
        raise RuntimeError(f"Copilot CLI falló ({proc.returncode}): {detail}")
    return copilot.extract_json(proc.stdout)


def build_prompt(material: str, correction: str = "") -> str:
    return f"""
Actuá como analista legislativo técnico del CEPOES para la Ciudad Autónoma de Buenos Aires.
Tu única fuente es la EVIDENCIA OFICIAL incluida al final. No uses memoria, conocimiento general ni web.

REGLAS DE GROUNDING OBLIGATORIAS:
1. Toda afirmación factual sobre leyes, artículos, organismos, competencias, actores, fechas, montos, plazos, estadísticas o antecedentes debe estar expresamente respaldada por la evidencia suministrada.
2. El silencio de la evidencia NO equivale a inexistencia. Si no hay un dato, escribí "No surge de la evidencia suministrada..."; no afirmes "no existe", "no hay", "es cero" o equivalentes salvo que la fuente lo diga explícitamente.
3. No nombres organismos, siglas, marcos internacionales, entidades sectoriales ni jurisdicciones que no aparezcan en la evidencia.
4. En impacto fiscal: si no hay estimación cuantificada, decilo. Sólo podés mencionar costos potenciales cuando deriven directamente de obligaciones expresas del proyecto y deben presentarse como potenciales, no como costos comprobados.
5. En impacto territorial: no infieras desigualdades, coordinación interjurisdiccional ni alcance geográfico más allá de lo que diga el texto.
6. En argumentos a favor/en contra y riesgos, distinguí claramente el contenido del proyecto de una evaluación técnica inferida.
7. Las modificaciones propuestas pueden sugerir precisiones conceptuales, pero NO inventes nombres de organismos, porcentajes, multas, montos, plazos numéricos ni umbrales. Cuando haga falta un parámetro no contenido en la evidencia, usá "a definir".
8. Las preguntas de comisión no deben asumir como hecho aquello que justamente buscan verificar.
9. recommendation sólo puede ser distinta de "sin_definir" si documentos_primarios_del_expediente >= 1 Y confidence >= 0.75. En cualquier otro caso debe ser "sin_definir".
10. intervention_arguments debe contener puntos técnicos verificables, no consignas ni afirmaciones no respaldadas.
11. Devolvé SOLAMENTE un objeto JSON válido ajustado exactamente al esquema; sin markdown ni claves extra.

ESQUEMA JSON:
{copilot.schema_instruction()}

{correction}

EVIDENCIA OFICIAL:
{material}
""".strip()


def call_copilot_strict(material: str) -> dict:
    result = run_copilot(build_prompt(material))
    bad_acronyms = unsupported_acronyms(result, material)
    bad_numbers = unsupported_numbers(result, material)
    if bad_acronyms or bad_numbers:
        correction = (
            "CORRECCIÓN OBLIGATORIA: la salida anterior introdujo elementos no presentes en la evidencia. "
            f"Siglas/entidades no verificadas: {bad_acronyms or 'ninguna'}. "
            f"Cifras/umbrales no verificados: {bad_numbers or 'ninguno'}. "
            "Regenerá el JSON eliminándolos o convirtiéndolos en brechas/preguntas, sin agregar nuevos elementos externos."
        )
        result = run_copilot(build_prompt(material, correction))
        bad_acronyms = unsupported_acronyms(result, material)
        bad_numbers = unsupported_numbers(result, material)
        if bad_acronyms or bad_numbers:
            raise RuntimeError(
                f"Salida no suficientemente grounded; siglas={bad_acronyms}, cifras={bad_numbers}"
            )

    primary_match = re.search(r"documentos_primarios_del_expediente=(\d+)", material)
    primary_count = int(primary_match.group(1)) if primary_match else 0
    confidence = float(result.get("confidence") or 0)

    # Barrera local adicional; existe otra barrera equivalente en PostgreSQL.
    if primary_count < 1:
        confidence = min(confidence, 0.45)
    if len(result.get("evidence_gaps") or []) >= 8:
        confidence = min(confidence, 0.69)
    result["confidence"] = confidence
    if confidence < 0.75 or primary_count < 1:
        result["recommendation"] = "sin_definir"

    # Normaliza afirmaciones fiscales incorrectamente derivadas de una omisión.
    fiscal = str(result.get("fiscal_impact") or "")
    if re.search(r"\b(presupuesto|costo|financiamiento).{0,30}\b(cero|inexistente|no existe)\b", fiscal, re.I):
        result["fiscal_impact"] = (
            "No surge de la evidencia suministrada una estimación fiscal cuantificada. "
            "La revisión humana debe determinar si las obligaciones expresas del proyecto generan necesidades de recursos y, en su caso, cuantificarlas."
        )
    return result


def self_test() -> None:
    material = (
        "CONTROL DE EVIDENCIA:\n- documentos_primarios_del_expediente=1\n"
        "FICHA PÚBLICA ESTRUCTURADA: Expediente TEST-2026. Proyecto hipotético que crea un registro administrativo. "
        "La evidencia no informa costo fiscal, partida presupuestaria ni plazo de reglamentación."
    )
    result = call_copilot_strict(material)
    if result["recommendation"] != "sin_definir" and result["confidence"] < 0.75:
        raise RuntimeError("Guardrail de recomendación no aplicado")
    print("Self-test Copilot CLI strict OK")
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

    pipeline.collect_source = collect_source_strict
    pipeline.call_model = call_copilot_strict
    pipeline.MODEL_ID = MODEL_LABEL
    if args.self_test:
        self_test()
        return
    pipeline.process(max(1, min(args.max_items, 25)))


if __name__ == "__main__":
    main()
