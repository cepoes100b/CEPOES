# Portada editorial automática

El publicador canónico reconstruye tres tarjetas: última nota de `assets/data/analisis.json` con página pública existente, último boletín por número de edición entre las páginas versionadas, y último informe de coyuntura por período en `deploy/reports-registry.json`. El mismo catálogo de análisis alimenta el archivo de notas. Los borradores no se incorporan a estos catálogos públicos.

Cada nueva publicación debe registrar su metadata en el catálogo correspondiente. El despliegue selecciona automáticamente la nueva pieza. Las pruebas `test_home_editorial.py` comprueban selección, reemplazo y enlaces accesibles.

Tres piezas visibles en escritorio; desplazamiento nativo y controles manuales en móvil, sin avance automático. La sección inferior conserva únicamente la suscripción, eliminando el boletín de agosto heredado.

Durante el debate presupuestario, `budget_feature` en `home-editorial.json` agrega un bloque inmediatamente debajo de las tres tarjetas, que conservan Salud Mental, boletín e informe con su selección automática. El bloque enlaza al análisis integral y al especial Salud y sólo acepta informes registrados con página pública. Al cerrar la etapa de discusión, desactivar `enabled` retira este bloque. Los enlaces a carpetas y documentos de trabajo internos no se incluyen en páginas, datos descargables ni piezas de difusión.

Desde el 14/10/2026, `budget_feature.placement=carousel` coloca Presupuesto 2027 en la primera tarjeta, conservando boletín e informe de coyuntura. `below_feature` muestra Salud Mental inmediatamente debajo del carrusel. Desactivar el destacado presupuestario restaura la selección automática. La selección explícita requiere un informe registrado y una página pública existente.
