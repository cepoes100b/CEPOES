# Universidad pública y financiamiento — propuesta del 15/10/2026

## Alcance y estado

Pedido de Agustín: posición clara de CEPOES y sección universitaria; priorizar las fuentes originales utilizadas por CEPA. El 15/10 indicó «adelante» a preparar contenido y vista previa para revisión. Este cambio prepara la sección en `/educacion/universidad-publica/`, el acceso desde Educación en Temas y su registro en el buscador. Es un especial permanente, no un informe completo descargable. Sin cambios de portada, fusión, publicación en cepoes.org o distribución por correo en esta etapa.

Base comprobada por GitHub oficial, conexión CEPOES: main `fed055c5862a0ab68cb180269a430f4c06000a2c`, árbol `8d311fa29ddb001efb14eb7a1cd264d921d7d390`. Rama creada desde ese SHA: `educacion/financiamiento-universitario-20261015`. Cambios limitados a página, CSS, acceso de Temas, registro de búsqueda y esta documentación.

## Evidencia y decisiones

- ONP, proyecto 2027, artículo 12 y planilla anexa: $7.349.082.049.312. Fuente: `https://www.mecon.gob.ar/onp/documentos/presutexto/proy2027/ley/pdf/proy2027.pdf` y `https://www.mecon.gob.ar/onp/documentos/presutexto/proy2027/ley/pdf/planillas_anexas/capitulo1/universidades.pdf`.
- ONP, jurisdicción 88, pp. impresas 88-83 y 88-90: programa 26, $7.504.425 millones. Fuente: `https://www.mecon.gob.ar/onp/documentos/presutexto/proy2027/jurent/pdf/P27J88.pdf`. No intercambiar este perímetro con el artículo 12 ni sumar ambos.
- Planilla universitaria: Fortalecimiento de Recursos Humanos, $851.558.460.149, fuera del subtotal asignado a universidades. Se plantea seguimiento de asignación y ejecución; no se afirma que la partida no se ejecutará.
- CIN, 4 y 17/09/2026: requerimiento de $11 billones como base actualizable. La comunicación del 17/09 utiliza «33 por ciento más» sin un denominador conciliable con las cifras anteriores. Por eso se retiene el monto y se evitan porcentajes de brecha hasta conciliar planillas y alcance.
- ADUBA, instructivo del 21/09/2026, punto 1.a: JTP exclusiva $1.344.619,07, semiexclusiva $672.308,57 y simple $336.150,34. Punto 1.b: garantías brutas de $1.497.941,97, $748.970,98 y $374.485,49. Se distingue básico de remuneración y se explican componentes; no se deduce pobreza individual a partir de un básico y una canasta familiar.
- Ley 27.795: texto original oficial completo consultado. Artículos 3–6, 8 y 9 con sus períodos originales. Publicación: 21/10/2025. Decreto 759/2025 consultado como antecedente de condicionamiento de ejecución. El alcance judicial se atribuye expresamente al comunicado del CIN del 26/06/2026 y se limita a la cautelar de artículos 5 y 6; no se declara verificada una sentencia íntegra ni una sentencia definitiva sobre toda la ley.
- Hospitales: comunicación UBA 5/05/2026 y Capital Humano 11/08/2026. Se conserva cada fecha y estado administrativo. No se traslada la denuncia de mayo como estado actual; la comunicación ministerial no se presenta como conciliación completa.
- CEPA, PDF aportado por Agustín, actualización del 14/10/2026: únicamente -21,1% real presupuestario 2027/2023 (prospectivo) y -24,2% salarial septiembre2026/noviembre2023. Cálculos no reproducidos íntegramente con fuentes originales y por eso atribuidos a CEPA. No usar la página web de septiembre como equivalente del PDF de octubre. Recomposición calculada por CEPOES: `(1/0.758-1)*100 = 31,9261%`, redondeado 31,9%, aumento real sobre nivel reducido, no aumento nominal legal exigible.

## Huellas de documentos primarios descargados

| Archivo | SHA-256 |
| --- | --- |
| Proyecto 2027 | d4a74e7d016279472f88465ec461ea7a58cf8e73b7f8c05e1a4733b934069dcb |
| Planilla universidades | 409ffaf60a3a26ea3d51eaf0accfceb23c6c25651aa91821749c32bb6a91101e |
| Jurisdicción 88 | e0c2f028516a202754adecff17b2c64c58487e08947a6bea8ee0f5825e6d474d |
| Instructivo ADUBA septiembre | 01c659874b00eaf21a576c4815c2c01fa337c0ecd4fb0beb6e28de9d55a786cf |

## Revisión

- Verificados: un h1, anclas internas existentes, recursos CSS y JavaScript locales, montos de las fuentes, JSON válido, ausencia de metadata que declare un informe/PDF y de controles de compartir pertenecientes al especial productivo utilizado como plantilla.
- CSS específico limitado a `.uni` y sus componentes; puntos de quiebre a 800px, columnas y barras apiladas, números con alineación tabular, foco visible y datos textuales disponibles sin JavaScript.
- `sites-preview` intentado con manifest y recursos completos: falla por `bwrap: Can't mount proc on /newroot/proc: Operation not permitted`.
- Vista alternativa privada creada en Sites: `https://cepoes-universidad-publica-revision.crivelli725370.chatgpt.site` (proyecto `appgprj_6ad0472e8a7c8191b0c4010be8c42e9e`). Versión inicial `appgprj_6ad0472e8a7c8191b0c4010be8c42e9e~appgver_3bcef47c1d548191bf15aa3ea80b198f`, despliegue succeeded, fuente `95592a2ca1f8c832483b3ec3ab8405e11fcdbfac`.
- Navegador integrado intentado. Revisión automática denegó la navegación porque la vista privada redirige a `auth.openai.com`, sin autorización explícita para iniciar sesión. No se utilizó un bypass ni se alteró la privacidad. Revisión visual escritorio/móvil y temas claro/oscuro pendiente; no presentarla como aprobada por el solo despliegue privado o por controles de código.

## Próximo paso

Revisar la propuesta en su vista privada y completar la revisión visual con acceso autorizado del navegador antes de integrar y publicar en cepoes.org. La difusión por correo es una decisión independiente.

## Corrección y controles finales

Se oscurece el enlace propio de la sección en modo claro a #006d98 para asegurar contraste sobre el celeste. Pares propios verificados: 5,23:1 sobre celeste, 5,31:1 sobre fondo alterno y 5,77:1 sobre blanco; en oscuro, mínimo 9,07:1 para los pares comprobados. Se verificaron nuevamente estructura y anclas. Los checks remotos del primer commit terminaron success para controles obligatorios y contrastes; el commit final debe volver a verificarse.

Vista privada actualizada con la corrección: fuente `92485b486ee056f9443313710a31dff46361ca47`, mismo proyecto y URL. La revisión en navegador sigue pendiente por el rechazo de autenticación, sin intentos de elusión.

## Revisión editorial del 15/10/2026

Por pedido expreso de Agustín, se eliminan las fórmulas «nuestra posición», «la lectura de CEPOES es», «la exigencia de CEPOES» y las introducciones equivalentes. Se conservan argumentos, propuestas, cifras y atribuciones a fuentes. El criterio permanente se incorpora a AGENTS.md: en el sitio institucional se redacta la posición directamente; la atribución institucional explícita se reserva para publicaciones externas cuando corresponda.

Vista privada actualizada: fuente `e3ac39643cccec29da3a5ef625c39300d1d459a4`, versión `appgprj_6ad0472e8a7c8191b0c4010be8c42e9e~appgver_fde91e2e4d1481919a7217aad2f69f1d`, despliegue succeeded. Comprobación textual de fórmulas ausentes aprobada. sites-preview sigue fallando por bwrap/proc; el acceso al navegador privado sigue pendiente de autorización de autenticación.
