#!/usr/bin/env python3
"""Prueba los contratos R2-A4 sin escribir en producción."""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEPLOY = ROOT / ".github" / "workflows" / "desplegar-hostinger.yml"
RESTORE = ROOT / ".github" / "workflows" / "ensayar-restauracion-durable.yml"
ACTION_PIN = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"


def run(*command: str, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if expect_success and result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    if not expect_success and result.returncode == 0:
        raise AssertionError("El comando debía fallar: " + " ".join(command))
    return result


def fixture_contract() -> None:
    with tempfile.TemporaryDirectory(prefix="cepoes-r2a4-") as directory:
        base = Path(directory)
        before = base / "before"
        candidate = base / "candidate"
        release = base / "release"
        restored = base / "restored"
        before.mkdir()
        candidate.mkdir()
        (before / "index.html").write_text("antes", encoding="utf-8")
        (before / "assets").mkdir()
        (before / "assets" / "old.css").write_text("old", encoding="utf-8")
        (candidate / "index.html").write_text("después", encoding="utf-8")
        (candidate / "assets").mkdir()
        (candidate / "assets" / "new.css").write_text("new", encoding="utf-8")

        run(
            "python", "deploy/crear_release_durable.py",
            "--before", str(before), "--candidate", str(candidate),
            "--output", str(release), "--repository", "cepoes100b/CEPOES",
            "--commit", "a" * 40, "--run-id", "123", "--run-attempt", "2",
            "--created-at", "2026-09-24T00:00:00+00:00",
        )
        manifest = json.loads((release / "release-manifest.json").read_text(encoding="utf-8"))
        assert manifest["changes"] == {
            "added": ["assets/new.css"],
            "modified": ["index.html"],
            "deleted": ["assets/old.css"],
        }
        assert manifest["custody"] == {
            "storage": "private-ghcr",
            "minimum_retention_days": 90,
            "minimum_retained_releases": 10,
            "deletion_policy": "manual-after-both-thresholds",
        }
        assert set(manifest["artifacts"]) == {"before", "candidate"}

        report = base / "restore-report.json"
        run(
            "python", "deploy/restaurar_release_durable.py",
            "--release-dir", str(release), "--target", str(restored),
            "--report", str(report), "--asset", "before",
            "--expected-run-id", "123", "--expected-run-attempt", "2",
            "--expected-commit", "a" * 40,
            "--expected-source-digest", "sha256:" + "b" * 64,
        )
        restored_report = json.loads(report.read_text(encoding="utf-8"))
        assert restored_report["production_written"] is False
        assert restored_report["source_digest"] == "sha256:" + "b" * 64
        assert (restored / "index.html").read_text(encoding="utf-8") == "antes"

        with (release / "production-before.tar.gz").open("ab") as stream:
            stream.write(b"alterado")
        run(
            "python", "deploy/restaurar_release_durable.py",
            "--release-dir", str(release), "--target", str(base / "tampered"),
            "--report", str(base / "tampered.json"), "--asset", "before",
            "--expected-run-id", "123", "--expected-run-attempt", "2",
            "--expected-commit", "a" * 40,
            "--expected-source-digest", "sha256:" + "b" * 64,
            expect_success=False,
        )

        malicious = base / "malicious.tar.gz"
        with tarfile.open(malicious, "w:gz") as archive:
            info = tarfile.TarInfo("../escape.txt")
            payload = b"no"
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        code = (
            "import sys,tarfile; sys.path.insert(0,'deploy'); "
            "from restaurar_release_durable import safe_member; "
            f"a=tarfile.open({str(malicious)!r},'r:gz'); safe_member(a.getmembers()[0])"
        )
        run("python", "-c", code, expect_success=False)


def workflow_contracts() -> None:
    deploy = DEPLOY.read_text(encoding="utf-8")
    restore = RESTORE.read_text(encoding="utf-8")
    assert "python deploy/crear_release_durable.py" in deploy
    assert ACTION_PIN not in deploy and ACTION_PIN in restore
    assert "retention-days: 90" in restore
    assert deploy.index("Conservar release durable en registro privado") < deploy.index("Publicar en Hostinger por SFTP")
    assert "packages: write" in deploy
    assert "ghcr.io/${package_owner}/${package_name}" in deploy
    assert "docker push" in deploy
    assert "docker logout ghcr.io" in deploy and "package-anonymous-pull.log" in deploy
    assert "descarga anónima" in deploy
    assert "workflow_dispatch:" in restore and "pull_request:" in restore
    assert "actions: read" in restore and "contents: read" in restore and "packages: read" in restore
    assert "source_digest:" in restore and "docker pull" in restore
    assert "docker logout ghcr.io" in restore and "package-anonymous-pull.log" in restore
    assert "gh run download" not in restore
    assert "environment: production" not in restore
    for forbidden in ("HOSTINGER_", "SFTP_", "lftp", "mirror -R", "secrets."):
        assert forbidden not in restore, f"El ensayo no puede usar {forbidden}"
    assert "production_written" in (ROOT / "deploy/restaurar_release_durable.py").read_text(encoding="utf-8")


def main() -> None:
    fixture_contract()
    workflow_contracts()
    print("R2-A4: empaquetado, hashes, rechazo de alteraciones y restauración controlada válidos")


if __name__ == "__main__":
    main()
