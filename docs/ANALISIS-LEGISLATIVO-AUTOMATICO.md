# CEPOES · Análisis legislativo automático

## Objetivo

Generar borradores técnicos privados a partir de expedientes y documentos oficiales, sin publicar análisis internos en GitHub ni convertir una salida automática en una decisión definitiva.

## Flujo

1. El núcleo legislativo público actualiza agenda, expedientes, dictámenes y sesiones.
2. El workflow privado consulta a Supabase cuáles son las comisiones habilitadas para análisis.
3. Se seleccionan expedientes de esas comisiones y se priorizan por proximidad, prioridad técnica y etapa legislativa.
4. Se recupera la ficha oficial y, cuando existen, documentos PDF/DOCX oficiales realmente vinculados al expediente.
5. Se detectan normas locales citadas y, cuando existe una fuente oficial registrada, se recupera normativa vigente complementaria para contraste jurídico. Esa fuente nunca cuenta como documento primario del proyecto.
6. Se calcula un hash de toda la evidencia. Si ya existe un análisis para exactamente esa evidencia, no se vuelve a ejecutar el modelo.
7. GitHub Copilot CLI genera un JSON estructurado con análisis técnico equilibrado, en modo no interactivo y sin permisos para usar herramientas externas.
8. Una capa local v3 elimina elementos no respaldados, comprueba coherencia entre posición y fundamento y clasifica la salida como análisis completo o ficha preliminar.
9. GitHub Actions obtiene un token OIDC de corta duración exclusivamente para autenticarse ante el receptor privado de Supabase.
10. La Edge Function valida emisor, audiencia, repositorio, rama y workflow y vuelve a aplicar los guardrails críticos antes de escribir.
11. El borrador se guarda en `expediente_analyses` como `analysis_origin = automatic`, `review_status = borrador` y `review_required = true`.
12. Un asesor/investigador revisa, corrige y valida desde `/legislativa/`.

## Modos de análisis

### `full`

Se utiliza sólo cuando existe al menos un documento primario del expediente. Puede incluir resumen, impactos, argumentos técnicos, preguntas y propuestas de modificación. Una recomendación sólo puede sobrevivir a los guardrails si la confianza es al menos 0,75.

### `preliminary_insufficient_evidence`

Se activa automáticamente cuando no se recupera ningún documento primario. La ficha se limita a:

- qué información oficial sí está disponible;
- qué evidencia falta;
- preguntas necesarias para completar el expediente;
- riesgos de decidir sin el texto primario.

En este modo quedan bloqueados por código y por PostgreSQL:

- recomendación;
- argumentos a favor/en contra;
- modificaciones propuestas;
- argumentos de intervención.

## Contenido del borrador completo

- resumen ejecutivo;
- impacto jurídico/normativo;
- impacto fiscal;
- impacto territorial;
- actores afectados;
- riesgos;
- argumentos técnicos a favor y en contra;
- prioridad interna preliminar;
- recomendación técnica preliminar, sólo si supera los guardrails;
- fundamento;
- modificaciones sugeridas;
- preguntas para comisión;
- puntos técnicos para intervención;
- brechas de evidencia;
- etiquetas;
- nivel de confianza;
- modo de análisis y flags de calidad.

## Grounding y coherencia v3

- Una omisión de la fuente no prueba inexistencia ni valor cero.
- No se admite el placeholder `a definir`: si un monto, plazo o umbral no está documentado, se expresa como una brecha en lenguaje natural.
- Las cifras no respaldadas se eliminan de la salida y reducen la confianza.
- Las siglas o entidades no presentes en la evidencia continúan siendo un error duro.
- Si la recomendación termina en `sin_definir`, el fundamento y los puntos de intervención no pueden conservar frases de apoyo, rechazo, abstención o voto.
- La normativa vigente complementaria se rotula por separado y sólo se usa para contraste jurídico; nunca reemplaza el proyecto ni eleva el conteo de documentos primarios.
- Cuando es posible identificar el artículo modificado, el motor extrae el fragmento pertinente de la norma vigente para comparar texto vigente y propuesta.

## Reglas de seguridad y gobernanza

- La lista concreta de comisiones prioritarias reside sólo en Supabase (`analysis_focus_commissions`).
- Esa tabla tiene RLS habilitado, no posee políticas para clientes y se revocó el acceso a `anon` y `authenticated`; sólo el backend administrativo puede leerla.
- El repositorio no contiene usuarios, correos ni configuración estratégica concreta.
- El workflow no usa `service_role`, secret keys de Supabase ni claves de proveedores externos de modelos.
- Al tratarse de un repositorio personal, Copilot CLI se autentica mediante el secreto de GitHub Actions `COPILOT_GITHUB_TOKEN`, con permiso **Copilot Requests**.
- La escritura backend pasa por una Edge Function que verifica GitHub OIDC.
- La Edge Function usa credenciales administrativas sólo dentro del entorno seguro de Supabase.
- Los documentos primarios descargados deben pertenecer a `legislatura.gob.ar` o sus subdominios.
- Las fuentes complementarias admitidas se limitan a dominios oficiales registrados del Gobierno de la Ciudad.
- Una salida automática nunca queda `validado` por sí sola.
- La recomendación automática es técnica, no electoral ni partidaria.

## Versionado

`automation_source_hash` identifica el conjunto de evidencia primaria y complementaria. Un hash ya procesado se omite. Cuando cambia cualquier fuente, se genera una nueva versión y la anterior queda marcada como no vigente. La interfaz prioriza `is_current = true`.

## Interfaz

Los análisis automáticos muestran procedencia, estado de revisión, confianza y cantidad de fuentes. Las fichas sin documento primario aparecen como `EVIDENCIA INSUFICIENTE` y no muestran una posición. La UI también incorpora actores afectados, argumentos técnicos y brechas de evidencia.

## Automatización

`.github/workflows/analizar-legislatura.yml` corre dos veces por día hábil después del workflow que actualiza el núcleo legislativo. También admite ejecución manual.

## Credencial necesaria

GitHub retiró GitHub Models el 30 de julio de 2026. Para repositorios personales, Copilot CLI en Actions requiere un fine-grained PAT del propietario con permiso **Copilot Requests**, guardado como secreto `COPILOT_GITHUB_TOKEN`. No se versiona ni se envía a Supabase.

## Fase siguiente

Después de validar v3 con los tres casos piloto, ejecutar un lote de 10 expedientes de las comisiones priorizadas. Sólo si ese lote mantiene grounding y coherencia se amplía el volumen y luego se extiende el selector a la carpeta de recinto.
