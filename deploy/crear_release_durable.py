#!/usr/bin/env python3
"""Empaqueta el estado anterior y el candidato exacto de un despliegue CEPOES."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1
ARCHIVES = {
    "before": "production-before.tar.gz",
    "candidate": "site-candidate.tar.gz",
}
SENSITIVE_BASENAMES = {
    ".htpasswd",
    "id_ed25519",
    "id_rsa",
    "wp-config.php",
}
SENSITIVE_SUFFIXES = {".db", ".key", ".p12", ".pem", ".pfx", ".sql", ".sqlite"}
SECRET_PATTERNS = {
    "clave privada": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "token GitHub": re.compile(rb"\b(?:gh[oprsu]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "clave AWS": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "token Slack": re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "URL con credenciales": re.compile(rb"\b(?:https?|sftp)://[^\s/:]+:[^\s/@]+@"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_files(root: Path) -> list[Path]:
    assert root.is_dir(), f"No existe el directorio requerido: {root}"
    files: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        if path.is_symlink():
            raise AssertionError(f"No se permiten enlaces simbólicos en el release: {path}")
        if path.is_file():
            files.append(path)
        elif not path.is_dir():
            raise AssertionError(f"Tipo de archivo no permitido: {path}")
    assert files, f"El directorio está vacío: {root}"
    return files


def validate_sensitive_path(relative: Path) -> None:
    names = {part.lower() for part in relative.parts}
    base = relative.name.lower()
    assert ".git" not in names, f"No se puede archivar metadata Git: {relative}"
    assert not (base == ".env" or base.startswith(".env.")), f"Archivo sensible: {relative}"
    assert base not in SENSITIVE_BASENAMES, f"Archivo sensible: {relative}"
    assert relative.suffix.lower() not in SENSITIVE_SUFFIXES, f"Archivo sensible: {relative}"


def scan_file(path: Path, relative: Path) -> None:
    validate_sensitive_path(relative)
    overlap = b""
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sample = overlap + chunk
            for label, pattern in SECRET_PATTERNS.items():
                assert not pattern.search(sample), f"Posible {label} en {relative}"
            overlap = sample[-256:]


def snapshot(root: Path) -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {}
    for path in relative_files(root):
        relative = path.relative_to(root)
        scan_file(path, relative)
        result[relative.as_posix()] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
    assert "index.html" in result, f"{root} no contiene index.html"
    return result


def normalized_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    return info


def create_archive(root: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
                    archive.add(
                        path,
                        arcname=path.relative_to(root).as_posix(),
                        recursive=False,
                        filter=normalized_tar_info,
                    )


def changed_paths(
    before: dict[str, dict[str, int | str]],
    candidate: dict[str, dict[str, int | str]],
) -> dict[str, list[str]]:
    old = set(before)
    new = set(candidate)
    return {
        "added": sorted(new - old),
        "modified": sorted(path for path in old & new if before[path] != candidate[path]),
        "deleted": sorted(old - new),
    }


def build_release(args: argparse.Namespace) -> dict:
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    before_files = snapshot(args.before.resolve())
    candidate_files = snapshot(args.candidate.resolve())

    for label, root in (("before", args.before), ("candidate", args.candidate)):
        create_archive(root.resolve(), output / ARCHIVES[label])

    artifacts = {}
    for label, filename in ARCHIVES.items():
        archive = output / filename
        files = before_files if label == "before" else candidate_files
        artifacts[label] = {
            "archive": filename,
            "sha256": sha256_file(archive),
            "bytes": archive.stat().st_size,
            "file_count": len(files),
            "files": files,
        }

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "release_id": f"github-{args.run_id}-{args.run_attempt}",
        "created_at_utc": args.created_at or datetime.now(timezone.utc).isoformat(),
        "repository": args.repository,
        "commit_sha": args.commit,
        "workflow": "Desplegar sitio en Hostinger",
        "run_id": str(args.run_id),
        "run_attempt": int(args.run_attempt),
        "custody": {
            "storage": "private-ghcr",
            "minimum_retention_days": int(args.retention_days),
            "minimum_retained_releases": 10,
            "deletion_policy": "manual-after-both-thresholds",
        },
        "recovery_objectives": {"rpo": "una publicación", "rto_minutes": 60},
        "changes": changed_paths(before_files, candidate_files),
        "artifacts": artifacts,
    }
    manifest_path = output / "release-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    checksums = [
        f"{sha256_file(output / filename)}  {filename}"
        for filename in (*ARCHIVES.values(), "release-manifest.json")
    ]
    (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")

    changed = manifest["changes"]
    summary = (
        f"Release durable {manifest['release_id']}: "
        f"{len(before_files)} archivos previos, {len(candidate_files)} candidatos; "
        f"{len(changed['added'])} altas, {len(changed['modified'])} modificaciones, "
        f"{len(changed['deleted'])} bajas"
    )
    print(summary)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with Path(step_summary).open("a", encoding="utf-8") as stream:
            stream.write(f"## Release durable\n\n{summary}\n")
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--before", type=Path, required=True)
    result.add_argument("--candidate", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "local/CEPOES"))
    result.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "local"))
    result.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "0"))
    result.add_argument("--run-attempt", type=int, default=int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")))
    result.add_argument("--retention-days", type=int, default=90)
    result.add_argument("--created-at")
    return result


def main() -> None:
    args = parser().parse_args()
    assert args.retention_days >= 30, "La retención no puede ser menor a 30 días"
    assert re.fullmatch(r"[0-9]+", str(args.run_id)), "run_id inválido"
    assert args.run_attempt >= 1, "run_attempt inválido"
    build_release(args)


if __name__ == "__main__":
    main()
