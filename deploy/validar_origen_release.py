#!/usr/bin/env python3
"""Distingue SHA del evento y SHA construido al ensayar un release por digest."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from encadenar_publicacion import Git, Rejected

WORKFLOW_ID = 340883917
WORKFLOW_PATH = ".github/workflows/desplegar-hostinger.yml"
WORKFLOW_NAME = "Desplegar sitio en Hostinger"


def validate_run(data: dict, *, repository: str, run_id: str, attempt: int,
                 commit: str, git: Git, main_sha: str) -> None:
    if (str(data.get("id")) != str(run_id) or data.get("run_attempt") != attempt
            or data.get("workflow_id") != WORKFLOW_ID or data.get("path") != WORKFLOW_PATH
            or data.get("name") != WORKFLOW_NAME):
        raise Rejected("Run, intento o workflow fuente no corresponde al publicador canónico")
    if data.get("status") != "completed" or data.get("conclusion") != "success":
        raise Rejected("La ejecución fuente no terminó exitosamente")
    if data.get("event") not in {"push", "workflow_dispatch", "workflow_run"} or data.get("head_branch") != "main":
        raise Rejected("Evento o rama fuente no autorizado")
    source_repo = data.get("repository") or {}
    head_repo = data.get("head_repository") or {}
    if (source_repo.get("full_name") != repository or head_repo.get("full_name") != repository
            or not source_repo.get("id") or source_repo.get("id") != head_repo.get("id")):
        raise Rejected("Origen de ejecución ajeno al repositorio")
    git.commit(commit)
    if not git.ancestor(commit, main_sha):
        raise Rejected("El SHA construido no pertenece al historial de main")
    # workflow_run.head_sha identifica el disparador. Puede preceder al SHA que
    # el preflight fijó, incluyendo commits concurrentes del productor y main.
    if not git.ancestor(str(data.get("head_sha", "")), commit):
        raise Rejected("El SHA construido no desciende de la entrada del publicador")


def validate_oci(labels: dict, *, repository: str, commit: str) -> None:
    if labels.get("org.opencontainers.image.source") != "https://github.com/" + repository:
        raise Rejected("OCI procede de otro repositorio")
    if labels.get("org.opencontainers.image.revision") != commit:
        raise Rejected("OCI no contiene el SHA construido esperado")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-json", type=Path)
    parser.add_argument("--oci-labels", type=Path)
    args = parser.parse_args()
    repository = os.environ["GITHUB_REPOSITORY"]
    commit = os.environ["SOURCE_COMMIT"]
    if args.run_json:
        git = Git(Path(__file__).resolve().parents[1])
        validate_run(json.loads(args.run_json.read_text()), repository=repository,
                     run_id=os.environ["SOURCE_RUN_ID"], attempt=int(os.environ["SOURCE_RUN_ATTEMPT"]),
                     commit=commit, git=git, main_sha=git.run("rev-parse", "refs/remotes/origin/main"))
        print("Run e intento canónicos; SHA construido validado como descendiente de la entrada y ancestro de main")
    elif args.oci_labels:
        validate_oci(json.loads(args.oci_labels.read_text()), repository=repository, commit=commit)
        print("Origen y SHA construido de OCI coinciden con el release solicitado")
    else:
        parser.error("Se requiere --run-json o --oci-labels")


if __name__ == "__main__":
    main()
