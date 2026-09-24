# CEPOES — Inventario R2-A2 de GitHub Actions

**Corte:** 23 de septiembre de 2026  
**Cobertura:** 30 workflows activos en `.github/workflows/`\
**Archivo no ejecutable:** 26 workflows históricos bajo `docs/seguridad/workflows-retirados/`\
**Alcance:** superficie activa posterior a la desactivación reversible propuesta en R2-A2.

## Resumen

| Clasificación | Cantidad |
| --- | ---: |
| operativo | 30 |
| migrar | 0 |

## Inventario

| Workflow | Disparadores | Permisos declarados | Evidencia sensible | Clasificación | Decisión propuesta |
| --- | --- | --- | --- | --- | --- |
| actualizar.yml | workflow_dispatch, schedule | contents:write | git commit | operativo | Actualización automática general de datos. |
| analizar-legislatura.yml | workflow_dispatch, schedule, push | contents:read, id-token:write | secretos | operativo | Análisis legislativo programado con identidad federada. |
| descentralizacion-comunas.yml | workflow_dispatch, schedule | contents:write | git push, git commit | operativo | Actualización programada de datos comunales. |
| desplegar-hostinger.yml | workflow_dispatch, push | contents:read | SFTP, secretos | operativo | Publicador canónico del sitio con validación y rollback inmediato. |
| dinamica-productiva.yml | workflow_dispatch, schedule, push | contents:write | git commit | operativo | Actualización de dinámica productiva. |
| endeudamiento-mensual.yml | workflow_dispatch, schedule | contents:write | git push, git commit | operativo | Pipeline mensual de endeudamiento. |
| estructura-productiva-actual.yml | workflow_dispatch, schedule, push, pull_request | contents:write | git commit | operativo | Actualización vigente de estructura productiva. |
| estructura-productiva.yml | workflow_dispatch, schedule, push | contents:write | git commit | operativo | Base estructural RUS 2017; salida diferenciada y publicación por el disparador canónico. |
| explorar-red-peatonal.yml | workflow_dispatch, push | contents:read | sin escritura detectada | operativo | Generación controlada de artefactos de red peatonal. |
| legislatura.yml | workflow_dispatch, schedule | contents:write | git commit | operativo | Pipeline regular de datos legislativos. |
| migraciones.yml | workflow_dispatch, schedule, push, pull_request | contents:write | git push, git commit | operativo | Pipeline regular de migraciones. |
| natalidad.yml | workflow_dispatch, schedule, pull_request | contents:write | sin escritura detectada | operativo | Pipeline regular de natalidad y demografía. |
| personas-mayores.yml | workflow_dispatch, schedule, push, pull_request | implícito | git push, git commit | operativo | Pipeline regular de Personas Mayores. |
| prensa-borradores.yml | workflow_dispatch, schedule, push | contents:read, id-token:write | sin escritura detectada | operativo | Generación programada de borradores de prensa. |
| presupuesto.yml | workflow_dispatch, schedule | contents:write | git commit | operativo | Pipeline regular del observatorio presupuestario. |
| reintentar-deploy-hostinger.yml | workflow_run | actions:write, contents:read | acciones:write | operativo | Reintenta sólo jobs fallidos del publicador canónico de main, hasta tres intentos. |
| salud-mental.yml | workflow_dispatch, schedule | contents:write | git push, git commit | operativo | Pipeline regular de Salud Mental. |
| salud-reproductiva.yml | workflow_dispatch, schedule, pull_request | contents:write | sin escritura detectada | operativo | Pipeline regular de Salud Reproductiva. |
| territorio.yml | workflow_dispatch, schedule, push | contents:write | git commit | operativo | Pipeline territorial regular. |
| validar-accesibilidad-visual.yml | workflow_dispatch, push, pull_request | contents:read | sin escritura detectada | operativo | Control específico de contraste y accesibilidad visual. |
| validar-analisis-automatico.yml | workflow_dispatch, pull_request | contents:read | secretos | operativo | Control del análisis automático legislativo. |
| validar-area-legislativa.yml | workflow_dispatch, push, pull_request | contents:read | sin escritura detectada | operativo | Control del área legislativa. |
| validar-deporte-salud.yml | push, pull_request | contents:read | sin escritura detectada | operativo | Control de datos, UI y accesibilidad de Deporte y Salud. |
| validar-endeudamiento-main.yml | workflow_dispatch, pull_request | contents:read | sin escritura detectada | operativo | Control de regresión del pipeline de endeudamiento. |
| validar-estructura-productiva-ui.yml | push, pull_request | contents:read | sin escritura detectada | operativo | Control de la interfaz de estructura productiva. |
| validar-integracion-v225.yml | workflow_dispatch, pull_request | contents:read | sin escritura detectada | operativo | Control de integración heredado aún referenciado por cambios vigentes. |
| validar-legislatura.yml | workflow_dispatch, pull_request | contents:write | git push, git commit | operativo | Control integral y actualización manual legislativa. |
| validar-pr-r2.yml | workflow_dispatch, pull_request | contents:read | sin escritura detectada | operativo | Control universal obligatorio propuesto para todo PR. |
| validar-presupuesto.yml | workflow_dispatch | contents:write | git push, git commit | operativo | Control integral y actualización manual presupuestaria. |
| validar-universo-v226.yml | workflow_dispatch, pull_request | contents:read | sin escritura detectada | operativo | Control del universo legislativo consolidado. |

## Regla de transición

No quedan workflows activos clasificados como `migrar`. Los dos productores de estructura productiva conservan salidas distintas y publican únicamente mediante el disparador por cambios del publicador canónico. Los 26 workflows históricos quedan fuera de `.github/workflows/`, preservados con checksum; ninguno puede restaurarse al área ejecutable sin revisión y autorización explícitas.
