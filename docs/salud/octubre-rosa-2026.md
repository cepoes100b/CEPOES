# Octubre Rosa 2026 · especial territorial

## Alcance

Ruta propuesta: `/salud/octubre-rosa/`. Especial de servicio e información sanitaria, con agenda y análisis de acceso. No se presenta como informe completo con PDF. Accesos desde home (después del bloque editorial, conserva las tres tarjetas), Observatorio, buscador y sitemaps. Lo nuevo incorpora la sección Salud y el tipo Especial.

## Contenido y fuentes consultadas el 09/10/2026

- GCBA, agenda del 01/10/2026: https://buenosaires.gob.ar/gcaba_historico/noticias/octubre-rosa-los-hospitales-de-la-ciudad-suman-jornadas-especiales-y
- Diagnóstico Rojas: https://www.diagnosticorojas.com.ar/blog/mes-de-la-lucha-contra-el-cancer-de-mama/
- Ministerio de Salud, incidencia: https://www.argentina.gob.ar/salud/instituto-nacional-del-cancer/estadisticas/incidencia
- Ministerio de Salud, mortalidad: https://www.argentina.gob.ar/salud/instituto-nacional-del-cancer/estadisticas/mortalidad
- PNCM: https://www.argentina.gob.ar/salud/instituto-nacional-del-cancer/institucional/pncm/objetivos-y-ejes
- OMS, ficha de julio de 2026: https://www.who.int/es/news-room/fact-sheets/detail/breast-cancer
- GCBA, dirección Zubizarreta: https://buenosaires.gob.ar/gcaba_historico/salud/hospitales-y-establecimientos-de-salud/hospital-zubizarreta
- GCBA, dirección María Curie: https://buenosaires.gob.ar/gcaba_historico/noticias/hospital-maria-curie

Agenda: cinco campañas hospitalarias próximas; una campaña privada con condiciones pendientes; una jornada hospitalaria finalizada. Rojas publica dos sedes: se incluye únicamente la sede CABA, con advertencia de confirmar condiciones locales. La gratuidad privada no está informada. Zubizarreta publica horarios de inscripción, diferentes de los de estudios. Piñero no publica horario. María Curie anuncia intervalo hasta el 6/11: confirmar días efectivos y modalidad; no se presume atención en fines de semana.

Datos: Argentina 2024, 20.750 nuevos casos estimados, 29,9% de nuevos cánceres en mujeres y 5.912 defunciones femeninas por cáncer de mama. Tasas estandarizadas de mortalidad 2014 y 2024: 17,76 y 15,36. Transformación: `(17,76 - 15,36) / 17,76 * 100 = 13,5135%`, presentado como 13,5%; Ministerio redondea a 14%. Barras con base cero y escala común 0–20. Complemento de composición: `100 - 29,9 = 70,1%`. Incidencia estimada y mortalidad registrada diferenciadas; no calcular letalidad o supervivencia a partir del cociente.

Pauta PNCM de tamizaje: mujeres asintomáticas, riesgo promedio, 50–69, cada dos años. GCBA difunde pauta anual desde los 40; se atribuyen por separado. Edades de ingreso a campañas no equivalen a indicación de estudios. Síntomas: consulta a cualquier edad. La agenda y la red asistencial corresponden a CABA; las cifras estadísticas, a Argentina. No se asignan cifras nacionales a comunas. Cupos y esperas no comprobados.

## Mantenimiento

La clasificación de jornadas usa fecha de Buenos Aires en el navegador. No implica comprobación automática de fuentes ni programación de revisión editorial. Conservar fecha de revisión real y actualizar tanto los registros JSON como las tarjetas HTML de la agenda; el HTML mantiene información útil sin JavaScript. Orden: actividades vigentes antes que finalizadas; hospitales públicos antes que privados; fecha y nombre dentro de cada grupo. La información faltante permanece explícita.

## Validación previa

- `node --check deploy/site-overlay/assets/octubre-rosa.js`: correcto.
- `python -m unittest test_octubre_rosa test_lo_nuevo test_home_editorial -q`: 16 pruebas aprobadas.
- `python -m py_compile deploy/preparar_sitio_publico.py generar_lo_nuevo.py`: correcto.
- Revisión supervisada con sites-preview y cua_repl: escritorio 1363 px, claro/oscuro; vista móvil en iframe 390 y 320 px, claro/oscuro. Sin desbordamiento horizontal. No equivale a prueba Safari/iPhone.
- Filtro sin turno: Penna y Durand; finalizadas: jornada Durand del 2/10; Villa Devoto: un resultado y requisitos de inscripción visibles. Acceso desde home navega al especial. Gráficos revisados visualmente.
- Contraste de textos de contenido en claro: mínimo 5,38:1. Contraste en oscuro: mínimo 7,06:1.
- Buscador generado con la nueva entrada. Integración Lo nuevo y preservación de tres tarjetas cubiertas por pruebas.

Estado: propuesta; no fusionada ni desplegada. Difusión por correo requiere orden independiente conforme AGENTS.md; esta pieza no queda aprobada para difusión por prepararla o publicarla.
