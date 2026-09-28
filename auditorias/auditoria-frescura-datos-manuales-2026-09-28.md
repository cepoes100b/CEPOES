# Auditoría de frescura de datos manuales — 28/09/2026

## Objetivo

Revisar los conjuntos publicados por CEPOES que no dependen de una actualización automática periódica y distinguir entre:

- **dato desactualizado**: existe una publicación oficial más reciente y comparable;
- **dato histórico vigente**: el período es anterior, pero sigue siendo el último universo o baseline oficial aplicable;
- **monitor manual al día**: fue revisado y no se localizó una novedad oficial que obligue a cambiar el estado;
- **base normativa/ editorial**: no tiene una frecuencia estadística y debe revisarse ante cambios normativos o editoriales.

La fecha de procesamiento, el período estadístico y la fecha de última verificación son dimensiones diferentes.

## Inventario de actualización

### Con actualización programada

No requieren intervención manual ordinaria para detectar una nueva edición de su fuente:

- Observatorio económico y social (IDECBA): dos corridas diarias.
- Presupuesto: control diario de nuevas publicaciones oficiales.
- Oferta y perfiles territoriales: control diario.
- Endeudamiento: ciclo mensual.
- Migraciones: control diario.
- Personas mayores: control diario.
- Natalidad y demografía: control mensual.
- Salud reproductiva / PAEV: control semanal.
- Salud mental: control mensual.
- Descentralización comunal presupuestaria: control periódico.
- Estructura productiva y dinámica productiva: workflows específicos.
- Legislatura, agenda y sesiones: workflows específicos.
- Borradores privados de prensa: generación programada.

### Con seguimiento manual o semimanual

#### Analgesia obstétrica

- Archivo: `deploy/site-overlay/assets/data/analgesia-peridural.json`.
- Dato sustantivo: sanción del 27/08/2026 y contexto sanitario disponible.
- Revisión realizada: 28/09/2026.
- Resultado: **sin novedad oficial localizada que permita fechar promulgación o reglamentación**.
- Acción: se conserva el dato del 27/08 y se agrega `last_checked_at` para no confundir falta de novedad con falta de revisión.
- Regla: no iniciar el cómputo de los plazos de 30/90 días sin una fuente oficial de promulgación.

#### Transparencia y descentralización — baseline 2024

- Archivo: `deploy/site-overlay/assets/data/descentralizacion-transparencia-2024.json`.
- Período: julio-agosto de 2024.
- Naturaleza: autorreporte oficial de las 15 Juntas Comunales en respuesta a la Resolución 178/2024.
- Revisión realizada: 28/09/2026.
- Resultado: **baseline histórico vigente; no es una medición del cumplimiento actual**.
- No se localizó una respuesta oficial consolidada posterior de alcance equivalente para las 15 Juntas.
- En 2026 se actualizaron procedimientos generales de Transparencia Activa bajo la Ley 104 (Disposiciones 3/DGAIGA/26 y 1/DGAIGA/26), pero esas normas no sustituyen el baseline específico de la Ley 5.629.
- Acción: agregar `last_checked_at` y contexto 2026, preservando sin cambios la matriz 2024.
- Próxima mejora sustantiva: nueva auditoría primaria de las 15 comunas o pedido de información actualizado.

#### Seguridad y derechos en barrios populares

- Archivo: `deploy/site-overlay/assets/data/seguridad-barrios-operativos.json`.
- Último episodio registrado: Tormenta Negra, 24/09/2026.
- Revisión realizada: 28/09/2026.
- Fuente oficial del GCBA publicada el 27/09/2026: 17 detenciones, 192 vehículos secuestrados, más de 1.500 policías/agentes y 15 barrios; además informa **30 locales inspeccionados y 12 clausurados**.
- Acción: incorporar esos dos últimos datos y actualizar la fecha de revisión.
- Se mantienen separados los balances oficiales, los registros atribuidos a otras organizaciones y los campos todavía sin dato público verificado.

### Bases sin periodicidad estadística

No deben marcarse como atrasadas sólo por su fecha:

- `descentralizacion-competencias.json`: base normativa; revisar ante modificación de Ley 1.777, Ley 5.629 o decretos relacionados.
- `taxonomia.json`: configuración editorial.
- `home-editorial.json` y `prensa.json`: contenidos/editorial, no series estadísticas.

## Hallazgo general

No se identificó otro conjunto estructurado publicado como “actual” que carezca a la vez de workflow de actualización y de una explicación de su carácter histórico. Los tres frentes que requieren disciplina manual quedan identificados arriba.

## Regla de mantenimiento propuesta

Todo conjunto manual o semimanual debe incorporar:

1. `last_checked_at`;
2. período del dato por separado;
3. fuente primaria revisada;
4. resultado del chequeo (novedad / sin novedad / fuente no disponible);
5. próxima condición de revisión;
6. prohibición de reemplazar una serie histórica válida con inferencias o datos no comparables.

## Fuentes oficiales verificadas en esta auditoría

- GCBA — Tormenta Negra (27/09/2026): https://buenosaires.gob.ar/gcaba_historico/noticias/tormenta-negra-megaoperativo-simultaneo-en-las-villas-con-mas-de-1500
- Boletín Oficial CABA — Disposición 3/DGAIGA/2026: https://boletinoficial.buenosaires.gob.ar/normativaba/norma/850289
- Boletín Oficial CABA — Disposición 1/DGAIGA/2026: https://boletinoficial.buenosaires.gob.ar/normativaba/norma/855833

## Resultado

- Automatizaciones críticas recuperadas: Presupuesto, Territorio y Prensa.
- Datos manuales revisados: Analgesia, Transparencia/Descentralización y Seguridad en barrios populares.
- Actualización factual necesaria encontrada: detalle de inspecciones/clausuras del operativo del 24/09.
- Baseline histórico que debe conservarse: transparencia comunal 2024.
- Monitor revisado sin novedad oficial localizada: analgesia obstétrica.
