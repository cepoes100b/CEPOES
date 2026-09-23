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

ACTION_USE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")
FULL_SHA_REF = re.compile(r"^[^@]+@[0-9a-fA-F]{40}$")

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

    allowed_permissions = {
        "actions", "attestations", "checks", "contents", "deployments", "discussions",
        "id-token", "issues", "models", "packages", "pages", "pull-requests",
        "security-events", "statuses",
    }
    for path in files:
        workflow_source = path.read_text(encoding="utf-8")
        assert re.search(r"(?m)^on:\s*$", workflow_source), f"Falta el bloque on en {path}"
        assert re.search(r"(?m)^jobs:\s*$", workflow_source), f"Falta el bloque jobs en {path}"
        permission_block = re.search(r"(?ms)^permissions:\s*\n(.*?)(?=^[A-Za-z_-][A-Za-z0-9_-]*:\s*(?:\n|$))", workflow_source)
        if permission_block:
            keys = set(re.findall(r"(?m)^  ([A-Za-z-]+):", permission_block.group(1)))
            unknown = sorted(keys - allowed_permissions)
            assert not unknown, f"Claves ajenas dentro de permissions en {path}: {unknown}"

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


def validate_action_pin_detector() -> None:
    assert FULL_SHA_REF.fullmatch("actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09")
    assert not FULL_SHA_REF.fullmatch("actions/checkout@v5")
    print("Detector de acciones sin SHA: pruebas internas correctas")


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
    unpinned_actions: list[str] = []
    current = "archivo desconocido"
    new_line = 0
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            new_line = int(match.group(1)) if match else 0
        elif line.startswith("+") and not line.startswith("+++"):
            added = line[1:]
            for label in findings_in_text(added):
                findings.append(f"{current}:{new_line} ({label})")
            action = ACTION_USE.match(added)
            if current.startswith(".github/workflows/") and action and not FULL_SHA_REF.fullmatch(action.group(1)):
                unpinned_actions.append(f"{current}:{new_line} ({action.group(1)})")
            new_line += 1
        elif not line.startswith("-"):
            new_line += 1

    assert not unsafe_names, "Archivos sensibles agregados o modificados: " + ", ".join(unsafe_names)
    assert not findings, "Posibles secretos agregados:\n- " + "\n- ".join(findings)
    assert not unpinned_actions, "Acciones nuevas sin SHA completo:\n- " + "\n- ".join(unpinned_actions)
    print(f"Secretos en diff: {len(names)} archivos revisados, sin hallazgos")


def validate_workflow_inventory() -> None:
    run(
        "python",
        "auditar_workflows_r2.py",
        "--check",
        "docs/seguridad/inventario-workflows-r2.md",
        "--check-retirement-matrix",
        "docs/seguridad/matriz-retiro-workflows-r2.md",
        "--check-archive-manifest",
        "docs/seguridad/workflows-retirados/README.md",
    )
    run("python", "validar_rutas_publicacion.py")


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


def create_canonical_publication_fixture(site: Path) -> None:
    observatory = site / "observatorio" / "index.html"
    observatory.parent.mkdir(parents=True)
    observatory.write_text(
        """<!doctype html><html><head></head><body>
        <nav class="subnav"><a href="/observatorio/agenda/">Agenda</a></nav>
        <main><header><h1>Observatorio</h1></header><section>Contenido</section></main>
        </body></html>""",
        encoding="utf-8",
    )

    for relative in ("legislatura/index.html", "legislatura/detalle/index.html"):
        target = site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "<!doctype html><html><head><title>Legislatura</title></head><body></body></html>",
            encoding="utf-8",
        )

    assets = site / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        ROOT / "deploy/site-overlay/assets/legislatura-public-bridge.js",
        assets / "legislatura-public-bridge.js",
    )

    run("python", "deploy/preparar_legislatura_publica.py", str(site))
    run("python", "deploy/parche_observatorio_salud.py", str(observatory))
    run("python", "deploy/preparar_puente_legislatura.py", str(site))
    run("python", "deploy/validar_publicacion_canonica.py", str(site))

    # Los transformadores deben poder ejecutarse otra vez sin duplicar salida.
    run("python", "deploy/parche_observatorio_salud.py", str(observatory))
    run("python", "deploy/preparar_puente_legislatura.py", str(site))
    run("python", "deploy/validar_publicacion_canonica.py", str(site))


def validate_product_contracts() -> None:
    run("python", "validar_contraste_visual.py")
    with tempfile.TemporaryDirectory(prefix="cepoes-r2-") as directory:
        site = Path(directory)
        create_runtime_fixture(site)
        run("python", "validar_busqueda_global.py", str(site))
        run("python", "validar_r1_runtime.py", str(site))
    with tempfile.TemporaryDirectory(prefix="cepoes-r2-publicacion-") as directory:
        create_canonical_publication_fixture(Path(directory))
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
    validate_action_pin_detector()
    scan_diff(args.base_sha)
    validate_workflow_inventory()
    validate_product_contracts()
    print("R2 / controles obligatorios: APROBADO")


if __name__ == "__main__":
    main()
