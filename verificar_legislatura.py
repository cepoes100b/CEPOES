"""Controles de integridad del núcleo público de seguimiento legislativo CEPOES."""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

BASE=Path(__file__).resolve().parent
DATA=BASE/"legislatura_publica.json"
ALLOWED={"www.legislatura.gob.ar","legislatura.gob.ar","parlamentaria.legislatura.gob.ar"}


def main()->int:
    problems=[]
    if not DATA.exists():
        print("✘ falta legislatura_publica.json"); return 1
    d=json.loads(DATA.read_text(encoding="utf-8"))
    agendas=d.get("agendas") or []; meetings=d.get("reuniones") or []; projects=d.get("expedientes") or []
    if not agendas: problems.append("no se detectaron agendas oficiales")
    if not meetings: problems.append("no se detectaron reuniones parlamentarias")
    if len({x.get('agenda_id') for x in agendas})!=len(agendas): problems.append("agenda_id duplicado")

    mkeys=[]; announced_total=0; announced_meetings=0; detail_urls=0
    for x in meetings:
        try: dt.date.fromisoformat(x.get("fecha") or "")
        except Exception: problems.append(f"fecha inválida en reunión {x.get('id')}")
        if x.get("url"):
            detail_urls+=1
            host=urlparse(x["url"]).hostname
            if host not in ALLOWED: problems.append(f"host no oficial: {host}")
        if x.get("url") and not x.get("id"):
            problems.append("reunión con URL de detalle pero sin id")
        mkeys.append(x.get("id") or (x.get("agenda_id"),x.get("comision"),x.get("hora")))
        announced=x.get("expedientes_anunciados")
        detailed=x.get("expedientes_detallados")
        if announced is not None:
            announced=int(announced or 0); announced_total+=announced
            if announced>0: announced_meetings+=1
        if announced is not None and detailed is not None and int(detailed)!=int(announced):
            problems.append(f"reunión {x.get('id')}: detallados {detailed} != anunciados {announced}")
        if announced and detailed is None:
            problems.append(f"reunión {x.get('id')}: anuncia {announced} expedientes pero no tiene conteo detallado")

    if len(set(map(str,mkeys)))!=len(mkeys): problems.append("reuniones duplicadas")
    if meetings and detail_urls==0: problems.append("ninguna reunión tiene URL de detalle")
    if announced_meetings>0 and not projects: problems.append("hay reuniones con expedientes anunciados pero se extrajeron 0 expedientes")
    if announced_total>0 and len(projects)<announced_total:
        problems.append(f"cobertura incompleta: {len(projects)} expedientes extraídos vs {announced_total} anunciados")

    for p in projects:
        if not p.get("numero") or not p.get("sumario"): problems.append("expediente sin número o sumario")
        if p.get("prioridad_tecnica") not in {"alta","media","baja"}: problems.append(f"prioridad inválida {p.get('numero')}")
        if not isinstance(p.get("temas"),list): problems.append(f"temas inválidos {p.get('numero')}")
        for key in ("fuente_reunion","url_expediente"):
            if p.get(key):
                host=urlparse(p[key]).hostname
                if host not in ALLOWED: problems.append(f"{p.get('numero')}: host no oficial en {key}: {host}")

    print(f"Núcleo legislativo · {len(agendas)} agendas · {len(meetings)} reuniones · {len(projects)} expedientes")
    print(f"  reuniones con expedientes anunciados: {announced_meetings} · anunciados acumulados: {announced_total}")
    if problems:
        print(f"✘ {len(problems)} problema(s) — NO se publica")
        for p in problems[:30]: print("  ·",p)
        return 1
    print("✔ verificación legislativa superada")
    return 0

if __name__=="__main__": raise SystemExit(main())
