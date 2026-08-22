"""Verifica la capa pública de ciclo legislativo incorporada en v2.23.1."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "legislatura_publica.json"
OFFICIAL_HOST = "parlamentaria.legislatura.gob.ar"

VALID_CURRENT_STATES = {
    "ingresado",
    "en_comision",
    "con_dictamen",
    "despacho",
    "sancionado",
    "archivado",
}
VALID_CYCLE_STAGES = {
    "ingresado",
    "en_comision",
    "con_dictamen",
    "sancionado",
    "archivado",
}
FORBIDDEN_KEYS = {
    "prioridad_interna",
    "posicion",
    "posición",
    "recomendacion",
    "recomendación",
    "responsable",
    "notas_internas",
    "notas internas",
    "estrategia",
    "argumentos_internos",
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


def current_text(ficha: dict) -> str:
    ultimo = ficha.get("ultimo_movimiento") or {}
    return " ".join([
        str(ficha.get("ubicacion") or ""),
        str(ultimo.get("oficina") or ""),
        str(ultimo.get("descripcion") or ""),
    ]).lower()


def main() -> int:
    if not DATA_PATH.exists():
        print("✘ falta legislatura_publica.json")
        return 1

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    projects = data.get("expedientes") or []
    with_url = [p for p in projects if p.get("url_expediente")]
    enriched = [p for p in with_url if p.get("ficha_oficial")]
    problems: list[str] = []

    if data.get("version", 0) < 5:
        problems.append("el dataset no fue elevado a schema 5")

    minimum = max(1, int(len(with_url) * 0.85)) if with_url else 0
    if len(enriched) < minimum:
        problems.append(
            f"sólo {len(enriched)}/{len(with_url)} expedientes con URL fueron enriquecidos; "
            f"mínimo esperado {minimum}"
        )

    current_states = Counter()
    cycle_stages = Counter()

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

        estado = ficha.get("estado_actual")
        etapa_ciclo = ficha.get("etapa_ciclo")
        current_states[estado or "sin_estado"] += 1
        cycle_stages[etapa_ciclo or "sin_etapa"] += 1

        if estado not in VALID_CURRENT_STATES:
            problems.append(f"{number}: estado actual inválido {estado}")
        if etapa_ciclo not in VALID_CYCLE_STAGES:
            problems.append(f"{number}: etapa de ciclo inválida {etapa_ciclo}")

        if ficha.get("etapa") != estado:
            problems.append(f"{number}: alias ficha.etapa no coincide con estado_actual")
        if project.get("etapa") != estado:
            problems.append(f"{number}: etapa top-level no coincide con estado_actual")
        if project.get("estado_actual") != estado:
            problems.append(f"{number}: estado_actual top-level no coincide con la ficha")
        if project.get("etapa_ciclo") != etapa_ciclo:
            problems.append(f"{number}: etapa_ciclo top-level no coincide con la ficha")

        ultimo = ficha.get("ultimo_movimiento")
        if ultimo and not ultimo.get("fecha"):
            problems.append(f"{number}: último movimiento sin fecha")

        dictamenes = ficha.get("dictamenes") or []
        events = ficha.get("eventos_documentales") or []
        sanctions = ficha.get("sanciones") or []
        sesiones = ficha.get("sesiones") or []
        hitos = ficha.get("hitos") or {}

        evidence_dictamen = bool(ficha.get("evidencia_dictamen"))
        evidence_sancion = bool(ficha.get("evidencia_sancion"))

        if not isinstance(events, list):
            problems.append(f"{number}: eventos_documentales no es lista")
        if not isinstance(hitos, dict):
            problems.append(f"{number}: hitos no es objeto")

        if dictamenes and not hitos.get("tuvo_dictamen"):
            problems.append(f"{number}: hay dictámenes detallados pero tuvo_dictamen=false")
        if evidence_dictamen != bool(hitos.get("tuvo_dictamen")):
            problems.append(f"{number}: evidencia_dictamen no coincide con hito tuvo_dictamen")

        if sanctions and not hitos.get("tuvo_sancion"):
            problems.append(f"{number}: hay sanción detallada pero tuvo_sancion=false")
        if evidence_sancion != bool(hitos.get("tuvo_sancion")):
            problems.append(f"{number}: evidencia_sancion no coincide con hito tuvo_sancion")

        if sesiones and not hitos.get("tuvo_sesion"):
            problems.append(f"{number}: hay sesión detallada pero tuvo_sesion=false")
        if bool(sesiones) != bool(hitos.get("tuvo_sesion")):
            problems.append(f"{number}: hito tuvo_sesion no coincide con sesiones")

        text = current_text(ficha)
        if estado == "sancionado" and "sancion" not in text:
            problems.append(f"{number}: estado sancionado no surge del último movimiento")
        if estado == "archivado" and "archiv" not in text:
            problems.append(f"{number}: estado archivado no surge del último movimiento")
        if estado == "despacho" and "despacho" not in text:
            problems.append(f"{number}: estado despacho no surge del último movimiento")
        if estado == "con_dictamen" and "dictamen" not in text:
            problems.append(f"{number}: estado con_dictamen no surge del último movimiento")

        if hitos.get("tuvo_sancion") and etapa_ciclo not in {"sancionado", "archivado"}:
            problems.append(f"{number}: tuvo sanción pero etapa_ciclo={etapa_ciclo}")
        if (
            hitos.get("tuvo_dictamen")
            and not hitos.get("tuvo_sancion")
            and etapa_ciclo not in {"con_dictamen", "archivado"}
        ):
            problems.append(f"{number}: tuvo dictamen pero etapa_ciclo={etapa_ciclo}")

        for dictamen in dictamenes:
            if not dictamen.get("fecha") or not dictamen.get("tipo") or not dictamen.get("comision"):
                problems.append(f"{number}: dictamen detallado incompleto")
                break

    forbidden = sorted(set(walk_keys(data)) & FORBIDDEN_KEYS)
    if forbidden:
        problems.append(
            "aparecieron campos privados en el JSON público: " + ", ".join(forbidden)
        )

    summary = data.get("resumen") or {}
    with_dictamen = sum(
        1
        for p in projects
        if ((p.get("ficha_oficial") or {}).get("hitos") or {}).get("tuvo_dictamen")
    )
    detailed_dictamens = sum(
        len((p.get("ficha_oficial") or {}).get("dictamenes") or []) for p in projects
    )
    with_sanction = sum(
        1
        for p in projects
        if ((p.get("ficha_oficial") or {}).get("hitos") or {}).get("tuvo_sancion")
    )
    currently_sanctioned = sum(
        1
        for p in projects
        if (p.get("ficha_oficial") or {}).get("estado_actual") == "sancionado"
    )
    with_session = sum(
        1
        for p in projects
        if ((p.get("ficha_oficial") or {}).get("hitos") or {}).get("tuvo_sesion")
    )

    if with_dictamen and detailed_dictamens == 0:
        problems.append(
            "hay evidencia histórica de dictámenes pero no se extrajo ningún dictamen detallado"
        )

    if summary.get("expedientes_enriquecidos") != len(enriched):
        problems.append("resumen.expedientes_enriquecidos no coincide con el detalle")
    if summary.get("expedientes_con_dictamen") != with_dictamen:
        problems.append("resumen.expedientes_con_dictamen no coincide con los hitos")
    if summary.get("dictamenes_detallados") != detailed_dictamens:
        problems.append("resumen.dictamenes_detallados no coincide con el detalle")
    if summary.get("expedientes_con_sancion") != with_sanction:
        problems.append("resumen.expedientes_con_sancion no coincide con los hitos")
    if summary.get("expedientes_sancionados") != currently_sanctioned:
        problems.append("resumen.expedientes_sancionados no coincide con el estado actual")
    if summary.get("expedientes_con_sesion") != with_session:
        problems.append("resumen.expedientes_con_sesion no coincide con los hitos")
    if summary.get("estados_actuales") != dict(sorted(current_states.items())):
        problems.append("resumen.estados_actuales no coincide con las fichas")
    if summary.get("etapas_ciclo") != dict(sorted(cycle_stages.items())):
        problems.append("resumen.etapas_ciclo no coincide con las fichas")
    if summary.get("etapas_legislativas") != dict(sorted(current_states.items())):
        problems.append("resumen.etapas_legislativas no coincide con estados actuales")

    print(
        f"Ciclo legislativo · {len(enriched)}/{len(with_url)} fichas oficiales"
        f" · con dictamen: {with_dictamen}"
        f" · dictámenes detallados: {detailed_dictamens}"
        f" · con sanción: {with_sanction}"
        f" · estado sancionado: {currently_sanctioned}"
        f" · con sesión: {with_session}"
    )
    print("  estado actual: " + " · ".join(
        f"{k} {v}" for k, v in sorted(current_states.items())
    ))
    print("  etapa ciclo: " + " · ".join(
        f"{k} {v}" for k, v in sorted(cycle_stages.items())
    ))

    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for problem in problems[:60]:
            print("   · " + problem)
        return 1

    print("✔ verificación de ciclo legislativo superada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
