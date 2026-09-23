# CEPOES — Inventario R2-A2 de GitHub Actions

**Corte:** 23 de septiembre de 2026  
**Cobertura:** 56 workflows activos en `.github/workflows/`  
**Alcance:** clasificación y evidencia estática; este documento no desactiva workflows.

## Resumen

| Clasificación | Cantidad |
| --- | ---: |
| operativo | 28 |
| migrar | 5 |
| archivar | 15 |
| eliminar después de retención | 8 |

## Inventario

| Workflow | Disparadores | Permisos declarados | Evidencia sensible | Clasificación | Decisión propuesta |
| --- | --- | --- | --- | --- | --- |
| CEPOES_auditar_reparar_publicar_FINAL.yml | workflow_dispatch | contents:write | SFTP, git push, git commit, secretos | archivar | Reparación/publicación manual histórica; duplica el publicador canónico. |
| CEPOES_auditoria_reparacion_final.yml | workflow_dispatch | contents:write, actions:write | SFTP, git push, git commit, secretos, acciones:write | archivar | Auditoría/reparación manual histórica con permisos amplios. |
| CEPOES_corregir_mapa_salud_mental_V2.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Corrección puntual ya incorporada al producto vigente. |
| CEPOES_descentralizacion_V4_auditar_publicar.yml | workflow_dispatch | contents:write | SFTP, git push, git commit, secretos | archivar | Publicador de proyecto histórico; conservar evidencia antes de retirarlo. |
| CEPOES_hotfix_validador_salud_mental_V1.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Hotfix puntual ya absorbido por el flujo vigente. |
| CEPOES_instalar_interfaz_salud_mental_V1.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Instalador de una versión ya desplegada. |
| CEPOES_instalar_salud_mental_V6.yml | workflow_dispatch | contents:write | git push, git commit | eliminar después de retención | Versión reemplazada por V6_CORREGIDO. |
| CEPOES_instalar_salud_mental_V6_CORREGIDO.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Instalador corregido; conservar como evidencia de migración. |
| actualizar.yml | workflow_dispatch, schedule | contents:write | git commit | operativo | Actualización automática general de datos. |
| analizar-legislatura.yml | workflow_dispatch, schedule, push | contents:read, id-token:write | secretos | operativo | Análisis legislativo programado con identidad federada. |
| descentralizacion-comunas.yml | workflow_dispatch, schedule | contents:write | git push, git commit | operativo | Actualización programada de datos comunales. |
| desplegar-hostinger.yml | workflow_dispatch, push | contents:read | SFTP, secretos | operativo | Publicador canónico del sitio con validación y rollback inmediato. |
| diagnosticar_fuente_presupuesto.yml | workflow_dispatch | contents:read | sin escritura detectada | archivar | Diagnóstico manual puntual; no forma parte del pipeline regular. |
| dinamica-productiva.yml | workflow_dispatch, schedule, push | contents:write | git commit | operativo | Actualización de dinámica productiva. |
| endeudamiento-mensual.yml | workflow_dispatch, schedule | contents:write | git push, git commit | operativo | Pipeline mensual de endeudamiento. |
| estructura-productiva-actual.yml | workflow_dispatch, schedule, push, pull_request | contents:write, actions:write | git commit, acciones:write | operativo | Actualización vigente de estructura productiva. |
| estructura-productiva.yml | workflow_dispatch, schedule, push | contents:write | git commit | migrar | Consolidar con estructura-productiva-actual para evitar dos rutas solapadas. |
| explorar-red-peatonal.yml | workflow_dispatch, push | contents:read | sin escritura detectada | operativo | Generación controlada de artefactos de red peatonal. |
| instalar-puente-legislatura.yml | workflow_dispatch, push | contents:read | SFTP, secretos | migrar | Absorber el puente en el build/publicador canónico. |
| instalar_descentralizacion_v2.yml | workflow_dispatch | contents:write | git push, git commit | eliminar después de retención | Instalador reemplazado por versiones posteriores. |
| instalar_descentralizacion_v2_1.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Último instalador de la serie; conservar evidencia antes de retirar. |
| instalar_extractor_salud_mental_v2.yml | workflow_dispatch | contents:write | git push, git commit | eliminar después de retención | Extractor reemplazado por v3/v4. |
| instalar_extractor_salud_mental_v3.yml | workflow_dispatch | contents:write | git push, git commit | eliminar después de retención | Extractor reemplazado por v4. |
| instalar_extractor_salud_mental_v4.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Último instalador del extractor; ya no debe ejecutarse. |
| instalar_observatorio_descentralizacion (1).yml | workflow_dispatch | contents:write | git push, git commit | eliminar después de retención | Copia nominal reemplazada por v2. |
| instalar_observatorio_descentralizacion_v2.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Instalador del observatorio ya desplegado. |
| instalar_salud_mental_descentralizacion.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Integración puntual ya desplegada. |
| instalar_salud_mental_v5.yml | workflow_dispatch | contents:write | git push, git commit | eliminar después de retención | Instalador reemplazado por V6. |
| instalar_scripts_salud_mental_descentralizacion.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Instalador puntual de scripts ya versionados. |
| integrar_descentralizacion_presupuesto.yml | workflow_dispatch | contents:write | git push, git commit | eliminar después de retención | Versión reemplazada por v2/v3. |
| integrar_descentralizacion_presupuesto_v2.yml | workflow_dispatch | contents:write | git push, git commit | eliminar después de retención | Versión reemplazada por v3 seguro. |
| integrar_descentralizacion_presupuesto_v3_seguro.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Última integración puntual; conservar evidencia. |
| legislatura.yml | workflow_dispatch, schedule | contents:write | git commit | operativo | Pipeline regular de datos legislativos. |
| migraciones.yml | workflow_dispatch, schedule, push, pull_request | contents:write | git push, git commit | operativo | Pipeline regular de migraciones. |
| natalidad.yml | workflow_dispatch, schedule, pull_request | contents:write | sin escritura detectada | operativo | Pipeline regular de natalidad y demografía. |
| parche-observatorio-salud.yml | workflow_dispatch, push, workflow_run | contents:read | SFTP, secretos | migrar | Integrar el parche al overlay y despliegue canónicos. |
| personas-mayores.yml | workflow_dispatch, schedule, push, pull_request | implícito | git push, git commit | operativo | Pipeline regular de Personas Mayores. |
| prensa-borradores.yml | workflow_dispatch, schedule, push | contents:read, id-token:write | sin escritura detectada | operativo | Generación programada de borradores de prensa. |
| presupuesto.yml | workflow_dispatch, schedule | contents:write | git commit | operativo | Pipeline regular del observatorio presupuestario. |
| publicar-datos-legislativos.yml | workflow_dispatch, workflow_run | contents:read | SFTP, secretos | migrar | Mantener sólo como publicador acotado o absorberlo en el canónico. |
| reintentar-deploy-hostinger.yml | push, workflow_run | actions:write, contents:read | acciones:write | migrar | Incorporar el reintento al publicador canónico sin un segundo controlador. |
| reparar_sitemap_xml.yml | workflow_dispatch | contents:write | git push, git commit | archivar | Reparación puntual ya cubierta por validaciones del despliegue. |
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

Ningún elemento clasificado como `migrar`, `archivar` o `eliminar después de retención` se mueve o elimina sin un PR separado, confirmación de reemplazo y evidencia de que no cumple una función única.

