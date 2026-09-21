#!/usr/bin/env python3
"""Genera informes CEPOES con la plantilla editorial institucional.

La portada, los interiores y las miniaturas comparten una misma identidad:
azul institucional, celeste CEPOES, metadatos, indice, encabezado y pie.
El contenido sustantivo se conserva en estructuras declarativas para que los
documentos puedan regenerarse de forma reproducible.
"""

from __future__ import annotations

import os
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = Path(os.environ.get("CEPOES_SITE_ROOT", REPO_ROOT / "deploy" / "site-overlay"))

NAVY = colors.HexColor("#172A4A")
NAVY_DARK = colors.HexColor("#10213C")
BLUE = colors.HexColor("#49A6DC")
BLUE_LIGHT = colors.HexColor("#DCEFF8")
TEXT = colors.HexColor("#1D2D45")
MUTED = colors.HexColor("#526477")
LINE = colors.HexColor("#AEB8C2")
PALE = colors.HexColor("#F3F7FA")
WHITE = colors.white


def register_fonts() -> tuple[str, str, str]:
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        ("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf"),
    ]
    for regular, bold, italic in candidates:
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont("CEPOES", regular))
            pdfmetrics.registerFont(TTFont("CEPOES-Bold", bold))
            if Path(italic).exists():
                pdfmetrics.registerFont(TTFont("CEPOES-Italic", italic))
            else:
                pdfmetrics.registerFont(TTFont("CEPOES-Italic", regular))
            return "CEPOES", "CEPOES-Bold", "CEPOES-Italic"
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


FONT, FONT_BOLD, FONT_ITALIC = register_fonts()


def clean_markup(text: str) -> str:
    return escape(text).replace("\n", "<br/>")


def styles():
    base = getSampleStyleSheet()
    return {
        "report": ParagraphStyle("Report", parent=base["Normal"], fontName=FONT_BOLD, fontSize=10.5, leading=13, textColor=TEXT, spaceAfter=4),
        "title": ParagraphStyle("Title", parent=base["Title"], fontName=FONT_BOLD, fontSize=27, leading=30, textColor=BLUE, alignment=TA_LEFT, spaceAfter=3),
        "subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontName=FONT, fontSize=14, leading=18, textColor=TEXT, spaceAfter=6),
        "section": ParagraphStyle("Section", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=16, leading=19, textColor=TEXT, spaceBefore=14, spaceAfter=7, keepWithNext=True),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName=FONT, fontSize=9.7, leading=14.1, textColor=TEXT, spaceAfter=7, allowWidows=0, allowOrphans=0),
        "lead": ParagraphStyle("Lead", parent=base["BodyText"], fontName=FONT, fontSize=10.4, leading=15, textColor=TEXT, spaceAfter=8),
        "bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName=FONT, fontSize=9.5, leading=13.7, textColor=TEXT, leftIndent=12, firstLineIndent=-7, bulletIndent=0, spaceAfter=4),
        "source": ParagraphStyle("Source", parent=base["BodyText"], fontName=FONT, fontSize=8.6, leading=12.4, textColor=MUTED, leftIndent=12, firstLineIndent=-7, bulletIndent=0, spaceAfter=3),
        "table": ParagraphStyle("Table", parent=base["BodyText"], fontName=FONT, fontSize=7.7, leading=10.1, textColor=TEXT),
        "table_bold": ParagraphStyle("TableBold", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=7.7, leading=10.1, textColor=TEXT),
        "table_head": ParagraphStyle("TableHead", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=7.7, leading=10.1, textColor=WHITE),
    }


S = styles()


def p(text: str, style="body") -> Paragraph:
    return Paragraph(clean_markup(text), S[style])


def bullet(text: str, style="bullet") -> Paragraph:
    return Paragraph("• " + clean_markup(text), S[style])


def make_table(headers, rows, widths):
    data = [[Paragraph(escape(str(x)), S["table_head"]) for x in headers]]
    data.extend([[Paragraph(escape(str(x)), S["table"]) for x in row] for row in rows])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D9D9D9")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def wrap_canvas_text(canvas, text, x, y, max_width, font, size, leading, color, max_lines=None):
    words = text.split()
    lines, current = [], []
    for word in words:
        trial = " ".join(current + [word])
        if canvas.stringWidth(trial, font, size) <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current)); current = [word]
    if current:
        lines.append(" ".join(current))
    if max_lines:
        lines = lines[:max_lines]
    canvas.setFont(font, size); canvas.setFillColor(color)
    for line in lines:
        canvas.drawString(x, y, line); y -= leading
    return y


def cover_page(report):
    def draw(canvas, doc):
        w, h = A4
        canvas.saveState()
        canvas.setFillColor(NAVY); canvas.rect(0, 0, w, h, fill=1, stroke=0)
        canvas.setFillColor(NAVY_DARK); canvas.rect(0, 0, w, 108, fill=1, stroke=0)
        # Marca circular de la plantilla.
        canvas.setStrokeColor(NAVY_DARK); canvas.setLineWidth(26)
        canvas.circle(w - 70, 250, 125, fill=0, stroke=1)
        canvas.setLineWidth(19); canvas.circle(w - 70, 250, 75, fill=0, stroke=1)

        canvas.setFillColor(WHITE); canvas.setFont(FONT, 10.5)
        canvas.drawString(54, h - 60, f'Informe “{report["short_name"]}”')
        canvas.setFont(FONT_BOLD, 11.5); canvas.drawRightString(w - 185, h - 60, report["number"])
        canvas.setFillColor(BLUE); canvas.drawRightString(w - 54, h - 60, "SEPTIEMBRE 2026")

        y = h - 145
        y = wrap_canvas_text(canvas, report["title"], 54, y, w - 108, FONT_BOLD, 29, 34, BLUE, 4)
        y -= 10
        y = wrap_canvas_text(canvas, report["subtitle"], 54, y, w - 108, FONT, 16.5, 21, WHITE, 3)
        y -= 6
        wrap_canvas_text(canvas, report["description"], 54, y, w - 108, FONT, 11.2, 15, BLUE, 2)

        meta_y = 430
        columns = [(54, "PUBLICACIÓN", "Septiembre\n2026"), (178, "FUENTES PRIMARIAS", report["sources_cover"]), (348, "ENFOQUE TEMÁTICO", report["theme"]), (475, "ALCANCE TERRITORIAL", report["scope"])]
        for x, label, value in columns:
            canvas.setFillColor(BLUE); canvas.setFont(FONT, 7.4); canvas.drawString(x, meta_y, label)
            wrap_canvas_text(canvas, value.replace("\n", " "), x, meta_y - 18, 105 if x != 178 else 145, FONT, 9.2, 13, WHITE, 3)

        idx_y = 340
        canvas.setFont(FONT, 10); canvas.setFillColor(BLUE)
        for i, heading in enumerate(report["index"], 1):
            canvas.drawString(54, idx_y, f"{roman(i)}.  {heading}")
            idx_y -= 19

        canvas.setFillColor(BLUE); canvas.setFont(FONT_BOLD, 10.5); canvas.drawString(60, 67, "CEPOES")
        canvas.setFont(FONT, 8.8); canvas.drawString(108, 67, "Centro de Estudios en Política, Economía y Sociedad | Somos 100 Barrios")
        canvas.setStrokeColor(LINE); canvas.setLineWidth(0.8); canvas.line(60, 58, w - 60, 58)
        canvas.restoreState()
    return draw


def body_page(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(TEXT); canvas.setFont(FONT_BOLD, 7.9); canvas.drawString(62, h - 42, "CEPOES")
    canvas.setFont(FONT, 7.9); canvas.drawString(100, h - 42, "Centro de Estudios en Política, Economía y Sociedad | Somos 100 Barrios")
    canvas.setStrokeColor(LINE); canvas.setLineWidth(0.7); canvas.line(62, h - 51, w - 62, h - 51)
    canvas.line(62, 42, w - 62, 42)
    canvas.setFillColor(MUTED); canvas.setFont(FONT_ITALIC, 7.2); canvas.drawString(62, 25, "CEPOES")
    canvas.setFont(FONT, 7.2); canvas.drawRightString(w - 62, 25, str(doc.page))
    canvas.restoreState()


def roman(n):
    return ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"][n - 1]


def section_story(report, sections):
    story = [PageBreak(), p(report["short_name"], "report"), p(report["title"], "title"), p(report["subtitle"], "subtitle"), p("CEPOES", "report"), Spacer(1, 6)]
    for idx, sec in enumerate(sections, 1):
        story.append(p(f"{roman(idx)}. {sec['title']}", "section"))
        for item in sec["items"]:
            kind = item[0]
            if kind == "p": story.append(p(item[1], item[2] if len(item) > 2 else "body"))
            elif kind == "bullet": story.append(bullet(item[1]))
            elif kind == "source": story.append(bullet(item[1], "source"))
            elif kind == "table":
                story.append(KeepTogether([Spacer(1, 2), make_table(item[1], item[2], item[3]), Spacer(1, 8)]))
    return story


EDUCATION = {
    "slug": "educacion-pisa-fepba",
    "short_name": "Educación PISA y FEPBA",
    "number": "I.04",
    "title": "Dos evaluaciones, dos respuestas opuestas",
    "subtitle": "Qué pasó con la educación porteña entre 2023 y 2025",
    "description": "Evaluaciones, comparabilidad y apertura de datos",
    "sources_cover": "OCDE / UEICEE / Cuenta Anual",
    "theme": "Educación",
    "scope": "Ciudad de Buenos Aires",
    "index": ["Síntesis", "Lo que dice PISA", "Evaluaciones porteñas", "Cómo pueden ser ciertas", "Contexto y alcance", "Propuestas y fuentes"],
    "filename": "informe-educacion-pisa-fepba-cepoes.pdf",
    "pdf_dir": "publicaciones/informes/educacion-pisa-fepba-2025",
    "thumb": "educacion-pisa-fepba.svg",
}

EDU_SECTIONS = [
    {"title": "Síntesis", "items": [
        ("p", "El 8 de septiembre de 2026 se publicaron los resultados de PISA 2025. La Ciudad de Buenos Aires participó con muestra ampliada propia y volvió a obtener el mejor desempeño del país: 418 puntos en Matemática, 432 en Lectura y 449 en Ciencias, entre 43 y 56 puntos por encima del promedio nacional. Ese es el dato que el Gobierno de la Ciudad va a comunicar, y es cierto.", "lead"),
        ("p", "Hay un segundo dato, y es el que no se está discutiendo: respecto de 2022, la Ciudad cae en las tres áreas, y en Lectura cae 17 puntos - casi el triple que en Matemática y más de ocho veces la caída en Ciencias."),
        ("p", "Hay un tercero, y es el que vuelve interesante a los dos anteriores. Nueve meses antes, en diciembre de 2025, el Ministerio de Educación porteño publicó los resultados de sus propias evaluaciones censales, FEPBA y TESBA, y el titular fue exactamente el contrario: mejoras en Lengua y Matemática, en los dos sectores de gestión, con reducción de la brecha entre escuela estatal y privada."),
        ("p", "Las dos cosas se afirman sobre la misma cohorte y el mismo período. El único instrumento que mejora es el que la jurisdicción evaluada diseña, aplica y reporta. El instrumento externo empeora. Este informe sostiene que esa discrepancia no es un detalle técnico: es el problema de política pública, y admite una solución concreta y barata."),
    ]},
    {"title": "Lo que dice PISA", "items": [
        ("p", "PISA 2025 evaluó a estudiantes de 15 años en 91 países y economías. La muestra argentina fue de 11.093 estudiantes en 412 escuelas."),
        ("p", "Argentina", "report"),
        ("table", ["Área", "2022", "2025", "Por debajo del nivel mínimo (2025)"], [["Matemática", "378", "367", "76%"], ["Lectura", "401", "389", "59%"], ["Ciencias", "406", "393", "59%"]], [35*mm, 23*mm, 23*mm, 82*mm]),
        ("p", "Ciudad de Buenos Aires, que participó como región adjudicada con muestra propia ampliada, igual que en 2022:", "report"),
        ("table", ["Área", "2025", "Variación vs. 2022", "Diferencia vs. promedio nacional"], [["Matemática", "418", "-6", "+51"], ["Lectura", "432", "-17", "+43"], ["Ciencias", "449", "-2", "+56"]], [35*mm, 23*mm, 48*mm, 57*mm]),
        ("p", "Conviene registrar una advertencia de fuente antes de seguir. Las cifras de posición en el ranking que circularon en prensa la semana del 8 de septiembre no coinciden entre sí: algunas coberturas ubicaron a la Argentina en el puesto 66 sobre 81 participantes en Matemática, mientras que el informe de Argentinos por la Educación sobre los datos de la OCDE consigna el puesto 75 sobre 91 países. Antes de citar cualquier ranking hay que fijar el universo."),
    ]},
    {"title": "Lo que dicen las evaluaciones porteñas", "items": [
        ("p", "FEPBA (7° grado de primaria) y TESBA (3° año de secundaria) son evaluaciones censales de la Ciudad, aplicadas y reportadas por la Unidad de Evaluación Integral de la Calidad y Equidad Educativa (UEICEE), que depende del Ministerio de Educación porteño. Los resultados de 2025 se publicaron el 10 de diciembre de 2025."),
        ("p", "FEPBA - 7° grado, porcentaje de estudiantes con desempeño medio-alto", "report"),
        ("table", ["Área", "2023", "2025"], [["Lengua", "61,7%", "65,5%"], ["Matemática", "33,5%", "40,7%"]], [75*mm, 44*mm, 44*mm]),
        ("p", "TESBA - 3° año, porcentaje con desempeño medio-alto: 38,4% en 2023 y 42,9% en 2025."),
        ("p", "En puntaje, las mejoras informadas respecto de 2023 fueron de 17,2 puntos en Matemática en escuelas estatales y 15,2 en privadas para FEPBA, y de 14,2 y 9,9 puntos respectivamente para TESBA. La brecha entre gestión estatal y privada se redujo en las dos evaluaciones."),
        ("p", "Hay una excepción, y es la que importa. En TESBA Lengua, la mejora es de apenas 2,9 puntos en el sector estatal, y en el sector privado el resultado cae 2,8 puntos. Es el único indicador del reporte oficial que retrocede."),
        ("p", "Es decir: Lectura es el área donde los dos instrumentos coinciden en el signo. PISA la marca con una caída de 17 puntos en la Ciudad; la propia evaluación porteña de secundaria la marca como el único punto donde no hay mejora y donde un sector directamente empeora. Cuando dos instrumentos independientes convergen, la hipótesis del error de medición se debilita."),
    ]},
    {"title": "Cómo pueden ser ciertas las dos cosas", "items": [
        ("p", "Hay al menos cuatro explicaciones posibles, y conviene enunciarlas como hipótesis y no como conclusiones:"),
        ("bullet", "1. Base deprimida. 2023 fue el primer ciclo de evaluación plenamente post-pandémico. Mejorar contra un piso bajo no equivale a recuperar el nivel previo."),
        ("bullet", "2. Poblaciones distintas. FEPBA evalúa 7° grado y TESBA 3° año; PISA evalúa a los estudiantes de 15 años que están escolarizados, sin importar el año que cursan. En una jurisdicción con sobreedad y abandono, las dos poblaciones no son idénticas."),
        ("bullet", "3. Constructos distintos. PISA mide competencia aplicada a situaciones nuevas; las evaluaciones jurisdiccionales se alinean con el diseño curricular local. Se puede mejorar en lo segundo sin moverse en lo primero."),
        ("bullet", "4. Falta de anclaje externo. Las escalas de FEPBA y TESBA no están ancladas públicamente a ninguna referencia externa. No existe una equivalencia publicada que permita saber qué significa, en términos de PISA o de Aprender, un \"desempeño medio-alto\" porteño."),
        ("p", "Las cuatro explicaciones son razonables. Ninguna se puede descartar hoy, porque el Estado porteño no publica la información que permitiría hacerlo. Ese es el hallazgo central de este informe: el problema no es que los resultados sean buenos o malos, sino que la Ciudad ha construido un sistema de evaluación cuyo resultado no es verificable por nadie más."),
    ]},
    {"title": "Contexto presupuestario y alcance metodológico", "items": [
        ("p", "La participación de Educación en el gasto total del Gobierno de la Ciudad, según la Cuenta Anual de Inversión:"),
        ("table", ["Año", "Participación"], [["2010", "26,6%"], ["2015", "23,1%"], ["2021", "17,8%"], ["2024", "20,6%"]], [82*mm, 81*mm]),
        ("p", "En catorce años, Educación perdió seis puntos de participación en el presupuesto porteño. Tocó su piso en 2021 y recuperó parcialmente hasta 2024, pero sigue seis puntos por debajo del nivel de 2010."),
        ("p", "A esto se agrega un dato del propio análisis fiscal del CEPOES: en 2025 la jurisdicción Educación ejecutó el 97,6% de su crédito sancionado y el 97,5% del vigente, sin refuerzo presupuestario durante el ejercicio. Es decir, no hubo subejecución ni reasignación: el área gastó lo que se le asignó. El problema no es de ejecución, es de asignación."),
        ("p", "Alcance metodológico y criterios de comparación", "report"),
        ("bullet", "PISA es una evaluación muestral; FEPBA y TESBA son evaluaciones censales y alcanzan poblaciones diferentes. La comparación entre sus resultados se utiliza como señal de alerta y de convergencia, no como equivalencia entre mediciones."),
        ("bullet", "Los puntajes de Lengua y Matemática pertenecen a escalas diferentes. Una priorización territorial rigurosa debe comparar cada comuna con el promedio de la Ciudad dentro de la misma materia o utilizar el porcentaje de estudiantes por debajo del nivel básico, una métrica de incidencia comparable entre áreas."),
        ("bullet", "PISA ofrece resultados para el conjunto de la jurisdicción. El análisis por comuna corresponde a FEPBA y TESBA, que cuentan con desagregación territorial."),
        ("bullet", "La unidad geográfica disponible es la comuna donde se ubica la escuela. Los resultados caracterizan a los establecimientos de ese territorio y deben distinguirse de las condiciones educativas de la población residente."),
        ("bullet", "FEPBA y TESBA observan dos momentos específicos: 7° grado y 3° año. Reconstruir una trayectoria educativa requiere sumar series intermedias de repitencia, sobreedad, promoción y materias adeudadas, que actualmente no se publican con ese nivel de detalle."),
    ]},
    {"title": "Propuestas y fuentes", "items": [
        ("p", "Las cuatro propuestas son de competencia exclusiva de la Ciudad, no requieren ley nacional y no tienen costo fiscal relevante."),
        ("bullet", "1. Anclar externamente la escala de FEPBA y TESBA. Publicar la equivalencia entre los niveles de desempeño porteños y los de PISA y Aprender, o someter una submuestra a corrección externa independiente. Mientras la jurisdicción evaluada sea la que diseña, aplica, corrige y comunica su propia evaluación, sus resultados no son verificables, y un resultado no verificable no sirve para conducir política pública ni para defenderla."),
        ("bullet", "2. Abrir el Boletín Tu Escuela. Desde el 10 de marzo de 2026 la Ciudad produce, con fondos públicos, un boletín con resultados por establecimiento más matrícula, repitencia, sobreedad, promoción y clima escolar. El acceso está restringido a supervisores y directivos. Es información pagada por los contribuyentes que los contribuyentes no pueden ver. Debe publicarse en formato abierto, con los resguardos de anonimización que correspondan."),
        ("bullet", "3. Publicar FEPBA y TESBA por comuna usando el porcentaje por debajo del nivel básico. El tablero Aprendizaje en Datos ya permite filtrar por comuna, pero comunica puntajes promedio, que no son comparables entre materias. Publicar la incidencia - qué proporción de estudiantes no alcanza el piso - permite priorizar territorialmente sin incurrir en el error de escala. La Ley 6.888, que reemplaza los 21 distritos escolares por las 15 comunas, convierte a la comuna en la unidad oficial de la geografía educativa porteña: la estadística debería seguir a la norma."),
        ("bullet", "4. Restituir la participación presupuestaria. Fijar por ley un piso de participación de Educación en el gasto total de la Ciudad no inferior al promedio de la década 2010-2019. La ejecución demuestra que el área usa lo que recibe; la discusión, entonces, es cuánto recibe."),
        ("p", "Fuentes", "report"),
        ("source", "OCDE, PISA 2025. Resultados nacionales procesados por Argentinos por la Educación, publicados el 8/9/2026."),
        ("source", "Resultados jurisdiccionales de CABA en PISA 2025, cobertura del 8/9/2026."),
        ("source", "Ministerio de Educación de CABA / UEICEE, Reporte de Resultados FEPBA-TESBA 2025, publicado el 10/12/2025."),
        ("source", "Ministerio de Hacienda y Finanzas de CABA, Dirección General de Contaduría, Cuenta Anual de Inversión, serie de participación del gasto educativo, vía Dirección General de Estadística y Censos (IDECBA)."),
        ("source", "CEPOES, Las cuentas de la Ciudad, junio de 2026, para la ejecución presupuestaria 2025 de la jurisdicción Educación."),
        ("source", "Ley 6.888 de la Ciudad Autónoma de Buenos Aires, sancionada el 27/11/2025."),
        ("source", "Boletín Tu Escuela, Ministerio de Educación de CABA, disponible desde el 10/3/2026."),
    ]},
]


PLATFORMS = {
    "slug": "plataformas-juventudes",
    "short_name": "Plataformas y juventudes",
    "number": "I.05",
    "title": "Seis años de registro y ningún número",
    "subtitle": "Trabajo de plataformas y juventudes en la Ciudad de Buenos Aires",
    "description": "Registro, condiciones laborales y propuestas",
    "sources_cover": "Ley 6.314 / IDECBA / CBC-UBA",
    "theme": "Empleo y economía urbana",
    "scope": "Ciudad de Buenos Aires",
    "index": ["Síntesis", "Cuánta gente", "Cruce con juventudes", "Norma y riesgo", "Propuestas", "Alcance y fuentes"],
    "filename": "informe-plataformas-juventudes-cepoes.pdf",
    "pdf_dir": "publicaciones/informes/plataformas-juventudes-caba",
    "thumb": "plataformas-juventudes.svg",
}

PLAT_SECTIONS = [
    {"title": "Síntesis", "items": [
        ("p", "El 5 de marzo de 2026 el Gobierno de la Ciudad firmó un acuerdo con las plataformas de reparto. Entre otras cosas, el acuerdo otorga 180 días para que los repartidores se inscriban en un régimen simplificado y revaliden su inscripción en el RUTRAMUR, el registro del sector. Ese plazo venció a comienzos de septiembre de 2026.", "lead"),
        ("p", "Es el segundo plazo de 180 días que fija el Estado porteño para lo mismo. El primero está en las cláusulas transitorias de la Ley 6.314, sancionada el 16 de julio de 2020, que creó ese mismo registro. Seis años y dos plazos después, no existe una sola cifra pública que diga cuántos repartidores trabajan en la Ciudad."),
        ("p", "No se trata de que el dato sea difícil de producir. La Ley 6.314 ya obliga a las plataformas a compartir con la autoridad de aplicación información sobre estado de actividad, demanda y recorridos. Si esa obligación se cumpliera, el Estado porteño tendría hoy la mejor - y probablemente la única - estadística del país sobre trabajo de plataformas. No la publica."),
        ("p", "Este informe sostiene que ahí, y no en una ley nacional que no existe, está la primera propuesta viable: la Ciudad no necesita nuevas facultades para regular este sector. Necesita usar las que ya tiene desde 2020."),
    ]},
    {"title": "Cuánta gente estamos hablando: nadie lo sabe", "items": [
        ("p", "Corresponde empezar por el límite. No hay estadística oficial de trabajo de plataformas en la Argentina. Ni el INDEC ni la Dirección General de Estadística y Censos de la Ciudad identifican la actividad como una categoría ocupacional propia. Todo lo que circula son estimaciones producidas por partes interesadas, y este informe las cita nombrando a su productor en el cuerpo del texto, no al pie."),
        ("table", ["Estimación", "Valor", "Quién la produce"], [
            ["Total país, 2025", "Más de 1 millón (aprox. 200 mil repartidores, 900 mil conductores)", "SiTraRepA, sindicato del sector"],
            ["Repartidores PedidosYa, 2025", "100 mil; 84% varones, 44% entre 26 y 35 años, 66% en moto, 70% se conecta 3 h diarias", "PedidosYa"],
            ["Conductores Cabify, 2025", "45 mil habilitados, +30% interanual", "Cabify"],
            ["Jornada de repartidores", "10 a 12 horas, 6 días por semana", "SiTraRepA"],
            ["Perfil de conductores, 2025", "36 años promedio; 7,5 h diarias conectados; más del 60% tiene otro trabajo simultáneo", "Investigación del CONICET con ocho universidades"],
        ], [40*mm, 80*mm, 43*mm]),
        ("p", "Las cifras de volumen las produce quien tiene interés en que sean altas - el sindicato, para mostrar magnitud - o quien tiene interés en que muestren crecimiento - las empresas -. Las de condiciones de trabajo provienen del CONICET y son las más sólidas del conjunto. Corresponde además advertir sobre el \"aumento del 900% en seis años\" que tituló la prensa en julio de 2026: no está publicada la base sobre la que se calcula, y sin base un porcentaje no es un dato."),
        ("p", "El único indicador oficial que se aproxima al fenómeno en la Ciudad es el cuentapropismo. Según la Dirección General de Estadística y Censos porteña, en el primer trimestre de 2026 había 350.500 trabajadores por cuenta propia, el 22% de los ocupados, con un crecimiento interanual del 8,4%. En el mismo período, el 27,3% de los asalariados no tenía descuento jubilatorio, el 9,7% de los ocupados trabajaba menos de 16 horas semanales y la subocupación alcanzaba al 9% de la población económicamente activa, con una desocupación del 7,9% equivalente a 136.500 personas."),
        ("p", "Debe decirse con claridad: el cuentapropismo no es trabajo de plataforma. Es la caja donde el trabajo de plataforma cae cuando se lo mide con instrumentos diseñados antes de que existiera. Es un proxy, no una medición."),
    ]},
    {"title": "Quiénes son: el cruce con las juventudes", "items": [
        ("p", "El estudio más reciente sobre juventudes vulnerables en la Argentina es el del proyecto PIDAE del Ciclo Básico Común de la Universidad de Buenos Aires, con trabajo de campo entre diciembre de 2025 y enero de 2026 sobre 1.002 jóvenes de 18 a 29 años en los principales aglomerados urbanos."),
        ("p", "Define como vulnerable a la persona de 18 a 29 años con primario incompleto o que reside en un hogar con privaciones materiales según el índice del INDEC. Bajo ese criterio:"),
        ("bullet", "4.145.458 jóvenes, el 48,9% del total del país, están en situación de vulnerabilidad. El 27% de ellos reside en el AMBA."),
        ("bullet", "75,9% de los que trabajan lo hacen sin registrar. Sólo 18,9% tiene empleo registrado y 5% monotributo."),
        ("bullet", "78% no tiene cobertura de salud."),
        ("bullet", "57% declara que no llega a fin de mes."),
        ("bullet", "Casi 20% no estudia ni trabaja, y un tercio de ese grupo ya no busca empleo."),
        ("bullet", "Más del 70% refiere ansiedad o nervios frecuentes y 50% desgano o depresión."),
        ("bullet", "85,7% valora estudiar, pero sólo el 15% accede a formación en oficios."),
        ("p", "Los dos temas se tocan en un punto y conviene nombrarlo sin rodeos: la plataforma es hoy la puerta de entrada al mercado de trabajo para el joven que quedó fuera del empleo registrado. No exige título, no exige experiencia, no exige entrevista y paga la misma semana. Es, exactamente por eso, la forma más eficiente de convertir desempleo juvenil en empleo precario sin que la estadística de desocupación se mueva."),
        ("p", "Los dos últimos datos de la lista - ansiedad y desgano - no son un adorno. Conectan de manera directa con la línea de trabajo sobre salud mental que el CEPOES abrió en septiembre de 2026, y sugieren que la pieza sobre juventudes y la pieza sobre salud mental deberían salir articuladas."),
        ("p", "Límite a declarar: el estudio del CBC-UBA es nacional por aglomerados y no publica un corte para la Ciudad de Buenos Aires. El 27% del AMBA incluye al conurbano. Para el dato estrictamente porteño hay que ir a la Encuesta Permanente de Hogares y a la estadística porteña, con las limitaciones señaladas en el apartado anterior."),
    ]},
    {"title": "La norma existe desde 2020 y el riesgo no se cuenta", "items": [
        ("p", "La Ley 6.314, sancionada el 16 de julio de 2020, promulgada el 7 de agosto y publicada el 11 de agosto de ese año, modificó el Código de Tránsito y Transporte de la Ciudad y creó el Registro Único de Transporte de Mensajería Urbana y/o Reparto a Domicilio (RUTRAMUR), donde deben inscribirse tanto las plataformas y prestadores como los repartidores."),
        ("p", "La ley impone a los operadores de plataformas, entre otras obligaciones:"),
        ("bullet", "Proveer sin costo para el trabajador seguro de accidentes de trabajo, seguro de vida obligatorio, responsabilidad civil y accidentes personales."),
        ("bullet", "Brindar capacitación en seguridad vial sin costo para el repartidor."),
        ("bullet", "No asignar viajes a repartidores sin habilitación vigente."),
        ("bullet", "Compartir con la autoridad de aplicación información sobre estado de actividad, demanda y recorridos."),
        ("bullet", "Implementar canales digitales accesibles de reclamo."),
        ("p", "El antecedente inmediato marca la escala del problema de implementación: en marzo de 2020, en el registro previo del sector, había quince trabajadores inscriptos en relación de dependencia."),
        ("p", "El acuerdo firmado el 5 de marzo de 2026 entre la Jefatura de Gabinete porteña y las plataformas, con duración inicial de dos años, se estructura en cuatro ejes - seguridad vial, uso del espacio público, protección del trabajador y seguros, y regularización de la actividad - y crea una Comisión de Seguimiento."),
        ("p", "Conviene leerlo con atención, porque el eje de seguros del acuerdo de 2026 reitera obligaciones que la ley impone desde 2020. Un acuerdo administrativo no puede ser el instrumento por el cual se vuelve exigible una obligación legal ya vigente; si hizo falta firmarlo, la inferencia razonable es que la obligación no se estaba cumpliendo. Y las contraprestaciones no son simétricas: mientras las obligaciones de las empresas se reiteran, la obligación del trabajador de inscribirse en 180 días viene acompañada de un régimen de faltas con multas, retención de licencias y de vehículos."),
        ("p", "En la Argentina, los motociclistas representan cerca de la mitad de las víctimas fatales del tránsito: los informes de seguridad vial difundidos en 2025 y 2026 los ubican entre el 46% y el 50% del total nacional."),
        ("p", "En la Ciudad, el Observatorio de Movilidad y Seguridad Vial informa 104 fallecidos por siniestros viales en 2023, con una tasa de 3,4 cada 100.000 habitantes. Los anuarios de siniestralidad publicados llegan hasta 2024."),
        ("p", "Ninguna de esas estadísticas registra si la víctima estaba trabajando en el momento del siniestro. No existe, por lo tanto, forma de dimensionar el riesgo laboral de una actividad que consiste en circular en moto entre diez y doce horas diarias bajo presión de tiempo algorítmica. Es un vacío de información, no de competencia: la variable ocupacional puede incorporarse a un registro que la Ciudad ya produce."),
    ]},
    {"title": "Propuestas", "items": [
        ("p", "Las siete son de competencia porteña. Ninguna requiere ley nacional. Las cuatro primeras no tienen costo fiscal."),
        ("bullet", "1. Publicar el RUTRAMUR. Cantidad de repartidores y de plataformas inscriptas, y resultado del plazo de 180 días vencido en septiembre de 2026. Es información que el Estado porteño ya tiene en su poder. Publicarla convierte seis años de registro en la primera cifra pública del sector."),
        ("bullet", "2. Hacer efectivo el artículo de la Ley 6.314 sobre entrega de datos. Exigir a las plataformas la información de actividad, demanda y recorridos que la ley ya les impone entregar, y publicarla agregada y anonimizada con periodicidad trimestral. Sería la primera estadística pública del país sobre trabajo de plataformas, producida sin crear un solo organismo nuevo."),
        ("bullet", "3. Incorporar la variable ocupacional al registro de siniestralidad vial. Que los informes del Observatorio de Movilidad y Seguridad Vial consignen si la víctima se encontraba trabajando. Sin esa variable, el riesgo laboral del sector es invisible para la política pública."),
        ("bullet", "4. Auditar y publicar el cumplimiento de los seguros obligatorios. La Ley 6.314 obliga a las plataformas a proveerlos sin costo desde 2020. Corresponde auditar su vigencia efectiva y publicar el resultado por empresa. Es una obligación patronal, no una carga del trabajador."),
        ("bullet", "5. Paradas seguras. El acuerdo de 2026 exige a los repartidores ordenar su uso del espacio público. La contrapartida razonable es que la Ciudad provea puntos de descanso en las zonas de mayor concentración de reparto, con acceso a agua, sanitarios, sombra y carga de dispositivos. Es infraestructura urbana de bajo costo y competencia municipal directa."),
        ("bullet", "6. Acceso sanitario efectivo. Con el 78% de las juventudes vulnerables sin cobertura de salud, corresponde un relevamiento y un dispositivo de acceso a la red de Centros de Salud y Acción Comunitaria orientado a trabajadores de plataformas, con horarios compatibles con la jornada real del sector. La salud es competencia directa de la Ciudad."),
        ("bullet", "7. Formación en oficios anclada en el entramado productivo comunal. El 85,7% de las juventudes vulnerables valora estudiar y sólo el 15% accede a formación en oficios. La Ciudad cuenta con infraestructura territorial ociosa en horarios no escolares. Corresponde un programa de formación corta, certificada y vinculada a la actividad económica efectiva de cada comuna, en lugar de una oferta única centralizada."),
    ]},
    {"title": "Alcance metodológico y fuentes", "items": [
        ("p", "La lectura de los resultados se apoya en cinco criterios que delimitan con precisión el alcance de la evidencia disponible:"),
        ("bullet", "La cantidad de trabajadores de plataformas en la Ciudad permanece sin una cifra oficial publicada. Esa ausencia de información constituye uno de los principales hallazgos del informe."),
        ("bullet", "El cuentapropismo porteño se utiliza como indicador de contexto del mercado laboral y como aproximación general, no como una medición directa del trabajo de plataformas."),
        ("bullet", "El estudio del CBC-UBA describe a jóvenes de 18 a 29 años de los principales aglomerados urbanos del país. Sus resultados permiten caracterizar el contexto nacional y del AMBA, pero no estimar específicamente la situación de la Ciudad de Buenos Aires."),
        ("bullet", "El análisis de los seguros se concentra en la evidencia pública disponible. La falta de información que permita verificar su cumplimiento fundamenta la propuesta de auditar y publicar los resultados por empresa."),
        ("bullet", "Las estimaciones sindicales y empresarias se identifican junto con la organización que las produce y se utilizan como referencias sectoriales, diferenciadas de la estadística oficial."),
        ("p", "Fuentes", "report"),
        ("source", "Ley 6.314 de la Ciudad Autónoma de Buenos Aires, sancionada el 16/7/2020, publicada en el Boletín Oficial el 11/8/2020."),
        ("source", "Acuerdo entre el Gobierno de la Ciudad y plataformas de reparto, 5/3/2026, según cobertura de prensa especializada."),
        ("source", "Dirección General de Estadística y Censos de la Ciudad, mercado de trabajo, primer trimestre de 2026."),
        ("source", "Proyecto PIDAE, Ciclo Básico Común, Universidad de Buenos Aires: Jóvenes vulnerables en la Argentina: condiciones de vida, creencias y expectativas sobre el futuro, campo diciembre 2025 - enero 2026, 1.002 casos."),
        ("source", "Chequeado, relevamiento de estimaciones del sector de repartidores y conductores de aplicaciones, con datos de SiTraRepA, PedidosYa, Cabify y la investigación del CONICET con ocho universidades."),
        ("source", "Observatorio de Movilidad y Seguridad Vial de la Ciudad, informes estadísticos de siniestralidad."),
        ("source", "Informes nacionales de seguridad vial sobre participación de motovehículos en víctimas fatales, 2025-2026."),
    ]},
]


def thumbnail_svg(report):
    def lines(text, max_chars=22):
        words, out, current = text.split(), [], []
        for word in words:
            if current and len(" ".join(current + [word])) > max_chars:
                out.append(" ".join(current)); current = [word]
            else:
                current.append(word)
        if current: out.append(" ".join(current))
        return out[:4]
    tspans = "".join(f'<tspan x="62" dy="{0 if i == 0 else 68}">{escape(line)}</tspan>' for i, line in enumerate(lines(report["title"])))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1120" role="img" aria-label="Tapa de {escape(report['title'])}"><rect width="800" height="1120" fill="#172a4a"/><rect x="0" y="0" width="18" height="1120" fill="#55b9e9"/><circle cx="642" cy="822" r="220" fill="none" stroke="#10213c" stroke-width="58"/><circle cx="642" cy="822" r="135" fill="none" stroke="#10213c" stroke-width="42"/><text x="62" y="88" fill="#fff" font-family="Arial,sans-serif" font-size="24">Informe temático · Septiembre de 2026</text><text x="62" y="230" fill="#55b9e9" font-family="Arial,sans-serif" font-weight="700" font-size="58">{tspans}</text><text x="62" y="1004" fill="#55b9e9" font-family="Arial,sans-serif" font-weight="700" font-size="29">CEPOES</text><text x="205" y="1004" fill="#fff" font-family="Arial,sans-serif" font-size="19">Somos 100 Barrios · 2026</text></svg>'''


def build(report, sections):
    output = SITE_ROOT / report["pdf_dir"] / report["filename"]
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(output), pagesize=A4, rightMargin=62, leftMargin=62, topMargin=66, bottomMargin=54,
                          title=report["title"], author="CEPOES", subject=report["description"], creator="CEPOES · Somos 100 Barrios")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=cover_page(report), autoNextPageTemplate="body"),
        PageTemplate(id="body", frames=[frame], onPage=body_page),
    ])
    doc.build(section_story(report, sections))
    thumb = SITE_ROOT / "assets" / "publicaciones" / report["thumb"]
    thumb.parent.mkdir(parents=True, exist_ok=True)
    thumb.write_text(thumbnail_svg(report), encoding="utf-8")
    return output


if __name__ == "__main__":
    for report, sections in ((EDUCATION, EDU_SECTIONS), (PLATFORMS, PLAT_SECTIONS)):
        print(build(report, sections))
