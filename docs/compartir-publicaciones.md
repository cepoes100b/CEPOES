# Compartir contenido público — CEPOES

## Resultado

La salida pública incorpora una fila discreta de iconos al comienzo de cada página canónica: WhatsApp, X, Facebook, copiar enlace, Instagram y compartir desde el dispositivo cuando está disponible. Los controles usan los tokens y la tipografía del sitio, foco visible, nombres accesibles y objetivos táctiles de 44 px. El diálogo de Instagram permite guardar dos placas y copiar el título con el enlace. La publicación en redes la decide y realiza el lector.

## Fuente y generación

`deploy/compartir_publicaciones.py` se ejecuta desde el normalizador canónico. Usa el título y la descripción de la página y, para informes registrados, los metadatos de `deploy/reports-registry.json`. Genera PNG de 1200 × 630 para la vista previa de enlaces, 1080 × 1350 para publicaciones y 1080 × 1920 para historias. Los informes con portada PNG/JPEG incorporan la portada completa, sin recortarla. Las miniaturas del catálogo y los PDF originales permanecen intactos. Las placas son materiales de difusión solicitados por Agustín, adicionales a la descarga del informe completo.

La imagen usa composición tipográfica y motivos decorativos urbanos; no introduce cifras ni gráficos estadísticos. El monitor Seguridad y derechos conserva la excepción de placas sin firma CEPOES / 100 Barrios. Las imágenes llevan una huella del contenido; los CSS y JS llevan revisión por contenido. Cada build elimina únicamente placas generadas que ya no se referencian.

Se reemplazan las etiquetas Open Graph y Twitter Cards de las páginas elegibles. La presentación final y el caché del enlace dependen de cada plataforma. Instagram ofrece descarga de placas y copia de texto; compartir una imagen desde el dispositivo requiere compatibilidad de Web Share y la aplicación elegida por la persona. No se promete publicación directa en Instagram.

## Alcance, privacidad y mapas

Se excluyen páginas privadas, administrativas, de autenticación/suscripción, noindex, redirecciones y alias. Se usa la URL canónica de cepoes.org. Se conservan únicamente filtros territoriales documentados (`comuna`, `barrio`, `tema`, `indicador`, `capa`, `dimension`, `medida`, `tipo`, `categoria`, `nivel`, `sector`) y anclas que corresponden a elementos existentes. Se descartan búsquedas libres y parámetros arbitrarios. Las placas representan la página; un enlace con filtros puede restaurar la selección cuando el módulo ya implementa esos parámetros. No se genera una captura del mapa filtrado.

Los enlaces agregan UTM de campaña `compartir`. Los eventos `share` pasan por `CEPOES_ANALYTICS.event`, con consentimiento y lista finita de plataformas y métodos. Abrir un compositor mide intención; no confirma que se haya publicado. No se cargan SDK de redes, no se almacenan credenciales y no se envían correos. La aprobación editorial de difusión por correo sigue su circuito independiente.

## Verificación del desarrollo — 2026-10-11

- Build local de la salida pública completa: 170 HTML, 164 páginas elegibles.
- Pruebas Python de exclusiones, idempotencia, escape, medidas PNG, títulos largos y excepción de firma.
- 12 pruebas JavaScript aprobadas, incluyendo portapapeles bloqueado y selección manual dentro del diálogo, carga de imagen, compatibilidad y cancelación del envío nativo. Pruebas de copia, conservación de filtros públicos, descarte de parámetros personales, enlaces de plataforma, cancelación nativa, diálogo y medición con consentimiento.
- Regresiones de analítica, catálogos, Lo nuevo y boletines; contrato R2 y contraste estático.
- Revisión de las placas PNG mediante inspección visual local.
- **Revisión visual de los controles en navegador pendiente:** `sites-preview` falló con `bwrap: Can't mount proc on /newroot/proc: Operation not permitted`. El intento de acceso alternativo desde `cua_repl` fue rechazado por la política del navegador. No se considera validado el diseño móvil/escritorio ni el envío real a aplicaciones de redes.

## Revisión alternativa — 2026-10-11

Se realizó una revisión visual estática de la fila de controles y del diálogo de Instagram mediante WeasyPrint 70 y Poppler, usando los HTML y CSS reales de la salida preparada. Ocho vistas: 1440 × 900 y 390 × 844, claro/oscuro, fila de iconos y panel de Instagram. Se ajustó la fila para conservar todos los iconos juntos y se ocultó el rótulo en móvil. Los estilos usan los tokens institucionales; se declaró explícitamente el color del trazo.

Esta revisión es una alternativa local de composición y legibilidad, no una prueba de navegador o de dispositivo real. El renderizador usa fuentes de respaldo locales, requiere aplicar explícitamente las reglas móviles y resolver currentColor de SVG según el token de tema; no ejecuta JavaScript. Se conservaron las pruebas funcionales independientes. La interacción con aplicaciones de redes y la revisión en navegador siguen pendientes.

El fallo remoto de R2 fue exclusivamente una falta de conectividad al consultar el marcador público. Se reintentó el job fallido y terminó correctamente, incluidas las pruebas nuevas, el contrato de publicación y la consulta del marcador.

El PR permanece en borrador hasta completar la prueba en navegador o acordar con Agustín el alcance alternativo de revisión. No se publica ni se difunde por correo desde esta sesión.


## Corrección de compartir con imagen en X y WhatsApp — 2026-10-12

Agustín informó que todos sus envíos de enlaces aparecieron sin imagen. La comprobación HTTP y de etiquetas anterior verificó disponibilidad del sitio, pero no la vista previa efectiva en las aplicaciones. No se atribuye una causa a caché, configuración personal o bloqueo del crawler sin evidencia.

Con JavaScript y soporte de dialog, los iconos X y WhatsApp abren un panel discreto con la placa horizontal: compartir archivo PNG junto con título y URL mediante el menú nativo del dispositivo, descargar imagen, copiar texto/enlace o continuar sólo con el enlace. La persona elige la aplicación de destino; una web no selecciona o confirma la publicación en ella. Se verifica canShare con el conjunto real de datos y se precarga el archivo al abrir el panel para conservar la activación en el segundo clic. Si la aplicación omite el texto, el panel permite copiarlo. En escritorio sin envío de archivos se conservan descarga y copia. Con JavaScript desactivado o sin dialog, los enlaces directos siguen funcionando. Instagram mantiene su panel actual.

La imagen usa la placa existente de 1200 × 630 y los colores institucionales; se conservan filtros públicos, privacidad y consentimiento de analítica. Abrir el panel no registra un envío; descarga, copia y compositor se miden por separado. Cancelar no registra éxito. No se garantiza la aparición de una tarjeta automática al enviar sólo el enlace. La prueba de imagen recibida en WhatsApp/X sigue pendiente.

Pruebas: 9 Python y 13 JavaScript de compartir aprobadas localmente, incluidos archivo+texto, fallback sin share, fallo de carga, cancelación y campo manual dentro del panel correcto.


## Ubicación al comienzo del contenido — 2026-10-12

Por pedido de Agustín, la fila se ubica justo después del primer título h1 del contenido, antes de la síntesis y el cuerpo. Se ignoran navegación, scripts, estilos y templates al buscar la ubicación. La portada conserva los controles fuera de la tarjeta destacada; las páginas que cargan el título dinámicamente los ubican antes de su contenedor, para que el loader no los borre. Sin título/contenedor se usa el comienzo del body. Se elimina la ubicación anterior al pie y se conserva una sola fila por página.

La fila hereda la estética y los controles existentes; dentro del bloque del título se evita un segundo margen del contenedor wrap. Se reduce el espacio vertical y se elimina la línea que separaba el pie. Imágenes, enlaces, medición y paneles conservados. Pruebas: 11 Python aprobadas, incluyendo ubicación tras título real, exclusión de nav/script, idempotencia y casos de portada/loader. Salida completa: 164 páginas actualizadas, sin duplicados. sites-preview sigue bloqueado por bwrap/proc; revisión estática alternativa de móvil/escritorio, claro/oscuro. Interacción real en navegador pendiente.
