# Especial productivo · Presupuesto CABA 2027

Pedido de Agustín del 14/10/2026: incorporar el aporte CEDEAM–UBA al análisis integral y preparar una nota de comercios. Rama desde main b79fbb66db21c536e27542341d7d386c76be23bb. Publicación y difusión por correo requieren órdenes propias.

## Fuente y contraste

Presentación de octubre de 2026 de Pablo Sebastián Barreto y Sabrina Judith Canelas, CEDEAM, FCE UBA, dirección Raúl Sánchez. Contrastada con PDLEY-2026-36, Mensaje IF-2026-43937265 y planillas IF-2026-43938160; proyecto impositivo PDLEY-2026-34, IF-2026-43944662, Anexo I art. 5, Mensaje 40/26, expediente 3080-J-2026, documento 227616; Código Fiscal PDLEY-2026-33, art. 1 modificación 16. Copias originales consultadas de la carpeta interna, que no se enlaza ni se publica.

Cambios frente al aporte: corregida escala de IIBB (13,28 billones); umbral exacto $461.530.000; escenarios promedio 21,54% y 23% conservados; 30% en el ejemplo comercial es supuesto separado. El 66,7% compara alícuotas sobre una misma base, no años. Con base imponible ilustrativa 2027 de $494 M, diferencia $9,88 M. No se incorpora +$12,2 M sin explicitar una base 2027 distinta. El Mensaje menciona Parque de Innovación: no se afirma cierre. No se afirma ausencia de inversión de toda CABA a partir de bienes de uso de una sola jurisdicción. Distrito Tecnológico concentra 92,8% del subtotal de tres regímenes productivos, no de todas las exenciones.

## Integración

Generador del análisis integral incorpora un bloque enlazado. `scripts/desarrollo_productivo_2027.py` produce el especial y la nota usando el snapshot presupuestario, estilos p27 y gráficos accesibles canónicos. Especial registrado en reports-registry; nota en analisis.json, con buscador y Lo nuevo generados en build. No se cambia la home manualmente, ni salud, newsletter o datos de usuarios. No hay correo autorizado.

## Validación

Verificador presupuestario aprobado. Build local completo desde captura pública verificada: 171 páginas, 889 archivos, 19 pasos aprobados (incluye catálogos, búsqueda, contraste y publicación canónica). La captura base corresponde a una release anterior; overlay y generadores corresponden al main citado más la intervención. No es prueba de publicación actual.

sites-preview probado sobre salida completa: fallo de bwrap al montar /proc. Servidor HTTP local alternativo: navegador integrado responde ERR_CONNECTION_REFUSED. Se prepara vista privada en Sites para verificar las páginas nuevas con navegador integrado en escritorio y iframe de 390px. Este iframe no equivale a una prueba en Safari/iPhone.

Vista privada de revisión: https://cepoes-presupuesto-productivo-revision.crivelli725370.chatgpt.site/ . Comprobada en navegador integrado: especial y nota en escritorio/iframe 390px, temas claro y oscuro, anclas, barras y tabla desplazable. Sin desbordamiento de página: 375px clientWidth y scrollWidth. Corregida variación real industrial de 23% a +5,2%, conforme a los valores exactos del snapshot (la presentación redondea a 5,1%).

Búsqueda global: dos entradas y consultas canónicas incorporadas en search-registry. Índice generado de 160 URLs; verificador actualizado sin cambios de implementación.

Control remoto inicial detectó desplazamiento automático de Salud Mental en el carrusel. Corregido mediante home_eligible=false en la nota nueva y filtro editorial en el selector canónico; las tres piezas actuales se conservan. Verificación existente de home y catálogos debe aprobar sobre el HEAD final.
