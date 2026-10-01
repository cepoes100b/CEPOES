# Informe económico de coyuntura N.º 2 — octubre de 2026

Publicación autorizada por Agustín Crivelli el 1 de octubre de 2026. Período analizado: mayo–agosto de 2026; corte de información: 1 de octubre de 2026.

## Entregables y diseño

- Página canónica: `/publicaciones/informe-coyuntura-02-octubre-2026/`. Conserva la estructura y las hojas de estilo de la síntesis pública del N.º 1.
- Lectura íntegra: `/publicaciones/informe-coyuntura-02-octubre-2026/lectura.html`. Adaptación del HTML aprobado, basado en el HTML original del N.º 1; conserva nueve secciones, gráficos, doce referencias y texto íntegro. Incorpora la navegación común; fuentes tipográficas embebidas y recursos propios externos.
- PDF completo: `/publicaciones/files/informe-coyuntura-02-octubre-2026.pdf`. Diez páginas, portada azul y plantilla interior de la serie. Se verificaron visualmente las diez páginas antes de esta integración.
- Miniatura: `/assets/publicaciones/informe-coyuntura-02-octubre-2026.png`, renderizada directamente de la portada del PDF.
- Catálogo y cinco informes recientes generados desde `deploy/reports-registry.json`. Registro de búsqueda y mapas del sitio actualizados. Lo nuevo se genera mediante el flujo canónico de despliegue.

## Fuentes y alcances

INDEC (EMAE, IPI, capacidad instalada y EPH), IDECBA (empleo, ingresos, PGB, ejes comerciales y canales de venta), CAME y Cámara Argentina de Comercio y Servicios. Las doce referencias con URL se conservan en el PDF y en el HTML íntegro.

Las series nacionales disponibles alcanzan julio: las comparaciones de actividad e industria corresponden a mayo–julio. Empleo, ingresos y PGB corresponden al segundo trimestre; industria pyme y ejes comerciales cubren agosto. Cada gráfico y tabla explicita su período, cobertura y transformación. La síntesis web conserva estas distinciones.

## Verificación previa

- 17 pruebas de catálogo y Lo nuevo aprobadas.
- Registro de informes y controles obligatorios R2 aprobados.
- 33/33 consultas canónicas del buscador aprobadas tras preparar la copia de publicación con el normalizador canónico.
- Contenido del cuerpo y doce referencias del HTML comparados exactamente con el archivo aprobado.
- Revisión con Chromium en 1440 y 390 píxeles, temas claro y oscuro: síntesis, lectura íntegra y catálogo sin desbordes horizontales, imágenes rotas, anclas rotas ni errores JavaScript. Copia de cita funcional. Un único PDF propio desde ambas vistas del informe.
- Catálogo con nueve informes, incluido Seguridad y derechos en los barrios populares; nuevo informe presente en búsqueda y en Lo nuevo como informe, sin duplicar la vista de lectura.

La publicación se realiza mediante el workflow canónico `desplegar-hostinger.yml`, activado por la fusión autorizada, con respaldo, validación, publicación y verificación posterior.
