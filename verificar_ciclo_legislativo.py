"""Verifica la capa pública de ciclo legislativo incorporada en v2.23."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "legislatura_publica.json"
OFFICIAL_HOST = "parlamentaria.legislatura.gob.ar"
VALID_STAGES = {"ingresado", "en_comision", "con_dictamen", "sancionado", "archivado"}
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
    problems: list[str] = []

    if data.get("version", 0) < 4:
        problems.append("el dataset no fue elevado a versión 4")

    minimum = max(1, int(len(with_url) * 0.85)) if with_url else 0
    if len(enriched) < minimum:
        problems.append(
            f"sólo {len(enriched)}/{len(with_url)} expedientes con URL fueron enriquecidos; "
            f"mínimo esperado {minimum}"
        )

    stages = Counter()
    for project in enriched:
        ficha = project.get("ficha_oficial") or {}
        number = project.get("numero")
        url = ficha.get("url") or project.get("url_expediente")
        if urlparse(url or "").hostname != OFFICIAL_HOST:
            problems.append(f"{number}: ficha fuera del host oficial")

        exp_id = expected_id(project.get("url_expediente"))
        if exp_id and ficha.get("expediente_id") != exp_id:
            problems.append(
                f"{number}: id de ficha {ficha.get('expediente_id')} no coincide con URL {exp_id}"
            )

        if not ficha.get("tipo_proyecto"):
            problems.append(f"{number}: falta tipo oficial")
        if not ficha.get("fecha_inicio"):
            problems.append(f"{number}: falta fecha de inicio")

        stage = ficha.get("etapa")
        stages[stage or "sin_etapa"] += 1
        if stage not in VALID_STAGES:
            problems.append(f"{number}: etapa inválida {stage}")
        if project.get("etapa") != stage:
            problems.append(
                f"{number}: etapa top-level {project.get('etapa')} != ficha_oficial {stage}"
            )

        ultimo = ficha.get("ultimo_movimiento")
        if ultimo and not ultimo.get("fecha"):
            problems.append(f"{number}: último movimiento sin fecha")

        dictamenes = ficha.get("dictamenes") or []
        events = ficha.get("eventos_documentales") or []
        evidence_dictamen = bool(ficha.get("evidencia_dictamen"))
        evidence_sancion = bool(ficha.get("evidencia_sancion"))
        sanctions = ficha.get("sanciones") or []

        if dictamenes and not evidence_dictamen:
            problems.append(f"{number}: hay dictámenes detallados pero evidencia_dictamen=false")
        if sanctions and not evidence_sancion:
            problems.append(f"{number}: hay sanción detallada pero evidencia_sancion=false")
        if stage == "con_dictamen" and not evidence_dictamen:
            problems.append(f"{number}: con_dictamen sin evidencia oficial de dictamen")
        if stage == "sancionado" and not evidence_sancion:
            problems.append(f"{number}: sancionado sin evidencia oficial de sanción")
        if not isinstance(events, list):
            problems.append(f"{number}: eventos_documentales no es lista")

    forbidden = sorted(set(walk_keys(data)) & FORBIDDEN_KEYS)
    if forbidden:
        problems.append(
            "aparecieron campos privados en el JSON público: " + ", ".join(forbidden)
        )

    summary = data.get("resumen") or {}
    with_dictamen = sum(
        1 for p in projects if (p.get("ficha_oficial") or {}).get("evidencia_dictamen")
    )
    detailed_dictamens = sum(
        len((p.get("ficha_oficial") or {}).get("dictamenes") or []) for p in projects
    )
    sanctioned = sum(
        1
        for p in projects
        if (p.get("ficha_oficial") or {}).get("etapa") == "sancionado"
    )
    with_session = sum(
        1 for p in projects if (p.get("ficha_oficial") or {}).get("sesiones")
    )

    if summary.get("expedientes_enriquecidos") != len(enriched):
        problems.append("resumen.expedientes_enriquecidos no coincide con el detalle")
    if summary.get("expedientes_con_dictamen") != with_dictamen:
        problems.append("resumen.expedientes_con_dictamen no coincide con la evidencia")
    if summary.get("dictamenes_detallados") != detailed_dictamens:
        problems.append("resumen.dictamenes_detallados no coincide con el detalle")
    if summary.get("expedientes_sancionados") != sanctioned:
        problems.append("resumen.expedientes_sancionados no coincide con el detalle")
    if summary.get("expedientes_con_sesion") != with_session:
        problems.append("resumen.expedientes_con_sesion no coincide con el detalle")
    if summary.get("etapas_legislativas") != dict(sorted(stages.items())):
        problems.append("resumen.etapas_legislativas no coincide con las fichas")

    stage_dictamen = stages.get("con_dictamen", 0)
    stage_sanctioned = stages.get("sancionado", 0)
    if stage_dictamen > with_dictamen:
        problems.append(
            f"hay {stage_dictamen} etapas con_dictamen pero sólo {with_dictamen} expedientes "
            "con evidencia de dictamen"
        )
    if stage_sanctioned > sanctioned:
        problems.append("hay etapas sancionado sin respaldo consistente")

    print(
        f"Ciclo legislativo · {len(enriched)}/{len(with_url)} fichas oficiales"
        f" · evidencia dictamen: {with_dictamen}"
        f" · dictámenes detallados: {detailed_dictamens}"
        f" · sancionados: {sanctioned}"
        f" · con sesión: {with_session}"
    )
    print("  etapas: " + " · ".join(f"{k} {v}" for k, v in sorted(stages.items())))

    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for problem in problems[:40]:
            print("   · " + problem)
        return 1

    print("✔ verificación de ciclo legislativo superada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
