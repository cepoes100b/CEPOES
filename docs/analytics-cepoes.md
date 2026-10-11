# Medición de audiencia CEPOES — 10/10/2026

## Configuración

Cuenta GA4 411518950; propiedad 558338723 «CEPOES · cepoes.org.»; flujo web
16103971528 «CEPOES», https://cepoes.org; ID público G-Z6E4BNZXMG proporcionado
por el usuario y confirmado en la interfaz de Google Analytics.

El error inicial de countries/gold/dataaccess impidió crear la propiedad desde
el navegador integrado. El usuario la creó; la sesión autenticada ahora permite
abrir el panel y los detalles del flujo. Medición mejorada desactivada en la
interfaz para evitar duplicados y captura automática de formularios/búsquedas.

## Integración

El normalizador público incorpora meta de configuración, CSS y JS de consentimiento
una sola vez. Excluye rutas privadas, de autenticación y suscripción/confirmación/baja.
El adaptador solo carga gtag.js en el origen de producción y tras consentimiento
específico. Las vistas previas permiten probar la elección sin enviar a Google.

Aviso con aceptar/no aceptar de igual prominencia, detalles y botón permanente
«Privacidad y medición» al pie. Elección guardada durante 180 días. Retirar detiene
medición, elimina cookies _ga accesibles y recarga para aplicar la elección. Si
localStorage no está disponible, la elección se limita a esa página.

Signals y personalización publicitaria desactivados. No se envían correos, consultas,
coordenadas, tokens ni query/fragmento de URL. Referencia de origen limitada al
host. Campañas permiten únicamente utm_source/medium/campaign como códigos de
letras, números, guiones o guiones bajos, hasta 80 caracteres. No usar datos de
personas en esos códigos.

## Qué mide

- page_view: una vista por carga, ruta de la página; título analítico usa la ruta.
- Tiempo de interacción: recogida automática estándar GA4 tras cargar la etiqueta.
  Página en primer plano es aproximación de interacción, no lectura demostrada.
- reading_progress: llegada a 25/50/75/100% de desplazamiento una vez por carga.
- report_download: clic a un PDF público, no descarga completada ni lectura del PDF.
- neighborhood_view: clic a ficha /territorio/barrios/; visitas directas en page_view.
- filter_change: cambio de selector público sin transmitir valor del control.
- map_interaction: clic en controles Leaflet de zoom/capas; sin coordenadas.
- outbound_click: host destino HTTPS externo; no URL completa.

newsletter_confirmed está reservado en el adaptador; todavía no tiene un emisor
verificado. No se declara medición de altas confirmadas, búsquedas o uso completo
de cada mapa. La instrumentación de estos resultados exige otra integración.

## Referencia para decisiones

Usar GA4 en privado: Informes → adquisición (origen/medio), interacción/páginas
(ranking), eventos (PDF/filtros/mapas), dispositivos y tiempo real para diagnóstico.
Comparar últimos 28 días con los anteriores. Separar visitas nuevas y recurrentes,
volumen e interacción; revisar muestras bajas antes de cambiar prioridades.
Los visitantes son estimaciones basadas en identificadores de navegador y
consentimiento. Rechazo de medición y bloqueadores reducen cobertura.

No existe historial anterior a activación verificable en GA4. Hostinger puede
aportar registros previos cuando se disponga de acceso, sin reconstruir tiempos
de lectura. Reporte automático mensual pendiente de un acceso durable y verificado
de lectura a GA4; no se ha programado ni prometido funcionamiento desatendido.

## Validación

Node: consentimiento, orígenes/rutas, sanitización, duplicados, PDF y retirada.
Python: inyección idempotente y exclusión privada/autenticación. La revisión
visual exige salida pública completa, sites-preview y cua_repl, escritorio y
viewport móvil de 390 px. Antes de cierre verificar despliegue y recepción real
GA4; registrar resultados en el PR #214.

Fuentes:
- https://developers.google.com/analytics/devguides/collection/ga4/reference/config
- https://developers.google.com/analytics/devguides/collection/ga4/events
- https://developers.google.com/analytics/devguides/collection/ga4/views
