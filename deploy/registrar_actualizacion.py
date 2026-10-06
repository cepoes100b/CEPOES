#!/usr/bin/env python3
"""Identidad del commit productor, conservada por git rebase (sin credenciales)."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

KEYS = {
    "workflow": "CEPOES-Producer-Workflow",
    "run_id": "CEPOES-Producer-Run",
    "attempt": "CEPOES-Producer-Attempt",
    "input_sha": "CEPOES-Producer-Input",
}


def identity(env: dict[str, str]) -> dict[str, str]:
    repository = env["GITHUB_REPOSITORY"]
    prefix = repository + "/"
    workflow_ref = env["GITHUB_WORKFLOW_REF"]
    if not workflow_ref.startswith(prefix):
        raise ValueError("Workflow ajeno al repositorio")
    path, ref = workflow_ref[len(prefix):].rsplit("@", 1)
    if not re.fullmatch(r"\.github/workflows/[a-z0-9-]+\.yml", path):
        raise ValueError("Ruta de workflow inválida")
    if not ref.startswith("refs/heads/"):
        raise ValueError("El productor debe ejecutar desde una rama")
    values = {"workflow": path, "run_id": env["GITHUB_RUN_ID"],
              "attempt": env["GITHUB_RUN_ATTEMPT"], "input_sha": env["GITHUB_SHA"]}
    for key in ("run_id", "attempt"):
        if not re.fullmatch(r"[1-9][0-9]*", values[key]):
            raise ValueError(f"{key} inválido")
    if not re.fullmatch(r"[0-9a-f]{40}", values["input_sha"]):
        raise ValueError("SHA de entrada inválido")
    return values


def trailers(values: dict[str, str]) -> str:
    return "\n".join(f"{label}: {values[key]}" for key, label in KEYS.items())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("trailers", "post-push"))
    args = parser.parse_args()
    values = identity(dict(os.environ))
    if args.command == "trailers":
        print(trailers(values))
        return
    # Sólo se llama después de git push exitoso; HEAD ya incluye cualquier rebase.
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    print("CEPOES_POST_PUSH " + json.dumps({**values, "commit_sha": sha}, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"\nCommit producido y empujado: `{sha}` · run {values['run_id']}, intento {values['attempt']}.\n")


if __name__ == "__main__":
    main()
