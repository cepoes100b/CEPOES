# Portada editorial automática

El publicador canónico reconstruye tres tarjetas: última nota de `assets/data/analisis.json` con página pública existente, último boletín por número de edición entre las páginas versionadas, y último informe de coyuntura por período en `deploy/reports-registry.json`. El mismo catálogo de análisis alimenta el archivo de notas. Los borradores no se incorporan a estos catálogos públicos.

Cada nueva publicación debe registrar su metadata en el catálogo correspondiente. El despliegue selecciona automáticamente la nueva pieza. Las pruebas `test_home_editorial.py` comprueban selección, reemplazo y enlaces accesibles.

Tres piezas visibles en escritorio; desplazamiento nativo y controles manuales en móvil, sin avance automático. La sección inferior conserva únicamente la suscripción, eliminando el boletín de agosto heredado.
