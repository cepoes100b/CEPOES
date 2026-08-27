#!/usr/bin/env python3
"""Construye `universo_consolidado` por expediente sin alterar la capa de agendas."""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from actualizar_legislatura import classify_project

LEG_PATH = Path("legislatura_publica.json")
SES_PATH = Path("sesiones_publicas.json")


def clean(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def norm_num(v) -> str:
    return re.sub(r"\s+", "", clean(v).upper())


def eid_from_url(url) -> str:
    try:
        return clean((parse_qs(urlparse(url or "").query).get("id") or [""])[0])
    except Exception:
        return ""


def key_for(p: dict) -> str:
    eid = clean(p.get("id_expediente") or p.get("expediente_id") or eid_from_url(p.get("url_expediente")))
    if eid:
        return f"id:{eid}"
    num = norm_num(p.get("numero") or p.get("numero_expediente"))
    return f"num:{num}" if num else ""


def merge_scalar(dst: dict, src: dict, field: str) -> None:
    value = src.get(field)
    if value not in (None, "", [], {}):
        if dst.get(field) in (None, "", [], {}):
            dst[field] = value


def merge_list(dst: dict, field: str, values) -> None:
    values = values if isinstance(values, list) else ([values] if values else [])
    current = list(dst.get(field) or [])
    seen = {json.dumps(x, ensure_ascii=False, sort_keys=True) for x in current}
    for value in values:
        marker = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if marker not in seen:
            current.append(value)
            seen.add(marker)
    dst[field] = current


def touch_source(dst: dict, source: str) -> None:
    merge_list(dst, "fuentes_captura", [source])


def ensure_row(store: dict, source: dict) -> dict | None:
    key = key_for(source)
    if not key:
        return None
    if key not in store:
        eid = clean(source.get("id_expediente") or source.get("expediente_id") or eid_from_url(source.get("url_expediente")))
        numero = norm_num(source.get("numero") or source.get("numero_expediente"))
        store[key] = {
            "clave_consolidada": key,
            "id_expediente": eid or None,
            "numero": numero or None,
            "fuentes_captura": [],
            "apariciones_agenda": [],
            "comisiones": [],
            "fechas_reunion": [],
            "actividad_recinto": [],
        }
    return store[key]


def ingest_agenda(store: dict, p: dict) -> None:
    dst = ensure_row(store, p)
    if dst is None:
        return
    touch_source(dst, "agenda")
    for f in (
        "numero", "sumario", "autor", "url_expediente", "documento",
        "prioridad_tecnica", "tipo_estimado", "tipo_oficial", "temas",
        "estado_actual", "etapa_ciclo", "etapa", "fecha_inicio",
        "ultimo_movimiento", "ficha_oficial",
    ):
        merge_scalar(dst, p, f)
    if p.get("comision"):
        merge_list(dst, "comisiones", [p["comision"]])
    if p.get("fecha_reunion"):
        merge_list(dst, "fechas_reunion", [p["fecha_reunion"]])
    merge_list(dst, "apariciones_agenda", [{
        "comision": p.get("comision"),
        "fecha": p.get("fecha_reunion"),
        "tipo_reunion": p.get("tipo_reunion"),
        "url_reunion": p.get("url_reunion"),
    }])


def ingest_radar(store: dict, p: dict) -> None:
    dst = ensure_row(store, p)
    if dst is None:
        return
    touch_source(dst, "radar_ingresos")
    for f in (
        "numero", "fecha_ingreso", "autor", "sumario", "tipo_oficial",
        "tipo_estimado", "origen", "ubicacion_reportada", "temas",
        "prioridad_tecnica", "url_expediente", "documento",
    ):
        merge_scalar(dst, p, f)


def ingest_institutional(store: dict, p: dict) -> None:
    dst = ensure_row(store, p)
    if dst is None:
        return
    touch_source(dst, "seguimiento_institucional")
    dst["seguimiento_institucional"] = True
    for f in (
        "numero", "fecha_ingreso", "autor_reportado", "autores", "rol_claudia",
        "sumario", "tipo_oficial", "origen", "ubicacion", "url_expediente",
        "documento", "persona_seguida",
    ):
        merge_scalar(dst, p, f)


def ingest_recinto(store: dict, sessions: dict) -> None:
    for ses in sessions.get("sesiones") or []:
        fecha = ses.get("fecha") or ses.get("fecha_sesion")
        for bucket, kind in (
            ("asuntos_considerados", "asunto"),
            ("sanciones", "sancion"),
            ("votaciones_nominales", "votacion"),
        ):
            for item in ses.get(bucket) or []:
                basic = item.get("expediente") or {}
                source = {
                    "id_expediente": item.get("id_expediente") or basic.get("id_expediente"),
                    "numero": item.get("numero_expediente") or basic.get("numero"),
                }
                dst = ensure_row(store, source)
                if dst is None:
                    continue
                touch_source(dst, "recinto")
                merge_list(dst, "actividad_recinto", [{
                    "fecha": fecha,
                    "tipo": kind,
                    "descripcion": item.get("descripcion") or item.get("asunto") or item.get("tipo"),
                }])


def finalize(row: dict) -> dict:
    # Ficha oficial enriquecida tiene prioridad para autores, estado, giros y tipo.
    ficha = row.get("ficha_oficial") or {}
    if ficha:
        if ficha.get("autores"):
            row["autores"] = ficha["autores"]
        if ficha.get("giros"):
            row["giros"] = ficha["giros"]
        for src, dst in (
            ("tipo_proyecto", "tipo_oficial"),
            ("fecha_inicio", "fecha_inicio"),
            ("ubicacion", "ubicacion"),
            ("estado_actual", "estado_actual"),
            ("etapa_ciclo", "etapa_ciclo"),
            ("ultimo_movimiento", "ultimo_movimiento"),
        ):
            if ficha.get(src) not in (None, "", [], {}):
                row[dst] = ficha[src]

    # Compatibilidad con la UI existente.
    if not row.get("comision"):
        row["comision"] = " · ".join(row.get("comisiones") or row.get("giros") or []) or None
    dates = []
    for value in (
        *(row.get("fechas_reunion") or []),
        row.get("fecha_ingreso"),
        row.get("fecha_inicio"),
        (row.get("ultimo_movimiento") or {}).get("fecha") if isinstance(row.get("ultimo_movimiento"), dict) else None,
    ):
        if value:
            dates.append(str(value)[:10])
    for item in row.get("actividad_recinto") or []:
        if item.get("fecha"):
            dates.append(str(item["fecha"])[:10])
    row["fecha_ultima_actividad"] = max(dates) if dates else None
    row["fecha_reunion"] = max(row.get("fechas_reunion") or []) if row.get("fechas_reunion") else (row.get("fecha_ingreso") or row.get("fecha_inicio"))

    if not row.get("temas") or not row.get("prioridad_tecnica"):
        estimated_type, topics, priority = classify_project(row.get("numero") or "", row.get("sumario") or "")
        row.setdefault("tipo_estimado", estimated_type)
        if not row.get("temas"):
            row["temas"] = topics
        if not row.get("prioridad_tecnica"):
            row["prioridad_tecnica"] = priority

    return row


def main() -> int:
    if not LEG_PATH.exists() or not SES_PATH.exists():
        print("✘ faltan archivos legislativos")
        return 1
    leg = json.loads(LEG_PATH.read_text(encoding="utf-8"))
    ses = json.loads(SES_PATH.read_text(encoding="utf-8"))

    store: dict[str, dict] = {}
    for p in leg.get("expedientes") or []:
        ingest_agenda(store, p)
    for p in (leg.get("radar_ingresos") or {}).get("expedientes") or []:
        ingest_radar(store, p)
    for p in (leg.get("seguimiento_institucional") or {}).get("expedientes") or []:
        ingest_institutional(store, p)
    ingest_recinto(store, ses)

    rows = [finalize(x) for x in store.values()]
    rows.sort(
        key=lambda p: (
            p.get("fecha_ultima_actividad") or "",
            int(p.get("id_expediente") or 0) if str(p.get("id_expediente") or "").isdigit() else 0,
        ),
        reverse=True,
    )

    leg["universo_consolidado"] = {
        "schema": 1,
        "actualizado": dt.datetime.now(dt.timezone.utc).isoformat(),
        "clave_primaria": "id_expediente; numero normalizado sólo como fallback",
        "criterio": "un expediente, una ficha; evidencia de agenda, ingresos, recinto y seguimiento institucional",
        "total": len(rows),
        "expedientes": rows,
    }
    summary = leg.setdefault("resumen", {})
    summary["universo_consolidado_total"] = len(rows)
    summary["universo_consolidado_agenda"] = sum("agenda" in (p.get("fuentes_captura") or []) for p in rows)
    summary["universo_consolidado_radar"] = sum("radar_ingresos" in (p.get("fuentes_captura") or []) for p in rows)
    summary["universo_consolidado_recinto"] = sum("recinto" in (p.get("fuentes_captura") or []) for p in rows)
    summary["universo_consolidado_claudia"] = sum(bool(p.get("seguimiento_institucional")) for p in rows)

    LEG_PATH.write_text(json.dumps(leg, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Universo consolidado · {len(rows)} expedientes · "
        f"agenda {summary['universo_consolidado_agenda']} · "
        f"radar {summary['universo_consolidado_radar']} · "
        f"recinto {summary['universo_consolidado_recinto']} · "
        f"Claudia {summary['universo_consolidado_claudia']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
