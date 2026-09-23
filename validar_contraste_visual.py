#!/usr/bin/env python3
"""Barrera estática para el sistema visual accesible de CEPOES."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

ROOT = Path(__file__).resolve().parent
ARCH = ROOT / "deploy/site-overlay/assets/arquitectura.css"
CRIANZA = ROOT / "deploy/site-overlay/assets/nota-crianza.css"
PREP = ROOT / "deploy/preparar_sitio_publico.py"
CRIANZA_HTML = ROOT / "deploy/site-overlay/publicaciones/notas/criar-en-buenos-aires-sala-de-3/index.html"

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

    light = re.search(r'\.cc-page\{([^}]*)\}', crianza).group(1)
    dark = re.search(r'\[data-theme="dark"\] \.cc-page\{([^}]*)\}', crianza).group(1)
    def token(block: str, name: str) -> str:
        match = re.search(rf'{re.escape(name)}\s*:\s*(#[0-9a-fA-F]{{3,6}})', block)
        assert match, f"Falta el token {name}"
        value = match.group(1)
        if len(value) == 4:
            value = '#' + ''.join(ch * 2 for ch in value[1:])
        return value

    surface_pairs = (
        ('Texto principal', '--cc-surface-ink', 4.5),
        ('Texto secundario', '--cc-surface-muted', 4.5),
        ('Volanta', '--cc-surface-kicker', 4.5),
    )
    for theme, block in (('claro', light), ('oscuro', dark)):
        surface = token(block, '--cc-surface')
        for label, ink, threshold in surface_pairs:
            value = token(block, ink) if re.search(rf'{ink}\s*:', block) else token(light, ink)
            ratio = contrast(value, surface)
            print(f"{theme}: {label} / superficie: {ratio:.2f}:1")
            assert ratio >= threshold, f"{theme}: {label} / superficie: {ratio:.2f}:1"
    assert '.cc-page .cc-split-card h3{color:var(--cc-surface-ink)' in crianza
    assert '.cc-page .cc-split-card p{margin:0;color:var(--cc-surface-muted)' in crianza
    assert '.cc-page .cc-split-card .eyebrow{color:var(--cc-surface-kicker)' in crianza
    assert "background:var(--cc-ink)" not in crianza, "La tinta vuelve a usarse como superficie"
    assert 'source = version_local_stylesheets(source, site)' in normalizer

    spec = spec_from_file_location('prepare_site', PREP)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as directory:
        asset = Path(directory) / 'assets/nota-crianza.css'
        asset.parent.mkdir()
        asset.write_text('body{color:red}', encoding='utf-8')
        sample = '<link href="/assets/nota-crianza.css?v=2" rel="stylesheet">'
        first = module.version_local_stylesheets(sample, Path(directory))
        assert '?v=2' not in first
        asset.write_text('body{color:blue}', encoding='utf-8')
        module.css_revision.cache_clear()
        second = module.version_local_stylesheets(first, Path(directory))
        assert first != second, 'Cambió el CSS pero no su URL'
    assert 'class="cc-split-card"' in CRIANZA_HTML.read_text(encoding='utf-8')

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
