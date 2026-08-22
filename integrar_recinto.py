#!/usr/bin/env python3
"""Cruza el núcleo de expedientes con sesiones/votaciones oficiales (v2.25).

No duplica el detalle nominal: legislatura_publica.json conserva referencias,
resultados agregados e hitos; sesiones_publicas.json sigue siendo la fuente
detallada de recinto.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent
LEG_PATH = BASE / "legislatura_publica.json"
SES_PATH = BASE / "sesiones_publicas.json"


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm_num(value) -> str:
    return re.sub(r"\s+", "", clean(value).upper())


def project_id(project: dict) -> str:
    ficha = project.get("ficha_oficial") or {}
    value = ficha.get("expediente_id")
    if value not in (None, ""):
        return str(value)
    url = ficha.get("url") or project.get("url_expediente") or ""
    try:
        return clean((parse_qs(urlparse(url).query).get("id") or [""])[0])
    except Exception:
        return ""


def source_key(item: dict) -> tuple[str, str]:
    return clean(item.get("id_expediente")), norm_num(item.get("numero_expediente"))


def session_ref(session: dict) -> dict:
    return {
        "id_sesion": clean(session.get("id_sesion")),
        "fecha": clean(session.get("fecha")),
        "tipo": clean((session.get("tipo") or {}).get("descripcion")),
        "url": clean((session.get("urls") or {}).get("votaciones")),
    }


def compact_vote(vote: dict) -> dict:
    return {
        "id_votacion": clean(vote.get("id_votacion")),
        "asunto": clean(vote.get("asunto")),
        "resultado": vote.get("resultado") or {},
    }


def main() -> int:
    if not LEG_PATH.exists() or not SES_PATH.exists():
        print("✘ faltan legislatura_publica.json o sesiones_publicas.json")
        return 1

    leg = json.loads(LEG_PATH.read_text(encoding="utf-8"))
    ses = json.loads(SES_PATH.read_text(encoding="utf-8"))
    projects = leg.get("expedientes") or []
    sessions = ses.get("sesiones") or []

    by_id: dict[str, int] = {}
    by_num: dict[str, int] = {}
    for i, project in enumerate(projects):
        pid = project_id(project)
        pnum = norm_num(project.get("numero"))
        if pid:
            by_id[pid] = i
        if pnum:
            by_num[pnum] = i

    links: dict[int, dict[str, dict]] = defaultdict(dict)
    discovered: dict[tuple[str, str], dict] = {}

    def resolve(eid: str, num: str) -> int | None:
        if eid and eid in by_id:
            return by_id[eid]
        if num and num in by_num:
            return by_num[num]
        return None

    def discovery(eid: str, num: str, session: dict, kind: str, basic: dict | None = None):
        if not eid and not num:
            return
        key = (eid, num)
        row = discovered.setdefault(key, {
            "id_expediente": eid or None,
            "numero": num or None,
            "url_ficha": f"https://parlamentaria.legislatura.gob.ar/pages/expediente.aspx?id={eid}" if eid else None,
            "primera_sesion": clean(session.get("fecha")),
            "ultima_sesion": clean(session.get("fecha")),
            "motivos": [],
            "datos_basicos": basic or None,
        })
        row["primera_sesion"] = min(row["primera_sesion"], clean(session.get("fecha")))
        row["ultima_sesion"] = max(row["ultima_sesion"], clean(session.get("fecha")))
        if kind not in row["motivos"]:
            row["motivos"].append(kind)
        if not row.get("datos_basicos") and basic:
            row["datos_basicos"] = basic

    def bucket(index: int, session: dict) -> dict:
        sid = clean(session.get("id_sesion"))
        if sid not in links[index]:
            links[index][sid] = {
                **session_ref(session),
                "asuntos_considerados": [],
                "sanciones": [],
                "votaciones_nominales": [],
            }
        return links[index][sid]

    for session in sessions:
        for item in session.get("asuntos_considerados") or []:
            eid, num = source_key(item)
            idx = resolve(eid, num)
            if idx is None:
                discovery(eid, num, session, "asunto_considerado")
                continue
            bucket(idx, session)["asuntos_considerados"].append({
                "tipo": clean(item.get("tipo")),
                "descripcion": clean(item.get("descripcion")),
                "procesado": bool(item.get("procesado")),
            })

        for item in session.get("sanciones") or []:
            eid, num = source_key(item)
            idx = resolve(eid, num)
            if idx is None:
                discovery(eid, num, session, "sancion")
                continue
            bucket(idx, session)["sanciones"].append({
                "tipo": clean(item.get("tipo")),
                "descripcion": clean(item.get("descripcion")),
            })

        for vote in session.get("votaciones_nominales") or []:
            basic = vote.get("expediente") or {}
            eid = clean(vote.get("id_expediente") or basic.get("id_expediente"))
            num = norm_num(basic.get("numero"))
            idx = resolve(eid, num)
            if idx is None:
                discovery(eid, num, session, "votacion_nominal", basic or None)
                continue
            bucket(idx, session)["votaciones_nominales"].append(compact_vote(vote))

    linked_projects = 0
    with_vote = 0
    with_session_sanction = 0
    linked_sessions = 0

    for i, project in enumerate(projects):
        ficha = project.get("ficha_oficial") or {}
        session_rows = sorted(links.get(i, {}).values(), key=lambda x: (x.get("fecha") or "", x.get("id_sesion") or ""))
        if not session_rows:
            project.pop("actividad_recinto", None)
            continue

        linked_projects += 1
        linked_sessions += len(session_rows)
        has_vote = any(row["votaciones_nominales"] for row in session_rows)
        has_sanction = any(row["sanciones"] for row in session_rows)
        with_vote += int(has_vote)
        with_session_sanction += int(has_sanction)

        project["actividad_recinto"] = {
            "fuente": "sesiones_publicas.json",
            "sesiones": session_rows,
            "total_sesiones": len(session_rows),
            "tuvo_votacion_nominal": has_vote,
            "tuvo_sancion_en_sesion": has_sanction,
        }

        existing = ficha.get("sesiones") or []
        existing_keys = {(clean(x.get("fecha")), clean(x.get("id_sesion"))) for x in existing if isinstance(x, dict)}
        for row in session_rows:
            key = (clean(row.get("fecha")), clean(row.get("id_sesion")))
            if key not in existing_keys:
                existing.append({
                    "id_sesion": row.get("id_sesion"),
                    "fecha": row.get("fecha"),
                    "tipo": row.get("tipo"),
                    "descripcion": "Vinculación con fuente oficial de recinto",
                    "presidente": None,
                    "asunto": "; ".join(v.get("asunto") or "" for v in row["votaciones_nominales"] if v.get("asunto")) or None,
                    "afirmativos": None,
                    "negativos": None,
                    "abstenciones": None,
                    "sin_votar": None,
                    "url": row.get("url"),
                    "fuente": "sesiones_publicas.json",
                })
                existing_keys.add(key)
        ficha["sesiones"] = existing

        hitos = ficha.setdefault("hitos", {})
        hitos["tuvo_sesion"] = bool(existing)
        if has_sanction:
            hitos["tuvo_sancion"] = True
            ficha["evidencia_sancion"] = True
            if ficha.get("estado_actual") != "archivado":
                ficha["etapa_ciclo"] = "sancionado"
                project["etapa_ciclo"] = "sancionado"

    summary = leg.setdefault("resumen", {})
    current_states = Counter()
    cycle_stages = Counter()
    with_dictamen = detailed_dictamens = with_sanction = currently_sanctioned = with_session = 0
    enriched = 0
    for project in projects:
        ficha = project.get("ficha_oficial") or {}
        if ficha:
            enriched += 1
            current_states[ficha.get("estado_actual") or "sin_estado"] += 1
            cycle_stages[ficha.get("etapa_ciclo") or "sin_etapa"] += 1
            hitos = ficha.get("hitos") or {}
            with_dictamen += int(bool(hitos.get("tuvo_dictamen")))
            with_sanction += int(bool(hitos.get("tuvo_sancion")))
            with_session += int(bool(hitos.get("tuvo_sesion")))
            currently_sanctioned += int(ficha.get("estado_actual") == "sancionado")
            detailed_dictamens += len(ficha.get("dictamenes") or [])

    summary.update({
        "expedientes_enriquecidos": enriched,
        "expedientes_con_dictamen": with_dictamen,
        "dictamenes_detallados": detailed_dictamens,
        "expedientes_con_sancion": with_sanction,
        "expedientes_sancionados": currently_sanctioned,
        "expedientes_con_sesion": with_session,
        "estados_actuales": dict(sorted(current_states.items())),
        "etapas_ciclo": dict(sorted(cycle_stages.items())),
        "etapas_legislativas": dict(sorted(current_states.items())),
        "expedientes_vinculados_recinto": linked_projects,
        "vinculaciones_sesion_expediente": linked_sessions,
        "expedientes_con_votacion_nominal": with_vote,
        "expedientes_con_sancion_en_sesion": with_session_sanction,
        "expedientes_descubiertos_solo_recinto": len(discovered),
    })

    leg["version"] = max(int(leg.get("version") or 0), 6)
    leg["integracion_recinto"] = {
        "schema": 1,
        "fuente": "sesiones_publicas.json",
        "actualizado_en_fuente": ses.get("actualizado_en"),
        "sesiones_fuente": len(sessions),
        "expedientes_vinculados": linked_projects,
        "expedientes_descubiertos_solo_recinto": len(discovered),
        "regla": "cruce por id_expediente oficial; número de expediente como respaldo",
    }
    leg["expedientes_descubiertos_recinto"] = sorted(
        discovered.values(),
        key=lambda x: (x.get("primera_sesion") or "", x.get("numero") or "", x.get("id_expediente") or ""),
    )

    LEG_PATH.write_text(json.dumps(leg, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(
        "Integración recinto · "
        f"{linked_projects}/{len(projects)} expedientes vinculados · "
        f"{with_vote} con votación nominal · {with_session_sanction} con sanción en sesión · "
        f"{len(discovered)} descubiertos sólo en recinto"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
