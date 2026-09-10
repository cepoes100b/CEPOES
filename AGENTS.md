# AGENTS.md — CEPOES

## Propósito del repositorio

Este repositorio mantiene el observatorio público de CEPOES sobre la Ciudad de Buenos Aires, sus pipelines de datos, productos editoriales, módulos presupuestarios y territoriales, actividad legislativa y despliegue a producción.

Toda intervención debe sostener tres objetivos simultáneos:

1. diagnóstico verificable;
2. interpretación crítica clara;
3. conexión con propuestas o acciones políticas cuando corresponda.

## Reglas obligatorias de trabajo

- Trabajar siempre en una rama nueva creada desde el `main` vigente.
- No escribir directamente en `main`.
- Antes de aplicar cambios, verificar el SHA esperado de la rama.
- Limitar cada rama y pull request a un objetivo identificable.
- No fusionar, desplegar ni ejecutar workflows de escritura sin autorización explícita.
- No modificar archivos ajenos al alcance pedido, aunque parezcan obsoletos.
- Preservar cambios preexistentes y no reemplazar archivos completos cuando alcance una edición localizada.

## Fuentes, datos y trazabilidad

- Priorizar fuentes públicas primarias: IDECBA, INDEC, BA Data, BCRA, ARCA y fuentes oficiales de la Legislatura.
- Registrar para cada indicador la fuente, URL estable, fecha de corte, fecha de actualización y método de transformación.
- Diferenciar de forma visible datos observados, estimaciones, proyecciones e interpretaciones.
- No presentar datos sintéticos, muestras o valores de demostración como datos oficiales.
- No inferir cobertura territorial o temporal que la fuente no permita sostener.
- La asignación CP4 → barrio es una estimación y debe conservar su advertencia metodológica.
- Si una fuente cambia de formato, conservar el último resultado válido y fallar de manera explícita; no publicar estructuras parciales silenciosamente.

## Archivos generados y sensibles al pipeline

- Tratar `datos.json`, `calendario.json`, los archivos `estado_*.json`, las salidas presupuestarias y territoriales y la capa legislativa como productos versionados del pipeline.
- Preferir modificar la fuente, parser, generador o verificador correspondiente antes que editar manualmente una salida generada.
- Excepción documentada: los bloques manuales de presupuesto, censo y población dentro de `datos.json` deben preservarse según el contrato del generador.
- No acortar series, eliminar jurisdicciones ni sustituir valores válidos por nulos sin una justificación documentada.
- Mantener la capa legislativa pública descriptiva: no incorporar allí posiciones políticas, recomendaciones, responsables, argumentos estratégicos ni notas internas.
- No sobrescribir un archivo que cambió desde la instantánea auditada. Detenerse y comparar el nuevo estado.

## Python y pipelines

- Mantener separadas descarga, normalización, generación y verificación.
- Los descargadores deben usar páginas o endpoints estables, no enlaces temporales a archivos cuando exista una fuente canónica.
- Los parsers deben tolerar las convenciones documentadas de datos faltantes y formatos locales sin convertir errores en ceros.
- Toda modificación de un pipeline debe incluir o actualizar una verificación reproducible.
- Evitar duplicar scripts con sufijos incrementales (`_v2`, `_v3`, etc.) cuando pueda evolucionarse el archivo canónico con historial Git.
- No eliminar variantes históricas ni consolidarlas sin una tarea explícita de saneamiento.

## GitHub Actions

- Revisar primero si existe un workflow canónico capaz de resolver la tarea.
- No crear workflows instaladores, parches o hotfix temporales salvo necesidad justificada y autorización explícita.
- Evitar scripts extensos incrustados dentro del YAML; ubicarlos en archivos versionados y testeables.
- Usar versiones actuales y soportadas de las acciones.
- Aplicar permisos mínimos, declarar `permissions` explícitamente y no imprimir secretos ni URLs autenticadas.
- Los workflows que escriben en el repositorio deben validar antes de commitear y evitar commits vacíos.
- Los despliegues deben ejecutarse únicamente después de validaciones satisfactorias.

## Web, mapas y experiencia de usuario

- Verificar escritorio y móvil en cada cambio visible.
- Mantener consistencia exacta entre valor, color, leyenda, tooltip, período y unidad.
- Los mapas deben preservar geometrías, límites, etiquetas y selección territorial correctos.
- Toda cifra destacada debe incluir comparación pertinente, período y fuente.
- Evitar controles que desplacen el contenido o produzcan saltos de página.
- Mantener contraste, foco de teclado, etiquetas accesibles y mensajes de error comprensibles.
- No degradar rutas, enlaces, suscripción, buscador ni zona privada al modificar la portada u otro módulo.

## Calidad editorial

- Usar lenguaje público claro, sin jerga técnica innecesaria.
- No confundir hallazgos descriptivos con conclusiones causales.
- Respaldar críticas de gestión con evidencia verificable.
- Cuando el producto lo permita, conectar el diagnóstico con una posición, acción o propuesta de CEPOES.
- Priorizar institucionalmente las acciones de Claudia Negri y del peronismo sin alterar datos ni ocultar limitaciones metodológicas.

## Seguridad y privacidad

- Nunca versionar credenciales, tokens, cookies, claves privadas, archivos `.env` ni URLs firmadas.
- No exponer lógica privada, notas internas o información de usuarios en la capa pública.
- No modificar autenticación, permisos o datos de la zona privada sin una revisión de seguridad específica.
- Redactar secretos que aparezcan accidentalmente en logs, artifacts o respuestas de servicios externos.

## Validación mínima antes de cerrar

Según el alcance, ejecutar y registrar:

- sintaxis y pruebas del código modificado;
- verificadores específicos del pipeline;
- validez de JSON y coherencia de esquema;
- cobertura esperada de 15 comunas y 48 barrios cuando corresponda;
- no regresión en longitud de series;
- consistencia entre datos, mapa y leyenda;
- revisión móvil y de accesibilidad para cambios visuales;
- diff completo contra `main`;
- resultado de GitHub Actions cuando se haya ejecutado.

## Entrega

El cierre debe informar:

- archivos modificados;
- fuentes utilizadas;
- pruebas realizadas y sus resultados;
- limitaciones o datos pendientes;
- enlace al pull request;
- impacto esperado sobre producción;
- único próximo paso recomendado.

