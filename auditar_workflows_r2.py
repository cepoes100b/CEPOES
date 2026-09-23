#!/usr/bin/env python3
"""Inventario reproducible de la superficie de GitHub Actions de CEPOES."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKFLOWS = ROOT / ".github" / "workflows"

# La clasificación no desactiva archivos. Documenta la decisión propuesta y obliga
# a revisar explícitamente cualquier workflow nuevo antes de incorporarlo.
DECISIONS = {
    "CEPOES_auditar_reparar_publicar_FINAL.yml": ("archivar", "Reparación/publicación manual histórica; duplica el publicador canónico."),
    "CEPOES_auditoria_reparacion_final.yml": ("archivar", "Auditoría/reparación manual histórica con permisos amplios."),
    "CEPOES_corregir_mapa_salud_mental_V2.yml": ("archivar", "Corrección puntual ya incorporada al producto vigente."),
    "CEPOES_descentralizacion_V4_auditar_publicar.yml": ("archivar", "Publicador de proyecto histórico; conservar evidencia antes de retirarlo."),
    "CEPOES_hotfix_validador_salud_mental_V1.yml": ("archivar", "Hotfix puntual ya absorbido por el flujo vigente."),
    "CEPOES_instalar_interfaz_salud_mental_V1.yml": ("archivar", "Instalador de una versión ya desplegada."),
    "CEPOES_instalar_salud_mental_V6.yml": ("eliminar después de retención", "Versión reemplazada por V6_CORREGIDO."),
    "CEPOES_instalar_salud_mental_V6_CORREGIDO.yml": ("archivar", "Instalador corregido; conservar como evidencia de migración."),
    "actualizar.yml": ("operativo", "Actualización automática general de datos."),
    "analizar-legislatura.yml": ("operativo", "Análisis legislativo programado con identidad federada."),
    "descentralizacion-comunas.yml": ("operativo", "Actualización programada de datos comunales."),
    "desplegar-hostinger.yml": ("operativo", "Publicador canónico del sitio con validación y rollback inmediato."),
    "diagnosticar_fuente_presupuesto.yml": ("archivar", "Diagnóstico manual puntual; no forma parte del pipeline regular."),
    "dinamica-productiva.yml": ("operativo", "Actualización de dinámica productiva."),
    "endeudamiento-mensual.yml": ("operativo", "Pipeline mensual de endeudamiento."),
    "estructura-productiva-actual.yml": ("operativo", "Actualización vigente de estructura productiva."),
    "estructura-productiva.yml": ("migrar", "Consolidar con estructura-productiva-actual para evitar dos rutas solapadas."),
    "explorar-red-peatonal.yml": ("operativo", "Generación controlada de artefactos de red peatonal."),
    "instalar-puente-legislatura.yml": ("migrar", "Absorber el puente en el build/publicador canónico."),
    "instalar_descentralizacion_v2.yml": ("eliminar después de retención", "Instalador reemplazado por versiones posteriores."),
    "instalar_descentralizacion_v2_1.yml": ("archivar", "Último instalador de la serie; conservar evidencia antes de retirar."),
    "instalar_extractor_salud_mental_v2.yml": ("eliminar después de retención", "Extractor reemplazado por v3/v4."),
    "instalar_extractor_salud_mental_v3.yml": ("eliminar después de retención", "Extractor reemplazado por v4."),
    "instalar_extractor_salud_mental_v4.yml": ("archivar", "Último instalador del extractor; ya no debe ejecutarse."),
    "instalar_observatorio_descentralizacion (1).yml": ("eliminar después de retención", "Copia nominal reemplazada por v2."),
    "instalar_observatorio_descentralizacion_v2.yml": ("archivar", "Instalador del observatorio ya desplegado."),
    "instalar_salud_mental_descentralizacion.yml": ("archivar", "Integración puntual ya desplegada."),
    "instalar_salud_mental_v5.yml": ("eliminar después de retención", "Instalador reemplazado por V6."),
    "instalar_scripts_salud_mental_descentralizacion.yml": ("archivar", "Instalador puntual de scripts ya versionados."),
    "integrar_descentralizacion_presupuesto.yml": ("eliminar después de retención", "Versión reemplazada por v2/v3."),
    "integrar_descentralizacion_presupuesto_v2.yml": ("eliminar después de retención", "Versión reemplazada por v3 seguro."),
    "integrar_descentralizacion_presupuesto_v3_seguro.yml": ("archivar", "Última integración puntual; conservar evidencia."),
    "legislatura.yml": ("operativo", "Pipeline regular de datos legislativos."),
    "migraciones.yml": ("operativo", "Pipeline regular de migraciones."),
    "natalidad.yml": ("operativo", "Pipeline regular de natalidad y demografía."),
    "parche-observatorio-salud.yml": ("migrar", "Integrar el parche al overlay y despliegue canónicos."),
    "personas-mayores.yml": ("operativo", "Pipeline regular de Personas Mayores."),
    "prensa-borradores.yml": ("operativo", "Generación programada de borradores de prensa."),
    "presupuesto.yml": ("operativo", "Pipeline regular del observatorio presupuestario."),
    "publicar-datos-legislativos.yml": ("migrar", "Mantener sólo como publicador acotado o absorberlo en el canónico."),
    "reintentar-deploy-hostinger.yml": ("migrar", "Incorporar el reintento al publicador canónico sin un segundo controlador."),
    "reparar_sitemap_xml.yml": ("archivar", "Reparación puntual ya cubierta por validaciones del despliegue."),
    "salud-mental.yml": ("operativo", "Pipeline regular de Salud Mental."),
    "salud-reproductiva.yml": ("operativo", "Pipeline regular de Salud Reproductiva."),
    "territorio.yml": ("operativo", "Pipeline territorial regular."),
    "validar-accesibilidad-visual.yml": ("operativo", "Control específico de contraste y accesibilidad visual."),
    "validar-analisis-automatico.yml": ("operativo", "Control del análisis automático legislativo."),
    "validar-area-legislativa.yml": ("operativo", "Control del área legislativa."),
    "validar-deporte-salud.yml": ("operativo", "Control de datos, UI y accesibilidad de Deporte y Salud."),
    "validar-endeudamiento-main.yml": ("operativo", "Control de regresión del pipeline de endeudamiento."),
    "validar-estructura-productiva-ui.yml": ("operativo", "Control de la interfaz de estructura productiva."),
    "validar-integracion-v225.yml": ("operativo", "Control de integración heredado aún referenciado por cambios vigentes."),
    "validar-legislatura.yml": ("operativo", "Control integral y actualización manual legislativa."),
    "validar-pr-r2.yml": ("operativo", "Control universal obligatorio propuesto para todo PR."),
    "validar-presupuesto.yml": ("operativo", "Control integral y actualización manual presupuestaria."),
    "validar-universo-v226.yml": ("operativo", "Control del universo legislativo consolidado."),
}


def inspect(path: Path) -> dict[str, str]:
    source = path.read_text(encoding="utf-8")
    triggers = [
        name for name in ("workflow_dispatch", "schedule", "push", "pull_request", "workflow_run")
        if re.search(rf"(?m)^  {name}\s*:", source)
    ]
    declared = re.findall(
        r"(?m)^\s{2,6}(contents|actions|checks|deployments|id-token|issues|packages|pull-requests|security-events|statuses):\s*([^#\n]+)",
        source,
    )
    permissions = ", ".join(f"{key}:{value.strip()}" for key, value in declared) or "implícito"
    evidence = []
    for label, pattern in (
        ("SFTP", r"(?i)\blftp\b|sftp://|HOSTINGER_SFTP"),
        ("git push", r"(?m)^\s*git push\b|git push origin"),
        ("git commit", r"(?m)^\s*git commit\b"),
        ("secretos", r"\$\{\{\s*secrets\."),
        ("acciones:write", r"(?m)^\s+actions:\s*write\b"),
    ):
        if re.search(pattern, source):
            evidence.append(label)
    return {
        "trigger": ", ".join(triggers) or "no detectado",
        "permissions": permissions,
        "evidence": ", ".join(evidence) or "sin escritura detectada",
    }


def inventory() -> list[dict[str, str]]:
    files = sorted(path.name for path in WORKFLOWS.glob("*.yml"))
    missing = sorted(set(files) - set(DECISIONS))
    stale = sorted(set(DECISIONS) - set(files))
    assert not missing, "Workflows sin clasificar: " + ", ".join(missing)
    assert not stale, "Clasificaciones sin workflow: " + ", ".join(stale)
    rows = []
    for name in files:
        classification, decision = DECISIONS[name]
        rows.append({"name": name, "classification": classification, "decision": decision, **inspect(WORKFLOWS / name)})
    return rows


def markdown(rows: list[dict[str, str]]) -> str:
    counts = Counter(row["classification"] for row in rows)
    lines = [
        "# CEPOES — Inventario R2-A2 de GitHub Actions",
        "",
        "**Corte:** 23 de septiembre de 2026  ",
        f"**Cobertura:** {len(rows)} workflows activos en `.github/workflows/`  ",
        "**Alcance:** clasificación y evidencia estática; este documento no desactiva workflows.",
        "",
        "## Resumen",
        "",
        "| Clasificación | Cantidad |",
        "| --- | ---: |",
    ]
    for label in ("operativo", "migrar", "archivar", "eliminar después de retención"):
        lines.append(f"| {label} | {counts[label]} |")
    lines.extend([
        "",
        "## Inventario",
        "",
        "| Workflow | Disparadores | Permisos declarados | Evidencia sensible | Clasificación | Decisión propuesta |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        cells = [row["name"], row["trigger"], row["permissions"], row["evidence"], row["classification"], row["decision"]]
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in cells) + " |")
    lines.extend([
        "",
        "## Regla de transición",
        "",
        "Ningún elemento clasificado como `migrar`, `archivar` o `eliminar después de retención` se mueve o elimina sin un PR separado, confirmación de reemplazo y evidencia de que no cumple una función única.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", type=Path)
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()
    rows = inventory()
    output = markdown(rows)
    if args.check:
        current = args.check.read_text(encoding="utf-8")
        assert current.rstrip() == output.rstrip(), f"Inventario desactualizado: {args.check}"
        print(f"Inventario R2-A2: {len(rows)} workflows clasificados y sincronizados")
    elif args.markdown:
        print(output)
    else:
        counts = Counter(row["classification"] for row in rows)
        print(f"Inventario R2-A2 válido: {len(rows)} workflows · {dict(counts)}")


if __name__ == "__main__":
    main()
