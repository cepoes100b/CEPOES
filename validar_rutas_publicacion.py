#!/usr/bin/env python3
"""Exige que sólo el publicador canónico pueda escribir en producción."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKFLOWS = ROOT / ".github" / "workflows"
CANONICAL = WORKFLOWS / "desplegar-hostinger.yml"

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

    print(
        "Rutas de publicación R2-A3: 1 publicador canónico; "
        "sin escritores laterales"
    )


if __name__ == "__main__":
    main()
