#!/usr/bin/env python3
"""Autoriza un SHA exacto de main desde eventos confiables, sin secretos ni API Actions."""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import time
from pathlib import Path

from evidencia_publicacion import MARKER_PATH, fetch_marker, validate_marker, verify_online
from registrar_actualizacion import KEYS

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"[0-9a-f]{40}")


class Rejected(ValueError):
    """El evento o historial no satisface el contrato fail-closed."""


class Git:
    def __init__(self, root: Path):
        self.root = root

    def run(self, *args: str, input: str | None = None) -> str:
        result = subprocess.run(["git", *args], cwd=self.root, input=input, text=True,
                                capture_output=True, check=False)
        if result.returncode:
            raise Rejected(f"No se pudo verificar el historial Git ({args[0]})")
        return result.stdout.strip()

    def commit(self, value: str) -> str:
        if not SHA.fullmatch(value):
            raise Rejected("SHA inválido")
        self.run("cat-file", "-e", value + "^{commit}")
        return value

    def ancestor(self, older: str, newer: str) -> bool:
        self.commit(older)
        self.commit(newer)
        result = subprocess.run(["git", "merge-base", "--is-ancestor", older, newer],
                                cwd=self.root, capture_output=True)
        if result.returncode not in (0, 1):
            raise Rejected("No se pudo verificar ancestría")
        return result.returncode == 0

    def changed(self, older: str, newer: str) -> list[str]:
        return self.run("diff", "--name-only", older, newer, "--").splitlines()

    def trailers(self, commit: str) -> dict[str, list[str]]:
        body = self.run("show", "-s", "--format=%B", commit)
        parsed = self.run("interpret-trailers", "--parse", input=body + "\n")
        values: dict[str, list[str]] = {}
        for line in parsed.splitlines():
            key, _, value = line.partition(":")
            values.setdefault(key.lower(), []).append(value.strip())
        return values


def publication_changes(paths: list[str], patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for path in paths for pattern in patterns)


def same_repository(data: dict, repository: str, repository_id: int) -> bool:
    return (isinstance(data, dict) and data.get("full_name") == repository
            and type(data.get("id")) is int and data["id"] == repository_id)


def positive_integer(value: object) -> bool:
    return type(value) is int and value > 0


def select_candidate(git: Git, event_name: str, event: dict, github_sha: str,
                     repository: str, repository_id: int, registry: dict,
                     patterns: list[str], main_sha: str, github_ref: str | None = None) -> dict:
    if registry["repository"] != repository or not same_repository(event.get("repository"), repository, repository_id):
        raise Rejected("Repositorio del evento no autorizado")
    git.commit(main_sha)
    result = {"deploy_sha": main_sha, "should_deploy": "true", "producer_sha": "", "reason": "main-validado"}
    if event_name == "workflow_run":
        run = event.get("workflow_run") or {}
        allowed = {item["id"]: item for item in registry["workflows"]}
        definition = allowed.get(run.get("workflow_id"))
        if event.get("action") != "completed" or run.get("status") != "completed" or run.get("conclusion") != "success":
            raise Rejected("El actualizador no terminó exitosamente")
        if not definition or type(run.get("workflow_id")) is not int:
            raise Rejected("ID del workflow fuera de la lista fija")
        if run.get("name") != definition["name"] or run.get("path") != definition["path"]:
            raise Rejected("Nombre o ruta del workflow no coincide con su ID")
        if run.get("head_branch") != "main" or run.get("event") not in definition["events"]:
            raise Rejected("Rama o evento productor no autorizado")
        if not same_repository(run.get("head_repository"), repository, repository_id):
            raise Rejected("Productor procedente de otro repositorio o fork")
        if not positive_integer(run.get("id")) or not positive_integer(run.get("run_attempt")):
            raise Rejected("Identidad del run o intento inválida")
        input_sha = git.commit(str(run.get("head_sha", "")))
        if not git.ancestor(input_sha, main_sha):
            raise Rejected("El SHA de entrada no es ancestro de main")
        expected = {"workflow": definition["path"], "run_id": str(run["id"]),
                    "attempt": str(run["run_attempt"]), "input_sha": input_sha}
        matches = []
        for commit in git.run("rev-list", "--first-parent", f"{input_sha}..{main_sha}").splitlines():
            trailers = git.trailers(commit)
            if str(run["id"]) in trailers.get(KEYS["run_id"].lower(), []) and str(run["run_attempt"]) in trailers.get(KEYS["attempt"].lower(), []):
                matches.append((commit, trailers))
        if not matches:
            return {**result, "should_deploy": "false", "reason": "sin-commit-producido"}
        if len(matches) != 1:
            raise Rejected("Más de un commit atribuido al mismo run e intento")
        produced, trailers = matches[0]
        if any(trailers.get(KEYS[key].lower()) != [value] for key, value in expected.items()):
            raise Rejected("Trailers del productor ambiguos o inconsistentes con el evento")
        parents = git.run("show", "-s", "--format=%P", produced).split()
        if len(parents) != 1:
            raise Rejected("El producto debe ser un commit directo, no una fusión")
        if not publication_changes(git.changed(parents[0], produced), patterns):
            return {**result, "should_deploy": "false", "reason": "solo-diagnostico"}
        result["producer_sha"] = produced
        result["trigger_sha"] = produced
    elif event_name in {"push", "workflow_dispatch"}:
        ref = event.get("ref") if event_name == "push" else github_ref
        if ref != "refs/heads/main" or event.get("deleted"):
            raise Rejected("Sólo se publica desde main")
        source = event.get("after") if event_name == "push" else github_sha
        input_sha = git.commit(str(source or ""))
        if not git.ancestor(input_sha, main_sha):
            raise Rejected("La entrada del publicador no pertenece al main actual")
        result["trigger_sha"] = input_sha
    else:
        raise Rejected("Evento del publicador no autorizado")
    return result


def check_previous(git: Git, selection: dict, previous: dict | None, patterns: list[str]) -> dict:
    result = {**selection, "previous_sha": "absent"}
    if selection["should_deploy"] != "true" or previous is None:
        return result
    deployed = git.commit(previous["commit_sha"])
    result["previous_sha"] = deployed
    candidate = selection["deploy_sha"]
    if deployed == candidate:
        return {**result, "should_deploy": "false", "reason": "sha-ya-publicado"}
    if not git.ancestor(deployed, candidate):
        raise Rejected("Se rechaza regresión o historia divergente respecto de producción")
    if git.ancestor(selection["trigger_sha"], deployed):
        # Los select corren sin mutex y GitHub reemplaza el único job pendiente.
        # Un evento viejo que llegó tarde debe recoger cambios publicables nuevos
        # de main; sólo es duplicado si también falta ese delta real.
        if publication_changes(git.changed(deployed, candidate), patterns):
            return {**result, "reason": "main-con-entradas-publicables-nuevas"}
        return {**result, "should_deploy": "false", "reason": "evento-ya-publicado"}
    return result


def guard_backup(git: Git, site: Path, repository: str, candidate: str, expected_previous: str) -> None:
    marker_path = site / MARKER_PATH
    marker = validate_marker(json.loads(marker_path.read_text()), repository) if marker_path.exists() else None
    actual = marker["commit_sha"] if marker else "absent"
    if actual != expected_previous:
        raise Rejected("Producción cambió desde la selección; se aborta sin escribir")
    if marker and (actual == candidate or not git.ancestor(actual, candidate)):
        raise Rejected("El respaldo evidencia publicación duplicada o regresiva")
    git.commit(candidate)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--repository-id", type=int, default=int(os.environ.get("REPOSITORY_ID", "0")))
    parser.add_argument("--event-file", type=Path, default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME"))
    parser.add_argument("--github-sha", default=os.environ.get("GITHUB_SHA"))
    parser.add_argument("--output", type=Path, default=os.environ.get("GITHUB_OUTPUT"))
    parser.add_argument("--guard-backup", type=Path)
    parser.add_argument("--preflight-only", action="store_true", help="Validar elegibilidad sin observar producción fuera del mutex")
    parser.add_argument("--deploy-sha")
    parser.add_argument("--expected-previous")
    args = parser.parse_args()
    git = Git(ROOT)
    if args.guard_backup:
        guard_backup(git, args.guard_backup, args.repository, args.deploy_sha, args.expected_previous)
        print("Respaldo coherente con producción observada; candidato no regresivo")
        return
    registry = json.loads((ROOT / "deploy/producer-workflows.json").read_text())
    patterns = [entry["path"] for entry in json.loads((ROOT / "deploy/publication-inputs.json").read_text())["inputs"]]
    # ref main se resuelve una sola vez desde el checkout completo del preflight.
    main_sha = git.run("rev-parse", "refs/remotes/origin/main")
    selection = select_candidate(git, args.event_name, json.loads(args.event_file.read_text()),
                                 args.github_sha, args.repository, args.repository_id, registry, patterns, main_sha,
                                 os.environ.get("GITHUB_REF"))
    previous = None
    nonce = f"preflight-{os.environ.get('GITHUB_RUN_ID', '0')}-{time.time_ns()}"
    if selection["should_deploy"] == "true" and not args.preflight_only:
        previous = fetch_marker(args.repository, nonce)
    selection = check_previous(git, selection, previous, patterns)
    if previous and selection["should_deploy"] == "false":
        verify_online(previous, nonce)  # No declarar duplicado sano sólo por metadata.
    if args.output:
        with args.output.open("a", encoding="utf-8") as output:
            for key, value in selection.items():
                output.write(f"{key}={value}\n")
    print(json.dumps(selection, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"\nSelección: {selection['reason']} · candidato `{main_sha}` · producto `{selection['producer_sha'] or 'n/a'}`.\n")


if __name__ == "__main__":
    main()
