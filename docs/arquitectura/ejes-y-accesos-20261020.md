# Ejes y acceso a los contenidos · 20 de octubre de 2026

## Pedido y diagnóstico

Agustín pidió revisar el sitio completo para que los contenidos se encuentren en sus ejes temáticos y dejar visibles los temas de Territorio. Se conserva su directiva previa: tarjetas equivalentes, sin tema destacado; una etiqueta Nuevo en la publicación más reciente de Salud y Educación.

Se inventariaron las 152 rutas del sitemap (cero errores de recuperación) y los contenidos adicionales del overlay versionado. El informe de Salud Mental estaba enlazado en Salud, pero faltaban su monitor y la nota de prevención; Deporte y salud aparecía en Territorio y Temas. Otros materiales de salud pública y analgesia estaban dispersos. Territorio dependía del menú desplegable para muchos accesos.

## Solución

`deploy/axes-registry.json` reúne nueve ejes, 31 grupos y 74 contenidos o accesos editoriales. Un mismo grupo admite varios ejes. No se cambian las URL ni se trasladan archivos de contenidos.

- Salud: once grupos con veinte accesos, incluidos los tres productos de Salud Mental, Deporte y salud, analgesia obstétrica, medicamentos, presupuesto, balance, prevención, cuidados y materiales del encuentro de salud pública.
- Educación: cuatro grupos con seis accesos, incluidos informes y notas relacionadas.
- Territorio: doce grupos con veintiocho accesos, visibles inmediatamente después de su encabezado. Se conservan mapas, referencias, quince comunas, barrios y herramientas. Navegación territorial visible en escritorio y móvil, sin desplegable obligatorio.
- Temas: nueve entradas equivalentes y el catálogo completo debajo de cada eje, con enlaces directos. Se incorpora Seguridad y derechos y se conservan los identificadores anteriores.
- Las páginas clasificadas incorporan accesos para regresar a sus ejes. Los catálogos, vínculos contextuales y sitemaps se actualizan desde la misma fuente durante el publicador canónico.
- Un verificador detiene el build ante destinos inexistentes, informes sin clasificación o páginas temáticas nuevas sin eje dentro de las familias declaradas. Las notas de prensa publicadas dinámicamente fuera del catálogo versionado no se descubren por acceso a bases privadas: al incorporarlas al catálogo deben clasificarse. No se afirma una clasificación de registros externos no recuperados.

## Implementación y validación

Módulo `deploy/ejes_publicos.py`, normalizador público, CSS de arquitectura, manifiesto de entradas y workflow canónico existente. No se crean workflows paralelos ni se modifican datos, cálculos, textos de informes o permisos.

La salida de revisión contiene 172 HTML normalizados. Catálogos de los cuatro portales idempotentes; 74 destinos existentes; los quince informes registrados quedan clasificados. Se conserva el texto completo de cuidados paliativos y se verifican los elementos, anclas y enlaces de las quince comunas del Territorio original.

116 pruebas aprobadas (siete nuevas de ejes y las de catálogo, fechas, tipografía, novedades y cadena de publicación). Verificador canónico de rutas de publicación aprobado tras alinear el orden de las nuevas entradas. Pruebas específicas repetidas después del ajuste del encabezado de Territorio.

La revisión visual continúa pendiente por el rechazo del navegador y de la revisión automática ya registrado en esta conversación. No se vuelve a intentar el acceso bloqueado ni se presenta una inspección estática como revisión visual. La copia privada incluye las cuatro portadas y sus estilos, scripts y recursos locales necesarios; los demás destinos conducen a los contenidos públicos existentes, salvo cuidados paliativos que conserva su copia de revisión. El runtime territorial mantiene sus fuentes remotas públicas originales y su respaldo local de indicadores.

## Entrega

PR de trabajo: https://github.com/cepoes100b/CEPOES/pull/243

Vista privada: https://cepoes-salud-cuidados-paliativos.crivelli725370.chatgpt.site

Se prepara la versión para revisión de Agustín. Sin fusión, despliegue a cepoes.org ni autorización de correo para esta revisión ampliada.
