#!/usr/bin/env python3
"""Verifica el cruce v2.25 entre expedientes y la fuente oficial de recinto."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent
LEG_PATH = BASE / "legislatura_publica.json"
SES_PATH = BASE / "sesiones_publicas.json"


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm_num(value) -> str:
    return re.sub(r"\s+", "", clean(value).upper())


def pid(project: dict) -> str:
    ficha = project.get("ficha_oficial") or {}
    if ficha.get("expediente_id") not in (None, ""):
        return str(ficha.get("expediente_id"))
    url = ficha.get("url") or project.get("url_expediente") or ""
    try:
        return clean((parse_qs(urlparse(url).query).get("id") or [""])[0])
    except Exception:
        return ""


def main() -> int:
    if not LEG_PATH.exists() or not SES_PATH.exists():
        print("✘ faltan datasets para verificar integración")
        return 1
    leg = json.loads(LEG_PATH.read_text(encoding="utf-8"))
    ses = json.loads(SES_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []

    if int(leg.get("version") or 0) < 6:
        problems.append("legislatura_publica.json no fue elevado a schema 6")
    if int(ses.get("version") or 0) < 2:
        problems.append("sesiones_publicas.json no fue normalizado a schema 2")

    source_sessions = {clean(s.get("id_sesion")): s for s in ses.get("sesiones") or []}
    source_votes = {}
    source_sanctions = {}
    for s in source_sessions.values():
        sid = clean(s.get("id_sesion"))
        for vote in s.get("votaciones_nominales") or []:
            vid = clean(vote.get("id_votacion"))
            if vid:
                source_votes[(sid, vid)] = vote
        for item in s.get("sanciones") or []:
            key = (
                sid,
                clean(item.get("id_expediente")),
                norm_num(item.get("numero_expediente")),
                clean(item.get("descripcion")),
            )
            source_sanctions[key] = item

    projects = leg.get("expedientes") or []
    main_ids = {pid(p) for p in projects if pid(p)}
    main_nums = {norm_num(p.get("numero")) for p in projects if norm_num(p.get("numero"))}

    linked = with_vote = with_any = with_initial = with_definitive = link_count = 0
    for project in projects:
        activity = project.get("actividad_recinto")
        if not activity:
            continue
        linked += 1
        rows = activity.get("sesiones") or []
        link_count += len(rows)
        if activity.get("total_sesiones") != len(rows):
            problems.append(f"{project.get('numero')}: total_sesiones inconsistente")

        project_vote = False
        project_initial = False
        project_definitive = False
        project_any = False
        for row in rows:
            sid = clean(row.get("id_sesion"))
            source = source_sessions.get(sid)
            if not source:
                problems.append(f"{project.get('numero')}: sesión {sid} no existe en sesiones_publicas.json")
                continue
            if clean(row.get("fecha")) != clean(source.get("fecha")):
                problems.append(f"{project.get('numero')}: fecha de sesión {sid} no coincide con fuente")

            for vote in row.get("votaciones_nominales") or []:
                project_vote = True
                key = (sid, clean(vote.get("id_votacion")))
                original = source_votes.get(key)
                if not original:
                    problems.append(f"{project.get('numero')}: votación {key[1]} no existe en fuente")
                    continue
                if vote.get("resultado") != (original.get("resultado") or {}):
                    problems.append(f"{project.get('numero')}: resultado de votación {key[1]} difiere de fuente")
                if "detalle_nominal" in vote:
                    problems.append(f"{project.get('numero')}: detalle nominal fue duplicado en el núcleo")

            for sanction in row.get("sanciones") or []:
                project_any = True
                alcance = sanction.get("alcance")
                project_initial = project_initial or alcance == "inicial"
                project_definitive = project_definitive or alcance == "definitiva"
                matches = [
                    src for key, src in source_sanctions.items()
                    if key[0] == sid and clean(src.get("descripcion")) == clean(sanction.get("descripcion"))
                ]
                if not matches:
                    problems.append(f"{project.get('numero')}: sanción de sesión {sid} no existe en fuente")
                elif all(src.get("alcance") != alcance for src in matches):
                    problems.append(f"{project.get('numero')}: alcance de sanción difiere de fuente")

        with_vote += int(project_vote)
        with_any += int(project_any)
        with_initial += int(project_initial)
        with_definitive += int(project_definitive)

        if bool(activity.get("tuvo_votacion_nominal")) != project_vote:
            problems.append(f"{project.get('numero')}: flag tuvo_votacion_nominal inconsistente")
        if bool(activity.get("tuvo_sancion_expediente")) != project_any:
            problems.append(f"{project.get('numero')}: flag tuvo_sancion_expediente inconsistente")
        if bool(activity.get("tuvo_sancion_inicial")) != project_initial:
            problems.append(f"{project.get('numero')}: flag tuvo_sancion_inicial inconsistente")
        if bool(activity.get("tuvo_sancion_definitiva")) != project_definitive:
            problems.append(f"{project.get('numero')}: flag tuvo_sancion_definitiva inconsistente")

        ficha = project.get("ficha_oficial") or {}
        hitos = ficha.get("hitos") or {}
        if rows and not hitos.get("tuvo_sesion"):
            problems.append(f"{project.get('numero')}: actividad de recinto sin hito tuvo_sesion")
        if project_initial and not hitos.get("tuvo_sancion_inicial"):
            problems.append(f"{project.get('numero')}: sanción inicial sin hito específico")
        if project_definitive and not hitos.get("tuvo_sancion_definitiva"):
            problems.append(f"{project.get('numero')}: sanción definitiva sin hito específico")
        if project_definitive and not hitos.get("tuvo_sancion"):
            problems.append(f"{project.get('numero')}: sanción definitiva sin hito tuvo_sancion")
        if project_definitive and not ficha.get("evidencia_sancion"):
            problems.append(f"{project.get('numero')}: sanción definitiva sin evidencia_sancion")
        if project_definitive and ficha.get("estado_actual") != "archivado" and ficha.get("etapa_ciclo") != "sancionado":
            problems.append(f"{project.get('numero')}: sanción definitiva sin etapa_ciclo sancionado")
        if project_initial and not project_definitive:
            # Una primera lectura no debe activar el hito legado de sanción definitiva.
            if hitos.get("tuvo_sancion"):
                problems.append(f"{project.get('numero')}: sanción inicial activó tuvo_sancion definitivo")
            if ficha.get("etapa_ciclo") == "sancionado":
                problems.append(f"{project.get('numero')}: sanción inicial elevó indebidamente etapa_ciclo")

    discovered = leg.get("expedientes_descubiertos_recinto") or []
    seen_ids = set()
    seen_nums = set()
    for item in discovered:
        eid = clean(item.get("id_expediente"))
        num = norm_num(item.get("numero"))
        if eid and eid in main_ids:
            problems.append(f"descubierto {eid}: ya existe en expedientes principales")
        if num and num in main_nums:
            problems.append(f"descubierto {item.get('numero')}: ya existe en expedientes principales")
        if eid and eid in seen_ids:
            problems.append(f"descubierto {eid}: id duplicado")
        if num and num in seen_nums:
            problems.append(f"descubierto {item.get('numero')}: número duplicado")
        if eid:
            seen_ids.add(eid)
        if num:
            seen_nums.add(num)
        if not item.get("motivos"):
            problems.append(f"descubierto {item.get('numero') or eid}: sin motivo de descubrimiento")

    summary = leg.get("resumen") or {}
    expected = {
        "expedientes_vinculados_recinto": linked,
        "vinculaciones_sesion_expediente": link_count,
        "expedientes_con_votacion_nominal": with_vote,
        "expedientes_con_sancion_expediente_en_sesion": with_any,
        "expedientes_con_sancion_inicial_en_sesion": with_initial,
        "expedientes_con_sancion_definitiva_en_sesion": with_definitive,
        "expedientes_descubiertos_solo_recinto": len(discovered),
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            problems.append(f"resumen.{key}={summary.get(key)}; esperado {value}")

    meta = leg.get("integracion_recinto") or {}
    if meta.get("schema") != 2:
        problems.append("integracion_recinto.schema debe ser 2")
    if meta.get("fuente") != "sesiones_publicas.json":
        problems.append("integracion_recinto no identifica sesiones_publicas.json")
    if meta.get("sesiones_fuente") != len(source_sessions):
        problems.append("integracion_recinto.sesiones_fuente no coincide")
    if meta.get("expedientes_vinculados") != linked:
        problems.append("integracion_recinto.expedientes_vinculados no coincide")

    print(
        "Integración recinto · "
        f"{linked} expedientes vinculados · {link_count} vínculos de sesión · "
        f"{with_vote} con votación nominal · {with_any} con sanción de expediente "
        f"({with_initial} inicial · {with_definitive} definitiva) · "
        f"{len(discovered)} descubiertos sólo en recinto"
    )
    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for problem in problems[:80]:
            print("   · " + problem)
        return 1
    print("✔ verificación de integración de recinto superada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
