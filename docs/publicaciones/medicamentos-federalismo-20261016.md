# Especial de medicamentos y financiamiento federal

Primera versión web para revisión editorial. Corte 16/10/2026. Rama desde main `d5987f51c4ce27ce7c7b0262dd8d8486fcbbe406`. No fusionar ni difundir por correo como parte de esta preparación.

## Producto

Ruta propuesta `/publicaciones/informes/medicamentos-federalismo/`. Informe web con comparación de alcance de los listados 2021 y 2026, seis denominaciones del nuevo anexo, cronología, infografía del desplazamiento de costos, escenarios explicativos interactivos y gráfico de dos hallazgos de auditoría de CABA de 2023. No hay datos sintéticos ni porcentajes de recorte calculados con unidades distintas. Sin mapa: no existe aún una base territorial actual comparable de existencias o entregas.

Entrada en catálogo y búsqueda; acceso en el bloque Salud y cuidados del Observatorio. Período editorial mensual hasta fijar publicación efectiva. No se altera home ni se ofrece el Word de trabajo como descarga pública. La vista privada de revisión no equivale a publicación en cepoes.org.

## Evidencia

Fuentes primarias enlazadas en la página: Resolución 1447/2026 y anexo IF-2026-74566510-APN-DNMYTS#MS; Resolución 3424/2021 y anexo I; comunicaciones del Ministerio de Salud del 28/02 y 14/03 de 2025; Ley 22.520 art. 23; comunicado del Gobierno de Salta del 22/07/2026; auditoría de Sindicatura General de CABA Proyecto 140/23, IF-2023-39953410-GCABA-SGCBA.

Anexo 2026 descargado del endpoint oficial de anexos del BORA (ID 7809903, anexo 1, publicación 20261015). Tabla en imagen revisada visualmente: aspirina, atorvastatina, candesartán, hidroclorotiazida, ramipril y rosuvastatina. El anexo 2021 (imagen oficial de Infoleg) contiene 128 renglones numerados, con dosis y formas repetidas. No se infiere porcentaje de cobertura ni se valida el número periodístico de 92 exclusiones.

Auditoría 2023: 5/16 centros sin saldos iniciales y movimientos de stock reconstruibles por formularios deficientes; 5/11 centros con formularios en tiempo y forma presentan diferencias entre cierre y stock físico. Bases distintas, grupos potencialmente superpuestos, porcentajes no aditivos. No se interpretan como faltantes actuales, ni como censo de centros. Se conservan avances y responsabilidades compartidas documentados.

Salta: más de $100 M nominales mensuales informados desde mayo de 2026; falta de envíos generales desde abril atribuida según el comunicado a demoras administrativas/logísticas nacionales. No causado por la resolución posterior ni extrapolado a todo el país. Los $66.000 M de Remediar anunciados en febrero de 2025 son proyección para 2025, no ejecución ni crédito 2026.

## Pendientes de investigación

Cotejo homogéneo por ingrediente de los anexos; presupuesto comparable 2023–2026 y metas físicas; licitaciones, cantidades recibidas y dispensación; respuesta presupuestaria y existencias actuales por CeSAC. Completar estas series antes de presentar gráficos de variación o mapas de impacto.

## Verificación

Sintaxis JS, catálogo de fuentes del overlay y 23 pruebas existentes de catálogo/Lo nuevo aprobadas. Captura y construcción pública completas en curso. sites-preview intentado primero: fallo de bwrap al montar /proc, corroborado por status detenido; terminal.local rechaza conexión. Copia privada Sites creada para revisión; el navegador integrado muestra acceso con ChatGPT y requiere autenticación. Revisión automática rechazó elegir Google sin selección directa del usuario. No declarar validación visual móvil/escritorio ni interacción en navegador mientras no se complete esa autenticación.

## Resultado de preparación

27 pruebas existentes de catálogo, novedades y fechas aprobadas; anclas, IDs e idempotencia del acceso Salud correctos. Captura de 805 recursos públicos con 34 fallas de descarga; el marcador productivo cambió durante la captura. El constructor canónico bloqueó correctamente el build por inconsistencia de base. No se declara salida integral validada.

Vista privada: https://cepoes-medicamentos-revision.crivelli725370.chatgpt.site/ . Proyecto appgprj_6ad2548f50ec819197c883ca6ef6901d. Salida de la página nueva normalizada con recursos públicos y overlay. Los enlaces de navegación externa de la copia privada apuntan a cepoes.org; el candidato del repositorio conserva rutas relativas.

El usuario eligió Google en el formulario seguro; la transición a accounts.google.com terminó en 502 Bad Gateway con conexión rechazada. La selección fue autorizada y realizada, pero no se completó el acceso. Sin revisión visual ni pruebas interactivas reales. No se vuelve a solicitar contraseña ni se cambia de método.

Antes de publicar en cepoes.org: reconstruir con una base estable y completar revisión visual de escritorio/móvil, claro/oscuro y los tres escenarios. La vista privada se entrega como propuesta para revisión, no como diseño validado.
