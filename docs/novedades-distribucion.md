# Novedades de CEPOES: aprobación editorial

La suscripción comprende boletines, informes, notas y avisos institucionales. Se conservan confirmación por correo, baja, identidad CEPOES y límite compartido de 50 primeras entregas por día.

## Regla obligatoria

Publicar, fusionar, desplegar o corregir contenido NO autoriza correo. El catálogo privado puede descubrir URLs automáticamente, pero no crea trabajos. Al finalizar una pieza, consultar a Agustín si quiere difundirla, salvo que exista una orden expresa para esa pieza. No enviar una consulta por email automáticamente.

Estados privados: draft (borrador), review (revisión), published (publicado sin difusión), ready (listo para difundir por orden expresa) y diffused (difundido). Las correcciones preservan ready/diffused y el snapshot aprobado. No se ofrece un panel nuevo ni un botón público: Agustín puede dar la orden en esta conversación.

## Operación de aprobación

1. Identificar la URL canónica exacta y comprobar que la pieza está publicada, revisada y completa. Leer el feed público actual y validar la pieza con validatePublication. Actualizar el catálogo privado mediante newsletter_enqueue_publications; este nombre histórico ahora SOLO registra catálogo y jamás envía.
2. Mostrar título, URL y alcance; pedir aprobación independiente si Agustín no dijo explícitamente que esa pieza está lista para difundir. Una orden genérica de publicación no alcanza.
3. Solo ante esa orden, invocar la RPC privada newsletter_approve_publication con p_key, p_expected_payload (snapshot completo revisado), p_approved_by y p_authorization_reference (referencia textual verificable de la orden). Solo service_role tiene acceso; nunca usar credenciales administrativas en navegador o frontend.
4. La RPC comprueba estado published, contenido sin cambios desde la revisión y ausencia de distribución anterior. Registra la aprobación y crea una entrega por suscriptor activo y confirmado. No aprobar piezas de prueba en producción.
5. El worker horario procesa únicamente cola aprobada; al terminar marca diffused. Una aprobación repetida devuelve cero: no crea duplicados ni envíos retroactivos a nuevas altas. Un reenvío de algo difundido requiere una tarea y orden separadas; no está habilitado por esta implementación.

## Historial y seguridad

La migración conserva entregas aceptadas y marca sus piezas diffused. Cualquier trabajo pendiente anterior queda en review y no se reanuda solo. El mecanismo legacy de boletines tampoco puede encolar sin aprobación. La función de claim exige ready en la tabla privada, incluso si aparece una fila de cola fuera del circuito.

El 8/10 se verificaron tres avisos diferentes del presupuesto (general, salud y nota de prensa), seis aceptaciones por pieza y un intento por entrega. No se detectaron reenvíos de la misma URL en la cola. Este historial no prueba recepción real de cada proveedor.

## Pruebas

Pruebas SQL aisladas: descubrimiento y edición sin envíos, consentimiento explícito, snapshot desactualizado rechazado, destinatarios confirmados, aprobación repetida sin duplicados, snapshot congelado, cierre diffused, permisos privados, bloqueo legacy y claim sin aprobación. Runner tests/editorial_approval.test.mjs con PGlite 0.5.8, también en CI. No se modifica HTML/CSS ni el diseño de la web en este cambio.
