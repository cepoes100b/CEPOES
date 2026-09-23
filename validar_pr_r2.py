#!/usr/bin/env python3
"""Control universal, reproducible y sin secretos para pull requests de CEPOES."""

from __future__ import annotations

import argparse
import os
import py_compile
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKFLOWS = ROOT / ".github" / "workflows"
R2_WORKFLOW = WORKFLOWS / "validar-pr-r2.yml"

SECRET_PATTERNS = {
    "clave privada": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "token personal de GitHub": re.compile(r"\b(?:gh[oprsu]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "clave de acceso de AWS": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "token de Slack": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "URL con credenciales": re.compile(r"\b(?:https?|sftp)://[^\s/:]+:[^\s/@]+@"),
}

SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
}
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


def run(*command: str) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def tracked_python_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        return [ROOT / line for line in result.stdout.splitlines() if line]
    return [path for path in ROOT.rglob("*.py") if ".git" not in path.parts]


def validate_python() -> None:
    files = tracked_python_files()
    assert files, "No se encontraron archivos Python"
    with tempfile.TemporaryDirectory(prefix="cepoes-pyc-") as directory:
        cache = Path(directory)
        for index, path in enumerate(files):
            py_compile.compile(path, cfile=str(cache / f"{index}.pyc"), doraise=True)
    print(f"Python: {len(files)} archivos compilan correctamente")


def validate_workflow_yaml() -> None:
    files = sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))
    assert files, "No se encontraron workflows"
    try:
        import yaml  # type: ignore
    except ImportError:
        ruby = shutil.which("ruby")
        assert ruby, "Se requiere PyYAML o Ruby para validar los workflows"
        program = (
            'require "yaml"; '
            'ARGV.each { |path| YAML.parse_file(path) }; '
            'puts "Workflows YAML válidos: #{ARGV.length}"'
        )
        subprocess.run([ruby, "-e", program, *map(str, files)], check=True, cwd=ROOT)
    else:
        for path in files:
            with path.open(encoding="utf-8") as stream:
                document = yaml.safe_load(stream)
            assert isinstance(document, dict), f"Workflow vacío o inválido: {path}"
        print(f"Workflows YAML válidos: {len(files)}")

    source = R2_WORKFLOW.read_text(encoding="utf-8")
    trigger = source.split("permissions:", 1)[0]
    assert "name: R2" in source, "El nombre estable del workflow R2 cambió"
    assert "name: controles obligatorios" in source, "El nombre estable del check R2 cambió"
    assert "pull_request:" in trigger and "paths:" not in trigger, "R2 debe ejecutarse en todo PR a main"
    assert re.search(r"permissions:\s*\n\s+contents: read", source), "R2 requiere permisos mínimos"
    assert "secrets." not in source, "R2 no debe consumir secretos"
    print("Contrato R2: trigger universal, nombre estable, solo lectura y sin secretos")


def findings_in_text(text: str) -> list[str]:
    return [label for label, pattern in SECRET_PATTERNS.items() if pattern.search(text)]


def validate_secret_detector() -> None:
    assert not findings_in_text("HOSTINGER_PASSWORD: ${{ secrets.HOSTINGER_SFTP_PASSWORD }}")
    assert findings_in_text("token=ghp_" + "012345678901234567890123456789012345")
    assert findings_in_text("-----BEGIN " + "PRIVATE KEY-----")
    assert findings_in_text("sftp://" + "usuario:clave@example.test/ruta")
    print("Detector de secretos: pruebas internas correctas")


def scan_diff(base_sha: str | None) -> None:
    if not base_sha:
        print("Secretos en diff: omitido fuera de un pull request")
        return

    names = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}...HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    unsafe_names = [
        name for name in names
        if Path(name).name in SENSITIVE_NAMES or Path(name).suffix.lower() in SENSITIVE_SUFFIXES
    ]

    patch = subprocess.run(
        ["git", "diff", "--unified=0", "--no-color", "--no-ext-diff", f"{base_sha}...HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    findings: list[str] = []
    current = "archivo desconocido"
    new_line = 0
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            new_line = int(match.group(1)) if match else 0
        elif line.startswith("+") and not line.startswith("+++"):
            for label in findings_in_text(line[1:]):
                findings.append(f"{current}:{new_line} ({label})")
            new_line += 1
        elif not line.startswith("-"):
            new_line += 1

    assert not unsafe_names, "Archivos sensibles agregados o modificados: " + ", ".join(unsafe_names)
    assert not findings, "Posibles secretos agregados:\n- " + "\n- ".join(findings)
    print(f"Secretos en diff: {len(names)} archivos revisados, sin hallazgos")


def create_runtime_fixture(site: Path) -> None:
    assets = site / "assets"
    assets.mkdir(parents=True)
    shutil.copy2(ROOT / "deploy/site-overlay/assets/common-r1.js", assets / "common-r1.js")

    pages = {
        "territorio/mapa-tematico/index.html": '<script src="/assets/thematic-map.js?v=258"></script>',
        "territorio/brechas/index.html": '<script src="/assets/brechas.js?v=258"></script>',
        "territorio/migraciones/index.html": '<script src="/assets/migraciones.js?v=258"></script>',
        "publicaciones/index.html": "Último boletín",
    }
    for relative, content in pages.items():
        target = site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    run("python", "generar_indice_busqueda_global.py", str(site))
    run("python", "generar_estado_datos.py", str(site))


def validate_product_contracts() -> None:
    run("python", "validar_contraste_visual.py")
    with tempfile.TemporaryDirectory(prefix="cepoes-r2-") as directory:
        site = Path(directory)
        create_runtime_fixture(site)
        run("python", "validar_busqueda_global.py", str(site))
        run("python", "validar_r1_runtime.py", str(site))
    print("Contratos de producto: contraste, búsqueda y runtime R1 válidos")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha", default=os.environ.get("R2_BASE_SHA"))
    args = parser.parse_args()

    if (ROOT / ".git").is_dir():
        run("git", "diff", "--check")
    else:
        print("Espacios y marcadores de conflicto: se validarán en el checkout del PR")
    validate_python()
    validate_workflow_yaml()
    validate_secret_detector()
    scan_diff(args.base_sha)
    validate_product_contracts()
    print("R2 / controles obligatorios: APROBADO")


if __name__ == "__main__":
    main()
