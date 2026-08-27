#!/usr/bin/env python3
"""Auditoría reproducible del seguimiento institucional de Claudia Negri.

Lee exclusivamente los archivos ya generados por el pipeline.
No modifica la clasificación legislativa. Produce:
- auditorias/claudia_negri_2026.json
- auditorias/claudia_negri_2026.csv

El objetivo es poder comprobar exhaustividad, autoría/coautoría, tipos,
estado actual, etapa máxima y evidencia de sanción expediente por expediente.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

LEG_PATH = Path("legislatura_publica.json")
SES_PATH = Path("sesiones_publicas.json")
OUT_DIR = Path("auditorias")
JSON_OUT = OUT_DIR / "claudia_negri_2026.json"
CSV_OUT = OUT_DIR / "claudia_negri_2026.csv"


def norm(value) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def target_is(value) -> bool:
    return norm(value) in {"negri claudia", "claudia negri"}


def normalize_number(value) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def is_832_2026(row: dict) -> bool:
    number = normalize_number(row.get("numero"))
    # Acepta 832/2026, 832-D-2026, 832-D-26, etc.
    if "832" in number and ("2026" in number or number.endswith("26")):
        return True
    text = norm(" ".join([
        str(row.get("numero") or ""),
        str(row.get("sumario") or ""),
    ]))
    return "832" in text and ("peridural" in text or "analgesia" in text)


def sanction_evidence(row: dict) -> tuple[bool, list[str]]:
    evidence = []
    ficha = row.get("ficha_oficial") or {}
    hitos = ficha.get("hitos") or {}
    if row.get("estado_actual") == "sancionado":
        evidence.append("estado_actual")
    if row.get("etapa_ciclo") == "sancionado":
        evidence.append("etapa_ciclo")
    if hitos.get("tuvo_sancion"):
        evidence.append("ficha_oficial.hitos.tuvo_sancion")
    if ficha.get("sanciones"):
        evidence.append("ficha_oficial.sanciones")
    for item in row.get("actividad_recinto") or []:
        if norm(item.get("tipo")) == "sancion":
            evidence.append("actividad_recinto")
            break
    return bool(evidence), evidence


def main() -> int:
    if not LEG_PATH.exists():
        print("✘ falta legislatura_publica.json")
        return 1
    if not SES_PATH.exists():
        print("✘ falta sesiones_publicas.json")
        return 1

    leg = json.loads(LEG_PATH.read_text(encoding="utf-8"))
    ses = json.loads(SES_PATH.read_text(encoding="utf-8"))
    inst = leg.get("seguimiento_institucional") or {}
    universe = leg.get("universo_consolidado") or {}
    inst_rows = inst.get("expedientes") or []
    uni_rows = universe.get("expedientes") or []

    by_id = {
        str(row.get("id_expediente")): row
        for row in uni_rows
        if row.get("id_expediente")
    }

    audit_rows = []
    problems = []
    for src in inst_rows:
        eid = str(src.get("id_expediente") or "")
        row = by_id.get(eid)
        if not row:
            problems.append(f"ausente_en_consolidado:{src.get('numero') or eid}")
            continue

        authors = row.get("autores") or (row.get("ficha_oficial") or {}).get("autores") or []
        target_positions = [i for i, a in enumerate(authors) if target_is(a)]
        author_confirmed = bool(target_positions)
        inferred_role = (
            "autora" if target_positions and target_positions[0] == 0
            else "coautora" if target_positions
            else None
        )
        declared_role = row.get("rol_claudia") or src.get("rol_claudia")
        role_consistent = inferred_role == declared_role if inferred_role else False
        ficha = row.get("ficha_oficial") or {}
        has_sanction, sanction_sources = sanction_evidence(row)

        if not author_confirmed:
            problems.append(f"claudia_no_confirmada:{row.get('numero') or eid}")
        if not role_consistent:
            problems.append(f"rol_inconsistente:{row.get('numero') or eid}")

        audit_rows.append({
            "id_expediente": eid,
            "numero": row.get("numero"),
            "fecha_ingreso": row.get("fecha_ingreso") or row.get("fecha_inicio"),
            "sumario": row.get("sumario"),
            "rol_claudia": declared_role,
            "rol_recalculado": inferred_role,
            "autoría_confirmada": author_confirmed,
            "rol_consistente": role_consistent,
            "autores": authors,
            "cantidad_autores": len(authors),
            "tipo_oficial": row.get("tipo_oficial") or ficha.get("tipo_proyecto"),
            "estado_actual": row.get("estado_actual") or ficha.get("estado_actual"),
            "etapa_ciclo": row.get("etapa_ciclo") or ficha.get("etapa_ciclo"),
            "ubicacion": row.get("ubicacion") or ficha.get("ubicacion"),
            "giros": row.get("giros") or ficha.get("giros") or [],
            "ultimo_movimiento": row.get("ultimo_movimiento") or ficha.get("ultimo_movimiento"),
            "evidencia_sancion": has_sanction,
            "fuentes_sancion": sanction_sources,
            "fuentes_captura": row.get("fuentes_captura") or [],
            "ficha_oficial_completa": bool(ficha),
            "url_expediente": row.get("url_expediente") or ficha.get("url"),
            "es_832_2026": is_832_2026(row),
        })

    audit_rows.sort(
        key=lambda r: (r.get("fecha_ingreso") or "", int(r["id_expediente"]) if r["id_expediente"].isdigit() else 0),
        reverse=True
    )

    roles = Counter(r.get("rol_claudia") or "sin_rol" for r in audit_rows)
    types = Counter(r.get("tipo_oficial") or "SIN_TIPO" for r in audit_rows)
    states = Counter(r.get("estado_actual") or "sin_estado" for r in audit_rows)
    stages = Counter(r.get("etapa_ciclo") or "sin_etapa" for r in audit_rows)

    # Estado de la sesión más reciente para diagnosticar latencia del día.
    sessions = ses.get("sesiones") or []
    latest = max(sessions, key=lambda x: str(x.get("fecha") or ""), default={})
    latest_session = {
        "id_sesion": latest.get("id_sesion"),
        "fecha": latest.get("fecha"),
        "realizada": latest.get("realizada"),
        "asuntos_considerados": len(latest.get("asuntos_considerados") or []),
        "sanciones": len(latest.get("sanciones") or []),
        "votaciones_nominales": len(latest.get("votaciones_nominales") or []),
        "version_taquigrafica_disponible": bool((latest.get("documentos") or {}).get("version_taquigrafica")),
    }

    matches_832 = [r for r in audit_rows if r["es_832_2026"]]
    coverage = inst.get("cobertura") or {}
    confirmed = (
        bool(coverage.get("completo"))
        and len(audit_rows) == len(inst_rows)
        and all(r["autoría_confirmada"] and r["rol_consistente"] for r in audit_rows)
        and not problems
    )

    report = {
        "schema": 1,
        "generado_en": dt.datetime.now(dt.timezone.utc).isoformat(),
        "persona": "Claudia Negri",
        "anio": int(coverage.get("anio") or 2026),
        "auditoria_confirmada": confirmed,
        "criterio_confirmacion": (
            "cobertura temporal completa + presencia en universo consolidado + "
            "Claudia confirmada en Autor / Coautores + rol consistente"
        ),
        "cobertura": coverage,
        "resumen": {
            "expedientes_seguimiento_institucional": len(inst_rows),
            "expedientes_auditados": len(audit_rows),
            "autoría_principal": roles.get("autora", 0),
            "coautoría": roles.get("coautora", 0),
            "fichas_oficiales_completas": sum(r["ficha_oficial_completa"] for r in audit_rows),
            "con_evidencia_sancion": sum(r["evidencia_sancion"] for r in audit_rows),
            "problemas": len(problems),
        },
        "por_tipo": dict(sorted(types.items(), key=lambda x: (-x[1], x[0]))),
        "por_estado_actual": dict(sorted(states.items(), key=lambda x: (-x[1], x[0]))),
        "por_etapa_ciclo": dict(sorted(stages.items(), key=lambda x: (-x[1], x[0]))),
        "control_832_2026": {
            "encontrados": len(matches_832),
            "expedientes": matches_832,
        },
        "ultima_sesion_detectada": latest_session,
        "problemas": problems,
        "expedientes": audit_rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fields = [
        "id_expediente","numero","fecha_ingreso","sumario","rol_claudia","rol_recalculado",
        "autoría_confirmada","rol_consistente","cantidad_autores","autores","tipo_oficial",
        "estado_actual","etapa_ciclo","ubicacion","giros","ultimo_movimiento",
        "evidencia_sancion","fuentes_sancion","fuentes_captura","ficha_oficial_completa",
        "url_expediente","es_832_2026"
    ]
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in audit_rows:
            flat = dict(row)
            for key in ("autores","giros","fuentes_sancion","fuentes_captura"):
                flat[key] = " | ".join(map(str, flat.get(key) or []))
            if isinstance(flat.get("ultimo_movimiento"), dict):
                flat["ultimo_movimiento"] = json.dumps(flat["ultimo_movimiento"], ensure_ascii=False)
            writer.writerow({k: flat.get(k) for k in fields})

    print("Auditoría Claudia Negri 2026")
    print(f"  cobertura completa: {bool(coverage.get('completo'))}")
    print(f"  auditados: {len(audit_rows)}/{len(inst_rows)}")
    print(f"  autoría principal: {roles.get('autora',0)} · coautoría: {roles.get('coautora',0)}")
    print(f"  fichas oficiales completas: {sum(r['ficha_oficial_completa'] for r in audit_rows)}")
    print(f"  con evidencia de sanción: {sum(r['evidencia_sancion'] for r in audit_rows)}")
    print(f"  832/2026 detectado: {len(matches_832)}")
    for r in matches_832:
        print(
            f"    {r.get('numero')} · rol {r.get('rol_claudia')} · "
            f"estado {r.get('estado_actual')} · etapa {r.get('etapa_ciclo')} · "
            f"sanción={r.get('evidencia_sancion')}"
        )
    print(
        f"  última sesión {latest_session.get('fecha')} (ID {latest_session.get('id_sesion')}): "
        f"asuntos {latest_session.get('asuntos_considerados')} · "
        f"sanciones {latest_session.get('sanciones')} · "
        f"votaciones {latest_session.get('votaciones_nominales')}"
    )
    if problems:
        print(f"✘ {len(problems)} problema(s)")
        for p in problems[:30]:
            print("  ·", p)
        return 1
    if not confirmed:
        print("✘ la auditoría no alcanza criterio de confirmación")
        return 2

    print("✓ inventario institucional confirmado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
