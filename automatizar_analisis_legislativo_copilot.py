#!/usr/bin/env python3
"""Adaptador vigente de inferencia para el pipeline legislativo CEPOES.

GitHub Models fue retirado el 30/07/2026. Este módulo reutiliza todo el pipeline
extractivo/versionado de `automatizar_analisis_legislativo.py`, pero reemplaza
exclusivamente la función de inferencia por GitHub Copilot CLI en modo no
interactivo y sin permisos de herramientas.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess

import automatizar_analisis_legislativo as pipeline

COPILOT_MODEL = os.getenv("COPILOT_MODEL", "").strip()
MODEL_LABEL = f"github-copilot-cli:{COPILOT_MODEL or 'auto'}"


def schema_instruction() -> str:
    schema = pipeline.SCHEMA["schema"]
    return json.dumps(schema, ensure_ascii=False, separators=(",", ":"))


def extract_json(text: str) -> dict:
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S | re.I)
    if fence:
        raw = fence.group(1)
    else:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start:end + 1]
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise RuntimeError("Copilot no devolvió un objeto JSON")
    required = set(pipeline.SCHEMA["schema"]["required"])
    missing = sorted(required - set(result))
    if missing:
        raise RuntimeError(f"Respuesta de Copilot incompleta: {missing}")
    if result.get("internal_priority") not in {"critica", "alta", "media", "baja"}:
        raise RuntimeError("Prioridad inválida en salida de Copilot")
    if result.get("recommendation") not in {
        "acompanar", "acompanar_con_modificaciones", "abstenerse", "rechazar", "sin_definir"
    }:
        raise RuntimeError("Recomendación inválida en salida de Copilot")
    try:
        confidence = float(result.get("confidence"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Confianza inválida en salida de Copilot") from exc
    if not 0 <= confidence <= 1:
        raise RuntimeError("La confianza debe estar entre 0 y 1")
    result["confidence"] = confidence
    return result


def call_copilot(material: str) -> dict:
    if not os.getenv("COPILOT_GITHUB_TOKEN"):
        raise RuntimeError(
            "Falta COPILOT_GITHUB_TOKEN: para un repositorio personal GitHub requiere "
            "un fine-grained PAT con permiso Copilot Requests"
        )

    prompt = f"""
Actuá como analista legislativo técnico del CEPOES para la Ciudad Autónoma de Buenos Aires.
Tu única fuente es la EVIDENCIA OFICIAL incluida al final de este mensaje.

REGLAS OBLIGATORIAS:
- No uses herramientas, archivos locales, web, memoria externa ni conocimiento no contenido en la evidencia.
- No inventes artículos, montos, competencias, antecedentes, impactos ni posiciones de actores.
- Diferenciá hechos de inferencias. Si algo no está sustentado, incluilo en evidence_gaps.
- Presentá argumentos técnicos a favor y en contra de manera equilibrada.
- La recomendación es preliminar y técnica: consistencia jurídica, impacto fiscal, territorial/social y factibilidad.
- No uses criterios electorales, partidarios, de campaña ni propaganda.
- Si la evidencia es insuficiente para recomendar, recommendation debe ser "sin_definir".
- intervention_arguments debe contener puntos técnicos y verificables, no consignas.
- Devolvé SOLAMENTE un objeto JSON válido, sin markdown, texto introductorio ni comentarios.
- El JSON debe ajustarse exactamente a este esquema; no agregues claves:
{schema_instruction()}

EVIDENCIA OFICIAL:
{material}
""".strip()

    cmd = [
        "copilot", "-p", prompt, "-s",
        "--no-ask-user", "--no-custom-instructions", "--no-auto-update",
        "--no-remote", "--no-remote-export", "--no-color",
        "--deny-tool=shell,write,read,url,memory",
    ]
    if COPILOT_MODEL:
        cmd.extend(["--model", COPILOT_MODEL])

    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        timeout=180,
        env=os.environ.copy(),
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "Error sin detalle").strip()[-1200:]
        raise RuntimeError(f"Copilot CLI falló ({proc.returncode}): {detail}")
    return extract_json(proc.stdout)


def self_test() -> None:
    material = (
        "Expediente TEST-2026. Proyecto hipotético que crea un registro administrativo. "
        "La evidencia no informa costo fiscal ni partida presupuestaria. La autoridad de aplicación "
        "está mencionada pero no se describen nuevas facultades sancionatorias."
    )
    result = call_copilot(material)
    print("Self-test Copilot CLI OK")
    print(json.dumps({
        "internal_priority": result["internal_priority"],
        "recommendation": result["recommendation"],
        "confidence": result["confidence"],
    }, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-items", type=int, default=int(os.getenv("ANALYSIS_MAX_ITEMS", "8")))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    pipeline.call_model = call_copilot
    pipeline.MODEL_ID = MODEL_LABEL
    if args.self_test:
        self_test()
        return
    pipeline.process(max(1, min(args.max_items, 25)))


if __name__ == "__main__":
    main()
