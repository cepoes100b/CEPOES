# CEPOES Mapa Territorial — Propuesta inmersiva experimental

**Estado:** diseño en revisión, no aprobado visualmente, NO apto para fusionar o desplegar.

La rama `design/mapa-3d-inmersivo-gpt6-20261009` parte de la implementación 3D del PR #195. El PR alternativo #202 reúne el motor existente y esta iteración editorial sin alterar el modo `Explorar servicios` ni publicar rutas nuevas.

## Hipótesis de producto

En `Analizar indicadores`, la escena cartográfica debe ocupar prácticamente todo el viewport. El indicador, su universo, la comuna seleccionada, la cifra y el ranking se reúnen en **un panel translúcido**. Búsqueda/selección territorial pasan a un control `details` progresivo. El 3D es la vista inicial al elegir `Analizar` desde el explorador; la vista plana y la tabla conservan la precisión estadística.

- Paleta editorial: azul petróleo → turquesa, naranja para selección.
- Rótulos de comunas sobre la altura gráfica, con proyección pública de MapLibre; no alteran la geometría.
- Cámara ajusta padding al panel lateral en escritorio o al panel inferior en móviles.
- En móvil, un panel inferior expandible permite elegir cuánto mapa o lectura mostrar.
- El ranking y las tablas conservan la fuente INDEC Censo 2022, sin copiar datos del benchmark HTML.
- Movimiento reducido, navegación con teclado y el modo 2D siguen siendo requisitos innegociables.

## URL de revisión al montar el árbol público completo

`/laboratorio/mapa-territorial/?capa=salud&escala=comuna&territorio=comuna%3A8&modo=analizar&vista=3d`

La ruta debe servirse desde la **copia construida del PR #202**, no desde una versión anterior ni desde `cepoes.org`. El PR no incorpora hosting ni despliegue.

## Checklist antes de solicitar aprobación

- [ ] Playwright y R2 sobre el **head exacto** de este PR.
- [ ] Capturas de pantalla de 320, 390, 430 y 1440 px, modos claro y oscuro.
- [ ] Geometrías 3D y etiquetas realmente visibles, sin superposición con controles.
- [ ] Revisar click/tap en comunas y ranking, cambios de modo, Atrás/Adelante y URL.
- [ ] Asegurar que el panel de usuario funcione en móvil con teclado y lector de pantalla.
- [ ] Confirmar que el panel no obstruye los polígonos, en especial Comuna 8.
- [ ] Validar cambio entre `Explorar` y `Analizar` sin regresiones.
- [ ] Contrastar rendimiento y peso inicial respecto del PR #195.
- [ ] Obtener aprobación **visual expresa del usuario** tras una demostración navegable.

**Nota:** Este archivo documenta hipótesis y requisitos, no declara realizadas las pruebas ni la revisión visual.
