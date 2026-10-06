#!/usr/bin/env python3
"""Prueba HTTP real de .htaccess en Apache aislado y sólo en 127.0.0.1.

Ejecutar como usuario sin privilegios: python test_cache_publicacion_apache.py --repo .
No instala software, lee configuración global ni registra/inicia servicios.
"""
from __future__ import annotations

import argparse
import grp
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


EXPECTED_CACHE = {"no-cache", "max-age=0", "must-revalidate"}
TARGETS = ("/", "/index.html", "/datos/estado/", "/datos/estado/index.html",
           "/assets/data/estructura-productiva/actual.json", "/.well-known/cepoes-release.json")
CONTROLS = ("/assets/fixture.css", "/assets/data/otra.json", "/publicaciones/fixture/",
            "/privado/", "/privado/index.html", "/private-marker.txt", "/legacy-cache-check")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def get(origin: str, path: str) -> dict:
    # No usar proxies configurados por el runner para una prueba de loopback.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(origin + path)
    try:
        response = opener.open(request, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read(1024 * 1024)
        return {"status": response.status,
                "cache_control": response.headers.get_all("Cache-Control", []),
                "existing": response.headers.get("X-CEPOES-Existing"),
                "location": response.headers.get("Location"),
                "sha256": hashlib.sha256(body).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--apache", type=Path)
    parser.add_argument("--modules", type=Path, default=Path("/usr/lib/apache2/modules"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise SystemExit("Ejecutar sin root; esta prueba no necesita privilegios")
    executable = str(args.apache) if args.apache else (shutil.which("apache2") or shutil.which("httpd"))
    if not executable:
        raise SystemExit("Falta Apache. Instalar apache2-bin oficial en el runner de CI; no se omite la prueba")
    repo = args.repo.resolve()
    source = repo / "deploy/preparar_sitio_publico.py"
    spec = importlib.util.spec_from_file_location("cepoes_site_cache_test", source)
    if spec is None or spec.loader is None:
        raise SystemExit("No se pudo cargar el preparador de la rama bajo prueba")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prepare = module.prepare_public_revalidation

    existing = ('# Reglas preexistentes de la fixture\n'
                'Header always set X-CEPOES-Existing "preserved"\n'
                'Redirect 301 /legacy-cache-check /datos/estado/\n'
                '<Files "private-marker.txt">\n  Require all denied\n</Files>\n')
    once = prepare(existing)
    twice = prepare(once)
    assert once.startswith(existing), "El preparador alteró reglas anteriores"
    assert once == twice, "El preparador no es idempotente"
    assert once.count("# BEGIN CEPOES PUBLIC REVALIDATION") == 1
    version = subprocess.run([executable, "-v"], check=True, capture_output=True, text=True).stdout.strip()

    with tempfile.TemporaryDirectory(prefix="cepoes-apache-") as temporary:
        root = Path(temporary)
        site = root / "site"
        site.mkdir()
        fixtures = {
            "index.html": "fixture-home",
            "datos/estado/index.html": "fixture-state",
            "assets/data/estructura-productiva/actual.json": '{"fixture":"current"}',
            ".well-known/cepoes-release.json": '{"fixture":"release"}',
            "assets/fixture.css": "body { color: black; }",
            "assets/data/otra.json": '{"fixture":"other"}',
            "publicaciones/fixture/index.html": "fixture-other-html",
            "privado/index.html": "synthetic-private-must-not-be-served",
            "privado/.htaccess": 'Require all denied\nHeader always set Cache-Control "private, no-store"\n',
            "private-marker.txt": "synthetic-protected-must-not-be-served",
        }
        for relative, content in fixtures.items():
            file = site / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content, encoding="utf-8")
        htaccess = site / ".htaccess"
        htaccess.write_text(existing, encoding="utf-8")
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        modules = []
        for name in ("mpm_event", "authz_core", "headers", "setenvif", "dir", "alias"):
            file = args.modules.resolve() / f"mod_{name}.so"
            if not file.is_file():
                raise SystemExit(f"Falta módulo oficial de Apache: {file}")
            modules.append(f'LoadModule {name}_module "{file}"')
        config = root / "httpd.conf"
        config.write_text(
            f'ServerRoot "{root}"\n'
            f'PidFile "{root / "httpd.pid"}"\n'
            f'Listen 127.0.0.1:{port}\n'
            f'ServerName 127.0.0.1:{port}\n'
            f'User {pwd.getpwuid(os.geteuid()).pw_name}\n'
            f'Group {grp.getgrgid(os.getegid()).gr_name}\n'
            + "\n".join(modules) + "\n"
            f'DocumentRoot "{site}"\n'
            f'ErrorLog "{root / "error.log"}"\n'
            'LogLevel warn\nServerTokens Prod\nServerSignature Off\n'
            'DirectoryIndex index.html\n'
            f'<Directory "{site}">\n'
            '  AllowOverride FileInfo AuthConfig\n'
            '  Options -Indexes\n'
            '  Require all granted\n'
            '</Directory>\n', encoding="utf-8")
        command = [executable, "-f", str(config), "-d", str(root)]
        syntax = subprocess.run(command + ["-t"], capture_output=True, text=True)
        if syntax.returncode:
            raise SystemExit("Apache rechazó la configuración temporal:\n" + syntax.stderr)
        with (root / "process.log").open("w") as log:
            process = subprocess.Popen(command + ["-X"], stdout=log, stderr=log)
            try:
                origin = f"http://127.0.0.1:{port}"
                deadline = time.monotonic() + 10
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Apache finalizó antes de aceptar conexiones")
                    try:
                        get(origin, "/")
                        break
                    except (OSError, urllib.error.URLError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError("Apache no respondió en loopback")
                        time.sleep(0.1)
                before = {path: get(origin, path) for path in (*TARGETS, *CONTROLS)}
                for path in TARGETS:
                    assert before[path]["status"] == 200, (path, before[path])
                    assert before[path]["cache_control"] == [], (path, before[path])
                assert before["/privado/"]["status"] == 403
                assert before["/privado/index.html"]["status"] == 403
                assert before["/private-marker.txt"]["status"] == 403
                assert before["/legacy-cache-check"]["status"] == 301
                assert before["/legacy-cache-check"]["location"] == origin + "/datos/estado/"

                htaccess.write_text(once, encoding="utf-8")
                after = {path: get(origin, path) for path in (*TARGETS, *CONTROLS)}
                for path in TARGETS:
                    observed = after[path]
                    assert observed["status"] == 200, (path, observed)
                    assert observed["sha256"] == before[path]["sha256"], (path, "Cambió el contenido")
                    assert len(observed["cache_control"]) == 1, (path, observed)
                    actual = {v.strip().lower() for v in observed["cache_control"][0].split(",")}
                    assert actual == EXPECTED_CACHE, (path, observed)
                    assert observed["existing"] == "preserved", (path, observed)
                for path in CONTROLS:
                    assert after[path] == before[path], (path, "Alteró un control", before[path], after[path])

                htaccess.write_text(twice, encoding="utf-8")
                repeated = {path: get(origin, path) for path in (*TARGETS, *CONTROLS)}
                assert repeated == after, "Repetir el preparador cambió las respuestas"
                # Las URLs canónicas terminadas en / realmente resuelven DirectoryIndex.
                assert after["/"]["sha256"] == after["/index.html"]["sha256"]
                assert after["/datos/estado/"]["sha256"] == after["/datos/estado/index.html"]["sha256"]
                result = {"ok": True, "apache": version, "listen": "127.0.0.1",
                          "target_urls": len(TARGETS), "control_urls": len(CONTROLS),
                          "phases": ["before", "after", "idempotent"], "after": after}
                if args.output:
                    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except Exception:
                for file in (root / "error.log", root / "process.log"):
                    if file.exists():
                        print(file.name + ":\n" + file.read_text(errors="replace"))
                raise
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


if __name__ == "__main__":
    main()
