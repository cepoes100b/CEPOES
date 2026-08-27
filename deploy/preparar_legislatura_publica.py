#!/usr/bin/env python3
"""Prepara la copia pública del núcleo legislativo para Hostinger.

La capa interna conserva:
  legislatura_publica.json["expedientes"] = expedientes asociados a agendas

La copia pública usa:
  legislatura_publica.json["expedientes"] = universo_consolidado.expedientes

Esto mantiene compatibilidad con el frontend existente de /legislatura/
sin degradar el modelo interno ni perder la trazabilidad de agenda.

También normaliza `autor` para que los filtros existentes encuentren tanto
autorías principales como coautorías.
"""
from __future__ import annotations

import copy
import json
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEG = ROOT / "legislatura_publica.json"
SES = ROOT / "sesiones_publicas.json"


def norm(value) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    # La fuente oficial publica autores como "APELLIDO, NOMBRE".
    # Quitamos puntuación para que "NEGRI, CLAUDIA" y "Claudia Negri"
    # puedan compararse de manera estable.
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def is_claudia(value) -> bool:
    return norm(value) in {"negri claudia", "claudia negri"}


def is_832(row: dict) -> bool:
    number = re.sub(r"[^A-Z0-9]", "", str(row.get("numero") or "").upper())
    if "832" in number and ("2026" in number or number.endswith("26")):
        return True
    text = norm(" ".join([
        str(row.get("numero") or ""),
        str(row.get("sumario") or ""),
    ]))
    return "832" in text and ("peridural" in text or "analgesia" in text)


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python deploy/preparar_legislatura_publica.py <directorio_salida>")
        return 2

    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)

    if not LEG.exists() or not SES.exists():
        print("✘ faltan legislatura_publica.json o sesiones_publicas.json")
        return 1

    source = json.loads(LEG.read_text(encoding="utf-8"))
    sessions = json.loads(SES.read_text(encoding="utf-8"))

    universe = source.get("universo_consolidado") or {}
    rows = universe.get("expedientes") or []
    expected_total = int(universe.get("total") or 0)

    if expected_total < 1000 or len(rows) != expected_total:
        print(f"✘ universo consolidado inválido: total={expected_total} filas={len(rows)}")
        return 1

    # Preservar explícitamente la vieja colección para trazabilidad.
    public = copy.deepcopy(source)
    public["expedientes_agenda"] = copy.deepcopy(source.get("expedientes") or [])

    public_rows = []
    for original in rows:
        row = copy.deepcopy(original)

        authors = row.get("autores") or []
        if not isinstance(authors, list):
            authors = [authors] if authors else []

        # Compatibilidad con frontends que todavía buscan sólo p.autor.
        if authors:
            row["autor"] = " · ".join(str(x) for x in authors if x)
        elif not row.get("autor"):
            row["autor"] = row.get("autor_reportado") or ""

        # Alias conservadores para componentes viejos.
        row["etapa"] = row.get("etapa_ciclo") or row.get("etapa") or row.get("estado_actual")
        row["fecha_reunion"] = (
            row.get("fecha_ultima_actividad")
            or row.get("fecha_reunion")
            or row.get("fecha_ingreso")
            or row.get("fecha_inicio")
        )
        if not row.get("comision"):
            row["comision"] = " · ".join(
                str(x) for x in (row.get("comisiones") or row.get("giros") or []) if x
            )

        public_rows.append(row)

    # Campo legado = universo canónico para la web pública.
    public["expedientes"] = public_rows

    summary = public.setdefault("resumen", {})
    summary["expedientes_publicos_total"] = len(public_rows)
    summary["fuente_expedientes_publicos"] = "universo_consolidado"

    claudia_rows = [
        row for row in public_rows
        if any(is_claudia(a) for a in (row.get("autores") or []))
    ]
    target_832 = [row for row in public_rows if is_832(row)]

    expected_claudia = int(summary.get("universo_consolidado_claudia") or 0)

    problems = []
    if expected_claudia and len(claudia_rows) != expected_claudia:
        problems.append(
            f"Claudia: público={len(claudia_rows)} esperado={expected_claudia}"
        )
    if len(claudia_rows) < 200:
        problems.append(f"Claudia: cobertura pública demasiado baja ({len(claudia_rows)})")
    if not target_832:
        problems.append("832-D-2026 no está en expedientes públicos")
    if not all("claudia negri" in norm(row.get("autor")) or "negri claudia" in norm(row.get("autor"))
               for row in claudia_rows):
        problems.append("alguna coautoría de Claudia no quedó reflejada en el alias `autor`")

    if problems:
        print("✘ publicación legislativa inválida")
        for p in problems:
            print("  ·", p)
        return 1

    leg_out = out / "legislatura_publica.json"
    ses_out = out / "sesiones_publicas.json"

    leg_out.write_text(
        json.dumps(public, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )
    ses_out.write_text(
        json.dumps(sessions, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )

    target = target_832[0]
    print(
        f"✓ JSON público preparado · {len(public_rows)} expedientes · "
        f"Claudia {len(claudia_rows)}"
    )
    print(
        "✓ 832-D-2026 presente · "
        f"estado={target.get('estado_actual')} · "
        f"etapa={target.get('etapa_ciclo')} · "
        f"autor={target.get('autor')}"
    )
    print(f"✓ salida: {leg_out}")
    print(f"✓ salida: {ses_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
