"""Normaliza hitos del ciclo legislativo usando evidencia oficial ya capturada.

El SLP puede publicar algunas grillas (dictámenes/sanciones) mediante componentes
dinámicos que no siempre están presentes en el HTML descargado por requests. Este
paso NO infiere contenido político ni agrega fuentes externas: estructura, como
fallback, eventos documentales y movimientos oficiales ya presentes en cada ficha.

Regla crítica: una palabra como "dictamen" o "sanción" dentro de las NOTAS libres de
un evento no constituye por sí sola evidencia del hito. Para clasificar un evento se
usa exclusivamente su tipo/subtipo oficial; las notas se conservan sólo como contexto.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "legislatura_publica.json"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%+./ -]+", " ", s)).strip()


def event_label_text(event: dict) -> str:
    """Texto clasificatorio del evento: sólo campos tipados, nunca notas libres."""
    return norm(" ".join([
        event.get("tipo") or "",
        event.get("subtipo") or "",
    ]))


def movement_text(movement: dict) -> str:
    return norm(" ".join([
        movement.get("oficina") or "",
        movement.get("descripcion") or "",
    ]))


def has_event_label(events: list[dict], needle: str) -> bool:
    n = norm(needle)
    return any(n in event_label_text(event) for event in events)


def has_movement(movements: list[dict], needle: str) -> bool:
    n = norm(needle)
    return any(n in movement_text(movement) for movement in movements)


def choose_movement(movements: list[dict], fecha: str | None, needle: str) -> dict | None:
    candidates = [m for m in movements if norm(needle) in movement_text(m)]
    if fecha:
        same_day = [m for m in candidates if m.get("fecha") == fecha]
        if same_day:
            candidates = same_day
    if not candidates:
        return None

    def rank(m: dict) -> tuple[int, str]:
        text = movement_text(m)
        score = 0
        if "firmado" in text:
            score += 4
        if "generado" in text:
            score += 2
        if "esperando recepcion" in text:
            score -= 1
        return (score, m.get("fecha") or "")

    return max(candidates, key=rank)


def fallback_dictamenes(ficha: dict) -> list[dict]:
    existing = ficha.get("dictamenes") or []
    if existing:
        return existing

    events = ficha.get("eventos_documentales") or []
    movements = ficha.get("movimientos") or []
    out: list[dict] = []
    seen: set[tuple[str | None, str | None]] = set()

    # Sólo un evento cuyo TIPO/SUBTIPO oficial sea dictamen puede activar este camino.
    dictamen_events = [e for e in events if "dictamen" in event_label_text(e)]
    for event in dictamen_events:
        fecha = event.get("fecha")
        movement = choose_movement(movements, fecha, "dictamen")
        comision = clean((movement or {}).get("oficina")) or None
        key = (fecha, comision)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "fecha": fecha,
            "tipo": clean(event.get("subtipo")) or "DICTAMEN",
            "comision": comision,
            "documento_url": event.get("documento_url"),
            "firmas_url": None,
            "fuente": "evento_documental_y_movimiento_oficial",
        })

    if out:
        return out

    # Si la grilla y el evento tipado no llegaron en el HTML, un movimiento que
    # diga explícitamente DICTAMEN sigue siendo evidencia oficial suficiente.
    grouped: dict[tuple[str | None, str | None], dict] = {}
    for movement in movements:
        if "dictamen" not in movement_text(movement):
            continue
        fecha = movement.get("fecha")
        comision = clean(movement.get("oficina")) or None
        key = (fecha, comision)
        current = grouped.get(key)
        if current is None or "firmado" in movement_text(movement):
            grouped[key] = movement

    for (fecha, comision), movement in sorted(grouped.items(), key=lambda item: item[0][0] or ""):
        out.append({
            "fecha": fecha,
            "tipo": "DICTAMEN",
            "comision": comision,
            "documento_url": None,
            "firmas_url": None,
            "descripcion_fuente": clean(movement.get("descripcion")) or None,
            "fuente": "movimiento_oficial",
        })
    return out


def fallback_sanciones(ficha: dict) -> list[dict]:
    existing = ficha.get("sanciones") or []
    if existing:
        return existing

    events = ficha.get("eventos_documentales") or []
    movements = ficha.get("movimientos") or []
    sanction_events = [e for e in events if "sancion" in event_label_text(e)]
    out: list[dict] = []

    for event in sanction_events:
        fecha = event.get("fecha")
        movement = choose_movement(movements, fecha, "sancion")
        out.append({
            "numero": None,
            "tipo": clean(event.get("subtipo")) or "SANCION",
            "aprobacion": None,
            "fecha_aprobacion": fecha,
            "documento_url": event.get("documento_url"),
            "descripcion_fuente": clean((movement or {}).get("descripcion")) or None,
            "fuente": "evento_documental_y_movimiento_oficial",
        })
    if out:
        return out

    seen: set[tuple[str | None, str | None]] = set()
    for movement in movements:
        if "sancionad" not in movement_text(movement):
            continue
        fecha = movement.get("fecha")
        descripcion = clean(movement.get("descripcion")) or None
        key = (fecha, descripcion)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "numero": None,
            "tipo": "SANCION",
            "aprobacion": None,
            "fecha_aprobacion": fecha,
            "documento_url": None,
            "descripcion_fuente": descripcion,
            "fuente": "movimiento_oficial",
        })
    return out


def strict_dictamen_evidence(ficha: dict) -> bool:
    if ficha.get("dictamenes"):
        return True
    events = ficha.get("eventos_documentales") or []
    movements = ficha.get("movimientos") or []
    return has_event_label(events, "dictamen") or has_movement(movements, "dictamen")


def strict_sanction_evidence(ficha: dict) -> bool:
    if ficha.get("sanciones"):
        return True
    events = ficha.get("eventos_documentales") or []
    movements = ficha.get("movimientos") or []
    return has_event_label(events, "sancion") or has_movement(movements, "sancionad")


def strict_dispatch_evidence(ficha: dict) -> bool:
    events = ficha.get("eventos_documentales") or []
    movements = ficha.get("movimientos") or []
    return (
        ficha.get("estado_actual") == "despacho"
        or has_event_label(events, "despacho")
        or has_movement(movements, "despacho")
    )


def recompute_cycle_stage(ficha: dict, hitos: dict) -> str:
    estado = ficha.get("estado_actual")
    if estado == "archivado":
        return "archivado"
    if hitos.get("tuvo_sancion"):
        return "sancionado"
    if hitos.get("tuvo_dictamen") or hitos.get("tuvo_despacho") or estado in {"con_dictamen", "despacho"}:
        return "con_dictamen"
    if estado == "en_comision" or ficha.get("giros"):
        return "en_comision"
    return "ingresado"


def main() -> int:
    if not DATA_PATH.exists():
        print("✘ falta legislatura_publica.json")
        return 1

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    projects = data.get("expedientes") or []
    completed_dictamenes = 0
    completed_sanctions = 0
    removed_false_dictamen = 0
    cycle_stages = Counter()

    for project in projects:
        ficha = project.get("ficha_oficial") or {}
        if not ficha:
            continue

        previous_dictamen_flag = bool((ficha.get("hitos") or {}).get("tuvo_dictamen"))
        before_dict = len(ficha.get("dictamenes") or [])
        before_sanc = len(ficha.get("sanciones") or [])

        ficha["dictamenes"] = fallback_dictamenes(ficha)
        ficha["sanciones"] = fallback_sanciones(ficha)

        if not before_dict and ficha["dictamenes"]:
            completed_dictamenes += 1
        if not before_sanc and ficha["sanciones"]:
            completed_sanctions += 1

        tuvo_dictamen = strict_dictamen_evidence(ficha)
        tuvo_sancion = strict_sanction_evidence(ficha)
        tuvo_despacho = strict_dispatch_evidence(ficha)
        if previous_dictamen_flag and not tuvo_dictamen:
            removed_false_dictamen += 1

        hitos = ficha.setdefault("hitos", {})
        hitos["tuvo_dictamen"] = tuvo_dictamen
        hitos["tuvo_despacho"] = tuvo_despacho
        hitos["tuvo_sesion"] = bool(ficha.get("sesiones") or [])
        hitos["tuvo_sancion"] = tuvo_sancion
        hitos["fue_archivado"] = ficha.get("estado_actual") == "archivado"

        ficha["evidencia_dictamen"] = tuvo_dictamen
        ficha["evidencia_sancion"] = tuvo_sancion
        ficha["etapa_ciclo"] = recompute_cycle_stage(ficha, hitos)
        project["etapa_ciclo"] = ficha["etapa_ciclo"]
        cycle_stages[ficha["etapa_ciclo"]] += 1

    summary = data.setdefault("resumen", {})
    summary["expedientes_con_dictamen"] = sum(
        1 for p in projects if ((p.get("ficha_oficial") or {}).get("hitos") or {}).get("tuvo_dictamen")
    )
    summary["dictamenes_detallados"] = sum(
        len((p.get("ficha_oficial") or {}).get("dictamenes") or []) for p in projects
    )
    summary["expedientes_con_sancion"] = sum(
        1 for p in projects if ((p.get("ficha_oficial") or {}).get("hitos") or {}).get("tuvo_sancion")
    )
    summary["expedientes_con_sesion"] = sum(
        1 for p in projects if ((p.get("ficha_oficial") or {}).get("hitos") or {}).get("tuvo_sesion")
    )
    summary["etapas_ciclo"] = dict(sorted(cycle_stages.items()))

    ciclo = data.setdefault("ciclo_legislativo", {})
    ciclo["normalizacion_hitos"] = (
        "si una grilla dinámica del SLP no está presente en el HTML descargado, "
        "dictámenes y sanciones se estructuran desde tipos/subtipos de eventos documentales "
        "y movimientos oficiales; las notas libres no clasifican hitos"
    )

    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(
        "Normalización ciclo · "
        f"dictámenes estructurados: {summary['dictamenes_detallados']} "
        f"(fallback en {completed_dictamenes} expedientes) · "
        f"sanciones con evidencia: {summary['expedientes_con_sancion']} "
        f"(fallback en {completed_sanctions}) · "
        f"falsos positivos de dictamen removidos: {removed_false_dictamen}"
    )
    print("  etapa ciclo normalizada: " + " · ".join(
        f"{k} {v}" for k, v in sorted(cycle_stages.items())
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
