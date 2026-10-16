# Calidad del monitor de limpieza urbana

Revisión: 16/10/2026. Dictamen: **apto con reservas explícitas de cobertura**, para describir demanda registrada. No permite afirmar niveles de limpieza ni resolución efectiva.

Universo: 858.461 contactos únicos HIGIENE de los archivos oficiales completos SUACI 2025 y 2026, corte 15/10/2026. No se imputan contactos ausentes. Octubre es parcial.

| Hallazgo | Impacto | Tratamiento y criterio de cierre |
|---|---|---|
| Tres prestaciones interrumpidas desde mayo de 2026 | Alto: una caída aparente puede ser cobertura faltante | Advertencia por filtros, gráfico marcado y s/d cuando corresponde. Cerrar con explicación oficial y continuidad verificable |
| Ocho motivos cambian de tipo administrativo predominante entre años | Alto: comparar Queja/Solicitud distorsiona un mismo motivo | Naturaleza estable por prestación, etiqueta original avanzada y aviso entre años. Mantener equivalencia explícita |
| 1.444 contactos sin barrio | Moderado: asignación territorial incompleta | Conservarlos en totales y tablas, sin atribuir barrio |
| 207 comunas discrepantes o faltantes con barrio válido | Moderado | Usar correspondencia oficial barrio/comuna, declarar corrección |
| Estado administrativo no prueba resolución | Alto si se infiere desempeño | No publicar tasa de solución sin verificación de intervención |

Controles: descarga completa y huella SHA-256, esquema y campos obligatorios, identificadores duplicados incompatibles, prestaciones nuevas, sumas, 48 barrios/15 comunas, retrocesos históricos y nuevas discontinuidades. Una fuente fallida no genera un commit de actualización. Se requiere revisión explícita de las nuevas interrupciones.

Reproducir: `python scripts/test_limpieza_urbana.py`, `node scripts/test_limpieza_urbana_model.cjs`; generar con los archivos anuales completos según docs/limpieza-urbana.md. El JSON público incluye huellas, tamaño, clasificación y evidencia mensual por prestación, sin identificadores ni direcciones de personas.

Pendiente: aclaración oficial de la discontinuidad; integración pública canónica y aprobación de publicación. No se contactaron terceros.
