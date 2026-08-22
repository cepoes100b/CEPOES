"""Completa hitos del ciclo legislativo usando evidencia oficial ya capturada.

El SLP puede publicar algunas grillas (dictámenes/sanciones) mediante componentes
dinámicos que no siempre están presentes en el HTML descargado por requests. Este
paso NO infiere contenido político ni agrega fuentes externas: estructura, como
fallback, los eventos documentales y movimientos oficiales ya presentes en cada
ficha.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "legislatura_publica.json"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%+./ -]+", " ", s)).strip()


def event_text(event: dict) -> str:
    return norm(" ".join([
        event.get("tipo") or "",
        event.get("subtipo") or "",
        event.get("notas") or "",
    ]))


def movement_text(movement: dict) -> str:
    return norm(" ".join([
        movement.get("oficina") or "",
        movement.get("descripcion") or "",
    ]))


def choose_movement(movements: list[dict], fecha: str | None, needle: str) -> dict | None:
    candidates = [m for m in movements if needle in movement_text(m)]
    if fecha:
        same_day = [m for m in candidates if m.get("fecha") == fecha]
        if same_day:
            candidates = same_day
    if not candidates:
        return None

    # Para dictámenes preferimos la constancia firmada sobre la mera generación.
    def rank(m: dict) -> tuple[int, str]:
        text = movement_text(m)
        score = 0
        if "firmado" in text:
            score += 4
        if "dictamen generado" in text:
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

    dictamen_events = [e for e in events if "dictamen" in event_text(e)]
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

    # Si la grilla y el evento documental no llegaron en el HTML, el historial
    # de movimientos sigue siendo una fuente oficial explícita del dictamen.
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
    sanction_events = [e for e in events if "sancion" in event_text(e)]
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


def main() -> int:
    if not DATA_PATH.exists():
        print("✘ falta legislatura_publica.json")
        return 1

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    projects = data.get("expedientes") or []
    completed_dictamenes = 0
    completed_sanctions = 0

    for project in projects:
        ficha = project.get("ficha_oficial") or {}
        if not ficha:
            continue

        before_dict = len(ficha.get("dictamenes") or [])
        before_sanc = len(ficha.get("sanciones") or [])
        ficha["dictamenes"] = fallback_dictamenes(ficha)
        ficha["sanciones"] = fallback_sanciones(ficha)
        if not before_dict and ficha["dictamenes"]:
            completed_dictamenes += 1
        if not before_sanc and ficha["sanciones"]:
            completed_sanctions += 1

        hitos = ficha.setdefault("hitos", {})
        if ficha["dictamenes"]:
            hitos["tuvo_dictamen"] = True
            ficha["evidencia_dictamen"] = True
        if ficha["sanciones"]:
            hitos["tuvo_sancion"] = True
            ficha["evidencia_sancion"] = True

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

    ciclo = data.setdefault("ciclo_legislativo", {})
    ciclo["normalizacion_hitos"] = (
        "si una grilla dinámica del SLP no está presente en el HTML descargado, "
        "dictámenes y sanciones se estructuran desde eventos documentales y movimientos oficiales"
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
        f"(fallback en {completed_sanctions})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
