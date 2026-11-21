#!/usr/bin/env python3
"""Verifica un release oficial en QA. Nunca llama al modelo ni carga credenciales."""
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener


VERSION = "1.0.114"
ASSET = "copilot-linux-x64.tar.gz"
URL = f"https://github.com/github/copilot-cli/releases/download/v{VERSION}/{ASSET}"
# https://github.com/github/copilot-cli/releases/expanded_assets/v1.0.114
SHA256 = "b91a96f2257297cfb67ed6784a2a658609a6b8c2ee2ded18af9c9abe8cc790ae"
DOWNLOAD_HOSTS = {"github.com", "release-assets.githubusercontent.com"}
MAX_BYTES = 170 * 1024 * 1024
FLAGS = (
    "-s", "--no-ask-user", "--no-custom-instructions", "--no-auto-update",
    "--sync-session=off", "--no-color", "--deny-tool=shell,write,read,url,memory",
)


def require_release_url(url: str) -> None:
    target = urlsplit(url)
    if (
        target.scheme != "https" or target.hostname not in DOWNLOAD_HOSTS
        or target.port not in (None, 443) or target.username is not None or target.password is not None
    ):
        raise RuntimeError("Destino inesperado al descargar el release público de GitHub")


class ReleaseRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require_release_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(archive: Path) -> None:
    require_release_url(URL)
    digest = hashlib.sha256()
    opener = build_opener(ProxyHandler({}), ReleaseRedirect())
    total = 0
    with opener.open(URL, timeout=30) as response, archive.open("xb") as out:
        require_release_url(response.geturl())
        while block := response.read(1024 * 1024):
            total += len(block)
            if total > MAX_BYTES:
                raise RuntimeError("El archivo supera el máximo previsto para el release fijado")
            digest.update(block)
            out.write(block)
    if digest.hexdigest() != SHA256:
        raise RuntimeError("El SHA-256 del release no coincide")


def extract_cli(archive: Path, binary: Path) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        matches = [m for m in tar.getmembers() if m.isfile() and m.name.rsplit("/", 1)[-1] == "copilot"]
        if len(matches) != 1:
            raise RuntimeError("No hay un único ejecutable regular copilot en el release")
        with tar.extractfile(matches[0]) as source, binary.open("xb") as dest:
            shutil.copyfileobj(source, dest)
    binary.chmod(0o700)


def isolated_command(binary: Path, home: Path, *args: str) -> list[str]:
    # GitHub-hosted Linux VM: sudo no-interactivo. Red aislada, luego baja a
    # usuario no privilegiado. Si no puede aislarse, no ejecuta el binario.
    return [
        "/usr/bin/timeout", "--kill-after=5s", "45s", "/usr/bin/sudo", "-n", "--",
        "/usr/bin/unshare", "--net", "--",
        "/usr/bin/setpriv", "--reuid", str(os.getuid()), "--regid", str(os.getgid()),
        "--clear-groups", "--no-new-privs", "--",
        "/usr/bin/env", "-i", f"PATH={home / 'empty-path'}", f"HOME={home}",
        f"XDG_CONFIG_HOME={home / '.config'}", f"COPILOT_HOME={home / '.copilot'}",
        "COPILOT_AUTO_UPDATE=false", "TERM=dumb", "CI=true",
        str(binary), *args,
    ]


def run_probe(binary: Path, home: Path, *args: str) -> str:
    proc = subprocess.run(
        isolated_command(binary, home, *args), cwd=home, stdin=subprocess.DEVNULL,
        text=True, capture_output=True, check=False, timeout=55,
        env={"PATH": "/usr/bin:/bin", "TERM": "dumb"},
    )
    if proc.returncode:
        # No imprimir sesiones, prompts, contenido o valores de entorno.
        err = proc.stderr
        reason = "el runner no pudo establecer el aislamiento de red/usuario" if re.search(r"(unshare|setpriv|sudo):", err) else "el CLI rechazó las opciones de QA"
        raise RuntimeError(f"{reason} (código {proc.returncode})")
    return proc.stdout


def main() -> None:
    if platform.system() != "Linux" or platform.machine() != "x86_64" or platform.libc_ver()[0] != "glibc":
        raise RuntimeError("La verificación requiere un runner Linux x86_64 con glibc")
    if os.getuid() == 0:
        raise RuntimeError("La verificación requiere un usuario de runner no privilegiado")
    with TemporaryDirectory(prefix="cepoes-copilot-qa-") as raw:
        work = Path(raw)
        home = work / "home"
        (home / "empty-path").mkdir(parents=True)
        archive = work / ASSET
        binary = work / "copilot"
        download(archive)
        extract_cli(archive, binary)
        version = run_probe(binary, home, "--version")
        if not re.search(r"(?<![\d.])" + re.escape(VERSION) + r"(?![\d.]|[-+])", version):
            raise RuntimeError("El binario no informa la versión estable fijada")
        help_text = run_probe(binary, home, "--help")
        for flag in (*FLAGS, "--prompt", "--model"):
            base = flag.split("=", 1)[0]
            if not re.search(r"(?<![\w-])" + re.escape(base) + r"(?![\w-])", help_text):
                raise RuntimeError(f"Opción esperada ausente del --help: {base}")
        run_probe(binary, home, "--help", *FLAGS)
    print(f"Copilot CLI {VERSION}: SHA-256, versión, ayuda y opciones verificados sin red en el proceso ni inferencia.")


if __name__ == "__main__":
    main()
