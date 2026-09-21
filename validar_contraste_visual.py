#!/usr/bin/env python3
"""Barrera estática para el sistema visual accesible de CEPOES."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCH = ROOT / "deploy/site-overlay/assets/arquitectura.css"
CRIANZA = ROOT / "deploy/site-overlay/assets/nota-crianza.css"
PREP = ROOT / "deploy/preparar_sitio_publico.py"

REQUIRED_ALIASES = {
    "--bg": "--papel",
    "--fondo": "--papel",
    "--card": "--panel",
    "--surface": "--panel",
    "--ink": "--tinta",
    "--text": "--tinta2",
    "--muted": "--gris",
    "--soft": "--papel2",
    "--border": "--borde",
    "--line": "--borde",
    "--accent": "--marca-osc",
}

PAIRS = {
    "CTA claro": ("#00a7e1", "#102430", 4.5),
    "CTA oscuro": ("#3ec8f0", "#102430", 4.5),
    "Texto secundario claro / blanco": ("#536d83", "#ffffff", 4.5),
    "Texto secundario claro / papel": ("#536d83", "#f2f6fa", 4.5),
    "Texto secundario oscuro / panel": ("#afc0cd", "#152634", 4.5),
    "Texto terciario oscuro / panel": ("#9cb2c3", "#152634", 4.5),
    "Acento claro / blanco": ("#0079a8", "#ffffff", 4.5),
    "Acento oscuro / panel": ("#8fdcf5", "#152634", 4.5),
    "Foco claro / blanco": ("#005f85", "#ffffff", 3.0),
    "Foco oscuro / papel": ("#8fdcf5", "#0e1b26", 3.0),
}


def luminance(value: str) -> float:
    channels = [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    values = sorted((luminance(foreground), luminance(background)))
    return (values[1] + 0.05) / (values[0] + 0.05)


def main() -> None:
    architecture = ARCH.read_text(encoding="utf-8")
    crianza = CRIANZA.read_text(encoding="utf-8")
    normalizer = PREP.read_text(encoding="utf-8")

    assert "CEPOES ACCESSIBILITY SYSTEM v1" in architecture, "Falta el sistema global de accesibilidad"
    for alias, source in REQUIRED_ALIASES.items():
        pattern = rf"{re.escape(alias)}\s*:\s*var\({re.escape(source)}\)"
        assert re.search(pattern, architecture), f"Falta el alias semántico {alias} → {source}"

    assert '--cc-surface:#16232f' in crianza
    assert '--cc-surface:#102430' in crianza
    assert "background:var(--cc-ink)" not in crianza, "La tinta vuelve a usarse como superficie"
    assert 'ARCHITECTURE_CSS = "/assets/arquitectura.css?v=21"' in normalizer

    failures = []
    for label, (foreground, background, required) in PAIRS.items():
        ratio = contrast(foreground, background)
        print(f"{label}: {ratio:.2f}:1 (mínimo {required:.1f}:1)")
        if ratio < required:
            failures.append(f"{label}: {ratio:.2f}:1")

    assert not failures, "Contrastes insuficientes:\n- " + "\n- ".join(failures)
    assert architecture.count("{") == architecture.count("}"), "Llaves desbalanceadas en arquitectura.css"
    assert crianza.count("{") == crianza.count("}"), "Llaves desbalanceadas en nota-crianza.css"
    print("Sistema visual accesible: tokens, superficies y pares críticos válidos")


if __name__ == "__main__":
    main()
