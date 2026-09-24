#!/usr/bin/env python3
"""Exige que sólo el publicador canónico pueda escribir en producción."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKFLOWS = ROOT / ".github" / "workflows"
CANONICAL = WORKFLOWS / "desplegar-hostinger.yml"
INPUT_MANIFEST = ROOT / "deploy" / "publication-inputs.json"

TRANSITION_WRITERS = {
    "desplegar-hostinger.yml",
}

WRITER_MARKERS = (
    "HOSTINGER_SFTP_HOST",
    "HOSTINGER_REMOTE_DIR",
    "sftp://$SFTP_HOST",
    "mirror -R",
    'put -O "$REMOTE_DIR',
)

CANONICAL_TOKENS = (
    "python deploy/preparar_legislatura_publica.py _site",
    "python deploy/parche_observatorio_salud.py _site/observatorio/index.html",
    "python deploy/preparar_puente_legislatura.py _site",
    "python deploy/validar_publicacion_canonica.py _site",
)

TRIGGER_INPUTS = (
    '"legislatura_publica.json"',
    '"sesiones_publicas.json"',
    '"deploy/preparar_legislatura_publica.py"',
    '"deploy/parche_observatorio_salud.py"',
    '"deploy/preparar_puente_legislatura.py"',
    '"deploy/validar_publicacion_canonica.py"',
)


def declared_push_paths(source: str) -> list[str]:
    match = re.search(
        r'(?ms)^  push:\s*\n\s+branches:\s*\[main\]\s*\n\s+paths:\s*\n(?P<paths>(?:\s+-\s+"[^"]+"\s*\n)+)',
        source,
    )
    assert match, "No se pudo leer on.push.paths del publicador canónico"
    return re.findall(r'^\s+-\s+"([^"]+)"\s*$', match.group("paths"), re.MULTILINE)


def validate_input_manifest(canonical: str) -> None:
    manifest = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    entries = manifest.get("inputs") or []
    expected = [entry["path"] for entry in entries]
    declared = declared_push_paths(canonical)
    assert len(expected) == len(set(expected)), "El manifiesto de entradas contiene rutas duplicadas"
    assert declared == expected, (
        "on.push.paths no coincide con deploy/publication-inputs.json: "
        f"faltan={sorted(set(expected) - set(declared))}; "
        f"sobran={sorted(set(declared) - set(expected))}; "
        "también debe conservarse el orden canónico"
    )
    required = {
        "equipamientos/**",
        "legislatura_publica.json",
        "sesiones_publicas.json",
        "territorio.json",
        "presupuesto.json",
        "deploy/site-overlay/**",
    }
    assert required <= set(expected), "El manifiesto no cubre todas las fuentes públicas directas"


def validate_orchestration_contracts() -> None:
    current = (WORKFLOWS / "estructura-productiva-actual.yml").read_text(encoding="utf-8")
    structural = (WORKFLOWS / "estructura-productiva.yml").read_text(encoding="utf-8")
    retry = (WORKFLOWS / "reintentar-deploy-hostinger.yml").read_text(encoding="utf-8")

    assert "gh workflow run desplegar-hostinger.yml" not in current
    assert re.search(r"(?m)^permissions:\n  contents: write$", current)
    assert "actions: write" not in current
    assert "manifest.json" in structural and "actual.json" in current
    assert "workflow_run:" in retry and "gh run rerun \"$RUN_ID\" --failed" in retry
    assert "head_branch == 'main'" in retry
    assert "head_repository.full_name == github.repository" in retry
    assert "run_attempt < 3" in retry and "run_attempt >= 3" in retry
    assert "gh workflow run" not in retry


def main() -> None:
    writers = set()
    for path in sorted(WORKFLOWS.glob("*.yml")):
        source = path.read_text(encoding="utf-8")
        if any(marker in source for marker in WRITER_MARKERS):
            writers.add(path.name)

    assert writers == TRANSITION_WRITERS, (
        "Escritores de producción fuera de la transición R2-A3: "
        f"esperados={sorted(TRANSITION_WRITERS)} reales={sorted(writers)}"
    )

    canonical = CANONICAL.read_text(encoding="utf-8")
    for token in (*CANONICAL_TOKENS, *TRIGGER_INPUTS):
        assert token in canonical, f"Publicador canónico incompleto: {token}"
    assert canonical.count("mirror -R --verbose --parallel=2 --no-perms --no-umask _site") == 1
    validate_input_manifest(canonical)
    validate_orchestration_contracts()

    print(
        "Rutas de publicación R2-A3: 1 publicador canónico; "
        "sin escritores laterales; entradas y reintentos acotados"
    )


if __name__ == "__main__":
    main()
