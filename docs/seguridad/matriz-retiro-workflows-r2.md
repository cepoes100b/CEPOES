# CEPOES — Matriz de retiro de workflows históricos R2-A2

**Corte:** 23 de septiembre de 2026  
**Base verificada:** `main` en `e75da214f9ba8146e5e92bae528e2a429a0d9dd3`  
**Cobertura:** 23 workflows clasificados como `archivar` o `eliminar después de retención`  
**Alcance:** evidencia y plan de transición; este documento no desactiva, mueve ni elimina workflows.

## 1. Resultado

Los 23 candidatos son instaladores, reparaciones o publicadores puntuales con ejecución exclusivamente manual mediante `workflow_dispatch`. Ninguno aporta hoy una actualización programada o un control requerido por pull requests. Sus resultados vigentes están versionados y cubiertos por pipelines o verificadores canónicos.

La conclusión es **retirable con transición controlada**, no “eliminar de inmediato”. La desactivación debe realizarse en otro pull request y sólo después de una última comprobación de reemplazos, historial de ejecuciones y controles verdes.

## 2. Criterios

- **Reemplazo confirmado:** existe un workflow, script o verificador canónico que cubre la función operativa vigente.
- **Sin función única:** el archivo sólo instala, repara o publica una versión ya materializada; no produce una actualización periódica distinta.
- **Archivar:** mover fuera de `.github/workflows/` y conservar una copia no ejecutable con checksum e identificación del commit de origen.
- **Eliminar después de retención:** aplicar primero el mismo archivo no ejecutable, observar 90 días y retirar luego esa copia; el historial Git permanece como evidencia.
- **Retención:** comienza con la fusión del PR que desactive el workflow, no con la fecha de esta matriz.

## 3. Matriz verificable

| Workflow | Familia y función histórica | Evidencia del reemplazo vigente | Función operativa única | Tratamiento | Riesgo mientras siga activo |
| --- | --- | --- | --- | --- | --- |
| `CEPOES_auditar_reparar_publicar_FINAL.yml` | Reparar, auditar y publicar Descentralización por SFTP | `desplegar-hostinger.yml`, `validar_sitio_despliegue.py` y activos versionados de Descentralización | No; duplica validación, publicación y rollback canónicos | archivar | alto |
| `CEPOES_auditoria_reparacion_final.yml` | Reparación integral y disparo del despliegue de Descentralización | Publicador canónico y verificadores de sitio/datos | No; combina controles ya permanentes con escritura directa | archivar | alto |
| `CEPOES_corregir_mapa_salud_mental_V2.yml` | Corrección puntual del mapa y la interfaz de Salud Mental | `validar_sitio_despliegue.py` controla página, JS, CSS y dataset vigentes | No; la corrección ya está materializada | archivar | medio |
| `CEPOES_descentralizacion_V4_auditar_publicar.yml` | Instalar la V4 y publicarla directamente | Página, JS, CSS y datasets están versionados; `desplegar-hostinger.yml` los publica | No; conserva una instantánea histórica extensa | archivar | alto |
| `CEPOES_hotfix_validador_salud_mental_V1.yml` | Hotfix puntual del contrato de despliegue | Los controles de Salud Mental están en `validar_sitio_despliegue.py` | No; el hotfix ya fue absorbido | archivar | medio |
| `CEPOES_instalar_interfaz_salud_mental_V1.yml` | Instalar página, JS, CSS y enlaces de Salud Mental | Activos vigentes en `deploy/site-overlay/` y contrato en `validar_sitio_despliegue.py` | No; instalador de una versión ya desplegada | archivar | medio |
| `CEPOES_instalar_salud_mental_V6.yml` | Instalar pipeline de Salud Mental anterior a la corrección | Reemplazado por V6_CORREGIDO y por los archivos canónicos vigentes | No; versión supersedida | eliminar después de retención | medio |
| `CEPOES_instalar_salud_mental_V6_CORREGIDO.yml` | Instalar el pipeline corregido de Salud Mental | `salud-mental.yml`, `actualizar_salud_mental.py` y `verificar_salud_mental.py` | No; el resultado final está versionado | archivar | medio |
| `diagnosticar_fuente_presupuesto.yml` | Diagnóstico manual de una fuente presupuestaria | `presupuesto.yml` y verificadores presupuestarios mantienen el pipeline vigente | No; utilidad diagnóstica puntual sin dependencia regular | archivar | bajo |
| `instalar_descentralizacion_v2.yml` | Instalar generador y verificador de Descentralización | Reemplazado por v2_1 y por scripts canónicos vigentes | No; versión supersedida | eliminar después de retención | medio |
| `instalar_descentralizacion_v2_1.yml` | Último instalador del generador de Descentralización | `generar_descentralizacion_comunas.py`, `verificar_descentralizacion_comunas.py` y `descentralizacion-comunas.yml` | No; el resultado final está versionado | archivar | medio |
| `instalar_extractor_salud_mental_v2.yml` | Instalar extractor V2 | Reemplazado por V3, V4 y el `actualizar_salud_mental.py` vigente | No; versión supersedida | eliminar después de retención | medio |
| `instalar_extractor_salud_mental_v3.yml` | Instalar extractor V3 | Reemplazado por V4 y el script canónico vigente | No; versión supersedida | eliminar después de retención | medio |
| `instalar_extractor_salud_mental_v4.yml` | Instalar último extractor previo al pipeline estable | `actualizar_salud_mental.py` y `salud-mental.yml` ejecutan la actualización vigente | No; instalador histórico del script actual | archivar | medio |
| `instalar_observatorio_descentralizacion (1).yml` | Primera copia del instalador del observatorio | Reemplazado por el instalador v2 y por activos versionados | No; copia nominal supersedida | eliminar después de retención | medio |
| `instalar_observatorio_descentralizacion_v2.yml` | Instalar página, datos y JS de Descentralización | Activos vigentes y contrato completo en `validar_sitio_despliegue.py` | No; instalador de producto ya materializado | archivar | medio |
| `instalar_salud_mental_descentralizacion.yml` | Integrar pipelines de Salud Mental y Descentralización | `salud-mental.yml` y `descentralizacion-comunas.yml` operan por separado | No; integración puntual ya aplicada | archivar | medio |
| `instalar_salud_mental_v5.yml` | Instalar pipeline V5 de Salud Mental | Reemplazado por V6_CORREGIDO y archivos canónicos actuales | No; versión supersedida | eliminar después de retención | medio |
| `instalar_scripts_salud_mental_descentralizacion.yml` | Instalar cuatro scripts de ambas familias | Los cuatro scripts están versionados y sus workflows canónicos los consumen | No; instalador puntual | archivar | medio |
| `integrar_descentralizacion_presupuesto.yml` | Primera integración de Descentralización en Presupuesto | Reemplazada por v2/v3 y por página/activos vigentes | No; versión supersedida | eliminar después de retención | medio |
| `integrar_descentralizacion_presupuesto_v2.yml` | Segunda integración de Descentralización en Presupuesto | Reemplazada por v3 seguro y contrato actual de despliegue | No; versión supersedida | eliminar después de retención | medio |
| `integrar_descentralizacion_presupuesto_v3_seguro.yml` | Última integración puntual, con controles previos | Página, sitemaps, datos y JS están versionados y validados en cada despliegue | No; el resultado final está materializado | archivar | medio |
| `reparar_sitemap_xml.yml` | Normalizar una vez el namespace y las entradas del sitemap | `validar_sitio_despliegue.py` parsea el XML, exige URLs y bloquea duplicados | No; reparación puntual ya aplicada | archivar | medio |

## 4. Evidencia transversal

- Los 23 archivos coinciden byte por byte con los blobs del `main` verificado.
- Los 23 sólo declaran `workflow_dispatch`; no tienen `schedule`, `push`, `pull_request` ni `workflow_run`.
- Ninguno apareció entre las 30 ejecuciones más recientes del repositorio consultadas al corte. Esto prueba ausencia reciente, pero no reemplaza la revisión completa del historial antes de desactivarlos.
- Salud Mental conserva pipeline, actualizador, verificador, página, JS, CSS y dataset versionados.
- Descentralización conserva pipeline, generador, verificador, página, JS, CSS y tres datasets versionados.
- El despliegue canónico valida ambos productos, el sitemap y los activos requeridos antes de publicar.

## 5. Secuencia de retiro propuesta

1. **Reconciliar nuevamente `main` y el historial de ejecución** inmediatamente antes del cambio.
2. **Mover los 23 workflows fuera de `.github/workflows/`** en un PR exclusivo, como archivos no ejecutables bajo `docs/seguridad/workflows-retirados/`, preservando nombre, checksum y commit de origen.
3. **Actualizar el inventario y su verificador** para exigir que sólo los 28 operativos y los 5 a migrar permanezcan activos.
4. **Ejecutar R2, todos los validadores afectados y un build local**, sin publicar el sitio.
5. **Conservar indefinidamente los 15 archivables** y observar durante 90 días los 8 marcados para eliminación.
6. **Eliminar sólo las ocho copias con retención cumplida** en otro PR, siempre que no exista pedido de restauración o evidencia de función única.

## 6. Gate para el próximo PR

El PR de desactivación sólo puede fusionarse si:

- el `main` base no cambió respecto del SHA revisado o el análisis fue rehecho;
- el historial completo no muestra uso operativo posterior a esta matriz;
- siguen presentes todos los reemplazos citados;
- el inventario activo queda sincronizado;
- `R2 / controles obligatorios` y los checks específicos finalizan en verde;
- no modifica Hostinger, DNS, credenciales, accesos, analítica ni el ruleset.

