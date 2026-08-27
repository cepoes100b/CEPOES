#!/usr/bin/env python3
"""Control de integridad del universo consolidado y cobertura institucional."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

PATH = Path("legislatura_publica.json")


def norm(v) -> str:
    s = unicodedata.normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def target_is(v) -> bool:
    return norm(v) in {"negri claudia", "claudia negri"}


def main() -> int:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    inst = data.get("seguimiento_institucional") or {}
    cov = inst.get("cobertura") or {}
    uni = data.get("universo_consolidado") or {}
    rows = uni.get("expedientes") or []

    errors = []
    if int(uni.get("schema") or 0) < 1:
        errors.append("universo_consolidado sin schema válido")
    if not rows:
        errors.append("universo_consolidado vacío")
    if not cov.get("completo"):
        errors.append(f"cobertura institucional incompleta: {cov.get('motivo') or cov.get('fichas_fallidas_en_corrida') or 'sin detalle'}")

    keys = [p.get("clave_consolidada") for p in rows]
    if len(keys) != len(set(keys)):
        errors.append("hay claves duplicadas en universo_consolidado")

    inst_rows = inst.get("expedientes") or []
    if not inst_rows:
        errors.append("seguimiento institucional no detectó proyectos de Claudia")

    by_id = {str(p.get("id_expediente")): p for p in rows if p.get("id_expediente")}
    missing = []
    bad_author = []
    for p in inst_rows:
        eid = str(p.get("id_expediente") or "")
        cp = by_id.get(eid)
        if not cp:
            missing.append(p.get("numero") or eid)
            continue
        authors = cp.get("autores") or []
        if not any(target_is(a) for a in authors):
            bad_author.append(p.get("numero") or eid)
        if cp.get("rol_claudia") not in {"autora", "coautora"}:
            errors.append(f"rol de Claudia ausente/incorrecto: {p.get('numero') or eid}")

    if missing:
        errors.append("proyectos institucionales ausentes del consolidado: " + ", ".join(map(str, missing[:20])))
    if bad_author:
        errors.append("autoría/coautoría no confirmada tras enriquecer: " + ", ".join(map(str, bad_author[:20])))

    if errors:
        print(f"✘ {len(errors)} problema(s) en universo consolidado")
        for e in errors:
            print("  ·", e)
        return 1

    print(
        f"✓ universo consolidado válido · {len(rows)} expedientes · "
        f"{len(inst_rows)} con seguimiento institucional Claudia · cobertura {cov.get('anio')} completa"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
