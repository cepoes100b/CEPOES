# Compartir contenido público — CEPOES

## Resultado

La salida pública incorpora una fila discreta de iconos al final de cada página canónica: WhatsApp, X, Facebook, copiar enlace, Instagram y compartir desde el dispositivo cuando está disponible. Los controles usan los tokens y la tipografía del sitio, foco visible, nombres accesibles y objetivos táctiles de 44 px. El diálogo de Instagram permite guardar dos placas y copiar el título con el enlace. La publicación en redes la decide y realiza el lector.

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
- Pruebas JavaScript de copia, conservación de filtros públicos, descarte de parámetros personales, enlaces de plataforma, cancelación nativa, diálogo y medición con consentimiento.
- Regresiones de analítica, catálogos, Lo nuevo y boletines; contrato R2 y contraste estático.
- Revisión de las placas PNG mediante inspección visual local.
- **Revisión visual de los controles en navegador pendiente:** `sites-preview` falló con `bwrap: Can't mount proc on /newroot/proc: Operation not permitted`. El intento de acceso alternativo desde `cua_repl` fue rechazado por la política del navegador. No se considera validado el diseño móvil/escritorio ni el envío real a aplicaciones de redes.

El PR queda en borrador hasta completar esa revisión. No se publica ni se difunde por correo desde esta sesión.
