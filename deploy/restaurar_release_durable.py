#!/usr/bin/env python3
"""Verifica y restaura un release durable sólo sobre un directorio controlado."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from crear_release_durable import SCHEMA_VERSION, sha256_file


def safe_member(member: tarfile.TarInfo) -> PurePosixPath:
    path = PurePosixPath(member.name)
    assert not path.is_absolute(), f"Ruta absoluta no permitida: {member.name}"
    assert path.parts and ".." not in path.parts, f"Traversal no permitido: {member.name}"
    assert member.isdir() or member.isfile(), f"Tipo de entrada no permitido: {member.name}"
    return path


def extract_safely(archive_path: Path, target: Path) -> None:
    assert not target.exists() or not any(target.iterdir()), f"El destino debe estar vacío: {target}"
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            relative = safe_member(member)
            destination = target.joinpath(*relative.parts)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            assert source is not None, f"No se pudo leer {member.name}"
            with source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)


def snapshot(root: Path) -> dict[str, dict[str, int | str]]:
    result = {}
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        assert not path.is_symlink(), f"Enlace simbólico inesperado: {path}"
        if path.is_file():
            result[path.relative_to(root).as_posix()] = {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
    return result


def restore(args: argparse.Namespace) -> dict:
    started = time.monotonic()
    release_dir = args.release_dir.resolve()
    manifest = json.loads((release_dir / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest.get("schema_version") == SCHEMA_VERSION, "Versión de manifiesto inválida"
    assert str(manifest.get("run_id")) == str(args.expected_run_id), "run_id inesperado"
    assert int(manifest.get("run_attempt")) == args.expected_run_attempt, "run_attempt inesperado"
    assert manifest.get("commit_sha") == args.expected_commit, "Commit inesperado"
    assert manifest.get("repository") == args.expected_repository, "Repositorio inesperado"

    artifact = manifest["artifacts"][args.asset]
    archive_name = Path(artifact["archive"])
    assert archive_name.name == str(archive_name), "Nombre de archivo inválido en manifiesto"
    archive_path = release_dir / archive_name
    assert sha256_file(archive_path) == artifact["sha256"], "Hash del archivo no coincide"

    extract_safely(archive_path, args.target.resolve())
    actual = snapshot(args.target.resolve())
    assert actual == artifact["files"], "El contenido restaurado no coincide con el manifiesto"
    assert (args.target / "index.html").is_file(), "La restauración no contiene index.html"

    report = {
        "status": "success",
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_release_id": manifest["release_id"],
        "source_run_id": str(manifest["run_id"]),
        "source_run_attempt": int(manifest["run_attempt"]),
        "source_commit": manifest["commit_sha"],
        "source_digest": args.expected_source_digest,
        "asset": args.asset,
        "restored_files": len(actual),
        "duration_seconds": round(time.monotonic() - started, 3),
        "target": "runner-ephemeral",
        "production_written": False,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Restauración controlada válida: {len(actual)} archivos · "
        f"{report['duration_seconds']} s · producción no modificada"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--asset", choices=("before", "candidate"), default="before")
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-run-attempt", type=int, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-source-digest", required=True)
    parser.add_argument("--expected-repository", default="cepoes100b/CEPOES")
    args = parser.parse_args()
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", args.expected_source_digest), "Digest OCI inválido"
    restore(args)


if __name__ == "__main__":
    main()
