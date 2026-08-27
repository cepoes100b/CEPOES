#!/usr/bin/env python3
"""Enriquece fichas consolidadas prioritarias con la ficha oficial.

Para evitar cientos de consultas repetidas, reutiliza fichas ya presentes y consulta
obligatoriamente sólo los expedientes de seguimiento institucional que aún no tengan
ficha oficial completa.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from enriquecer_expedientes import parse_official_file, norm

PATH = Path("legislatura_publica.json")


def target_is(person: str) -> bool:
    return norm(person) in {"negri claudia", "claudia negri"}


def main() -> int:
    if not PATH.exists():
        print("✘ falta legislatura_publica.json")
        return 1
    data = json.loads(PATH.read_text(encoding="utf-8"))
    universe = data.get("universo_consolidado") or {}
    rows = universe.get("expedientes") or []
    if not rows:
        print("✘ universo_consolidado vacío")
        return 1

    enriched = reused = failed = 0
    for p in rows:
        ficha = p.get("ficha_oficial")
        if ficha:
            reused += 1
        elif p.get("seguimiento_institucional"):
            ficha = parse_official_file(p)
            if not ficha:
                failed += 1
                continue
            p["ficha_oficial"] = ficha
            enriched += 1
            time.sleep(0.04)
        else:
            continue

        if ficha:
            p["autores"] = ficha.get("autores") or p.get("autores") or []
            p["giros"] = ficha.get("giros") or p.get("giros") or []
            p["tipo_oficial"] = ficha.get("tipo_proyecto") or p.get("tipo_oficial")
            p["fecha_inicio"] = ficha.get("fecha_inicio") or p.get("fecha_inicio")
            p["ubicacion"] = ficha.get("ubicacion") or p.get("ubicacion")
            p["estado_actual"] = ficha.get("estado_actual") or p.get("estado_actual")
            p["etapa_ciclo"] = ficha.get("etapa_ciclo") or p.get("etapa_ciclo")
            p["ultimo_movimiento"] = ficha.get("ultimo_movimiento") or p.get("ultimo_movimiento")
            if p.get("seguimiento_institucional"):
                idx = next((i for i, name in enumerate(p["autores"]) if target_is(name)), None)
                if idx is not None:
                    p["rol_claudia"] = "autora" if idx == 0 else "coautora"

    universe["enriquecimiento"] = {
        "fichas_reutilizadas": reused,
        "fichas_institucionales_nuevas": enriched,
        "fichas_institucionales_fallidas": failed,
    }
    PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Enriquecimiento consolidado · reutilizadas {reused} · nuevas {enriched} · fallas {failed}")
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
