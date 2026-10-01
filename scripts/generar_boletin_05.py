#!/usr/bin/env python3
"""Genera el Boletín CEPOES N.º 5 con la plantilla editorial de la serie."""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

from plantilla_boletin_cepoes import (
    BOTTOM, CONTENT_W, GREEN, LEFT, LINE, MUTED, NAVY, ORANGE, PAGE_H, PAGE_W,
    PALE, PURPLE, RED, RIGHT, STYLES, TEAL, TOP, YELLOW, agenda, kpi_band,
    make_page_decor, occupancy_guard, p, section_head, source, two_columns,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deploy/site-overlay/publicaciones/files/boletin-05-septiembre-2026.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

PAGE_META = {
    2: (TEAL, "RESUMEN EJECUTIVO"),
    3: (TEAL, "ACTIVIDAD ECONÓMICA"),
    4: (RED, "TRABAJO E INGRESOS"),
    5: (ORANGE, "POBREZA E INGRESOS"),
    6: (PURPLE, "CONSUMO Y COMERCIO"),
    7: (GREEN, "PROPUESTAS"),
    8: (NAVY, "NUEVOS INFORMES"),
}

COVER_ITEMS = [
        ("02", "Resumen ejecutivo", "La economía apenas crece y el impulso financiero no mejora la vida cotidiana."),
        ("03", "Actividad económica", "El PGB sube 0,3%, pero comercio, industria y servicios personales retroceden."),
        ("04", "Trabajo e ingresos", "La presión laboral aumenta y los ingresos quedan por detrás de los precios."),
        ("05", "Condiciones de vida", "La pobreza alcanza a 675.000 personas y conserva fuertes brechas territoriales."),
        ("06", "Consumo y comercio", "Supermercados y mayoristas caen; los shoppings no compensan el retroceso."),
        ("07", "Agenda pública", "Cinco líneas para llevar financiamiento, innovación y empleo a los barrios."),
        ("08", "Nuevos informes", "Siete investigaciones recientes de CEPOES, con acceso directo."),
]

page_decor = make_page_decor(
    5,
    "Septiembre 2026",
    PAGE_META,
    COVER_ITEMS,
    [
        "La recuperación que no llega a los barrios: crecimiento concentrado,",
        "ingresos rezagados y consumo cotidiano en retroceso.",
    ],
)


doc = BaseDocTemplate(
    str(OUT), pagesize=(PAGE_W, PAGE_H), leftMargin=LEFT, rightMargin=RIGHT, topMargin=TOP, bottomMargin=BOTTOM,
    title="La recuperación que no llega a los barrios", author="CEPOES",
    subject="Boletín CEPOES N.º 5, septiembre de 2026", pageCompression=1,
)
frame = Frame(LEFT, BOTTOM, CONTENT_W, PAGE_H - TOP - BOTTOM, id="main")
doc.addPageTemplates(PageTemplate(id="boletin", frames=[frame], onPage=page_decor))
story = [PageBreak()]

# 02 · Resumen ejecutivo
story += section_head("ANÁLISIS", "La recuperación que no llega a los barrios", "El PGB porteño apenas crece y su impulso se concentra en las finanzas. Comercio, industria, consumo e ingresos describen otra Ciudad.", TEAL)
left = [
    p("El Producto Geográfico Bruto de la Ciudad creció apenas 0,3% frente al segundo trimestre de 2025 y cayó 0,2% respecto del trimestre anterior. El propio IDECBA identifica una desaceleración iniciada en el tercer trimestre de 2025: no es una recuperación robusta, sino un nivel general prácticamente estancado."),
    p("La composición del crecimiento es más reveladora. La intermediación financiera aumentó 7,7% y aportó más de un punto porcentual al resultado general. Sin ese impulso, el agregado habría sido negativo."),
]
right = [
    p("Comercio cayó 2,2%, industria manufacturera 1,8% y servicios personales 3,3%. La desocupación se mantuvo en 7,2%, pero la presión laboral alcanzó a 14,8% de la población económicamente activa."),
    p("Los ingresos laborales crecieron 23,6%, nueve puntos por debajo de la inflación porteña. La pobreza alcanza a 675.000 personas y golpea más al sur de la Ciudad y a los hogares con niñas y niños."),
]
story += [two_columns(left, right), Spacer(1, 2 * mm)]
quote = Table([[p("Cuando el crecimiento depende de las finanzas y no llega al empleo, los ingresos ni el consumo cotidiano, la recuperación existe en el promedio, pero no en los barrios.", "quote")]], colWidths=[CONTENT_W])
quote.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), PALE), ("LINEBEFORE", (0, 0), (0, 0), 2, YELLOW),
    ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story += [quote, Spacer(1, 3 * mm), two_columns([
    p("El ingreso de los hogares confirma esa distancia. Mientras el IPC porteño acumuló una variación interanual de 32,7%, el ingreso total familiar subió 27,1% y los ingresos laborales, 23,6%. La brecha es todavía mayor entre cuentapropistas y asalariados sin descuento jubilatorio: sus ingresos crecieron 8,6% y 5%, respectivamente."),
    p("La consecuencia es una recuperación que no recompone capacidad de compra. Aun cuando una tasa general permanezca estable, la calidad del empleo, las horas disponibles y la evolución real de las remuneraciones determinan cuánto de ese crecimiento llega a cada hogar."),
], [
    p("Los datos de pobreza completan el cuadro: 21,9% de las personas está debajo de la línea de pobreza y 6,3% es indigente. La incidencia asciende a 24,9% de los hogares en la zona sur y a 28,2% entre los hogares con menores de 14 años. A un hogar pobre promedio le faltan $424.597 mensuales para alcanzar la canasta básica total."),
    p("El consumo masivo reproduce la misma tensión. Las ventas reales de supermercados cayeron 1,2% y las de mayoristas, 17,6%. El aumento de 6,5% en centros de compras no alcanza para compensar un retroceso concentrado en los circuitos cotidianos y en los hogares con menos margen financiero."),
]), Spacer(1, 2 * mm), two_columns([
    p("Un mismo patrón", "h2", textColor=TEAL),
    p("Actividad, trabajo, ingresos y consumo no son escenas separadas. La concentración del crecimiento en las finanzas convive con sectores productivos en baja; esa debilidad limita la demanda de empleo de calidad y deja a los hogares con menos capacidad de compra."),
    p("La estabilidad de algunos indicadores generales no contradice el deterioro. Una tasa de desocupación sin cambios puede coexistir con más personas buscando horas, mayor informalidad y remuneraciones que crecen por debajo de los precios."),
], [
    p("Una agenda territorial", "h2", textColor=TEAL),
    p("El promedio de la Ciudad oculta diferencias persistentes. La pobreza en la zona sur y en los hogares con niñas y niños muestra que el territorio y la composición familiar deben ser criterios explícitos de asignación de recursos."),
    p("Este número propone combinar crédito productivo, transferencia tecnológica, formalización, compras públicas y seguimiento por comuna. El objetivo es que la capacidad financiera de la Ciudad se traduzca en producción, empleo e ingresos reales."),
]), Spacer(1, 3 * mm), p("Indicadores síntesis del boletín", "h2", textColor=TEAL)]
summary_data = [
    [p("TEMA", "table_head"), p("INDICADOR CLAVE", "table_head"), p("DATO", "table_head"), p("FUENTE", "table_head")],
    [p("Actividad", "table"), p("Producto Geográfico Bruto, variación interanual", "table"), p("+0,3%", "table", textColor=RED), p("IDECBA 2061", "table")],
    [p("Trabajo", "table"), p("Presión sobre el mercado laboral", "table"), p("14,8%", "table", textColor=RED), p("IDECBA 2058", "table")],
    [p("Ingresos", "table"), p("Ingresos laborales frente a inflación de 32,7%", "table"), p("+23,6%", "table", textColor=RED), p("IDECBA 2059", "table")],
    [p("Pobreza", "table"), p("Personas bajo la línea de pobreza", "table"), p("675.000", "table", textColor=RED), p("IDECBA 2060", "table")],
    [p("Comercio", "table"), p("Ventas reales en autoservicios mayoristas", "table"), p("-17,6%", "table", textColor=RED), p("IDECBA 2062", "table")],
]
summary = Table(summary_data, colWidths=[24 * mm, 86 * mm, 25 * mm, CONTENT_W - 135 * mm], repeatRows=1)
summary.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
    ("GRID", (0, 0), (-1, -1), .3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
]))
story += [summary, source("IDECBA, Informes de resultados 2058 a 2062, septiembre de 2026."), PageBreak()]

# 03 · Actividad
story += section_head("ACTIVIDAD", "Quién crece y quién retrocede", "El promedio del PGB oculta una economía de velocidades opuestas: las finanzas explican el avance y la economía real permanece estancada o en retroceso.", TEAL)
story += [kpi_band([
    ("+0,3%", "PGB frente al segundo trimestre de 2025", "IDECBA 2061"),
    ("-0,2%", "Variación frente al trimestre anterior", "Serie desestacionalizada"),
    ("+7,7%", "Intermediación financiera", "Principal motor"),
], TEAL), Spacer(1, 4 * mm)]
story += [two_columns([
    p("El motor financiero", "h2", textColor=TEAL),
    p("La intermediación financiera creció 7,7%. Sobresalieron los fondos comunes de inversión, los agentes de bolsa y la intermediación bancaria y no bancaria. Su aporte fue de 1,01 puntos porcentuales: sin ese impulso, el resultado agregado habría sido negativo."),
    p("Una recuperación estrecha", "h2", textColor=TEAL),
    p("La actividad total apenas superó el nivel de un año atrás y retrocedió frente al trimestre previo. La desaceleración que comenzó en 2025 continúa y limita cualquier lectura de recuperación generalizada."),
    p("La comparación desestacionalizada es central: el retroceso de 0,2% respecto del trimestre anterior indica que el aumento interanual no se tradujo en una trayectoria sostenida dentro de 2026. El nivel general se mantiene, pero sin la amplitud sectorial necesaria para hablar de una fase expansiva."),
    p("La industria manufacturera y el comercio tienen efectos encadenados sobre proveedores, logística y empleo. Su contracción no es un dato aislado: reduce actividad en circuitos productivos que atraviesan varias comunas."),
    p("Qué mirar en los próximos trimestres", "h2", textColor=TEAL),
    p("La prueba de una recuperación más amplia será que el comercio y la industria reviertan sus caídas, que la construcción acelere por encima del 0,3% y que el crecimiento deje de depender de un aporte financiero excepcional. También será necesario observar si el avance genera empleo formal y mejora los ingresos reales."),
], [
    p("La economía real", "h2", textColor=TEAL),
    p("El comercio cayó 2,2% y la industria 1,8%. La construcción apenas avanzó 0,3%; los servicios inmobiliarios y empresariales retrocedieron 0,7% y los servicios personales, 3,3%."),
    p("El contraste territorial", "h2", textColor=TEAL),
    p("Los sectores que concentran empleo, consumo cotidiano y vínculos con pequeñas empresas no acompañan el crecimiento financiero. El promedio oculta una recuperación sin derrame automático sobre los barrios."),
    p("El aporte financiero de 1,01 puntos porcentuales fue mayor que la variación del producto total. Esa relación permite una lectura simple: el avance de un solo sector compensó caídas simultáneas en ramas más conectadas con el trabajo y el consumo urbano."),
    p("La política pública debe mirar la composición y no sólo el promedio. Sin información por comuna, tamaño de empresa y calidad del empleo, la mejora agregada puede convivir con cierres comerciales, menor producción y deterioro de ingresos en amplias zonas de la Ciudad."),
    p("Una lectura territorial", "h2", textColor=TEAL),
    p("Los promedios sectoriales tampoco indican dónde se localizan las mejoras y las caídas. Publicar series por comuna y eje comercial permitiría distinguir si el estancamiento se concentra en zonas con menor acceso al crédito, mayor informalidad o una estructura productiva más vulnerable. Esa información es indispensable para orientar instrumentos con precisión."),
]), Spacer(1, 4 * mm)]
story += [agenda([
    ("Crédito productivo", "orientar el Banco Ciudad a inversión y capital de trabajo de pymes y comercios con metas verificables de empleo."),
    ("Transferencia tecnológica", "vincular financiamiento, universidades, centros tecnológicos y sistema científico para resolver problemas productivos concretos."),
    ("Seguimiento por comuna", "publicar indicadores de actividad, empleo y cierres comerciales por barrio y eje productivo."),
], TEAL), source("<link href='https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2061.pdf'>IDECBA, Informe de resultados 2061</link>. Datos preliminares."), PageBreak()]

# 04 · Trabajo e ingresos
story += section_head("TRABAJO", "Más presión laboral y menos poder adquisitivo", "La desocupación se mantiene, pero crece la búsqueda de más horas y de otra ocupación. Los ingresos laborales pierden contra los precios.", RED)
story += [kpi_band([
    ("7,2%", "Tasa de desocupación", "125.000 personas"),
    ("14,8%", "Presión sobre el mercado laboral", "+1,8 pp interanual"),
    ("26,5%", "Asalariados sin descuento jubilatorio", "IDECBA 2058"),
], RED), Spacer(1, 4 * mm)]
story += [two_columns([
    p("Una estabilidad que no alcanza", "h2", textColor=RED),
    p("La tasa de desocupación no varió de manera significativa, pero aumentó la búsqueda de más horas y de otra ocupación entre quienes ya trabajan. La presión laboral reúne a desocupados, subocupados y ocupados demandantes."),
    p("Brecha de género", "h2", textColor=RED),
    p("Las mujeres representan 60,7% de la población desocupada y 61,9% de la subocupada. El deterioro no se distribuye de manera homogénea."),
    p("La presión laboral no se limita a quienes están desempleados. Incluye a las personas que ya trabajan pero buscan más horas o una segunda ocupación. Por eso el 14,8% ofrece una imagen más completa que la tasa de desocupación tomada de manera aislada."),
    p("El aumento interanual de 1,8 puntos porcentuales muestra que la estabilidad del desempleo abierto convive con una necesidad creciente de ampliar ingresos. El mercado absorbe ocupación, pero no siempre ofrece horas, remuneraciones ni protección suficientes."),
    p("El problema de las horas", "h2", textColor=RED),
    p("La subocupación y la búsqueda de otra ocupación expresan una insuficiencia concreta: tener trabajo no garantiza alcanzar el volumen de horas necesario para sostener el hogar. Esa presión puede anticipar mayor rotación, pluriempleo y disponibilidad para aceptar condiciones más precarias."),
], [
    p("Los ingresos pierden", "h2", textColor=RED),
    p("El ingreso total familiar creció 27,1% frente a una inflación de 32,7%. Los ingresos laborales aumentaron 23,6%; los de trabajadores por cuenta propia, 8,6%; y los de asalariados sin descuento jubilatorio, apenas 5%."),
    p("Precariedad persistente", "h2", textColor=RED),
    p("Más de una cuarta parte de los asalariados no registra descuento jubilatorio. La estabilidad de la desocupación convive con empleos de menor calidad y con ingresos que pierden capacidad de compra."),
    p("La brecha con la inflación es de 9,1 puntos para los ingresos laborales y se amplía a 24,1 puntos entre los cuentapropistas. En el segmento sin aportes, la diferencia llega a 27,7 puntos. Son trayectorias distintas que una media general de ingresos no alcanza a mostrar."),
    p("El resultado combina tres problemas: informalidad, pérdida real y desigualdad de género. Una política de empleo que sólo contabilice puestos creados puede omitir si esos empleos garantizan continuidad, cobertura social y un ingreso compatible con el costo de vida porteño."),
    p("La referencia debe ser el costo porteño", "h2", textColor=RED),
    p("Las políticas de ingresos y empleo necesitan evaluar el salario contra la inflación y las canastas locales. El rezago no se corrige con una mejora nominal menor que los precios. En especial, los segmentos informales requieren instrumentos que combinen registración, protección y recuperación real."),
]), Spacer(1, 4 * mm)]
story += [agenda([
    ("Formalización con incentivos", "priorizar plataformas, cuidados, cuenta propia y pequeñas unidades productivas, donde la pérdida real fue más intensa."),
    ("Empleo joven con derechos", "articular formación y primer empleo registrado con empresas y organizaciones de cada comuna."),
    ("Ingresos de referencia", "incorporar el costo de vida porteño y la composición de los hogares al diseño de políticas de apoyo."),
], RED), source("<link href='https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2058.pdf'>IDECBA 2058</link> · <link href='https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2059.pdf'>IDECBA 2059</link>."), PageBreak()]

# 05 · Condiciones de vida
story += section_head("CONDICIONES DE VIDA", "La pobreza dejó de bajar y conserva un mapa desigual", "El estancamiento agregado convive con 675.000 personas pobres y con brechas persistentes por territorio y composición del hogar.", ORANGE)
story += [kpi_band([
    ("21,9%", "Personas bajo la línea de pobreza", "675.000 personas"),
    ("6,3%", "Personas indigentes", "193.000 personas"),
    ("24,9%", "Hogares pobres en la zona sur", "+7,6 pp sobre CABA"),
], ORANGE), Spacer(1, 4 * mm)]
story += [two_columns([
    p("La mejora se frenó", "h2", textColor=ORANGE),
    p("La pobreza se mantiene cerca del registro del segundo trimestre de 2025, pero aumentó frente al cierre de ese año. En el primer semestre también creció interanualmente, impulsada por la indigencia."),
    p("La brecha que falta cubrir", "h2", textColor=ORANGE),
    p("A un hogar pobre promedio le faltan $424.597 mensuales para alcanzar la canasta básica total. La distancia muestra la magnitud del problema que no captura la sola tasa de incidencia."),
    p("La pobreza dejó de descender al ritmo observado previamente. El dato exige separar una mejora estadística de una solución estructural: cientos de miles de personas permanecen debajo de las canastas y una parte relevante ni siquiera cubre la alimentaria."),
    p("La brecha monetaria también importa para diseñar respuestas. Una transferencia uniforme puede ser insuficiente cuando los hogares parten de distancias tan distintas respecto de la canasta y enfrentan costos específicos de vivienda, movilidad y cuidados."),
    p("Indigencia y urgencia", "h2", textColor=ORANGE),
    p("Las 193.000 personas indigentes no alcanzan a cubrir una canasta alimentaria. Ese núcleo requiere respuestas inmediatas en ingresos y acceso a alimentos, articuladas con una estrategia de vivienda, salud y empleo que evite que la emergencia se vuelva permanente."),
], [
    p("El promedio esconde territorio", "h2", textColor=ORANGE),
    p("La pobreza alcanza a 24,9% de los hogares de la zona sur, 7,6 puntos por encima del promedio de la Ciudad. Los hogares con menores de 14 años llegan a una incidencia de 28,2%."),
    p("Ingresos y composición familiar", "h2", textColor=ORANGE),
    p("La pérdida de poder adquisitivo golpea de manera distinta según la presencia de niñas y niños, la inserción laboral y el costo territorial de vivienda, transporte y cuidados."),
    p("La diferencia entre el sur y el promedio de la Ciudad alcanza 7,6 puntos porcentuales. Esa distancia confirma que la pobreza no se distribuye de forma homogénea y que las políticas universales necesitan complementos territoriales."),
    p("En los hogares con menores de 14 años, la incidencia llega a 28,2%. Los ingresos deben sostener a más integrantes y suelen combinarse con mayores necesidades de cuidado, lo que condiciona la disponibilidad horaria para trabajar y eleva gastos cotidianos."),
    p("Del promedio a la política", "h2", textColor=ORANGE),
    p("El mapa de la pobreza exige asignar recursos con criterios de territorio y composición familiar. La misma tasa general puede ocultar hogares con brechas de ingreso muy distintas. Por eso la Ciudad debe publicar canastas y resultados desagregados que permitan seguir tanto la incidencia como la intensidad del problema."),
]), Spacer(1, 4 * mm)]
story += [agenda([
    ("Política focalizada territorialmente", "priorizar el sur y los hogares con niñas y niños mediante transferencias y servicios de cercanía."),
    ("Sistema integral de cuidados", "ampliar infraestructura y prestaciones para reducir costos que hoy absorben los hogares."),
    ("Canastas por perfil de hogar", "publicar referencias de costo diferenciadas para orientar políticas con mayor precisión."),
], ORANGE), source("<link href='https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2060.pdf'>IDECBA, Informe de resultados 2060</link>. Algunas estimaciones poseen carácter indicativo según su coeficiente de variación."), PageBreak()]

# 06 · Consumo
story += section_head("CONSUMO", "El consumo cotidiano sigue en retroceso", "Los indicadores del comercio minorista describen una recuperación desigual. El crecimiento de los shoppings no compensa la caída del consumo masivo.", PURPLE)
story += [kpi_band([
    ("-1,2%", "Ventas reales en supermercados", "Variación interanual"),
    ("-17,6%", "Ventas reales en mayoristas", "Diez trimestres de caída"),
    ("+6,5%", "Ventas reales en shoppings", "Impulso promocional"),
], PURPLE), Spacer(1, 4 * mm)]
story += [two_columns([
    p("Consumo masivo en baja", "h2", textColor=PURPLE),
    p("Las ventas reales en supermercados bajaron 1,2% y confirmaron la tendencia del primer trimestre. Los autoservicios mayoristas cayeron 17,6% y completaron diez trimestres consecutivos de retracción."),
    p("Otros rubros", "h2", textColor=PURPLE),
    p("También descendieron las ventas de electrodomésticos, 3,7%, y los patentamientos de automotores, 3,9%. La debilidad excede a un único canal comercial."),
    p("La caída mayorista es la señal más intensa: acumula diez trimestres consecutivos de retracción. Ese canal abastece a comercios y hogares que buscan reducir precios por volumen, por lo que su deterioro revela una restricción persistente en el consumo esencial."),
    p("El retroceso simultáneo de bienes durables indica cautela frente a decisiones de gasto de mayor monto. Cuando el ingreso real pierde contra los precios, los hogares postergan reposiciones y priorizan alimentos, vivienda y servicios."),
    p("Una cadena que se retrae", "h2", textColor=PURPLE),
    p("Menos ventas no afectan solamente al punto de compra. También reducen pedidos a distribuidores, presionan sobre el empleo comercial y achican el margen de los pequeños negocios. La persistencia de la caída mayorista vuelve necesario seguir cierres y aperturas por comuna."),
], [
    p("El dato positivo", "h2", textColor=PURPLE),
    p("Los shoppings crecieron 6,5%, impulsados parcialmente por descuentos y promociones financieras extraordinarias durante mayo. Registraron, sin embargo, nueve locales activos menos que un año atrás."),
    p("Dos circuitos de consumo", "h2", textColor=PURPLE),
    p("La mejora de los centros de compras no representa al conjunto del comercio porteño. El consumo cotidiano, más ligado al ingreso disponible de los hogares, continúa mostrando señales de retracción."),
    p("El crecimiento de los shoppings estuvo atravesado por descuentos y promociones financieras extraordinarias. Además, funcionaron nueve locales menos que un año antes. El dato positivo debe leerse con esas dos condiciones y no como evidencia de una recuperación general."),
    p("La divergencia entre canales expresa capacidades de compra distintas. Los hogares con acceso al crédito y promociones pueden adelantar consumos, mientras el comercio de cercanía depende en mayor medida del ingreso disponible del mes."),
    p("No confundir promoción con recuperación", "h2", textColor=PURPLE),
    p("Una suba apoyada en eventos promocionales puede concentrar compras sin sostener un nuevo nivel de actividad. Para evaluar la tendencia conviene observar varios trimestres, la cantidad de locales activos y el desempeño simultáneo de supermercados, mayoristas y comercios barriales."),
]), Spacer(1, 4 * mm)]
story += [agenda([
    ("Crédito para comercios de cercanía", "financiar capital de trabajo e inversión con tasa real negativa y criterios territoriales."),
    ("Compras públicas locales", "orientar parte de la demanda del GCBA hacia proveedores, cooperativas y pymes porteñas."),
    ("Monitor de ventas barriales", "publicar indicadores por comuna y eje comercial para detectar cierres y caídas de actividad."),
], PURPLE), source("<link href='https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2062.pdf'>IDECBA, Informe de resultados 2062</link>. Datos provisorios."), PageBreak()]

# 07 · Agenda pública
story += section_head("AGENDA PÚBLICA", "Hacer que el crecimiento llegue a la economía real y a los barrios", "La Ciudad cuenta con capacidad fiscal, financiera, institucional y científica. La discusión es qué actividades, empresas y territorios prioriza.", GREEN)
story += [two_columns([
    p("Los datos del trimestre no describen una falta absoluta de recursos, sino una recuperación concentrada. El desafío es transformar capacidad financiera en inversión productiva, innovación, empleo formal y mejora de ingresos."),
], [
    p("La agenda propone instrumentos verificables. Cada línea debe publicar destinatarios, costo fiscal, metas de empleo y resultados territoriales para que el apoyo público pueda evaluarse."),
]), Spacer(1, 2 * mm)]
proposal_rows = []
proposals = [
    ("01", "Crédito productivo con tasa real negativa", "Usar el Banco Ciudad para financiar inversión, capital de trabajo, digitalización y eficiencia energética de pymes y comercios. Las líneas deben tener plazos compatibles con la inversión y metas verificables de empleo, producción y permanencia territorial."),
    ("02", "Transferencia tecnológica", "Vincular el financiamiento con universidades, centros tecnológicos y el sistema científico para resolver problemas productivos concretos. El apoyo puede incluir diagnósticos, asistencia técnica y adopción de herramientas que mejoren productividad y gestión."),
    ("03", "Ingresos y formalización", "Priorizar a trabajadores por cuenta propia, asalariados no registrados, plataformas y actividades de cuidados, donde la pérdida real fue más intensa. Combinar incentivos a la registración con acceso a protección social y formación."),
    ("04", "Compras públicas para el desarrollo local", "Orientar una porción de la demanda del GCBA hacia proveedores, cooperativas y pymes locales. Los pliegos pueden ponderar empleo formal, innovación, arraigo territorial y encadenamientos productivos dentro de la Ciudad."),
    ("05", "Tablero territorial de actividad y empleo", "Publicar indicadores comparables por comuna y ejes comerciales sobre ventas, cierres, empleo, ingresos y acceso al crédito. La desagregación permitiría diseñar políticas que no operen sólo con promedios de toda la Ciudad."),
]
for number, title, body in proposals:
    proposal_rows.append([p(number, "kpi_value", textColor=GREEN), [p(title, "h2", textColor=GREEN), p(body, "body")]])
proposal_table = Table(proposal_rows, colWidths=[14 * mm, CONTENT_W - 14 * mm])
proposal_table.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -2), .35, LINE),
    ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story += [proposal_table, Spacer(1, 4 * mm)]
story += [two_columns([
    p("La secuencia importa", "h2", textColor=GREEN),
    p("El crédito debe estar ligado a proyectos adicionales y no reemplazar financiamiento que ya existía. La asistencia técnica puede acompañar la formulación, mientras las compras públicas crean una primera demanda y reducen el riesgo de la inversión."),
], [
    p("Medir para corregir", "h2", textColor=GREEN),
    p("Los resultados deben observarse por tamaño de empresa, sector y comuna. Si el empleo, las ventas o la formalización no mejoran, las condiciones del instrumento deben revisarse. La evaluación es parte de la política, no una instancia posterior."),
]), Spacer(1, 3 * mm)]
story += [agenda([
    ("Principio rector", "cada instrumento debe publicar objetivos, beneficiarios, costo fiscal, metas de empleo y resultados territoriales."),
    ("Evaluación", "el crédito subsidiado debe estar condicionado a inversión adicional y no sustituir financiamiento privado ya disponible."),
    ("Equidad territorial", "la intensidad del apoyo debe considerar brechas productivas y sociales entre comunas."),
], GREEN, "CRITERIOS DE IMPLEMENTACIÓN"), source("Elaboración CEPOES sobre los diagnósticos de los Informes IDECBA 2058 a 2062."), PageBreak()]

# 08 · Nuevos informes
story += section_head("PRODUCCIÓN RECIENTE", "Nuevos informes de CEPOES", "Siete investigaciones y notas recientes amplían los problemas sociales, productivos y territoriales tratados en este boletín. Los títulos tienen enlace activo.", NAVY)
reports = [
    ("01", "Endeudarse para llegar a fin de mes", "Analiza el uso creciente de deuda para cubrir gastos cotidianos, la mora y las diferencias territoriales que atraviesan a los hogares porteños.", "https://cepoes.org/publicaciones/informes/endeudarse-para-llegar-a-fin-de-mes/"),
    ("02", "Situación de calle en la Ciudad de Buenos Aires", "Compara conteos oficiales y sociales, describe perfiles y recorridos territoriales y examina el alcance de la respuesta estatal.", "https://cepoes.org/publicaciones/informes/situacion-de-calle-caba/"),
    ("03", "Personas mayores en la Ciudad de Buenos Aires", "Reúne indicadores de envejecimiento, ingresos, vivienda, salud y cuidados para caracterizar una población central en la estructura demográfica porteña.", "https://cepoes.org/publicaciones/informes/personas-mayores-caba/"),
    ("04", "Seis años de registro y ningún número", "Reconstruye la regulación del trabajo en plataformas y muestra la ausencia de información pública sobre empleo, empresas y juventudes alcanzadas.", "https://cepoes.org/publicaciones/informes/plataformas-juventudes-caba/"),
    ("05", "Dos evaluaciones, dos respuestas opuestas", "Contrasta los resultados de PISA, FEPBA y TESBA y discute qué diagnósticos y decisiones de política educativa se derivan de cada lectura.", "https://cepoes.org/publicaciones/informes/educacion-pisa-fepba-2025/"),
    ("06", "Tormenta Negra y la seguridad que queda en el barrio", "Propone mirar la seguridad desde la presencia estatal, el territorio, la organización comunitaria y las condiciones de la vida cotidiana.", "https://cepoes.org/publicaciones/notas/tormenta-negra-seguridad-territorio/"),
    ("07", "Tierras y soberanía", "Examina la Ley de Tierras, las transformaciones regulatorias recientes y los riesgos que abren para el control nacional de recursos estratégicos.", "https://cepoes.org/territorio/tierras-y-soberania/"),
]
report_rows = []
for number, title, desc, url in reports:
    report_rows.append([
        p(number, "kpi_value", textColor=TEAL),
        Paragraph(f"<link href='{url}'><b>{title}</b></link>", STYLES["report_title"]),
        p(desc, "table"),
        Paragraph(f"<link href='{url}'><b>Abrir →</b></link>", STYLES["table"]),
    ])
report_table = Table(report_rows, colWidths=[13 * mm, 62 * mm, CONTENT_W - 100 * mm, 25 * mm])
report_table.setStyle(TableStyle([
    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, PALE]), ("LINEBELOW", (0, 0), (-1, -2), .35, LINE),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story += [report_table, Spacer(1, 5 * mm), two_columns([
    p("Una agenda común", "h2", textColor=NAVY),
    p("Los siete trabajos abordan problemas distintos, pero comparten una pregunta: cómo las decisiones públicas se traducen en condiciones concretas de vida. Deuda, calle, envejecimiento, trabajo, educación, seguridad y tierra se cruzan en el territorio y no pueden leerse como compartimentos aislados."),
], [
    p("Leer, verificar y discutir", "h2", textColor=NAVY),
    p("Cada enlace conduce a la publicación completa, con sus datos, fuentes y argumentos. Esta sección funciona como puerta de entrada a la producción reciente de CEPOES y permite ampliar los diagnósticos sintetizados en el boletín."),
]), Spacer(1, 3 * mm), two_columns([
    p("Recorrido social", "h2", textColor=NAVY),
    p("Endeudamiento, situación de calle y personas mayores permiten seguir cómo los ingresos insuficientes se combinan con vivienda, salud y redes de cuidado. Leídos en conjunto, muestran distintos grados de vulnerabilidad y las respuestas estatales disponibles."),
], [
    p("Recorrido institucional", "h2", textColor=NAVY),
    p("Plataformas, evaluaciones educativas, seguridad territorial y soberanía ponen el foco en registros, capacidades públicas y reglas. Son trabajos que preguntan qué información produce el Estado, cómo decide y qué intereses prioriza."),
]), Spacer(1, 4 * mm)]
citation = Table([[[p("CITA SUGERIDA", "agenda_title"), p("CEPOES (2026). «La recuperación que no llega a los barrios». <i>La Ciudad que habitamos</i>, N.º 5, septiembre de 2026.", "agenda_item")]]], colWidths=[CONTENT_W])
citation.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
    ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story += [citation, Spacer(1, 4 * mm), source("Datos centrales: IDECBA, Informes de resultados 2058, 2059, 2060, 2061 y 2062. Interpretación y propuestas: CEPOES.")]

doc.build(story)
occupancy_guard(OUT)
print(OUT)
