#!/usr/bin/env python3
"""Agrega a legislatura_publica.json un radar temprano de últimos expedientes oficiales.

No modifica el núcleo `expedientes`: esa lista sigue representando expedientes incluidos
en agendas de comisión. El radar permite detectar ingresos antes de su primera agenda.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from actualizar_legislatura import classify_project
from actualizar_sesiones import extract_nodes, expediente_basicos, post_xml

LEG_PATH = Path("legislatura_publica.json")
SES_PATH = Path("sesiones_publicas.json")
LIMIT = 500
CHUNK = 100
OFFICIAL_HOST = "parlamentaria.legislatura.gob.ar"


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm_num(value) -> str:
    return re.sub(r"\s+", "", clean(value).upper())


def iso_datetime(value: str | None) -> str | None:
    text = clean(value)
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            parsed = dt.datetime.strptime(text, fmt)
            if fmt == "%d/%m/%Y":
                return parsed.date().isoformat()
            return parsed.isoformat()
        except ValueError:
            pass
    return None


def id_from_url(url: str | None) -> str:
    try:
        return clean((parse_qs(urlparse(url or "").query).get("id") or [""])[0])
    except Exception:
        return ""


def agenda_keys(data: dict) -> tuple[set[str], set[str]]:
    ids, nums = set(), set()
    for project in data.get("expedientes") or []:
        eid = id_from_url(project.get("url_expediente"))
        num = norm_num(project.get("numero"))
        if eid:
            ids.add(eid)
        if num:
            nums.add(num)
    return ids, nums


def recinto_keys(data: dict) -> tuple[set[str], set[str]]:
    ids, nums = set(), set()
    for session in data.get("sesiones") or []:
        for item in session.get("asuntos_considerados") or []:
            eid = clean(item.get("id_expediente"))
            num = norm_num(item.get("numero_expediente"))
            if eid:
                ids.add(eid)
            if num:
                nums.add(num)
        for item in session.get("sanciones") or []:
            eid = clean(item.get("id_expediente"))
            num = norm_num(item.get("numero_expediente"))
            if eid:
                ids.add(eid)
            if num:
                nums.add(num)
        for vote in session.get("votaciones_nominales") or []:
            basic = vote.get("expediente") or {}
            eid = clean(vote.get("id_expediente") or basic.get("id_expediente"))
            num = norm_num(basic.get("numero"))
            if eid:
                ids.add(eid)
            if num:
                nums.add(num)
    return ids, nums


def fetch_basics(http: requests.Session, ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(ids), CHUNK):
        out.update(expediente_basicos(http, ids[i:i + CHUNK]))
    return out


def main() -> int:
    if not LEG_PATH.exists():
        print("✘ falta legislatura_publica.json")
        return 1
    if not SES_PATH.exists():
        print("✘ falta sesiones_publicas.json")
        return 1

    leg = json.loads(LEG_PATH.read_text(encoding="utf-8"))
    ses = json.loads(SES_PATH.read_text(encoding="utf-8"))
    if int(ses.get("version") or 0) < 2:
        print("✘ sesiones_publicas.json debe normalizarse antes del radar")
        return 1

    http = requests.Session()
    root = post_xml(http, "GetUltimosExpedientes", {"cantRegistros": str(LIMIT)})
    raw = extract_nodes(root, "ultimoExpediente")
    raw_by_id = {}
    for row in raw:
        eid = clean(row.get("id_expediente"))
        if eid:
            raw_by_id[eid] = row
    ids = list(raw_by_id)
    basics = fetch_basics(http, ids)

    agenda_ids, agenda_nums = agenda_keys(leg)
    recinto_ids, recinto_nums = recinto_keys(ses)

    rows = []
    with_basics = 0
    for eid, raw_row in raw_by_id.items():
        basic = basics.get(eid) or {}
        with_basics += int(bool(basic))
        numero = norm_num(basic.get("numero") or raw_row.get("expediente"))
        sumario = clean(basic.get("sumario"))
        estimated_type, topics, priority = classify_project(numero, sumario)
        official_type = clean(basic.get("tipo")).upper() or None
        in_agenda = eid in agenda_ids or (numero and numero in agenda_nums)
        in_recinto = eid in recinto_ids or (numero and numero in recinto_nums)
        url = clean(basic.get("url_ficha")) or f"https://{OFFICIAL_HOST}/pages/expediente.aspx?id={eid}"
        rows.append({
            "id_expediente": eid,
            "numero": numero or None,
            "fecha_ingreso": iso_datetime(raw_row.get("fecha_ingreso")),
            "autor": clean(basic.get("autor") or raw_row.get("autor")) or None,
            "sumario": sumario or None,
            "tipo_oficial": official_type,
            "tipo_estimado": estimated_type,
            "origen": clean(basic.get("origen")).upper() or None,
            "ubicacion_reportada": clean(raw_row.get("ubicacion")) or None,
            "temas": topics,
            "prioridad_tecnica": priority,
            "url_expediente": url,
            "documento": basic.get("documento"),
            "en_agenda_retenida": bool(in_agenda),
            "en_recinto_2026": bool(in_recinto),
        })

    rows.sort(key=lambda x: (x.get("fecha_ingreso") or "", int(x.get("id_expediente") or 0)), reverse=True)
    outside_agenda = sum(1 for x in rows if not x["en_agenda_retenida"])
    outside_both = sum(1 for x in rows if not x["en_agenda_retenida"] and not x["en_recinto_2026"])
    laws_outside = sum(1 for x in rows if not x["en_agenda_retenida"] and x.get("tipo_oficial") == "LEY")
    high_outside = sum(1 for x in rows if not x["en_agenda_retenida"] and x.get("prioridad_tecnica") == "alta")

    leg["radar_ingresos"] = {
        "schema": 1,
        "actualizado": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fuente": "Sistema de Consultas Parlamentarias de la Legislatura CABA · GetUltimosExpedientes + GetExpedienteDatosBasicos",
        "limite_solicitado": LIMIT,
        "criterio": "últimos expedientes ingresados; capa descriptiva separada del núcleo de agendas",
        "expedientes": rows,
    }
    summary = leg.setdefault("resumen", {})
    summary.update({
        "radar_ultimos_expedientes": len(rows),
        "radar_con_datos_basicos": with_basics,
        "radar_fuera_agenda_retenida": outside_agenda,
        "radar_fuera_agenda_y_recinto": outside_both,
        "radar_leyes_fuera_agenda": laws_outside,
        "radar_prioridad_alta_fuera_agenda": high_outside,
    })
    sources = leg.setdefault("fuentes", [])
    service = "https://parlamentaria.legislatura.gob.ar/webservices/Json.asmx/GetUltimosExpedientes"
    if service not in sources:
        sources.append(service)

    LEG_PATH.write_text(json.dumps(leg, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Radar ingresos · {len(rows)} últimos expedientes · {with_basics} con datos básicos · "
        f"{outside_agenda} fuera de agenda retenida · {outside_both} fuera también de recinto"
    )
    print(f"  leyes fuera de agenda: {laws_outside} · prioridad técnica alta fuera de agenda: {high_outside}")
    if rows:
        newest = rows[0]
        oldest = rows[-1]
        print(f"  ventana efectiva: {oldest.get('fecha_ingreso')} → {newest.get('fecha_ingreso')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
