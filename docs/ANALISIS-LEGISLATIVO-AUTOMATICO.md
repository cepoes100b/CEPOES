# CEPOES · Análisis legislativo automático

## Objetivo

Generar borradores técnicos privados a partir de expedientes y documentos oficiales, sin publicar análisis internos en GitHub ni convertir una salida automática en una decisión definitiva.

## Flujo

1. El núcleo legislativo público actualiza agenda, expedientes, dictámenes y sesiones.
2. El workflow privado consulta a Supabase cuáles son las comisiones habilitadas para análisis.
3. Se seleccionan expedientes de esas comisiones y se priorizan por proximidad, prioridad técnica y etapa legislativa.
4. Se recupera la ficha oficial y, cuando existen, documentos PDF/DOCX oficiales vinculados.
5. Se calcula un hash de la evidencia. Si ya existe un análisis para exactamente esa evidencia, no se vuelve a ejecutar el modelo.
6. GitHub Models genera un JSON estructurado con análisis técnico equilibrado.
7. GitHub Actions obtiene un token OIDC de corta duración.
8. La Edge Function de Supabase valida emisor, audiencia, repositorio, rama y workflow antes de aceptar la carga.
9. El borrador se guarda en `expediente_analyses` como `analysis_origin = automatic`, `review_status = borrador` y `review_required = true`.
10. Un asesor/investigador revisa, corrige y valida desde `/legislativa/`.

## Contenido del borrador

- resumen ejecutivo;
- impacto jurídico/normativo;
- impacto fiscal;
- impacto territorial;
- actores afectados;
- riesgos;
- argumentos técnicos a favor y en contra;
- prioridad interna preliminar;
- recomendación técnica preliminar;
- fundamento;
- modificaciones sugeridas;
- preguntas para comisión;
- puntos técnicos para intervención;
- brechas de evidencia;
- etiquetas;
- nivel de confianza.

## Reglas de seguridad y gobernanza

- La lista concreta de comisiones prioritarias reside sólo en Supabase (`private.analysis_focus_commissions`).
- El repositorio no contiene usuarios, correos ni configuración estratégica concreta.
- El workflow no usa `service_role`, secret keys de Supabase ni claves de proveedor de IA.
- La escritura backend pasa por una Edge Function que verifica GitHub OIDC.
- La Edge Function usa credenciales administrativas sólo dentro del entorno seguro de Supabase.
- Los documentos descargados deben pertenecer al dominio oficial `legislatura.gob.ar` o sus subdominios.
- Una salida automática nunca queda `validado` por sí sola.
- Si falta evidencia, el modelo debe declararlo; no debe completar vacíos con conocimiento general.
- La recomendación automática es técnica, no electoral ni partidaria.

## Versionado

`automation_source_hash` identifica el conjunto de evidencia. Un hash ya procesado se omite. Cuando cambia la evidencia, se genera una nueva versión y la anterior queda marcada como no vigente. La interfaz debe priorizar registros `is_current = true`.

## Automatización

`.github/workflows/analizar-legislatura.yml` corre dos veces por día hábil después del workflow que actualiza el núcleo legislativo. También admite ejecución manual y una primera ejecución al incorporarse el pipeline a `main`.

## Fase siguiente

Una vez estabilizado el análisis por comisiones, ampliar el selector a la carpeta de recinto y agregar comparación explícita entre proyecto original, dictamen/despacho y texto sometido a votación.
