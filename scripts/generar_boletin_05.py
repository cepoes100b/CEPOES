#!/usr/bin/env python3
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deploy/site-overlay/publicaciones/files/boletin-05-septiembre-2026.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = HexColor("#16232F")
TEAL = HexColor("#39B8AE")
LIGHT_TEAL = HexColor("#D9F1EE")
RED = HexColor("#D0554B")
PAPER = HexColor("#F5F1E8")
INK = HexColor("#1B252D")
MUTED = HexColor("#52636E")
LINE = HexColor("#D6DEE2")

fonts = {
    "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}
for key, path in fonts.items():
    name = "CEPOES" + key.title()
    pdfmetrics.registerFont(TTFont(name, path))

PAGE_W, PAGE_H = A4
MARGIN_X = 19 * mm
MARGIN_TOP = 22 * mm
MARGIN_BOTTOM = 18 * mm

styles = getSampleStyleSheet()
S = {
    "eyebrow": ParagraphStyle("eyebrow", fontName="CEPOESBold", fontSize=7.5, leading=10, textColor=TEAL, spaceAfter=4, uppercase=True),
    "h1": ParagraphStyle("h1", fontName="CEPOESBold", fontSize=28, leading=32, textColor=NAVY, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="CEPOESBold", fontSize=19, leading=23, textColor=NAVY, spaceBefore=5, spaceAfter=9),
    "h3": ParagraphStyle("h3", fontName="CEPOESBold", fontSize=11, leading=14, textColor=NAVY, spaceBefore=5, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="CEPOESRegular", fontSize=9.2, leading=13.7, textColor=INK, spaceAfter=7),
    "small": ParagraphStyle("small", fontName="CEPOESRegular", fontSize=7.4, leading=10.2, textColor=MUTED, spaceAfter=4),
    "quote": ParagraphStyle("quote", fontName="CEPOESBold", fontSize=13, leading=18, textColor=NAVY, leftIndent=9*mm, rightIndent=6*mm, borderColor=TEAL, borderWidth=0, borderPadding=7, spaceBefore=6, spaceAfter=10),
    "cardv": ParagraphStyle("cardv", fontName="CEPOESBold", fontSize=19, leading=21, textColor=NAVY, alignment=TA_CENTER),
    "cardl": ParagraphStyle("cardl", fontName="CEPOESRegular", fontSize=7.2, leading=9.4, textColor=MUTED, alignment=TA_CENTER),
    "link": ParagraphStyle("link", fontName="CEPOESBold", fontSize=9, leading=12, textColor=NAVY, spaceAfter=2),
}

def P(text, style="body"):
    return Paragraph(text, S[style])

def kpis(items):
    cells = []
    for value, label, source in items:
        cells.append([P(value, "cardv"), P(label, "cardl"), P(source, "cardl")])
    t = Table([cells], colWidths=[(PAGE_W - 2*MARGIN_X)/len(cells)], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.white),
        ("BOX", (0,0), (-1,-1), 0.6, LINE),
        ("INNERGRID", (0,0), (-1,-1), 0.6, LINE),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 9),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]))
    return t

def sector_chart():
    labels = ["Finanzas", "Agro", "Salud", "Transporte", "Inmobiliarios", "Industria", "Comercio", "Serv. personales"]
    vals = [7.7, 2.4, 1.0, 0.9, -0.7, -1.8, -2.2, -3.3]
    d = Drawing(470, 210)
    chart = HorizontalBarChart()
    chart.x, chart.y, chart.width, chart.height = 115, 25, 330, 165
    chart.data = [vals]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = "CEPOESRegular"
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = -4
    chart.valueAxis.valueMax = 8
    chart.valueAxis.valueStep = 2
    chart.valueAxis.labels.fontName = "CEPOESRegular"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.gridStrokeColor = LINE
    chart.bars[0].fillColor = TEAL
    chart.bars[0].strokeColor = None
    for i, value in enumerate(vals):
        chart.bars[(0, i)].fillColor = TEAL if value >= 0 else RED
    d.add(chart)
    d.add(String(115, 202, "Variación interanual por sector (%)", fontName="CEPOESBold", fontSize=9, fillColor=NAVY))
    return d

def income_chart():
    labels = ["IPCBA", "Ingreso familiar", "Ingresos laborales", "Cuenta propia", "Asalariados sin descuento"]
    vals = [32.7, 27.1, 23.6, 8.6, 5.0]
    d = Drawing(470, 205)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 48, 42, 390, 135
    chart.data = [vals]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = "CEPOESRegular"
    chart.categoryAxis.labels.fontSize = 6.2
    chart.categoryAxis.labels.angle = 18
    chart.categoryAxis.labels.boxAnchor = "ne"
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 35
    chart.valueAxis.valueStep = 5
    chart.valueAxis.labels.fontName = "CEPOESRegular"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.gridStrokeColor = LINE
    chart.bars[0].fillColor = TEAL
    chart.bars[0].strokeColor = None
    d.add(chart)
    d.add(String(48, 192, "Variación interanual (%)", fontName="CEPOESBold", fontSize=9, fillColor=NAVY))
    return d

def consumption_chart():
    labels = ["Supermercados", "Mayoristas", "Shoppings", "Electrodomésticos", "Autos"]
    vals = [-1.2, -17.6, 6.5, -3.7, -3.9]
    d = Drawing(470, 205)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 48, 42, 390, 135
    chart.data = [vals]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = "CEPOESRegular"
    chart.categoryAxis.labels.fontSize = 6.5
    chart.categoryAxis.labels.angle = 15
    chart.categoryAxis.labels.boxAnchor = "ne"
    chart.valueAxis.valueMin = -20
    chart.valueAxis.valueMax = 10
    chart.valueAxis.valueStep = 5
    chart.valueAxis.labels.fontName = "CEPOESRegular"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.gridStrokeColor = LINE
    chart.bars[0].fillColor = RED
    chart.bars[0].strokeColor = None
    for i, value in enumerate(vals):
        chart.bars[(0, i)].fillColor = TEAL if value >= 0 else RED
    d.add(chart)
    d.add(String(48, 192, "Ventas reales / unidades, variación interanual (%)", fontName="CEPOESBold", fontSize=9, fillColor=NAVY))
    return d

def report_table():
    rows = [
        ("Endeudarse para llegar a fin de mes", "https://cepoes.org/publicaciones/informes/endeudarse-para-llegar-a-fin-de-mes/"),
        ("Situación de calle en la Ciudad de Buenos Aires", "https://cepoes.org/publicaciones/informes/situacion-de-calle-caba/"),
        ("Personas mayores en la Ciudad de Buenos Aires", "https://cepoes.org/publicaciones/informes/personas-mayores-caba/"),
        ("Seis años de registro y ningún número", "https://cepoes.org/publicaciones/informes/plataformas-juventudes-caba/"),
        ("Dos evaluaciones, dos respuestas opuestas", "https://cepoes.org/publicaciones/informes/educacion-pisa-fepba-2025/"),
        ("Tormenta Negra y la seguridad que queda en el barrio", "https://cepoes.org/publicaciones/notas/tormenta-negra-seguridad-territorio/"),
        ("Tierras y soberanía", "https://cepoes.org/territorio/tierras-y-soberania/"),
    ]
    data = []
    for i, (title, url) in enumerate(rows, 1):
        data.append([P(f"{i:02d}", "h3"), Paragraph(f'<link href="{url}"><b>{title}</b><br/><font color="#52636E">Abrir publicación en cepoes.org →</font></link>', S["link"])])
    t = Table(data, colWidths=[13*mm, PAGE_W-2*MARGIN_X-13*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.white),
        ("LINEBELOW", (0,0), (-1,-2), .5, LINE),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    return t

def on_page(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H-14*mm, PAGE_W, 14*mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("CEPOESBold", 8)
        canvas.drawString(MARGIN_X, PAGE_H-9*mm, "CEPOES · LA CIUDAD QUE HABITAMOS · N.º 5")
        canvas.setFillColor(MUTED)
        canvas.setFont("CEPOESRegular", 7)
        canvas.drawString(MARGIN_X, 9*mm, "Septiembre de 2026 · Datos oficiales del segundo trimestre")
        canvas.drawRightString(PAGE_W-MARGIN_X, 9*mm, str(doc.page))
        canvas.setStrokeColor(LINE)
        canvas.line(MARGIN_X, 13*mm, PAGE_W-MARGIN_X, 13*mm)
    canvas.restoreState()

doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=MARGIN_X, rightMargin=MARGIN_X, topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
                      title="La recuperación que no llega a los barrios", author="CEPOES", subject="Boletín CEPOES N.º 5, septiembre de 2026")
frame = Frame(MARGIN_X, MARGIN_BOTTOM, PAGE_W-2*MARGIN_X, PAGE_H-MARGIN_TOP-MARGIN_BOTTOM, id="normal")
doc.addPageTemplates(PageTemplate(id="all", frames=[frame], onPage=on_page))

story = []

# Cover
story += [Spacer(1, 8*mm), P("LA CIUDAD QUE HABITAMOS", "eyebrow"), P("Boletín CEPOES · N.º 5 · Septiembre 2026", "small"), Spacer(1, 26*mm)]
cover_title = Paragraph("La recuperación<br/>que no llega<br/>a los barrios", ParagraphStyle("cover", fontName="CEPOESBold", fontSize=35, leading=41, textColor=NAVY, spaceAfter=16))
story += [cover_title, Paragraph("La economía porteña casi no crece y su impulso se concentra en las finanzas. Comercio, industria, consumo e ingresos muestran otra Ciudad.", ParagraphStyle("coverdek", fontName="CEPOESRegular", fontSize=14, leading=20, textColor=MUTED, spaceAfter=18)), HRFlowable(width="100%", thickness=5, color=TEAL), Spacer(1, 24*mm)]
story += [P("+0,3% PGB interanual · -0,2% frente al trimestre anterior · 675.000 personas pobres", "h3"), Spacer(1, 23*mm), P("CEPOES", "h1"), P("Centro de Estudios en Política, Economía y Sociedad", "small"), PageBreak()]

# Executive summary
story += [P("RESUMEN EJECUTIVO", "eyebrow"), P("Una recuperación concentrada que no mejora la vida cotidiana", "h1")]
story += [kpis([("+0,3%", "PGB interanual", "IDECBA"), ("-0,2%", "Variación trimestral", "Desestacionalizada"), ("-9,1 pp", "Ingresos laborales vs. precios", "23,6% vs. 32,7%"), ("675 mil", "Personas pobres", "21,9%")]), Spacer(1, 7*mm)]
story += [P("El Producto Geográfico Bruto de la Ciudad creció apenas 0,3% frente al segundo trimestre de 2025 y cayó 0,2% frente al trimestre anterior. El propio IDECBA identifica una desaceleración iniciada en el tercer trimestre de 2025. No se trata de una recuperación robusta: el nivel general prácticamente se estancó."), P("La composición del crecimiento es todavía más reveladora. La intermediación financiera aumentó 7,7% y aportó más de un punto porcentual al resultado general. En sentido contrario, el comercio cayó 2,2%, la industria manufacturera 1,8%, los servicios personales 3,3% y el servicio doméstico 2,1%."), P("La desocupación se mantuvo en 7,2%, pero la presión laboral alcanzó al 14,8% de la población económicamente activa. Los ingresos laborales crecieron 23,6%, nueve puntos por debajo de la inflación porteña. La pobreza afecta a 675.000 personas y se concentra especialmente en el sur y en los hogares con niños y niñas."), P("La pregunta no es solamente cuánto crece la Ciudad, sino qué actividades crecen, quiénes reciben ese crecimiento y en qué barrios se transforma en empleo e ingresos.", "quote"), PageBreak()]

# Activity
story += [P("ACTIVIDAD ECONÓMICA", "eyebrow"), P("Quién crece y quién retrocede", "h1"), P("El promedio del PGB oculta una economía de velocidades opuestas. La intermediación financiera explica el avance, mientras sectores con mayor presencia territorial permanecen estancados o en retroceso."), sector_chart(), Spacer(1, 3*mm)]
story += [Table([[P("El motor financiero", "h3"), P("La intermediación financiera creció 7,7%. Sobresalieron fondos comunes de inversión, agentes de bolsa e intermediación bancaria y no bancaria. Su contribución al PGB fue de 1,01 puntos porcentuales: sin ese impulso, el resultado agregado habría sido negativo.")], [P("La economía real", "h3"), P("Comercio cayó 2,2% e industria 1,8%. La construcción apenas creció 0,3%. Servicios inmobiliarios y empresariales retrocedieron 0,7% y servicios personales 3,3%. El crecimiento no está asentado en actividades capaces de derramarse territorialmente por sí solas.")]], colWidths=[45*mm, PAGE_W-2*MARGIN_X-45*mm], style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-2),.5,LINE),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)])), Spacer(1,3*mm), P("Fuente: IDECBA, Informe de resultados 2061. Datos preliminares.", "small"), PageBreak()]

# Work and income
story += [P("TRABAJO E INGRESOS", "eyebrow"), P("Más presión laboral y menos poder adquisitivo", "h1"), kpis([("7,2%", "Desocupación", "125.000 personas"), ("14,8%", "Presión laboral", "+1,8 pp interanual"), ("26,5%", "Asalariados sin descuento", "IDECBA")]), Spacer(1, 6*mm), income_chart()]
story += [P("La tasa de desocupación no cambió significativamente, pero aumentó la búsqueda de más horas o de otra ocupación entre quienes ya trabajan. Las mujeres representan el 60,7% de la población desocupada y el 61,9% de la subocupada."), P("Los ingresos quedaron detrás de los precios en casi todas las categorías. El ingreso total familiar creció 27,1% frente a una inflación de 32,7%. Los ingresos laborales aumentaron 23,6%; los de trabajadores por cuenta propia, 8,6%; y los de asalariados sin descuento jubilatorio, apenas 5%."), P("Fuentes: IDECBA, informes de resultados 2058 y 2059.", "small"), PageBreak()]

# Poverty
story += [P("CONDICIONES DE VIDA", "eyebrow"), P("La pobreza dejó de bajar y conserva un mapa desigual", "h1"), kpis([("21,9%", "Personas pobres", "675.000"), ("6,3%", "Personas indigentes", "193.000"), ("24,9%", "Hogares pobres en zona sur", "IDECBA"), ("28,2%", "Hogares con menores de 14", "IDECBA")]), Spacer(1, 8*mm)]
story += [P("La pobreza se mantiene cerca del registro del mismo trimestre de 2025, pero la trayectoria reciente empeoró. Frente al cuarto trimestre de 2025 aumentó 1,6 puntos entre los hogares y 0,8 puntos entre las personas. En el primer semestre también creció en términos interanuales, impulsada por la indigencia."), P("El promedio oculta diferencias territoriales y demográficas. La incidencia en los hogares de la zona sur supera en 7,6 puntos el promedio de la Ciudad. Los hogares con niños y niñas menores de 14 años alcanzan una incidencia de 28,2%. La brecha media para que un hogar pobre llegue a la canasta básica total es de $424.597."), P("Estos resultados dialogan directamente con la pérdida de poder adquisitivo. El crecimiento agregado convive con ingresos laborales que pierden contra los precios y con una mayor presión por conseguir trabajo o ampliar la jornada."), P("Fuente: IDECBA, Informe de resultados 2060. Algunos valores poseen carácter indicativo según el coeficiente de variación informado por la fuente.", "small"), PageBreak()]

# Consumption
story += [P("CONSUMO Y COMERCIO", "eyebrow"), P("El consumo cotidiano sigue en retroceso", "h1"), P("Los indicadores del comercio minorista describen una recuperación muy desigual. El crecimiento de los shoppings no compensa la caída del consumo masivo ni la debilidad de otros rubros."), consumption_chart(), Spacer(1, 4*mm)]
story += [P("Las ventas reales en supermercados bajaron 1,2% y confirmaron la tendencia del primer trimestre. Los autoservicios mayoristas cayeron 17,6% y completaron diez trimestres consecutivos de retracción. También descendieron las ventas de electrodomésticos y los patentamientos de automotores."), P("Los shoppings crecieron 6,5%, impulsados parcialmente por descuentos y promociones financieras extraordinarias durante mayo. Pese a la mejora, registraron nueve locales activos menos que un año antes. El dato positivo es real, pero no representa al conjunto del comercio porteño."), P("Fuente: IDECBA, Informe de resultados 2062. Datos provisorios.", "small"), PageBreak()]

# Proposals
story += [P("AGENDA PÚBLICA", "eyebrow"), P("Hacer que el crecimiento llegue a la economía real y a los barrios", "h1")]
proposals = [
    ("01", "Crédito productivo con tasa real negativa", "Usar el Banco Ciudad para financiar inversión, capital de trabajo, digitalización y eficiencia energética de pymes y comercios, con metas verificables de empleo y producción."),
    ("02", "Transferencia tecnológica", "Vincular el financiamiento con universidades, centros tecnológicos y el sistema científico para resolver problemas productivos concretos y mejorar capacidades de las pequeñas empresas."),
    ("03", "Ingresos y formalización", "Priorizar a trabajadores por cuenta propia, asalariados no registrados, plataformas y actividades de cuidados, donde la pérdida real fue más intensa."),
    ("04", "Compras públicas para el desarrollo local", "Orientar una porción de la demanda del GCBA hacia proveedores y cooperativas locales con criterios de empleo formal, innovación y arraigo territorial."),
    ("05", "Tablero territorial de actividad y empleo", "Publicar indicadores comparables por comuna y ejes comerciales para diseñar políticas que no operen sólo con promedios de toda la Ciudad."),
]
rows=[]
for n,t,b in proposals:
    rows.append([P(n,"h3"), [P(t,"h3"), P(b)]])
pt=Table(rows,colWidths=[14*mm,PAGE_W-2*MARGIN_X-14*mm])
pt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.white),("LINEBELOW",(0,0),(-1,-2),.5,LINE),("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
story += [pt, Spacer(1, 7*mm), P("La Ciudad tiene capacidad fiscal, financiera, institucional y científica para orientar una estrategia productiva. La discusión central es qué actividades, empresas y territorios prioriza.", "quote"), PageBreak()]

# Reports
story += [P("PRODUCCIÓN RECIENTE", "eyebrow"), P("Nuevos informes de CEPOES", "h1"), P("El boletín se integra con una agenda de investigaciones y dossiers que profundizan los problemas sociales, productivos y territoriales. Los enlaces son activos en esta versión PDF."), report_table(), Spacer(1, 8*mm), P("Cita sugerida", "h3"), P("CEPOES (2026). «La recuperación que no llega a los barrios». La Ciudad que habitamos, N.º 5, septiembre de 2026."), PageBreak()]

# Sources
story += [P("DATOS Y FUENTES", "eyebrow"), P("Fuentes oficiales y criterios de lectura", "h1")]
sources = [
    ("IDECBA 2058", "Situación del mercado laboral de la Ciudad de Buenos Aires. 2.º trimestre de 2026.", "https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2058.pdf"),
    ("IDECBA 2059", "Ingresos en la Ciudad de Buenos Aires. 2.º trimestre de 2026.", "https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2059.pdf"),
    ("IDECBA 2060", "Condiciones de vida: indigencia, pobreza por ingresos y estratificación. 2.º trimestre de 2026.", "https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2060.pdf"),
    ("IDECBA 2061", "Actividad económica. Estimación del Producto Geográfico Bruto. 2.º trimestre de 2026.", "https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2061.pdf"),
    ("IDECBA 2062", "Dinámica del comercio minorista. 2.º trimestre de 2026.", "https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2062.pdf"),
]
for code,title,url in sources:
    story += [Paragraph(f'<link href="{url}"><b>{code}</b> · {title}</link>', S["body"])]
story += [Spacer(1,5*mm), P("Criterios metodológicos", "h2"), P("Los datos de actividad económica son preliminares; los de comercio minorista son provisorios. Los indicadores de mercado laboral, ingresos y pobreza provienen de la Encuesta Trimestral de Ocupación e Ingresos. Cuando IDECBA identifica estimaciones con coeficientes de variación elevados, se conserva esa advertencia. Las comparaciones expresadas en puntos porcentuales son cálculos directos sobre valores publicados; la interpretación política corresponde a CEPOES."), Spacer(1,12*mm), HRFlowable(width="100%", thickness=4, color=TEAL), Spacer(1,5*mm), P("CEPOES", "h1"), P("Centro de Estudios en Política, Economía y Sociedad · Evidencia para decidir y gobernar", "small")]

doc.build(story)
print(OUT)
