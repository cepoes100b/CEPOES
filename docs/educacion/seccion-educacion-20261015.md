# Sección Educación

La sección `/educacion/` reúne universidad pública, evaluación y aprendizajes, nivel inicial y vacantes, y establecimientos en el territorio. Tiene acceso directo desde el menú principal y el pie compartidos. El especial universitario enlaza a esta portada desde su breadcrumb.

Se usan los componentes existentes de las portadas editoriales (`page-hero`, `editorial-feature`, `ia-topic-card`). El menú se contrae a 1480 px para admitir Educación sin superponer enlaces. Se preserva el ancla histórica `educacion-e-infancias` y el filtro de prensa para conservar accesos previos; el rótulo público pasa a Educación. Se registra la portada en el buscador y en ambos mapas del sitio.

Los contenidos enlazados mantienen sus rutas y fechas. Se corrigen además las descripciones autorreferenciales que aún contenían «Posición de CEPOES» en el especial y el buscador.

Validación local: sintaxis Python, JSON y XML; normalización de portada, especial y Temas con contenido preservado, un solo menú, Educación activa en sus páginas e idempotencia; cuatro destinos públicos HTTP 200. Se utilizaron datos locales preexistentes únicamente como contexto del normalizador, sin modificar ni publicar esos archivos. La vista `sites-preview` no pudo arrancar: `bwrap: Can't mount proc on /newroot/proc: Operation not permitted`. Revisión en navegador público pendiente de despliegue. Los controles remotos y el despliegue canónico son obligatorios antes del cierre.

El usuario pidió dar a Educación una sección propia y ya había autorizado publicar los cambios del sitio. No se autoriza ninguna difusión por correo.
