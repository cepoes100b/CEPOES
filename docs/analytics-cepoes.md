# Medición de audiencia CEPOES — preparación 10/10/2026

Estado: adaptador candidato y pruebas preparados; sin ID real, sin inyección en
HTML, sin medición activa y sin despliegue. La cuenta Google institucional fue
autenticada, pero Analytics muestra «Se ha producido un error interno». Los logs
del navegador registran status 0 / Unknown Error para countries/gold y dataaccess.
El fallo persiste tras recargar y abrir una pestaña nueva. Esto identifica el
componente que falla, no permite atribuir una causa a Google, la red o el navegador.

## Activación pendiente

1. Crear cuenta CEPOES y propiedad «CEPOES · cepoes.org» en GA4, zona Buenos Aires,
   moneda ARS, finalidad de contenidos y tráfico. Mantener desactivadas las opciones
   adicionales de compartir datos y publicidad. La aceptación de los términos de
   servicio requiere confirmación puntual del titular en la interfaz.
2. Crear flujo web https://cepoes.org y obtener ID G-…. El ID es público, no una
   contraseña. Desactivar medición optimizada antes de activar este adaptador:
   evita doble page_view y captura automática de formularios/búsquedas/URLs.
3. Incorporar elección de consentimiento y aviso de privacidad con revisión visual
   en sites-preview/cua_repl, usando la salida pública completa, antes de publicar.
   Invocar start solo con consentimiento específico de analítica; la suscripción
   editorial no constituye ese consentimiento. stop bloquea recogida posterior;
   recargar tras retirada. Documentar eliminación de cookies en la integración.
4. Integrar el módulo en el normalizador público; excluir zona privada, páginas de
   confirmación/baja y cualquier URL sensible. Validar cobertura de rutas y CSP.
5. Vincular eventos semánticos de mapas, fichas y lectura al adaptador. Confirmación
   de suscripción debe medir el resultado real, no clic ni envío de formulario.
6. Verificar recepción real en GA4, filtros de tráfico interno, diferencias entre
   producción y vista previa, móvil/escritorio y retirada del consentimiento.

## Adaptador preparado

assets/analytics-cepoes.js no realiza ninguna petición al cargarse. start requiere
ID válido, origen de producción, ruta pública y analyticsConsent=true. Configura
una única vista por carga, sin Signals ni personalización publicitaria. Descarta
query, fragmento, referrer completo y payload arbitrario. Registra clics a PDF
como report_download: un clic no acredita descarga completada ni lectura del PDF.
Los parámetros admitidos son ruta pública y porcentaje 25/50/75/100.

Este módulo no sustituye la configuración de privacidad de GA4 ni la validación
de sus eventos automáticos. La revisión de URLs incluye todas las rutas antes
de activación. Falta instrumentar adquisición por campañas con códigos permitidos
sin reenviar query completa.

## Reporte privado propuesto

Comparar últimos 28 días con los anteriores: visitantes estimados, sesiones,
páginas, interacción, fuentes de tráfico, dispositivos, clics a PDF, mapas,
fichas y suscripciones confirmadas. Separar tráfico de revisión y bots en la
medida que la fuente permita. Tiempo en primer plano es proxy de interacción,
no lectura demostrada. Informar muestras bajas y fecha de inicio de medición.
Cerrar cada informe con tres decisiones editoriales sustentadas en los datos.

Automatización pendiente, no programada: requiere acceso durable de lectura a
los datos de GA4. El acceso de navegador no acredita acceso para tareas futuras.
Los datos históricos de Hostinger deben inspeccionarse con acceso a hPanel/logs;
no se reconstruye tiempo de lectura retrospectivo a partir de solicitudes.

## Pruebas y fuentes

`node --test tests/analytics_cepoes.test.mjs` verifica consentimiento, rutas privadas,
vistas previas, sanitización, idempotencia, clic a PDF y retirada.

- https://developers.google.com/analytics/devguides/collection/ga4/reference/config
- https://developers.google.com/analytics/devguides/collection/ga4/events
- https://developers.google.com/analytics/devguides/collection/ga4/views

No hay cambios visuales ni publicación en esta preparación. La revisión supervisada
de consentimiento y páginas queda como requisito explícito de activación.
