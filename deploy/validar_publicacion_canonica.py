#!/usr/bin/env python3
"""Valida las salidas incorporadas al publicador canónico R2-A3."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


BRIDGE_PATTERN = re.compile(
    r'<script\b[^>]*src=["\']/assets/legislatura-public-bridge\.js'
    r'(?:\?[^"\']*)?["\'][^>]*></script>',
    flags=re.I,
)


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text)).strip()


def validate_health(site: Path) -> None:
    path = site / "observatorio" / "index.html"
    source = path.read_text(encoding="utf-8")
    required = [
        'id="observatorio-salud-cuidados"',
        ">Salud mental<",
        ">Natalidad y demografía<",
        ">Salud reproductiva<",
        ">Personas mayores<",
        '/observatorio/#observatorio-salud-cuidados">Salud</a>',
    ]
    missing = [token for token in required if token not in source]
    assert not missing, f"Observatorio sin contrato Salud: {missing}"
    assert source.count('id="observatorio-salud-cuidados"') == 1, "Hub Salud duplicado"
    assert source.count('id="observatorio-health-hub-style"') == 1, "CSS Salud duplicado"


def validate_bridge(site: Path) -> None:
    asset = site / "assets" / "legislatura-public-bridge.js"
    assert asset.is_file(), "Falta el puente legislativo"
    assert "__CEPOES_LEGISLATURA_PUBLIC_BRIDGE__" in asset.read_text(encoding="utf-8")
    pages = sorted((site / "legislatura").rglob("*.html"))
    assert pages, "No hay HTML legislativos"
    for path in pages:
        source = path.read_text(encoding="utf-8")
        assert len(BRIDGE_PATTERN.findall(source)) == 1, (
            f"Puente legislativo ausente o duplicado: {path.relative_to(site)}"
        )


def validate_legislative_json(site: Path) -> None:
    legislation_path = site / "legislatura_publica.json"
    sessions_path = site / "sesiones_publicas.json"
    legislation = json.loads(legislation_path.read_text(encoding="utf-8"))
    sessions = json.loads(sessions_path.read_text(encoding="utf-8"))

    rows = legislation.get("expedientes") or []
    expected = int((legislation.get("universo_consolidado") or {}).get("total") or 0)
    assert expected >= 1000 and len(rows) == expected, (
        f"Universo legislativo inválido: total={expected} filas={len(rows)}"
    )
    claudia = [row for row in rows if "claudia negri" in norm(row.get("autor")) or "negri claudia" in norm(row.get("autor"))]
    assert len(claudia) >= 200, f"Cobertura Claudia insuficiente: {len(claudia)}"
    assert any(
        "832" in str(row.get("numero") or "")
        and ("2026" in str(row.get("numero") or "") or "26" in str(row.get("numero") or ""))
        for row in rows
    ), "832-D-2026 ausente"
    assert isinstance(sessions, (dict, list)) and bool(sessions), "Sesiones públicas vacías"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    assert site.is_dir(), site
    validate_health(site)
    validate_bridge(site)
    validate_legislative_json(site)
    print("Publicación canónica R2-A3: Salud, puente y JSON legislativos válidos")


if __name__ == "__main__":
    main()
