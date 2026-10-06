# Productores de la publicación canónica

Corte y verificación de identidad: 6 de octubre de 2026. Repositorio: `cepoes100b/CEPOES`.

## Identidades y eventos

La lista ejecutable vive en `deploy/producer-workflows.json`. El publicador contrasta ID, nombre, ruta, repositorio, rama, evento, resultado e identidad del commit. Todos los eventos de publicación exigen `main`; los eventos PR y push sobre ramas de validación no se incluyen. Los seis productores iniciales fueron verificados en la primera incorporación. Para los diez siguientes se enlaza una ejecución del conector oficial de GitHub que confirma su identidad; la lista de eventos también se contrasta con el YAML vigente.

| Workflow | ID | Eventos que pueden producir | Evidencia nueva |
| --- | ---: | --- | --- |
| `actualizar.yml` | 337417145 | schedule, workflow_dispatch | Primera incorporación |
| `territorio.yml` | 339505784 | push, schedule, workflow_dispatch | Primera incorporación |
| `presupuesto.yml` | 339765461 | schedule, workflow_dispatch | Primera incorporación |
| `legislatura.yml` | 339821576 | schedule, workflow_dispatch | Primera incorporación |
| `estructura-productiva-actual.yml` | 341632026 | push, schedule, workflow_dispatch | Primera incorporación |
| `estructura-productiva.yml` | 341586229 | push, schedule, workflow_dispatch | Primera incorporación |
| `descentralizacion-comunas.yml` | 345939227 | schedule, workflow_dispatch | [run](https://github.com/cepoes100b/CEPOES/actions/runs/33320973086) |
| `dinamica-productiva.yml` | 341604701 | push, schedule, workflow_dispatch | [run](https://github.com/cepoes100b/CEPOES/actions/runs/35727963735) |
| `migraciones.yml` | 341396408 | schedule, workflow_dispatch | [run](https://github.com/cepoes100b/CEPOES/actions/runs/37393174591) |
| `natalidad.yml` | 349531314 | schedule, workflow_dispatch | [run](https://github.com/cepoes100b/CEPOES/actions/runs/34112987257) |
| `personas-mayores.yml` | 343636989 | schedule, workflow_dispatch | [run](https://github.com/cepoes100b/CEPOES/actions/runs/37374116882) |
| `salud-mental.yml` | 345939229 | schedule, workflow_dispatch | [run](https://github.com/cepoes100b/CEPOES/actions/runs/35504973010) |
| `salud-reproductiva.yml` | 349531436 | schedule, workflow_dispatch | [run](https://github.com/cepoes100b/CEPOES/actions/runs/37364609412) |
| `validar-legislatura.yml` | 339811495 | workflow_dispatch | [run](https://github.com/cepoes100b/CEPOES/actions/runs/37497141270) |
| `validar-presupuesto.yml` | 339761156 | workflow_dispatch | [run](https://github.com/cepoes100b/CEPOES/actions/runs/32547258464) |
| `endeudamiento-mensual.yml` | 340534138 | schedule, workflow_dispatch | [run](https://github.com/cepoes100b/CEPOES/actions/runs/37370433408) |

Los nombres exactos se conservan en el registro. `validar-legislatura.yml` mantiene el ID 339811495 aunque las ejecuciones históricas anteriores a las sesiones muestran un nombre más corto. Su nombre actual es «Validar núcleo legislativo y sesiones».

## Salidas de la segunda incorporación

Sólo un cambio en entradas del manifiesto permite encolar publicación. Un commit con sólo las salidas secundarias indicadas termina sin SFTP, aun con trailers válidos. Los tests ejecutan ese caso para cada archivo omitido.

| Productor | Entradas publicables | Otras salidas versionadas, sin disparador propio |
| --- | --- | --- |
| Descentralización | `deploy/site-overlay/assets/data/descentralizacion-comunas.json` | `descentralizacion_comunas.json`, copia fuente |
| Dinámica productiva | `deploy/site-overlay/assets/data/estructura-productiva/dinamica.json` | `diagnostico_dinamica_productiva.txt`; error explícito |
| Migraciones | `deploy/site-overlay/assets/data/migraciones.json` | `datos/migraciones/migraciones.json`, copia fuente |
| Natalidad | `deploy/site-overlay/assets/data/natalidad.json` | `natalidad.json`, copia fuente |
| Personas Mayores | `deploy/site-overlay/assets/data/personas-mayores.json` y `deploy/site-overlay/observatorio/personas-mayores/index.html` | Ninguna en el staging |
| Salud Mental | `deploy/site-overlay/assets/data/salud-mental.json` | `salud_mental.json`, copia fuente |
| Salud Reproductiva | `deploy/site-overlay/assets/data/salud-reproductiva.json` | `salud_reproductiva.json`, copia fuente |
| Validar Legislatura | `legislatura_publica.json`, `sesiones_publicas.json` | `estado_legislatura.json`, `estructura_legislativa.json` |
| Validar Presupuesto | `presupuesto.json`, `diagnostico_presupuestario.json` | `estado_presupuesto.json`, `presupuesto_analitico.json`, `presupuesto_historico.json`, `presupuesto_territorial.json` |
| Endeudamiento | `datos/endeudamiento/manifest.json` y agregados mensuales `AAAA-MM.json` referidos en el manifest | Matriz, crudos y diagnósticos quedan excluidos del staging automático |

## Contrato de Endeudamiento

Las únicas entradas nuevas de datos son manifest y nombres mensuales con meses 01–12. El verificador exige los esquemas existentes `cepoes-endeudamiento-manifest-v1` y `cepoes-endeudamiento-barrios-v2-compact`, verifica todos los períodos referidos y rechaza campos ajenos, valores inválidos, rutas fuera de la carpeta y enlaces simbólicos. El comando de staging devuelve exclusivamente manifest y el último período después de validarlos. No se permite el glob `datos/endeudamiento/*.json`, ni un glob recursivo de datos, ni cambios a la matriz CP4-barrio.

El publicador ejecuta el verificador antes de preparar el sitio y conserva los gates privados, respaldo durable y rollback existentes. No agrega publicadores, credenciales ni permisos; tampoco copia los agregados a nuevas rutas del sitio. `preparar_sitio_publico.py` sigue leyendo manifest y el último mes para actualizar la portada.

Fuentes de contrato inspeccionadas en main `18a2d482ae8d1defc88172430486ff3f89efe5d2`: [generador](https://github.com/cepoes100b/CEPOES/blob/18a2d482ae8d1defc88172430486ff3f89efe5d2/generar_endeudamiento_barrios.py), [manifest](https://github.com/cepoes100b/CEPOES/blob/18a2d482ae8d1defc88172430486ff3f89efe5d2/datos/endeudamiento/manifest.json) y [agregado 2026-08](https://github.com/cepoes100b/CEPOES/blob/18a2d482ae8d1defc88172430486ff3f89efe5d2/datos/endeudamiento/2026-08.json). No se descargaron microdatos.

## Diagnóstico presupuestario y dependencias directas

Se inspeccionaron por el conector oficial el [agregado vigente](https://github.com/cepoes100b/CEPOES/blob/18a2d482ae8d1defc88172430486ff3f89efe5d2/diagnostico_presupuestario.json), su [generador](https://github.com/cepoes100b/CEPOES/blob/18a2d482ae8d1defc88172430486ff3f89efe5d2/generar_diagnostico_presupuestario.py) y su [verificador](https://github.com/cepoes100b/CEPOES/blob/18a2d482ae8d1defc88172430486ff3f89efe5d2/verificar_diagnostico_presupuestario.py). El archivo contiene montos y porcentajes por función, jurisdicción y comuna, con nombres institucionales, reglas y advertencias ya existentes; no contiene personas ni registros individuales.

`deploy/preparar_sitio_publico.py` lo abre en `apply_fallbacks` y usa sus señales para las tres tarjetas de `/presupuesto/index.html`. Se agrega sólo la ruta exacta `diagnostico_presupuestario.json`, sin glob de diagnósticos ni copia integral del JSON al sitio. Ambos workflows presupuestarios verifican el diagnóstico antes de commitear. El test ejecuta cambios aislados de ese archivo desde el productor programado y el validador manual. No se cambia el contenido, método o editoriales del agregado.

Las demás salidas declaradas que permanecen fuera de entradas no son leídas directamente por los preparadores públicos inspeccionados:

| Salida excluida | Motivo comprobado |
| --- | --- |
| `descentralizacion_comunas.json`, `datos/migraciones/migraciones.json`, `natalidad.json`, `salud_mental.json`, `salud_reproductiva.json` | La copia pública correspondiente vive en `deploy/site-overlay/` y ya activa el build. Los JSON fuente duplicados no se leen desde esos paths. |
| `estado_presupuesto.json`, `estado_legislatura.json`, `estado_territorio.json`, `diagnostico_dinamica_productiva.txt`, `diagnostico_estructura_actual.txt`, `diagnostico_estructura_productiva.txt` | Estados y diagnósticos de ejecución; los preparadores no los leen. Los fallos no producen una publicación válida. |
| `presupuesto_analitico.json`, `presupuesto_historico.json`, `presupuesto_territorial.json` | Son productos intermedios/upstream del pipeline presupuestario; el build inspeccionado consume `presupuesto.json` y `diagnostico_presupuestario.json`, no estos paths. |
| `estructura_legislativa.json` | Entrada institucional del pipeline; la publicación usa `legislatura_publica.json` y `sesiones_publicas.json`. |
| `auditorias/claudia_negri_2026.json`, `auditorias/claudia_negri_2026.csv` | Archivos de auditoría del productor legislativo; el preparador no los lee ni copia. |
| `badata/` | Fuente intermedia del pipeline territorial; el build lee los productos normalizados de `equipamientos/` y `territorio.json`. |
| `datos/endeudamiento/matriz_cp_barrio.json`, `bcra_deudores/`, `diagnostico_endeudamiento_productivo.json`, `novedad_bcra.json` | Matriz congelada, crudos o diagnóstico interno; sólo manifest y meses agregados validados alimentan la portada. |

El control AST verifica todas las llamadas de lectura JSON del preparador público y Estado de los datos, además de las dos entradas del preparador legislativo. Los registros de búsqueda/informes, el catálogo de equipamientos y sus capas, y el árbol overlay ya figuran en el manifiesto. Este inventario describe dependencias del build, no presume que todas las fuentes intermedias se copian al sitio ni cambia módulos heredados o mapas.

## Límites comprobados

- Las lecturas directas del preparador público, Estado de los datos y el preparador legislativo están cubiertas por el manifiesto. La lectura variable de Endeudamiento se resuelve únicamente mediante el manifest validado. No queda una dependencia JSON directa conocida fuera entre las salidas de los productores inspeccionados.
- El encadenamiento no corrige por sí mismo fuentes remotas caídas, restricciones de TLS ni parsers rotos. Salud Mental elimina los bypass TLS preexistentes y falla antes de escribir ante errores de transporte o certificado, preservando sus salidas. Una lectura segura del CKAN el 6/10/2026 a las 17:11 UTC obtuvo HTTP 502; la disponibilidad sigue sin verificarse. Los tests de productor son offline.
- Los tests de identidad y selección no sustituyen una ejecución GitHub ni la verificación posterior del sitio. Antes de cerrar la reparación, verificar el SHA integrado, Actions del mismo SHA y el marcador público del despliegue canónico.

## Verificación reproducible

```sh
python -m unittest test_cadena_publicacion.py test_endeudamiento_publico.py
python validar_rutas_publicacion.py
python validar_rollback_durable.py
python auditar_workflows_r2.py --check docs/seguridad/inventario-workflows-r2.md
```

La matriz de tests recorre los dieciséis productores y todos sus eventos permitidos; para cada productor rechaza origen ajeno, fork, rama ajena, evento no autorizado, identidad inválida, fallo, cancelación, timeout y ejecución inconclusa. También ejecuta ausencia de commit, diagnóstico, intento anterior y publicación duplicada. Los controles de privacidad y rutas se prueban con fixtures sintéticos. Los diez pasos de commit se ejecutan además con repositorios Git locales temporales: push válido, no-op y rechazo del remoto, sin redes ni fuentes; el diagnóstico fallido de Dinámica se conserva como fallo.
