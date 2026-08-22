#!/usr/bin/env python3
"""Verifica consistencia semántica y privacidad de sesiones_publicas.json."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

PATH = Path("sesiones_publicas.json")
PRIVATE_KEYS = {
    "prioridad_interna", "posicion", "recomendacion", "responsable",
    "notas_internas", "analisis_tecnico", "argumentos", "preguntas",
    "oportunidad", "modificaciones",
}


def norm(value) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def walk_private(obj, path="$"):
    issues = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in PRIVATE_KEYS:
                issues.append(f"clave privada {path}.{key}")
            issues.extend(walk_private(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            issues.extend(walk_private(value, f"{path}[{i}]"))
    return issues


def official_url(url: str) -> bool:
    host = (urlparse(url or "").hostname or "").lower()
    return host == "parlamentaria.legislatura.gob.ar" or host.endswith(".legislatura.gob.ar")


def main() -> None:
    if not PATH.exists():
        raise SystemExit("✘ falta sesiones_publicas.json")
    data = json.loads(PATH.read_text(encoding="utf-8"))
    issues = []

    if data.get("version") != 1:
        issues.append("version debe ser 1")
    if data.get("resumen", {}).get("fallas") != 0 or data.get("fallas"):
        issues.append("hay fallas de extracción")

    fuente = data.get("fuente", {})
    for key in ("busqueda_sesiones", "servicio_sesiones", "pagina_votaciones"):
        if not official_url(fuente.get(key, "")):
            issues.append(f"fuente no oficial: {key}")

    sesiones = data.get("sesiones", [])
    if not sesiones:
        issues.append("no hay sesiones")

    ids = [str(s.get("id_sesion", "")) for s in sesiones]
    if any(not re.fullmatch(r"\d+", x) for x in ids):
        issues.append("hay id_sesion inválidos")
    dup = [x for x, n in Counter(ids).items() if n > 1]
    if dup:
        issues.append(f"id_sesion duplicados: {', '.join(dup)}")

    for s in sesiones:
        sid = s.get("id_sesion", "?")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s.get("fecha", ""))):
            issues.append(f"sesión {sid}: fecha inválida")
        tipo = s.get("tipo", {})
        if not tipo.get("descripcion"):
            issues.append(f"sesión {sid}: falta tipo")
        if s.get("criterio_realizada") not in {"presentismo_quorum", "documento_labor"}:
            issues.append(f"sesión {sid}: criterio_realizada inválido")

        for name, doc in (s.get("documentos") or {}).items():
            if doc is None:
                continue
            if not re.fullmatch(r"\d+", str(doc.get("id_documento", ""))):
                issues.append(f"sesión {sid}: documento {name} sin id válido")
            if not official_url(doc.get("url", "")):
                issues.append(f"sesión {sid}: documento {name} con URL no oficial")

        for name, url in (s.get("urls") or {}).items():
            if not official_url(url):
                issues.append(f"sesión {sid}: URL {name} no oficial")

        p = s.get("presentismo", {})
        registros = p.get("registros", [])
        if p.get("total") != len(registros):
            issues.append(f"sesión {sid}: total presentismo != registros")
        if p.get("total") != (p.get("presentes", 0) + p.get("ausentes", 0)):
            issues.append(f"sesión {sid}: presentes + ausentes != total")
        if p.get("total"):
            esperada = p.get("presentes", 0) >= 30
            if s.get("criterio_realizada") == "presentismo_quorum" and bool(s.get("realizada")) != esperada:
                issues.append(f"sesión {sid}: realizada incoherente con quórum")

        for v in s.get("votaciones_nominales", []):
            vid = v.get("id_votacion", "?")
            res = v.get("resultado", {})
            total = sum(int(res.get(k, 0) or 0) for k in ("afirmativos", "negativos", "abstenciones"))
            if res.get("total_emitidos") != total:
                issues.append(f"sesión {sid} voto {vid}: total_emitidos incoherente")
            detalle = v.get("detalle_nominal", [])
            if detalle:
                c = Counter(norm(x.get("voto")) for x in detalle)
                reconocidos = c["afirmativo"] + c["negativo"] + c["abstencion"]
                if reconocidos == len(detalle):
                    if c["afirmativo"] != res.get("afirmativos", 0):
                        issues.append(f"sesión {sid} voto {vid}: afirmativos no coinciden con detalle")
                    if c["negativo"] != res.get("negativos", 0):
                        issues.append(f"sesión {sid} voto {vid}: negativos no coinciden con detalle")
                    if c["abstencion"] != res.get("abstenciones", 0):
                        issues.append(f"sesión {sid} voto {vid}: abstenciones no coinciden con detalle")
            exp = v.get("expediente")
            if exp and not official_url(exp.get("url_ficha", "")):
                issues.append(f"sesión {sid} voto {vid}: ficha de expediente no oficial")

    resumen = data.get("resumen", {})
    expected = {
        "sesiones": len(sesiones),
        "sesiones_realizadas": sum(1 for s in sesiones if s.get("realizada")),
        "registros_presentismo": sum(len(s.get("presentismo", {}).get("registros", [])) for s in sesiones),
        "asuntos_considerados": sum(len(s.get("asuntos_considerados", [])) for s in sesiones),
        "items_sanciones": sum(len(s.get("sanciones", [])) for s in sesiones),
        "votaciones_asuntos": sum(len(s.get("votaciones_nominales", [])) for s in sesiones),
        "votos_nominales": sum(len(v.get("detalle_nominal", [])) for s in sesiones for v in s.get("votaciones_nominales", [])),
        "expedientes_votados_unicos": len({v.get("id_expediente") for s in sesiones for v in s.get("votaciones_nominales", []) if v.get("id_expediente")}),
        "fallas": 0,
    }
    for key, value in expected.items():
        if resumen.get(key) != value:
            issues.append(f"resumen.{key}: {resumen.get(key)!r} != {value!r}")

    issues.extend(walk_private(data))

    print(
        "Sesiones públicas · "
        f"{len(sesiones)} sesiones · {expected['sesiones_realizadas']} realizadas · "
        f"{expected['votaciones_asuntos']} asuntos votados · "
        f"{expected['votos_nominales']} votos nominales"
    )

    if issues:
        print(f"✘ {len(issues)} problema(s) — NO se publica")
        for x in issues[:80]:
            print(f"   · {x}")
        raise SystemExit(1)
    print("✔ verificación de sesiones superada")


if __name__ == "__main__":
    main()
