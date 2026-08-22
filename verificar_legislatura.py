"""Controles de integridad del núcleo público de seguimiento legislativo CEPOES."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
DATA = BASE / "legislatura_publica.json"
ALLOWED_HOSTS = {"www.legislatura.gob.ar", "legislatura.gob.ar", "parlamentaria.legislatura.gob.ar"}
ALLOWED_TYPES = {"asesores", "diputados", "audiencia_publica", "especial"}
EXCLUDED_PREFIXES = ("direccion general", "programa la legislatura")


def official_url(url: str | None) -> bool:
    return bool(url) and urlparse(url).hostname in ALLOWED_HOSTS


def norm(value: object) -> str:
    import re, unicodedata
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    problems: list[str] = []
    if not DATA.exists():
        print("✘ falta legislatura_publica.json")
        return 1

    d = json.loads(DATA.read_text(encoding="utf-8"))
    agendas = d.get("agendas") or []
    meetings = d.get("reuniones") or []
    projects = d.get("expedientes") or []

    if not agendas:
        problems.append("no se detectaron agendas oficiales")
    if not meetings:
        problems.append("no se detectaron reuniones parlamentarias")
    if len({x.get("agenda_id") for x in agendas}) != len(agendas):
        problems.append("agenda_id duplicado")

    meeting_ids: set[int] = set()
    announced_total = 0
    announced_meetings = 0
    for x in meetings:
        mid = x.get("id")
        if not mid:
            problems.append(f"reunión sin id: agenda {x.get('agenda_id')} · {x.get('comision')}")
        elif mid in meeting_ids:
            problems.append(f"reunión id duplicado: {mid}")
        else:
            meeting_ids.add(mid)

        try:
            dt.date.fromisoformat(x.get("fecha") or "")
        except Exception:
            problems.append(f"fecha inválida en reunión {mid}")

        if not official_url(x.get("url")):
            problems.append(f"reunión {mid}: URL ausente o no oficial")
        if x.get("detalle_disponible") is not True:
            problems.append(f"reunión {mid}: detalle oficial no disponible")

        name = norm(x.get("comision"))
        if not name or name == "sin identificar":
            problems.append(f"reunión {mid}: comisión/organismo sin identificar")
        if name.startswith(EXCLUDED_PREFIXES):
            problems.append(f"reunión {mid}: evento administrativo/protocolario incluido: {x.get('comision')}")

        kind = x.get("tipo_reunion")
        if kind not in ALLOWED_TYPES:
            problems.append(f"reunión {mid}: tipo no parlamentario o inválido: {kind}")
        if kind == "especial" and "labor parlamentaria" not in name:
            problems.append(f"reunión {mid}: reunión especial no identificada como Labor Parlamentaria")

        announced = int(x.get("expedientes_anunciados") or 0)
        detailed = x.get("expedientes_detallados")
        announced_total += announced
        if announced > 0:
            announced_meetings += 1
        if detailed is None:
            problems.append(f"reunión {mid}: falta conteo de expedientes detallados")
        elif int(detailed) != announced:
            problems.append(f"reunión {mid}: detallados {detailed} != anunciados {announced}")

    if announced_meetings > 0 and not projects:
        problems.append("hay reuniones con expedientes anunciados pero se extrajeron 0 expedientes")
    if announced_total != len(projects):
        problems.append(f"cobertura inconsistente: {len(projects)} expedientes extraídos vs {announced_total} anunciados")

    project_keys = set()
    for p in projects:
        number = p.get("numero")
        rid = p.get("reunion_id")
        key = (number, rid, p.get("fecha_reunion"))
        if key in project_keys:
            problems.append(f"expediente duplicado en la misma reunión: {number} / {rid}")
        project_keys.add(key)
        if not number or not p.get("sumario"):
            problems.append("expediente sin número o sumario")
        if rid not in meeting_ids:
            problems.append(f"{number}: reunion_id {rid} no existe en reuniones")
        if p.get("prioridad_tecnica") not in {"alta", "media", "baja"}:
            problems.append(f"prioridad inválida {number}")
        if not isinstance(p.get("temas"), list):
            problems.append(f"temas inválidos {number}")
        if not official_url(p.get("fuente_reunion")):
            problems.append(f"{number}: fuente_reunion ausente o no oficial")
        if p.get("url_expediente") and not official_url(p.get("url_expediente")):
            problems.append(f"{number}: url_expediente no oficial")

    summary = d.get("resumen") or {}
    if summary.get("reuniones_parlamentarias") is not None and int(summary["reuniones_parlamentarias"]) != len(meetings):
        problems.append("resumen.reuniones_parlamentarias no coincide con el detalle")
    if summary.get("expedientes_en_reuniones") is not None and int(summary["expedientes_en_reuniones"]) != len(projects):
        problems.append("resumen.expedientes_en_reuniones no coincide con el detalle")

    print(f"Núcleo legislativo · {len(agendas)} agendas · {len(meetings)} reuniones parlamentarias · {len(projects)} expedientes")
    print(f"  reuniones con expedientes anunciados: {announced_meetings} · anunciados acumulados: {announced_total}")
    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for problem in problems[:40]:
            print("  ·", problem)
        return 1
    print("✔ verificación legislativa superada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
