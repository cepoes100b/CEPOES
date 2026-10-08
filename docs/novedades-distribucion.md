# Novedades de CEPOES

La suscripción comprende boletines, informes, notas, publicaciones de prensa y avisos institucionales publicados expresamente. La confirmación por correo y la baja se conservan. El alta guarda `privacy_version=2026-10-novedades`.

## Identidad

Marca CEPOES: tinta `#16232F`, celeste `#00A7E1`, enlaces y botones `#0079A8`, fondo `#F2F6FA`. Encabezado compartido entre confirmaciones, boletines y avisos de nuevas publicaciones. No se introduce la combinación petróleo/amarillo anterior. Tablas y estilos en línea, texto alternativo completo y enlace de baja.

## Regla

Tras un despliegue exitoso se genera `newsletter-publications.json` desde Lo nuevo y los boletines canónicos. Se incluyen contenidos editoriales con URL propia. Los índices, borradores, redirecciones y `noindex` quedan fuera. Los avisos deben tener `<meta name="cepoes:publication" content="notice">`; las actualizaciones rutinarias de datos no generan correo.

El workflow existente detecta publicaciones tras el despliegue y revisa la cola cada hora. La URL canónica es su identidad permanente: corregir texto, cifras o fecha no genera un segundo aviso. Cada novedad se encola para quienes estén activos y confirmados en ese momento; no hay archivo retroactivo para altas posteriores. El contenido se congela al encolarse; cada entrega tiene un UUID y clave estable de reintento. Se preservan los trabajos anteriores y el límite compartido de 50 primeras entregas por día.

## Activación

1. Revisar el catálogo y completar los marcadores de archivo si hubo publicaciones entre revisión y activación. La migración registra 145 rutas públicas conocidas el 8 de octubre como archivo, sin crear trabajos.
2. Aplicar `20261008153824_publication_notifications.sql`. Suscripciones y trabajos actuales se conservan. Tabla nueva con RLS, sin acceso público; RPC exclusiva de `service_role`.
3. Publicar sitio, formulario y feed. El dispatcher anterior puede seguir usando el feed de boletines v1 hasta el cambio de servicio.
4. Desplegar `newsletter-subscribe`, `newsletter-dispatch` y `newsletter-unsubscribe`, con `_shared/email-brand.js` y dependencias. Comprobar el feed antes de distribuir.
5. Verificar una ejecución sin novedades: cero nuevos trabajos. La primera publicación futura permitirá comprobar recepción real. Las pruebas de este cambio no envían correos ni crean altas reales.

## Pruebas

`node --test tests/newsletter_delivery.test.mjs tests/newsletter_logic.test.mjs tests/publication_delivery.test.mjs`.

`python -m unittest discover -s tests -p test_publications_feed.py`.

`supabase/tests/publication_notifications.sql` prueba archivo, destinatarios confirmados, no duplicación, snapshot, baja, leases y permisos en una transacción que se revierte. La ejecución local usa PostgreSQL embebido (PGlite), sin cambios productivos.

Vista previa supervisada del HTML a 1363 px y 390 px: comprueba composición, no recepción real en Gmail/Outlook. El fallo de clic Android/Windows permanece separado en el PR #185.
