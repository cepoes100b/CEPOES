#!/usr/bin/env python3
"""Adaptador de proveedor para el análisis legislativo privado CEPOES.

El pipeline y sus guardrails no dependen del proveedor. Soporta:
- GitHub Copilot CLI (credencial COPILOT_GITHUB_TOKEN);
- OpenAI API (credencial OPENAI_API_KEY), usando Structured Outputs.

ANALYSIS_MODEL_PROVIDER puede ser: auto, copilot, openai.
En auto se prefiere OpenAI si existe su secreto; si no, Copilot.
"""
from __future__ import annotations

import json
import os

import requests

import automatizar_analisis_legislativo as pipeline
import automatizar_analisis_legislativo_copilot as copilot_schema
import automatizar_analisis_legislativo_hardened as strict

OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = os.getenv("OPENAI_ANALYSIS_MODEL", "gpt-5.6-terra").strip() or "gpt-5.6-terra"
TIMEOUT = 180


def provider_name() -> str:
    requested = os.getenv("ANALYSIS_MODEL_PROVIDER", "auto").strip().lower() or "auto"
    if requested not in {"auto", "copilot", "openai"}:
        raise RuntimeError(f"ANALYSIS_MODEL_PROVIDER inválido: {requested}")
    if requested == "auto":
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        return "copilot"
    return requested


def schema_payload() -> dict:
    # Reutiliza el esquema canónico del pipeline; no duplica contratos de salida.
    return pipeline.SCHEMA["schema"]


def call_openai(prompt: str) -> dict:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Falta OPENAI_API_KEY para ANALYSIS_MODEL_PROVIDER=openai")

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Respondé exclusivamente con el JSON solicitado. "
                    "No uses herramientas, web, memoria externa ni conocimiento fuera de la evidencia incluida en el prompt."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "cepoes_legislative_analysis",
                "strict": True,
                "schema": schema_payload(),
            },
        },
    }
    response = requests.post(
        OPENAI_ENDPOINT,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        detail = response.text[:1200]
        raise RuntimeError(f"OpenAI API falló HTTP {response.status_code}: {detail}")
    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
    except Exception as exc:
        raise RuntimeError(f"Respuesta OpenAI no interpretable: {exc}") from exc
    required = set(pipeline.SCHEMA["schema"]["required"])
    missing = sorted(required - set(result))
    if missing:
        raise RuntimeError(f"Respuesta OpenAI incompleta: {missing}")
    return result


def call_provider(prompt: str) -> tuple[dict, str]:
    provider = provider_name()
    if provider == "openai":
        result = call_openai(prompt)
        return result, f"openai:{OPENAI_MODEL}"
    # Copilot conserva el runner endurecido que prohíbe herramientas externas.
    result = strict.run_copilot(prompt)
    model = os.getenv("COPILOT_MODEL", "").strip() or "auto"
    return result, f"github-copilot-cli:{model}"


def static_self_test() -> None:
    assert provider_name() in {"copilot", "openai"}
    schema = schema_payload()
    assert schema.get("type") == "object"
    assert "confidence" in schema.get("properties", {})
    assert "recommendation" in schema.get("properties", {})
    print("Proveedor legislativo · validación estática OK")
    print(f"  proveedor_resuelto={provider_name()}")


if __name__ == "__main__":
    static_self_test()
