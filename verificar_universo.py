#!/usr/bin/env python3
"""Verifica el radar público de últimos expedientes (v2.26)."""
from __future__ import annotations

import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

LEG_PATH = Path("legislatura_publica.json")
SES_PATH = Path("sesiones_publicas.json")
OFFICIAL_HOST = "parlamentaria.legislatura.gob.ar"
PRIVATE_KEYS = {
    "prioridad_interna", "posicion", "posición", "recomendacion", "recomendación",
    "responsable", "notas_internas", "estrategia", "argumentos_internos",
    "analisis_tecnico", "argumentos", "preguntas", "oportunidad", "modificaciones",
}


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm_num(value) -> str:
    return re.sub(r"\s+", "", clean(value).upper())


def id_from_url(url: str | None) -> str:
    try:
        return clean((parse_qs(urlparse(url or "").query).get("id") or [""])[0])
    except Exception:
        return ""


def walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key).lower()
            yield from walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_keys(item)


def main() -> int:
    if not LEG_PATH.exists() or not SES_PATH.exists():
        print("✘ faltan datasets para verificar radar de ingresos")
        return 1
    leg = json.loads(LEG_PATH.read_text(encoding="utf-8"))
    ses = json.loads(SES_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []

    radar = leg.get("radar_ingresos") or {}
    rows = radar.get("expedientes") or []
    if radar.get("schema") != 1:
        problems.append("radar_ingresos.schema debe ser 1")
    limit = int(radar.get("limite_solicitado") or 0)
    if limit < 100:
        problems.append("limite_solicitado demasiado bajo")
    if not rows:
        problems.append("radar sin expedientes")
    if len(rows) > limit:
        problems.append("radar devuelve más expedientes que el límite solicitado")
    if limit >= 100 and len(rows) < 100:
        problems.append(f"radar devolvió sólo {len(rows)} expedientes; esperado al menos 100")

    agenda_ids, agenda_nums = set(), set()
    for p in leg.get("expedientes") or []:
        eid = id_from_url(p.get("url_expediente"))
        num = norm_num(p.get("numero"))
        if eid:
            agenda_ids.add(eid)
        if num:
            agenda_nums.add(num)

    recinto_ids, recinto_nums = set(), set()
    for s in ses.get("sesiones") or []:
        for item in (s.get("asuntos_considerados") or []) + (s.get("sanciones") or []):
            eid = clean(item.get("id_expediente"))
            num = norm_num(item.get("numero_expediente"))
            if eid:
                recinto_ids.add(eid)
            if num:
                recinto_nums.add(num)
        for vote in s.get("votaciones_nominales") or []:
            basic = vote.get("expediente") or {}
            eid = clean(vote.get("id_expediente") or basic.get("id_expediente"))
            num = norm_num(basic.get("numero"))
            if eid:
                recinto_ids.add(eid)
            if num:
                recinto_nums.add(num)

    ids = Counter(clean(x.get("id_expediente")) for x in rows)
    nums = Counter(norm_num(x.get("numero")) for x in rows if norm_num(x.get("numero")))
    dup_ids = [x for x, n in ids.items() if x and n > 1]
    dup_nums = [x for x, n in nums.items() if x and n > 1]
    if dup_ids:
        problems.append("ids duplicados: " + ", ".join(dup_ids[:10]))
    if dup_nums:
        problems.append("números duplicados: " + ", ".join(dup_nums[:10]))

    with_basics = outside_agenda = outside_both = laws_outside = high_outside = 0
    dates = []
    today = dt.date.today()
    for row in rows:
        eid = clean(row.get("id_expediente"))
        num = norm_num(row.get("numero"))
        if not re.fullmatch(r"\d+", eid):
            problems.append(f"id_expediente inválido: {eid!r}")
            continue
        url = clean(row.get("url_expediente"))
        if urlparse(url).hostname != OFFICIAL_HOST or id_from_url(url) != eid:
            problems.append(f"{num or eid}: URL oficial inconsistente")
        if not num or not re.fullmatch(r"\d+-[A-ZÁÉÍÓÚÜÑ]+-\d{4}", num, re.I):
            problems.append(f"{eid}: número de expediente inválido {num!r}")
        raw_date = clean(row.get("fecha_ingreso"))
        try:
            d = dt.datetime.fromisoformat(raw_date).date() if "T" in raw_date else dt.date.fromisoformat(raw_date)
            dates.append(d)
            if d > today:
                problems.append(f"{num}: fecha de ingreso futura")
        except Exception:
            problems.append(f"{num or eid}: fecha_ingreso inválida")

        in_agenda = eid in agenda_ids or num in agenda_nums
        in_recinto = eid in recinto_ids or num in recinto_nums
        if bool(row.get("en_agenda_retenida")) != bool(in_agenda):
            problems.append(f"{num}: en_agenda_retenida inconsistente")
        if bool(row.get("en_recinto_2026")) != bool(in_recinto):
            problems.append(f"{num}: en_recinto_2026 inconsistente")

        has_basic = bool(row.get("tipo_oficial") or row.get("sumario") or row.get("origen"))
        with_basics += int(has_basic)
        outside_agenda += int(not in_agenda)
        outside_both += int(not in_agenda and not in_recinto)
        laws_outside += int(not in_agenda and row.get("tipo_oficial") == "LEY")
        high_outside += int(not in_agenda and row.get("prioridad_tecnica") == "alta")

        if row.get("prioridad_tecnica") not in {"alta", "media", "baja"}:
            problems.append(f"{num}: prioridad_tecnica inválida")
        if not isinstance(row.get("temas"), list):
            problems.append(f"{num}: temas debe ser lista")

    if rows and with_basics / len(rows) < 0.95:
        problems.append(f"sólo {with_basics}/{len(rows)} expedientes con datos básicos")
    if dates and max(dates) < today - dt.timedelta(days=7):
        problems.append("el expediente más reciente del radar tiene más de 7 días")

    summary = leg.get("resumen") or {}
    expected = {
        "radar_ultimos_expedientes": len(rows),
        "radar_con_datos_basicos": with_basics,
        "radar_fuera_agenda_retenida": outside_agenda,
        "radar_fuera_agenda_y_recinto": outside_both,
        "radar_leyes_fuera_agenda": laws_outside,
        "radar_prioridad_alta_fuera_agenda": high_outside,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            problems.append(f"resumen.{key}={summary.get(key)!r}; esperado {value!r}")

    forbidden = sorted(set(walk_keys(radar)) & PRIVATE_KEYS)
    if forbidden:
        problems.append("campos privados en radar público: " + ", ".join(forbidden))

    print(
        f"Radar ingresos · {len(rows)} expedientes · {with_basics} con datos básicos · "
        f"{outside_agenda} fuera de agenda retenida · {outside_both} fuera también de recinto"
    )
    print(f"  leyes fuera de agenda: {laws_outside} · prioridad técnica alta fuera de agenda: {high_outside}")
    if dates:
        print(f"  ventana efectiva: {min(dates).isoformat()} → {max(dates).isoformat()}")

    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for p in problems[:80]:
            print("   ·", p)
        return 1
    print("✔ verificación de universo temprano superada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
