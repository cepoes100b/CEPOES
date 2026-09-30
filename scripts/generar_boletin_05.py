#!/usr/bin/env python3
"""Genera el Boletín CEPOES N.º 5 con la plantilla editorial de la serie."""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deploy/site-overlay/publicaciones/files/boletin-05-septiembre-2026.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

PAGE_W, PAGE_H = A4
LEFT, RIGHT, TOP, BOTTOM = 18 * mm, 18 * mm, 21 * mm, 17 * mm
CONTENT_W = PAGE_W - LEFT - RIGHT

NAVY = HexColor("#0B485A")
INK = HexColor("#24333B")
MUTED = HexColor("#5C6C73")
LINE = HexColor("#C9D6D9")
PALE = HexColor("#EFF4F4")
TEAL = HexColor("#168D9C")
RED = HexColor("#D04C55")
ORANGE = HexColor("#D47816")
PURPLE = HexColor("#676CC7")
GREEN = HexColor("#2C8954")
YELLOW = HexColor("#EDB521")

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("CEPOES", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("CEPOES-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("CEPOES-Italic", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFontFamily(
    "CEPOES", normal="CEPOES", bold="CEPOES-Bold",
    italic="CEPOES-Italic", boldItalic="CEPOES-Bold",
)

STYLES = {
    "kicker": ParagraphStyle("kicker", fontName="CEPOES-Bold", fontSize=6.4, leading=8, textColor=TEAL, spaceAfter=3),
    "h1": ParagraphStyle("h1", fontName="CEPOES-Bold", fontSize=19.5, leading=21.5, textColor=TEAL, spaceAfter=4),
    "dek": ParagraphStyle("dek", fontName="CEPOES", fontSize=8, leading=10.2, textColor=INK, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="CEPOES-Bold", fontSize=9.4, leading=11, textColor=TEAL, spaceBefore=2, spaceAfter=2),
    "body": ParagraphStyle("body", fontName="CEPOES", fontSize=7.45, leading=10.1, textColor=INK, spaceAfter=4),
    "small": ParagraphStyle("small", fontName="CEPOES", fontSize=5.7, leading=7.2, textColor=MUTED),
    "source": ParagraphStyle("source", fontName="CEPOES", fontSize=5.25, leading=6.5, textColor=MUTED, spaceBefore=3),
    "quote": ParagraphStyle("quote", fontName="CEPOES-Bold", fontSize=8.2, leading=10.5, textColor=NAVY, leftIndent=3 * mm, rightIndent=3 * mm),
    "kpi_value": ParagraphStyle("kpi_value", fontName="CEPOES-Bold", fontSize=15, leading=16, textColor=TEAL),
    "kpi_label": ParagraphStyle("kpi_label", fontName="CEPOES", fontSize=5.8, leading=7.2, textColor=INK),
    "kpi_src": ParagraphStyle("kpi_src", fontName="CEPOES", fontSize=4.8, leading=6, textColor=MUTED),
    "agenda_title": ParagraphStyle("agenda_title", fontName="CEPOES-Bold", fontSize=6.7, leading=8, textColor=colors.white, spaceAfter=2),
    "agenda_item": ParagraphStyle("agenda_item", fontName="CEPOES", fontSize=5.8, leading=7.4, textColor=colors.white, leftIndent=3 * mm, firstLineIndent=-3 * mm, spaceAfter=1.6),
    "table_head": ParagraphStyle("table_head", fontName="CEPOES-Bold", fontSize=5.3, leading=6.2, textColor=colors.white),
    "table": ParagraphStyle("table", fontName="CEPOES", fontSize=5.6, leading=7, textColor=INK),
    "report_title": ParagraphStyle("report_title", fontName="CEPOES-Bold", fontSize=7.3, leading=8.6, textColor=NAVY),
}


def p(text, style="body", **overrides):
    base = STYLES[style]
    if not overrides:
        return Paragraph(text, base)
    return Paragraph(text, ParagraphStyle(f"{style}-variant", parent=base, **overrides))


PAGE_META = {
    2: (TEAL, "RESUMEN EJECUTIVO"),
    3: (TEAL, "ACTIVIDAD ECONÓMICA"),
    4: (RED, "TRABAJO E INGRESOS"),
    5: (ORANGE, "POBREZA E INGRESOS"),
    6: (PURPLE, "CONSUMO Y COMERCIO"),
    7: (GREEN, "PROPUESTAS"),
    8: (NAVY, "NUEVOS INFORMES"),
}


def draw_cover(canvas):
    canvas.setFillColor(NAVY)
    canvas.rect(0, 160 * mm, PAGE_W, PAGE_H - 160 * mm, stroke=0, fill=1)
    canvas.setFillColor(YELLOW)
    canvas.rect(PAGE_W - 68 * mm, 159.2 * mm, 50 * mm, 1.2 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("CEPOES-Bold", 6.5)
    canvas.drawString(LEFT, PAGE_H - 16 * mm, "BOLETÍN NRO. 5 · SEPTIEMBRE 2026")
    canvas.drawRightString(PAGE_W - RIGHT, PAGE_H - 16 * mm, "CIUDAD DE BUENOS AIRES")
    canvas.setFont("CEPOES-Bold", 26)
    canvas.drawString(LEFT, PAGE_H - 36 * mm, "CEPOES")
    canvas.setFont("CEPOES", 6.4)
    canvas.drawString(LEFT, PAGE_H - 43 * mm, "Centro de Estudios en Política, Economía y Sociedad · Somos 100 Barrios")
    canvas.setFont("CEPOES-Bold", 21)
    canvas.drawString(LEFT, PAGE_H - 58 * mm, "La Ciudad que habitamos")
    canvas.setFont("CEPOES", 9)
    canvas.drawString(LEFT, PAGE_H - 67 * mm, "La recuperación que no llega a los barrios: crecimiento concentrado,")
    canvas.drawString(LEFT, PAGE_H - 72 * mm, "ingresos rezagados y consumo cotidiano en retroceso.")
    canvas.setFont("CEPOES", 7)
    canvas.drawString(LEFT, PAGE_H - 87 * mm, "Datos, análisis y propuestas desde el territorio.")

    items = [
        ("02", "Resumen ejecutivo", "La economía apenas crece y el impulso financiero no mejora la vida cotidiana."),
        ("03", "Actividad económica", "El PGB sube 0,3%, pero comercio, industria y servicios personales retroceden."),
        ("04", "Trabajo e ingresos", "La presión laboral aumenta y los ingresos quedan por detrás de los precios."),
        ("05", "Condiciones de vida", "La pobreza alcanza a 675.000 personas y conserva fuertes brechas territoriales."),
        ("06", "Consumo y comercio", "Supermercados y mayoristas caen; los shoppings no compensan el retroceso."),
        ("07", "Agenda pública", "Cinco líneas para llevar financiamiento, innovación y empleo a los barrios."),
        ("08", "Nuevos informes", "Siete investigaciones recientes de CEPOES, con acceso directo."),
    ]
    y = 148 * mm
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(1.2)
    canvas.line(LEFT + 4 * mm, 47 * mm, LEFT + 4 * mm, y + 1 * mm)
    for number, title, desc in items:
        canvas.setFillColor(NAVY)
        canvas.setFont("CEPOES-Bold", 8)
        canvas.drawString(LEFT + 7 * mm, y, number)
        canvas.setFont("CEPOES-Bold", 7.4)
        canvas.drawString(LEFT + 20 * mm, y, title)
        canvas.setFont("CEPOES", 5.9)
        canvas.setFillColor(MUTED)
        canvas.drawString(LEFT + 20 * mm, y - 4 * mm, desc)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(.35)
        canvas.line(LEFT + 20 * mm, y - 7 * mm, PAGE_W - RIGHT, y - 7 * mm)
        y -= 15 * mm
    canvas.setFillColor(MUTED)
    canvas.setFont("CEPOES", 5.5)
    canvas.drawString(LEFT, 12 * mm, "CEPOES · Centro de Estudios en Política, Economía y Sociedad")
    canvas.drawRightString(PAGE_W - RIGHT, 12 * mm, "contacto@cepoes.org · www.cepoes.org")


def page_decor(canvas, doc):
    canvas.saveState()
    if doc.page == 1:
        draw_cover(canvas)
        canvas.restoreState()
        return
    accent, right_label = PAGE_META[doc.page]
    y = PAGE_H - 12 * mm
    canvas.setStrokeColor(accent)
    canvas.setLineWidth(.75)
    canvas.line(LEFT, y - 2.5 * mm, PAGE_W - RIGHT, y - 2.5 * mm)
    canvas.setFillColor(NAVY)
    canvas.setFont("CEPOES-Bold", 5.8)
    canvas.drawString(LEFT, y, "CEPOES · BOLETÍN Nro. 5 · Septiembre 2026")
    canvas.setFillColor(accent)
    canvas.drawRightString(PAGE_W - RIGHT, y, right_label)
    canvas.setFillColor(MUTED)
    canvas.setFont("CEPOES", 5.3)
    canvas.drawString(LEFT, 10 * mm, "CEPOES · Centro de Estudios en Política, Economía y Sociedad")
    canvas.setFillColor(accent)
    canvas.drawRightString(PAGE_W - RIGHT, 10 * mm, f"p. {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(.35)
    canvas.line(LEFT, 13 * mm, PAGE_W - RIGHT, 13 * mm)
    canvas.restoreState()


def kpi_band(items, accent):
    width = CONTENT_W / len(items)
    cells = []
    for value, label, source_text in items:
        cells.append([p(value, "kpi_value", textColor=accent), p(label, "kpi_label"), p(source_text, "kpi_src")])
    table = Table([cells], colWidths=[width] * len(items), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("LINEABOVE", (0, 0), (-1, -1), 1.4, accent),
        ("LINEAFTER", (0, 0), (-2, -1), .35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def two_columns(left_flow, right_flow):
    gap = 8 * mm
    col = (CONTENT_W - gap) / 2
    table = Table([[left_flow, right_flow]], colWidths=[col, col], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0), ("RIGHTPADDING", (0, 0), (0, 0), gap / 2),
        ("LEFTPADDING", (1, 0), (1, 0), gap / 2), ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def agenda(items, accent, title="AGENDA PÚBLICA · QUÉ DEBERÍA HACER EL GCBA"):
    flow = [p(title, "agenda_title")]
    for head, body in items:
        flow.append(p(f"<font color='#EDB521'>■</font> <b>{head}.</b> {body}", "agenda_item"))
    table = Table([[flow]], colWidths=[CONTENT_W], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), accent),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def section_head(kicker, title, dek, accent):
    return [p(kicker, "kicker", textColor=accent), p(title, "h1", textColor=accent), p(dek, "dek")]


def source(text):
    return p(f"<b>Fuentes:</b> {text}", "source")


doc = BaseDocTemplate(
    str(OUT), pagesize=A4, leftMargin=LEFT, rightMargin=RIGHT, topMargin=TOP, bottomMargin=BOTTOM,
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
story += [quote, Spacer(1, 3 * mm), p("Indicadores síntesis del boletín", "h2", textColor=TEAL)]
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
], [
    p("La economía real", "h2", textColor=TEAL),
    p("El comercio cayó 2,2% y la industria 1,8%. La construcción apenas avanzó 0,3%; los servicios inmobiliarios y empresariales retrocedieron 0,7% y los servicios personales, 3,3%."),
    p("El contraste territorial", "h2", textColor=TEAL),
    p("Los sectores que concentran empleo, consumo cotidiano y vínculos con pequeñas empresas no acompañan el crecimiento financiero. El promedio oculta una recuperación sin derrame automático sobre los barrios."),
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
], [
    p("Los ingresos pierden", "h2", textColor=RED),
    p("El ingreso total familiar creció 27,1% frente a una inflación de 32,7%. Los ingresos laborales aumentaron 23,6%; los de trabajadores por cuenta propia, 8,6%; y los de asalariados sin descuento jubilatorio, apenas 5%."),
    p("Precariedad persistente", "h2", textColor=RED),
    p("Más de una cuarta parte de los asalariados no registra descuento jubilatorio. La estabilidad de la desocupación convive con empleos de menor calidad y con ingresos que pierden capacidad de compra."),
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
], [
    p("El promedio esconde territorio", "h2", textColor=ORANGE),
    p("La pobreza alcanza a 24,9% de los hogares de la zona sur, 7,6 puntos por encima del promedio de la Ciudad. Los hogares con menores de 14 años llegan a una incidencia de 28,2%."),
    p("Ingresos y composición familiar", "h2", textColor=ORANGE),
    p("La pérdida de poder adquisitivo golpea de manera distinta según la presencia de niñas y niños, la inserción laboral y el costo territorial de vivienda, transporte y cuidados."),
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
], [
    p("El dato positivo", "h2", textColor=PURPLE),
    p("Los shoppings crecieron 6,5%, impulsados parcialmente por descuentos y promociones financieras extraordinarias durante mayo. Registraron, sin embargo, nueve locales activos menos que un año atrás."),
    p("Dos circuitos de consumo", "h2", textColor=PURPLE),
    p("La mejora de los centros de compras no representa al conjunto del comercio porteño. El consumo cotidiano, más ligado al ingreso disponible de los hogares, continúa mostrando señales de retracción."),
]), Spacer(1, 4 * mm)]
story += [agenda([
    ("Crédito para comercios de cercanía", "financiar capital de trabajo e inversión con tasa real negativa y criterios territoriales."),
    ("Compras públicas locales", "orientar parte de la demanda del GCBA hacia proveedores, cooperativas y pymes porteñas."),
    ("Monitor de ventas barriales", "publicar indicadores por comuna y eje comercial para detectar cierres y caídas de actividad."),
], PURPLE), source("<link href='https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2062.pdf'>IDECBA, Informe de resultados 2062</link>. Datos provisorios."), PageBreak()]

# 07 · Agenda pública
story += section_head("AGENDA PÚBLICA", "Hacer que el crecimiento llegue a la economía real y a los barrios", "La Ciudad cuenta con capacidad fiscal, financiera, institucional y científica. La discusión es qué actividades, empresas y territorios prioriza.", GREEN)
proposal_rows = []
proposals = [
    ("01", "Crédito productivo con tasa real negativa", "Usar el Banco Ciudad para financiar inversión, capital de trabajo, digitalización y eficiencia energética de pymes y comercios, con metas verificables de empleo y producción."),
    ("02", "Transferencia tecnológica", "Vincular el financiamiento con universidades, centros tecnológicos y el sistema científico para resolver problemas productivos concretos y mejorar capacidades empresariales."),
    ("03", "Ingresos y formalización", "Priorizar a trabajadores por cuenta propia, asalariados no registrados, plataformas y actividades de cuidados, donde la pérdida real fue más intensa."),
    ("04", "Compras públicas para el desarrollo local", "Orientar una porción de la demanda del GCBA hacia proveedores y cooperativas locales con criterios de empleo formal, innovación y arraigo territorial."),
    ("05", "Tablero territorial de actividad y empleo", "Publicar indicadores comparables por comuna y ejes comerciales para diseñar políticas que no operen sólo con promedios de toda la Ciudad."),
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
story += [agenda([
    ("Principio rector", "cada instrumento debe publicar objetivos, beneficiarios, costo fiscal, metas de empleo y resultados territoriales."),
    ("Evaluación", "el crédito subsidiado debe estar condicionado a inversión adicional y no sustituir financiamiento privado ya disponible."),
    ("Equidad territorial", "la intensidad del apoyo debe considerar brechas productivas y sociales entre comunas."),
], GREEN, "CRITERIOS DE IMPLEMENTACIÓN"), source("Elaboración CEPOES sobre los diagnósticos de los Informes IDECBA 2058 a 2062."), PageBreak()]

# 08 · Nuevos informes
story += section_head("PRODUCCIÓN RECIENTE", "Nuevos informes de CEPOES", "Siete investigaciones y notas recientes amplían los problemas sociales, productivos y territoriales tratados en este boletín. Los títulos tienen enlace activo.", NAVY)
reports = [
    ("01", "Endeudarse para llegar a fin de mes", "Deuda de los hogares, mora y desigualdad territorial.", "https://cepoes.org/publicaciones/informes/endeudarse-para-llegar-a-fin-de-mes/"),
    ("02", "Situación de calle en la Ciudad de Buenos Aires", "Conteos, perfiles, territorio y respuesta estatal.", "https://cepoes.org/publicaciones/informes/situacion-de-calle-caba/"),
    ("03", "Personas mayores en la Ciudad de Buenos Aires", "Envejecimiento, ingresos, vivienda, salud y cuidados.", "https://cepoes.org/publicaciones/informes/personas-mayores-caba/"),
    ("04", "Seis años de registro y ningún número", "Trabajo de plataformas, juventudes y opacidad estadística.", "https://cepoes.org/publicaciones/informes/plataformas-juventudes-caba/"),
    ("05", "Dos evaluaciones, dos respuestas opuestas", "Qué muestran PISA, FEPBA y TESBA sobre la educación porteña.", "https://cepoes.org/publicaciones/informes/educacion-pisa-fepba-2025/"),
    ("06", "Tormenta Negra y la seguridad que queda en el barrio", "Presencia estatal, territorio y seguridad cotidiana.", "https://cepoes.org/publicaciones/notas/tormenta-negra-seguridad-territorio/"),
    ("07", "Tierras y soberanía", "La Ley de Tierras, su transformación y los riesgos para el control nacional.", "https://cepoes.org/territorio/tierras-y-soberania/"),
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
story += [report_table, Spacer(1, 6 * mm)]
citation = Table([[[p("CITA SUGERIDA", "agenda_title"), p("CEPOES (2026). «La recuperación que no llega a los barrios». <i>La Ciudad que habitamos</i>, N.º 5, septiembre de 2026.", "agenda_item")]]], colWidths=[CONTENT_W])
citation.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
    ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story += [citation, Spacer(1, 4 * mm), source("Datos centrales: IDECBA, Informes de resultados 2058, 2059, 2060, 2061 y 2062. Interpretación y propuestas: CEPOES.")]

doc.build(story)
print(OUT)
