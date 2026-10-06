#!/usr/bin/env python3
"""Marcador público mínimo y smoke por bytes; nunca expone el respaldo privado."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

MARKER_PATH = ".well-known/cepoes-release.json"
PUBLIC_ORIGIN = "https://cepoes.org"
# Whitelist fija: ni el marcador remoto ni un argumento pueden agregar rutas.
PUBLIC_FILES = {
    "index.html": "/",
    "datos/estado/index.html": "/datos/estado/",
    "assets/data/estructura-productiva/actual.json": "/assets/data/estructura-productiva/actual.json",
}
SHA = re.compile(r"[0-9a-f]{40}")
HASH = re.compile(r"[0-9a-f]{64}")


def fingerprint(data: bytes) -> dict:
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def validate_marker(marker: dict, repository: str) -> dict:
    if not isinstance(marker, dict) or marker.get("schema_version") != 1:
        raise ValueError("Marcador público con esquema inválido")
    if marker.get("repository") != repository or not SHA.fullmatch(str(marker.get("commit_sha", ""))):
        raise ValueError("Marcador público con repositorio o SHA inválido")
    if not re.fullmatch(r"[1-9][0-9]*", str(marker.get("run_id", ""))):
        raise ValueError("Marcador público con run inválido")
    if type(marker.get("run_attempt")) is not int or marker["run_attempt"] < 1:
        raise ValueError("Marcador público con intento inválido")
    files = marker.get("files")
    if not isinstance(files, dict) or set(files) != set(PUBLIC_FILES):
        raise ValueError("El marcador debe describir sólo las tres rutas públicas verificadas")
    for data in files.values():
        if not isinstance(data, dict) or not HASH.fullmatch(str(data.get("sha256", ""))):
            raise ValueError("Huella pública inválida")
        if type(data.get("bytes")) is not int or data["bytes"] <= 0:
            raise ValueError("Tamaño público inválido")
    return marker


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        raise ValueError("Se rechaza redirección del origen/ruta pública verificada")


def read_public(path: str, nonce: str | None, *, limit: int = 8 * 1024 * 1024) -> bytes:
    if path not in {"/" + MARKER_PATH, *PUBLIC_FILES.values()}:
        raise ValueError("Ruta fuera de la whitelist pública")
    if nonce is not None and not re.fullmatch(r"[A-Za-z0-9-]+", nonce):
        raise ValueError("Identificador de comprobación inválido")
    # None prueba exactamente la URL y los encabezados de una visita ordinaria.
    suffix = "?release_check=" + nonce if nonce is not None else ""
    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"} if nonce is not None else {}
    request = urllib.request.Request(PUBLIC_ORIGIN + path + suffix, headers=headers)
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=40) as response:
        if nonce is None:
            directives = {part.strip().lower() for part in response.headers.get("Cache-Control", "").split(",")}
            if not {"no-cache", "max-age=0", "must-revalidate"} <= directives:
                raise ValueError(f"La ruta canónica no aplica la política de revalidación: {path}")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Respuesta pública demasiado grande")
    return data


def fetch_marker(repository: str, nonce: str) -> dict | None:
    try:
        raw = read_public("/" + MARKER_PATH, nonce, limit=16 * 1024)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None  # Transición inicial desde el publicador sin marcador.
        raise
    return validate_marker(json.loads(raw), repository)


def create_marker(site: Path, repository: str, commit: str, run_id: str, attempt: int) -> dict:
    files = {}
    for relative in PUBLIC_FILES:
        path = site / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Falta ruta pública regular: {relative}")
        files[relative] = fingerprint(path.read_bytes())
    marker = validate_marker({"schema_version": 1, "repository": repository,
                              "commit_sha": commit, "run_id": str(run_id),
                              "run_attempt": attempt, "files": files}, repository)
    target = site / MARKER_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(marker, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return marker


def verify_online(marker: dict, nonce: str) -> None:
    # Primero la visita ordinaria: consultar antes con nonce podría refrescar una
    # caché compartida y ocultar que los visitantes recibían una versión anterior.
    ordinary_marker = validate_marker(json.loads(read_public("/" + MARKER_PATH, None,
                                                            limit=16 * 1024)), marker["repository"])
    if ordinary_marker != marker:
        raise ValueError("El marcador canónico no coincide con el candidato exacto")
    for relative, url_path in PUBLIC_FILES.items():
        if fingerprint(read_public(url_path, None)) != marker["files"][relative]:
            raise ValueError(f"Los bytes canónicos no coinciden con el candidato: {relative}")
        print(f"Bytes canónicos verificados: {relative} · {marker['files'][relative]['sha256']}")
    # Comparar metadata primero evita declarar éxito con el marker de otro build.
    observed = fetch_marker(marker["repository"], nonce)
    if observed != marker:
        raise ValueError("El marcador público no coincide con el candidato exacto")
    for relative, url_path in PUBLIC_FILES.items():
        if fingerprint(read_public(url_path, nonce)) != marker["files"][relative]:
            raise ValueError(f"Los bytes publicados no coinciden con el candidato: {relative}")
        print(f"Bytes públicos verificados: {relative} · {marker['files'][relative]['sha256']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "smoke"))
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--commit")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument("--run-attempt", type=int, default=int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")))
    args = parser.parse_args()
    if args.command == "create":
        marker = create_marker(args.site, args.repository, args.commit, args.run_id, args.run_attempt)
        print(f"Marcador del candidato {marker['commit_sha']}: /{MARKER_PATH}")
    else:
        marker = validate_marker(json.loads((args.site / MARKER_PATH).read_text()), args.repository)
        for attempt in range(5):
            try:
                verify_online(marker, f"{args.run_id}-{args.run_attempt}-{time.time_ns()}")
                return
            except (OSError, ValueError) as error:
                if attempt == 4:
                    raise
                print(f"Smoke por bytes aún no coincide (intento {attempt + 1}/5): {error}")
                time.sleep(5)


if __name__ == "__main__":
    main()
