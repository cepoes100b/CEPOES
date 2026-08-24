#!/usr/bin/env python3
"""Genera borradores técnicos privados para expedientes legislativos priorizados.

- Lee únicamente fuentes públicas ya detectadas por CEPOES y documentos oficiales.
- Obtiene el foco de comisiones desde Supabase mediante un endpoint autenticado con GitHub OIDC.
- Usa GitHub Models para producir JSON estructurado.
- Envía el borrador a Supabase sin persistir análisis internos en GitHub.
- No pisa trabajo humano: cada cambio de evidencia genera una nueva versión automática.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
LEG_PATH = BASE / "legislatura_publica.json"
MODEL_ENDPOINT = "https://models.github.ai/inference/chat/completions"
MODEL_ID = os.getenv("GITHUB_MODEL", "openai/gpt-4.1")
FUNCTION_URL = os.getenv(
    "LEGISLATIVE_ANALYSIS_FUNCTION_URL",
    "https://nriexnijkjamrmfivfmd.supabase.co/functions/v1/legislative-analysis-ingest",
)
OIDC_AUDIENCE = "cepoes-supabase-legislative-analysis"
TIMEOUT = 35
MAX_MATERIAL = 65000
UA = "CEPOES-legislative-analysis/1.0 (+https://cepoes.org)"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9"})

SCHEMA = {
    "name": "cepoes_legislative_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "executive_summary": {"type": "string"},
            "legal_impact": {"type": "string"},
            "fiscal_impact": {"type": "string"},
            "territorial_impact": {"type": "string"},
            "affected_actors": {"type": "string"},
            "risks": {"type": "string"},
            "arguments_for": {"type": "string"},
            "arguments_against": {"type": "string"},
            "internal_priority": {"type": "string", "enum": ["critica", "alta", "media", "baja"]},
            "recommendation": {"type": "string", "enum": ["acompanar", "acompanar_con_modificaciones", "abstenerse", "rechazar", "sin_definir"]},
            "rationale": {"type": "string"},
            "proposed_amendments": {"type": "string"},
            "committee_questions": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            "intervention_arguments": {"type": "string"},
            "evidence_gaps": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "executive_summary", "legal_impact", "fiscal_impact", "territorial_impact",
            "affected_actors", "risks", "arguments_for", "arguments_against",
            "internal_priority", "recommendation", "rationale", "proposed_amendments",
            "committee_questions", "intervention_arguments", "evidence_gaps", "tags", "confidence",
        ],
    },
}


def norm(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


def clean(value: object, max_len: int = 100000) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:max_len]


def allowed_official_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
        return host == "legislatura.gob.ar" or host.endswith(".legislatura.gob.ar")
    except Exception:
        return False


def request_oidc_token() -> str:
    base = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not base or not token:
        raise RuntimeError("GitHub OIDC no está disponible en este job")
    sep = "&" if "?" in base else "?"
    r = requests.get(
        f"{base}{sep}audience={OIDC_AUDIENCE}",
        headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["value"]


def private_call(payload: dict) -> dict:
    oidc = request_oidc_token()
    r = requests.post(
        FUNCTION_URL,
        headers={"Authorization": f"Bearer {oidc}", "Content-Type": "application/json"},
        json=payload,
        timeout=TIMEOUT,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Supabase function HTTP {r.status_code}: {r.text[:500]}")
    return r.json()


def get_focus_commissions() -> list[str]:
    data = private_call({"action": "focus"})
    return [clean(x.get("commission_name")) for x in data.get("commissions", []) if clean(x.get("commission_name"))]


def project_commissions(project: dict) -> list[str]:
    out: list[str] = []
    for key in ("comision", "comisión"):
        value = project.get(key)
        if isinstance(value, str) and value.strip():
            out.append(value.strip())
    for key in ("giros", "comisiones"):
        value = project.get(key)
        if isinstance(value, list):
            out.extend(clean(x) for x in value if clean(x))
    for d in project.get("dictamenes") or []:
        if isinstance(d, dict) and clean(d.get("comision")):
            out.append(clean(d.get("comision")))
    return list(dict.fromkeys(out))


def matches_focus(project: dict, focus: list[str]) -> bool:
    pnames = [norm(x) for x in project_commissions(project)]
    fnames = [norm(x) for x in focus]
    return any(p == f or p in f or f in p for p in pnames for f in fnames if p and f)


def parse_iso_date(value: object) -> dt.date | None:
    s = clean(value, 40)[:10]
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


def project_score(project: dict) -> tuple[int, str]:
    score = 0
    today = dt.datetime.now(dt.timezone.utc).date()
    d = parse_iso_date(project.get("fecha_reunion") or project.get("fecha"))
    if d:
        delta = (d - today).days
        if 0 <= delta <= 10:
            score += 100 - delta
        elif -14 <= delta < 0:
            score += 35 + delta
    prio = norm(project.get("prioridad_tecnica"))
    score += {"alta": 30, "media": 15, "baja": 5}.get(prio, 0)
    estado = norm(project.get("estado_actual") or project.get("etapa_legislativa"))
    if "dictamen" in estado or "despacho" in estado:
        score += 25
    tipo = norm(project.get("tipo_estimado") or project.get("tipo"))
    if "ley" in tipo:
        score += 15
    numero = clean(project.get("numero"), 120)
    return score, numero


def dedupe_candidates(projects: list[dict], focus: list[str]) -> list[dict]:
    best: dict[str, dict] = {}
    for p in projects:
        numero = clean(p.get("numero"), 120)
        if not numero or not matches_focus(p, focus):
            continue
        prev = best.get(numero)
        if prev is None or project_score(p) > project_score(prev):
            best[numero] = p
    return sorted(best.values(), key=project_score, reverse=True)


def compact_snapshot(project: dict) -> dict:
    keys = [
        "numero", "sumario", "autor", "autores", "coautores", "tipo", "tipo_estimado", "temas",
        "prioridad_tecnica", "comision", "giros", "fecha_reunion", "estado_actual", "etapa_ciclo",
        "ubicacion", "ultimo_movimiento", "movimientos", "eventos", "dictamenes", "reuniones",
        "sesiones", "sanciones", "url_expediente",
    ]
    return {k: project.get(k) for k in keys if project.get(k) not in (None, "", [], {})}


def extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    bits: list[str] = []
    for page in reader.pages[:80]:
        bits.append(page.extract_text() or "")
        if sum(map(len, bits)) > 45000:
            break
    return clean("\n".join(bits), 45000)


def extract_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    return clean("\n".join(p.text for p in doc.paragraphs), 45000)


def fetch_document(url: str) -> tuple[str, dict] | None:
    if not allowed_official_url(url):
        return None
    try:
        r = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code != 200 or len(r.content) > 12_000_000 or not allowed_official_url(r.url):
            return None
        ctype = (r.headers.get("content-type") or "").lower()
        data = r.content
        text = ""
        kind = "binary"
        if data[:4] == b"%PDF" or "pdf" in ctype:
            kind, text = "pdf", extract_pdf(data)
        elif "wordprocessingml" in ctype or r.url.lower().endswith(".docx"):
            kind, text = "docx", extract_docx(data)
        elif "html" in ctype or b"<html" in data[:1000].lower():
            kind = "html"
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = clean(soup.get_text("\n", strip=True), 45000)
        if not text:
            return None
        meta = {
            "url": r.url,
            "kind": kind,
            "sha256": hashlib.sha256(data).hexdigest(),
            "characters": len(text),
        }
        return text, meta
    except Exception as exc:
        print(f"  · documento no legible: {url} ({exc})")
        return None


def page_and_links(url: str) -> tuple[str, list[str], dict | None]:
    if not url or not allowed_official_url(url):
        return "", [], None
    try:
        r = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code != 200 or not allowed_official_url(r.url):
            return "", [], None
        soup = BeautifulSoup(r.text, "html.parser")
        links: list[str] = []
        for a in soup.find_all("a", href=True):
            text = norm(a.get_text(" ", strip=True))
            absolute = urljoin(r.url, a["href"])
            path = urlparse(absolute).path.lower()
            if not allowed_official_url(absolute):
                continue
            if path.endswith((".pdf", ".docx")) or "download.aspx" in path or any(x in text for x in ("texto", "documento", "proyecto", "dictamen", "expediente")):
                links.append(absolute)
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        page_text = clean(soup.get_text("\n", strip=True), 30000)
        meta = {"url": r.url, "kind": "official_page", "sha256": hashlib.sha256(r.content).hexdigest(), "characters": len(page_text)}
        return page_text, list(dict.fromkeys(links)), meta
    except Exception as exc:
        print(f"  · ficha oficial no disponible: {exc}")
        return "", [], None


def collect_source(project: dict) -> tuple[str, str, dict]:
    snapshot = compact_snapshot(project)
    source_url = clean(project.get("url_expediente"), 2000)
    page_text, discovered, page_meta = page_and_links(source_url)

    links: list[str] = []
    for d in project.get("dictamenes") or []:
        if isinstance(d, dict) and clean(d.get("documento_url")):
            links.append(clean(d.get("documento_url"), 2000))
    for s in project.get("sanciones") or []:
        if isinstance(s, dict) and clean(s.get("documento_url")):
            links.append(clean(s.get("documento_url"), 2000))
    links.extend(discovered)
    links = [x for x in dict.fromkeys(links) if allowed_official_url(x)][:4]

    materials = ["FICHA PÚBLICA ESTRUCTURADA:\n" + json.dumps(snapshot, ensure_ascii=False, sort_keys=True)]
    evidence_docs: list[dict] = []
    if page_text:
        materials.append("FICHA OFICIAL - TEXTO VISIBLE:\n" + page_text)
    if page_meta:
        evidence_docs.append(page_meta)
    for url in links:
        result = fetch_document(url)
        if result:
            text, meta = result
            materials.append(f"DOCUMENTO OFICIAL {meta['kind'].upper()} ({meta['url']}):\n{text}")
            evidence_docs.append(meta)

    material = "\n\n".join(materials)[:MAX_MATERIAL]
    hash_input = json.dumps({"snapshot": snapshot, "documents": [{"url": x.get("url"), "sha256": x.get("sha256")} for x in evidence_docs]}, ensure_ascii=False, sort_keys=True)
    source_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    evidence = {
        "public_snapshot": snapshot,
        "documents": evidence_docs,
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    return material, source_hash, evidence


def call_model(material: str) -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Falta GITHUB_TOKEN")
    system = (
        "Sos un analista legislativo técnico del CEPOES para la Ciudad Autónoma de Buenos Aires. "
        "Trabajá exclusivamente con la evidencia suministrada. No inventes artículos, montos, competencias, antecedentes ni impactos. "
        "Cuando la fuente no permita concluir algo, indicalo como brecha de evidencia. Diferenciá hechos de inferencias. "
        "Presentá argumentos técnicos a favor y en contra de forma equilibrada. La recomendación es preliminar y debe basarse en consistencia jurídica, "
        "impacto fiscal, territorial, social y factibilidad; no uses criterios electorales, partidarios ni propaganda. "
        "Si la evidencia es insuficiente para recomendar, devolvé recommendation='sin_definir'. "
        "Los argumentos para intervención deben ser puntos técnicos y verificables, no consignas."
    )
    user = (
        "Generá un borrador de análisis 360° para revisión humana. Considerá especialmente: qué cambia normativamente, "
        "actores afectados, costos o recursos si están sustentados, efectos territoriales si pueden inferirse, riesgos, preguntas para comisión, "
        "eventuales modificaciones de redacción y una posición técnica preliminar.\n\nEVIDENCIA OFICIAL:\n" + material
    )
    payload = {
        "model": MODEL_ID,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2,
        "max_tokens": 4200,
        "response_format": {"type": "json_schema", "json_schema": SCHEMA},
    }
    r = requests.post(
        MODEL_ENDPOINT,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"},
        json=payload, timeout=120,
    )
    if r.status_code >= 400:
        # Fallback para modelos que no admitan json_schema.
        payload["response_format"] = {"type": "json_object"}
        r = requests.post(MODEL_ENDPOINT, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"}, json=payload, timeout=120)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    result = json.loads(content)
    required = set(SCHEMA["schema"]["required"])
    missing = sorted(required - set(result))
    if missing:
        raise RuntimeError(f"Respuesta del modelo incompleta: {missing}")
    return result


def kind_for(project: dict) -> str:
    if project.get("dictamenes"):
        return "dictamen"
    if "despacho" in norm(project.get("estado_actual")):
        return "despacho"
    return "proyecto"


def process(max_items: int) -> int:
    if not LEG_PATH.exists():
        raise RuntimeError(f"No existe {LEG_PATH.name}")
    data = json.loads(LEG_PATH.read_text(encoding="utf-8"))
    focus = get_focus_commissions()
    if not focus:
        print("Sin comisiones privadas habilitadas; no se generan análisis.")
        return 0
    print(f"Foco privado: {len(focus)} comisión(es) habilitada(s)")
    candidates = dedupe_candidates(data.get("expedientes") or [], focus)
    print(f"Candidatos en foco: {len(candidates)}")

    generated = 0
    scanned = 0
    for project in candidates:
        if generated >= max_items or scanned >= max(max_items * 8, 40):
            break
        scanned += 1
        numero = clean(project.get("numero"), 120)
        print(f"· {numero}")
        try:
            material, source_hash, evidence = collect_source(project)
            kind = kind_for(project)
            check = private_call({"action": "check", "expediente_numero": numero, "document_kind": kind, "source_hash": source_hash})
            if check.get("exists"):
                print("  ↳ sin cambios de fuente; se conserva la versión existente")
                continue
            analysis = call_model(material)
            title_sum = clean(project.get("sumario"), 300)
            title = f"{numero} · {title_sum}" if title_sum else f"Análisis técnico · {numero}"
            result = private_call({
                "action": "ingest", "expediente_numero": numero, "document_kind": kind,
                "source_hash": source_hash, "source_url": clean(project.get("url_expediente"), 2000),
                "title": title, "model": MODEL_ID, "analysis": analysis, "source_evidence": evidence,
            })
            if result.get("inserted"):
                generated += 1
                print(f"  ✓ borrador automático v{result.get('version')} guardado en Supabase")
            else:
                print("  ↳ duplicado evitado")
        except Exception as exc:
            print(f"  ✗ {exc}", file=sys.stderr)
    print(f"Generados: {generated} · escaneados: {scanned}")
    return generated


def self_test() -> None:
    material = (
        "Expediente TEST-2026. Proyecto hipotético para crear un registro administrativo sin información sobre costo fiscal. "
        "El texto establece una autoridad de aplicación pero no especifica partida presupuestaria."
    )
    result = call_model(material)
    print("Self-test GitHub Models OK")
    print(json.dumps({k: result[k] for k in ("internal_priority", "recommendation", "confidence")}, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-items", type=int, default=int(os.getenv("ANALYSIS_MAX_ITEMS", "8")))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    process(max(1, min(args.max_items, 25)))


if __name__ == "__main__":
    main()
