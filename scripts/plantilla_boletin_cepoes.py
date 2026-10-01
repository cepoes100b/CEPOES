"""Plantilla A4 reutilizable para la serie de boletines de CEPOES.

La geometría toma como patrón el Boletín N.º 4 (agosto de 2026):
márgenes, portada, cabeceras, pie, columnas, indicadores y agendas.
"""

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

PAGE_W, PAGE_H = A4
LEFT, RIGHT, TOP, BOTTOM = 9 * mm, 9 * mm, 18 * mm, 17 * mm
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

# El N.º 4 usa Liberation Sans. La plantilla busca esa familia y la incrusta;
# DejaVu Sans queda sólo como alternativa para entornos sin LibreOffice/PDF.js.
runtime_root = Path(os.environ.get("CODEX_PRIMARY_RUNTIME_ROOT", "/opt/codex/runtimes/codex-primary-runtime"))
font_roots = [
    runtime_root / "dependencies/native/libreoffice-headless/libreoffice/share/fonts/truetype",
    Path("/usr/share/fonts/truetype/liberation2"),
    Path("/usr/share/fonts/truetype/dejavu"),
]
for font_root in font_roots:
    regular = font_root / "LiberationSans-Regular.ttf"
    bold = font_root / "LiberationSans-Bold.ttf"
    italic = font_root / "LiberationSans-Italic.ttf"
    if regular.exists() and bold.exists() and italic.exists():
        break
else:
    font_root = Path("/usr/share/fonts/truetype/dejavu")
    regular = font_root / "DejaVuSans.ttf"
    bold = font_root / "DejaVuSans-Bold.ttf"
    italic = font_root / "DejaVuSans-Oblique.ttf"

pdfmetrics.registerFont(TTFont("CEPOES", str(regular)))
pdfmetrics.registerFont(TTFont("CEPOES-Bold", str(bold)))
pdfmetrics.registerFont(TTFont("CEPOES-Italic", str(italic)))
pdfmetrics.registerFontFamily("CEPOES", normal="CEPOES", bold="CEPOES-Bold", italic="CEPOES-Italic", boldItalic="CEPOES-Bold")
FONT = "CEPOES"
FONT_BOLD = "CEPOES-Bold"
FONT_ITALIC = "CEPOES-Italic"

STYLES = {
    "kicker": ParagraphStyle("kicker", fontName=FONT_BOLD, fontSize=8.0, leading=9.2, textColor=TEAL, spaceAfter=4),
    "h1": ParagraphStyle("h1", fontName=FONT_BOLD, fontSize=18.2, leading=19.7, textColor=TEAL, spaceAfter=4),
    "dek": ParagraphStyle("dek", fontName=FONT, fontSize=10.0, leading=12.0, textColor=INK, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName=FONT_BOLD, fontSize=11.3, leading=13.0, textColor=TEAL, spaceBefore=3, spaceAfter=3),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=9.7, leading=12.2, textColor=INK, spaceAfter=6),
    "small": ParagraphStyle("small", fontName=FONT, fontSize=7.0, leading=8.4, textColor=MUTED),
    "source": ParagraphStyle("source", fontName=FONT, fontSize=6.6, leading=7.7, textColor=MUTED, spaceBefore=4),
    "quote": ParagraphStyle("quote", fontName=FONT_BOLD, fontSize=10.0, leading=12.0, textColor=NAVY, leftIndent=3 * mm, rightIndent=3 * mm),
    "kpi_value": ParagraphStyle("kpi_value", fontName=FONT_BOLD, fontSize=20.0, leading=21.0, textColor=TEAL),
    "kpi_label": ParagraphStyle("kpi_label", fontName=FONT, fontSize=8.3, leading=9.5, textColor=INK),
    "kpi_src": ParagraphStyle("kpi_src", fontName=FONT, fontSize=7.0, leading=8.1, textColor=MUTED),
    "agenda_title": ParagraphStyle("agenda_title", fontName=FONT_BOLD, fontSize=8.0, leading=9.5, textColor=colors.white, spaceAfter=3),
    "agenda_item": ParagraphStyle("agenda_item", fontName=FONT, fontSize=7.7, leading=9.2, textColor=colors.white, leftIndent=3 * mm, firstLineIndent=-3 * mm, spaceAfter=2.2),
    "table_head": ParagraphStyle("table_head", fontName=FONT_BOLD, fontSize=7.4, leading=8.4, textColor=colors.white),
    "table": ParagraphStyle("table", fontName=FONT, fontSize=8.3, leading=9.6, textColor=INK),
    "report_title": ParagraphStyle("report_title", fontName=FONT_BOLD, fontSize=9.0, leading=10.4, textColor=NAVY),
}


def p(text, style="body", **overrides):
    base = STYLES[style]
    if not overrides:
        return Paragraph(text, base)
    return Paragraph(text, ParagraphStyle(f"{style}-variant", parent=base, **overrides))


def make_page_decor(issue, month, page_meta, cover_items, cover_subtitle):
    """Crea la función de dibujo común a portada y páginas interiores."""

    def draw_cover(canvas):
        transition = 197 * mm
        canvas.setFillColor(NAVY)
        canvas.rect(0, transition, PAGE_W, PAGE_H - transition, stroke=0, fill=1)
        canvas.setFillColor(TEAL)
        canvas.rect(LEFT, transition - 1.2 * mm, PAGE_W - LEFT - RIGHT - 28 * mm, 1.2 * mm, stroke=0, fill=1)
        canvas.setFillColor(YELLOW)
        canvas.rect(PAGE_W - RIGHT - 28 * mm, transition - 1.2 * mm, 28 * mm, 1.2 * mm, stroke=0, fill=1)

        canvas.setFillColor(colors.white)
        canvas.setFont(FONT_BOLD, 6.3)
        canvas.drawString(LEFT, PAGE_H - 14 * mm, f"BOLETÍN NRO. {issue} · {month.upper()}")
        canvas.drawRightString(PAGE_W - RIGHT, PAGE_H - 14 * mm, "CIUDAD DE BUENOS AIRES")
        canvas.setFont(FONT_BOLD, 25)
        canvas.drawString(LEFT, PAGE_H - 34 * mm, "CEPOES")
        canvas.setFont(FONT, 6.2)
        canvas.drawString(LEFT, PAGE_H - 41 * mm, "Centro de Estudios en Política, Economía y Sociedad · Somos 100 Barrios")
        canvas.setFont(FONT_BOLD, 20)
        canvas.drawString(LEFT, PAGE_H - 55 * mm, "La Ciudad que habitamos")
        canvas.setFont(FONT, 11.0)
        text = canvas.beginText(LEFT, PAGE_H - 64 * mm)
        text.setLeading(4.6 * mm)
        for line in cover_subtitle:
            text.textLine(line)
        canvas.drawText(text)
        canvas.setFont(FONT_ITALIC, 8.0)
        canvas.drawString(LEFT, PAGE_H - 79 * mm, "Datos, análisis y propuestas desde el territorio.")

        y = 186 * mm
        step = 22.7 * mm if len(cover_items) <= 6 else 19.3 * mm
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(1.05)
        canvas.line(LEFT + 3 * mm, 31 * mm, LEFT + 3 * mm, y + 2 * mm)
        for number, title, desc in cover_items:
            canvas.setFillColor(NAVY)
            canvas.setFont(FONT_BOLD, 11)
            canvas.drawString(LEFT + 6 * mm, y, number)
            canvas.setFont(FONT_BOLD, 11)
            canvas.drawString(LEFT + 19 * mm, y, title)
            canvas.setFont(FONT, 9)
            canvas.setFillColor(MUTED)
            t = canvas.beginText(LEFT + 19 * mm, y - 4 * mm)
            t.setLeading(3.9 * mm)
            # Las descripciones se entregan ya partidas para evitar cambios de reflujo.
            for line in desc if isinstance(desc, (list, tuple)) else [desc]:
                t.textLine(line)
            canvas.drawText(t)
            canvas.setStrokeColor(LINE)
            canvas.setLineWidth(.35)
            canvas.line(LEFT + 19 * mm, y - 8.8 * mm, PAGE_W - RIGHT, y - 8.8 * mm)
            y -= step

        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(.7)
        canvas.line(LEFT, 16 * mm, PAGE_W - RIGHT, 16 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont(FONT, 5.5)
        canvas.drawString(LEFT, 12 * mm, "CEPOES · Centro de Estudios en Política, Economía y Sociedad")
        canvas.drawRightString(PAGE_W - RIGHT, 12 * mm, "contacto@cepoes.org.ar · @cepoesarg · www.cepoes.org.ar")

    def page_decor(canvas, doc):
        canvas.saveState()
        if doc.page == 1:
            draw_cover(canvas)
            canvas.restoreState()
            return
        accent, right_label = page_meta[doc.page]
        y = PAGE_H - 11 * mm
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(.75)
        canvas.line(LEFT, y - 2.5 * mm, PAGE_W - RIGHT, y - 2.5 * mm)
        canvas.setFillColor(NAVY)
        canvas.setFont(FONT_BOLD, 5.8)
        canvas.drawString(LEFT, y, f"CEPOES · BOLETÍN Nro. {issue} · {month}")
        canvas.setFillColor(accent)
        canvas.drawRightString(PAGE_W - RIGHT, y, right_label)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(.35)
        canvas.line(LEFT, 13 * mm, PAGE_W - RIGHT, 13 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont(FONT, 5.3)
        canvas.drawString(LEFT, 10 * mm, "CEPOES · Centro de Estudios en Política, Economía y Sociedad")
        canvas.setFillColor(accent)
        canvas.drawRightString(PAGE_W - RIGHT, 10 * mm, f"p. {doc.page}")
        canvas.restoreState()

    return page_decor


def kpi_band(items, accent):
    width = CONTENT_W / len(items)
    cells = [[p(value, "kpi_value", textColor=accent), p(label, "kpi_label"), p(src, "kpi_src")] for value, label, src in items]
    table = Table([cells], colWidths=[width] * len(items), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE), ("LINEABOVE", (0, 0), (-1, -1), 1.4, accent),
        ("LINEAFTER", (0, 0), (-2, -1), .35, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
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


def occupancy_guard(pdf_path, max_bottom_blank_mm=85):
    """Falla si una página interior termina demasiado arriba (señal de maqueta vacía)."""
    import fitz

    doc = fitz.open(pdf_path)
    failures = []
    for index, page in enumerate(doc, start=1):
        if index == 1:
            continue
        blocks = page.get_text("blocks")
        content_bottom = max((block[3] for block in blocks if block[1] > 35 and block[3] < page.rect.height - 35), default=0)
        empty_bottom = page.rect.height - content_bottom
        if empty_bottom > max_bottom_blank_mm * mm:
            failures.append((index, round(empty_bottom / mm, 1)))
    if failures:
        detail = ", ".join(f"p. {page}: {blank} mm" for page, blank in failures)
        raise RuntimeError(f"Exceso de espacio en blanco inferior: {detail}")
