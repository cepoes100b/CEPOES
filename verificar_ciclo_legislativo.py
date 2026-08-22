"""Verifica la capa pública de ciclo legislativo incorporada en v2.23."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "legislatura_publica.json"
OFFICIAL_HOST = "parlamentaria.legislatura.gob.ar"
FORBIDDEN_KEYS = {
    "prioridad_interna", "posicion", "posición", "recomendacion", "recomendación",
    "responsable", "notas_internas", "notas internas", "estrategia", "argumentos_internos",
}


def walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key).lower()
            yield from walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_keys(item)


def expected_id(url: str | None) -> int | None:
    if not url:
        return None
    try:
        value = (parse_qs(urlparse(url).query).get("id") or [None])[0]
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def main() -> int:
    if not DATA_PATH.exists():
        print("✘ falta legislatura_publica.json")
        return 1
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    projects = data.get("expedientes") or []
    with_url = [p for p in projects if p.get("url_expediente")]
    enriched = [p for p in with_url if p.get("ficha_oficial")]
    problems = []

    if data.get("version", 0) < 4:
        problems.append("el dataset no fue elevado a versión 4")
    minimum = max(1, int(len(with_url) * 0.85)) if with_url else 0
    if len(enriched) < minimum:
        problems.append(f"sólo {len(enriched)}/{len(with_url)} expedientes con URL fueron enriquecidos; mínimo esperado {minimum}")

    for project in enriched:
        ficha = project.get("ficha_oficial") or {}
        url = ficha.get("url") or project.get("url_expediente")
        if urlparse(url or "").hostname != OFFICIAL_HOST:
            problems.append(f"{project.get('numero')}: ficha fuera del host oficial")
        exp_id = expected_id(project.get("url_expediente"))
        if exp_id and ficha.get("expediente_id") != exp_id:
            problems.append(f"{project.get('numero')}: id de ficha {ficha.get('expediente_id')} no coincide con URL {exp_id}")
        if not ficha.get("tipo_proyecto"):
            problems.append(f"{project.get('numero')}: falta tipo oficial")
        if not ficha.get("fecha_inicio"):
            problems.append(f"{project.get('numero')}: falta fecha de inicio")
        if ficha.get("etapa") not in {"ingresado", "en_comision", "con_dictamen", "sancionado", "archivado"}:
            problems.append(f"{project.get('numero')}: etapa inválida {ficha.get('etapa')}")
        ultimo = ficha.get("ultimo_movimiento")
        if ultimo and not ultimo.get("fecha"):
            problems.append(f"{project.get('numero')}: último movimiento sin fecha")

    forbidden = sorted(set(walk_keys(data)) & FORBIDDEN_KEYS)
    if forbidden:
        problems.append("aparecieron campos privados en el JSON público: " + ", ".join(forbidden))

    summary = data.get("resumen") or {}
    with_dictamen = sum(1 for p in projects if (p.get("ficha_oficial") or {}).get("dictamenes"))
    sanctioned = sum(1 for p in projects if p.get("etapa") == "sancionado")
    with_session = sum(1 for p in projects if (p.get("ficha_oficial") or {}).get("sesiones"))
    if summary.get("expedientes_enriquecidos") != len(enriched):
        problems.append("resumen.expedientes_enriquecidos no coincide con el detalle")
    if summary.get("expedientes_con_dictamen") != with_dictamen:
        problems.append("resumen.expedientes_con_dictamen no coincide con el detalle")
    if summary.get("expedientes_sancionados") != sanctioned:
        problems.append("resumen.expedientes_sancionados no coincide con el detalle")
    if summary.get("expedientes_con_sesion") != with_session:
        problems.append("resumen.expedientes_con_sesion no coincide con el detalle")

    print(f"Ciclo legislativo · {len(enriched)}/{len(with_url)} fichas oficiales · dictamen: {with_dictamen} · sancionados: {sanctioned} · con sesión: {with_session}")
    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for problem in problems[:30]:
            print("   · " + problem)
        return 1
    print("✔ verificación de ciclo legislativo superada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
