# ETAPA1 · candidato visual inmersivo

Estado: candidato navegable, **pendiente de aprobación visual**. No fusionar ni publicar en producción. Se leyó íntegramente la revisión del propietario `cepoes100b` (id 318432452): https://github.com/cepoes100b/CEPOES/pull/195#issuecomment-6081525763 . PR195 no fue aprobado visualmente.

## Base y alcance

Rama aislada creada desde main comprobado `73d0cf3f10c972a6f404060fb574754a4789b8ad`; reutiliza por fast-forward los siete commits de PR195 hasta `b1eb068331831e6533f7188033f62fa0bca20a43`, que seguía siendo su punta remota. Se modifica exclusivamente el experimento territorial, sus pruebas y esta evidencia. No se tocan IPC, natalidad, analgesia, pipelines o datos. Sin operaciones Sites, cambios de audiencia, fusión, despliegue o almacenamiento facturable.

## Decisiones visibles

- La entrada sin parámetros abre Analizar en 3D con Comuna 8: es la mayor tasa del indicador verificado, no una cifra del prototipo. Las URL explícitas conservan su selección y representación.
- Escena de viewport completo, título editorial y un único panel flotante para indicador, selección, cifra y ranking. Controles de cámara separados; búsqueda, escala territorial y explicación metodológica por revelado progresivo. Tabla y fuentes permanecen en el documento.
- En móvil el panel inferior se expande mediante un botón accesible. Se conserva una cartografía visible en la entrada, con dato, período y referencia a Ciudad en la ficha. Los nombres de comunas se proyectan en sus techos, con control de oclusión y colisiones.
- Petróleo, turquesas y selección naranja. La selección reemplaza **sólo el color del prisma elegido**, no su altura. La leyenda declara esa excepción; el ranking mantiene su color estadístico. Esto sustituye la decisión visual anterior de PR195 de usar sólo contorno naranja.
- Escala fija 0–100 %, base cero, 100 % = 3.200 m gráficos. El volumen sigue dependiendo del área administrativa y no representa un total. Se preservan numeradores, denominadores, 48 barrios/15 comunas y todos los recursos de datos byte por byte.
- Cámara vinculada a selección, con contexto de toda la Ciudad y un desplazamiento acotado. El encuadre analítico libera temporalmente los límites de cámara 2D, que se restituyen al volver a Explorar.
- Giro apagado por defecto, se detiene por interacción o movimiento reducido. Durante el movimiento se conserva el rótulo seleccionado y se retiran temporalmente los demás nombres para reducir consultas de profundidad; vuelven al reposo.
- Envoltura propia del experimento: ya no depende de `site.css`, `arquitectura.css` ni `common.js`. Motor MapLibre, datos y módulos compartidos siguen siendo los mismos. El paquete de handoff incorpora sólo este mapa, no el sitio completo.

## Inspección y evidencia

Se inspeccionaron píxeles reales en Chromium. Capturas de entrada en 1440×1000 y 430/390/320×844, en claro y oscuro. El ZIP de handoff contiene las ocho imágenes originales y los JSON de prueba. El modo móvil a 320 px conserva toda la selección y no genera scroll horizontal.

- **10/10 escenarios de navegador** aprobados: ocho combinaciones de ancho/tema, fallback sin WebGL y giro medido. Ocho auditorías Axe sin violaciones WCAG A/AA. Sin errores JavaScript ni respuestas HTTP fallidas en esos flujos.
- WebGL2 real de Chromium, ANGLE/SwiftShader; contexto vivo, extrusión visible, 15 IDs y alturas estadísticas verificadas. Los screenshots son renders, no maquetas.
- Ranking/ficha/tabla coinciden; selección cambia cámara y URL; Atrás restaura selección. Vista plana, giro voluntario, interrupción por teclado, reduced-motion, retorno a servicios y selección barrial sin imputar cifras comunales comprobados.
- **24/24 pruebas JS/DOM/adaptador** aprobadas.
- **13/15 pruebas Python** aprobadas, incluidas las cuatro de salud censal. Dos verificaciones históricas no pueden completarse: falta `data-pipeline/raw/verdes.geojson.gz` y los insumos raw necesarios para regeneración reproducible. No se descargaron ni se sustituyeron datos para ocultarlo. El paquete público conservado valida cobertura y geometrías.
- Giro en 390 px: 90 intervalos RAF, media **27,84 ms**, p95 **50,0 ms**, tras reducir las consultas de rótulos (primera medición: 39,40 ms de media). Evidencia por software; **no acredita 60 FPS ni fluidez en hardware móvil**. Sin prueba física de Safari/iPhone o lector de pantalla.

## Comparación crítica y bloqueo de referencia

La referencia y el encargo extendido de Library fueron resueltos, pero ambos fallaron al materializarse con `library file transfer failed: download failed`. Se hizo el único reintento soportado con destino `/workspace/reference`, con idéntico resultado y sin archivo local legible. No se ejecutó el HTML, no se copió su código, no se descargó su script Kaspersky ni se intentó eludir el bloqueo. No se solicitó `cepoes.org`.

Por ello **no hay comparación visual válida contra los píxeles del benchmark ni afirmación de superioridad**. Respecto del diagnóstico escrito del propietario, el candidato sí elimina las tres columnas, abre directamente en 3D y reúne dato/ranking en panel flotante. Subsisten compromisos visibles: oclusión inherente a prismas contiguos, menor detalle cartográfico y tipográfico a 320 px y ranking completo dentro de un panel desplazable. La aceptación estética pertenece al propietario, no a las pruebas.

## Handoff y siguiente paso

`python3 experiments/mapa-territorial/scripts/package_stage1.py --output /workspace/CEPOES-etapa1 --evidence /workspace/etapa1-evidence` genera fuente estática autocontenida, root `index.html`, manifiesto SHA-256, capturas y LEEME. Para navegar: servir `site/` por HTTP estático. No requiere build ni descargas para el render inicial. Calles opcionales y enlaces a catálogo/fuentes mantienen sus destinos oficiales.

Destino coordinado externamente: **el mismo Site privado** `appgprj_6ac8da2772ac81918f139b851872e602`, https://cepoes-mapa-territorial-pr195.crivelli725370.chatgpt.site . Esta tarea no lo actualiza ni cambia su audiencia.

Próximo paso: que el coordinador entregue este candidato en esa vista privada, recupere la referencia por el flujo autorizado y solicite aprobación visual explícita antes de integración final.
