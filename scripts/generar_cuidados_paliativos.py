"""Adaptación íntegra del documento aprobado; texto y enlaces en JSON versionado."""
import json
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deploy/site-overlay'
SLUGS = ['resumen', 'marco', 'necesidad', 'oferta', 'condiciones', 'brechas', 'recomendaciones', 'fuentes']

def rich(runs):
    parts = []
    for r in runs:
        text = e(r['text'])
        if r.get('bold'): text = '<strong>' + text + '</strong>'
        if r.get('italic'): text = '<em>' + text + '</em>'
        if r.get('href'): text = '<a href="' + e(r['href'], quote=True) + '">' + text + '</a>'
        parts.append(text)
    return ''.join(parts)

def bar(label, value, display, note=''):
    return f'<div class="cp-bar-row"><div><strong>{label}</strong><span>{display}</span></div><div class="cp-track"><span style="width:{value}%"></span></div><small>{note}</small></div>'

def visual(section):
    if section == 'marco':
        return '<aside class="cp-visual"><span class="eyebrow">El recorrido institucional</span><h3>De la red al derecho integral</h3><ol class="cp-timeline"><li><strong>2007</strong><span>Red porteña</span></li><li><strong>2010</strong><span>Programa porteño</span></li><li><strong>2022</strong><span>Ley nacional 27.678</span></li><li><strong>2023</strong><span>Reglamentación nacional</span></li></ol><p class="cp-source">Instrumentos y alcances en el cuadro normativo de esta sección. La adhesión porteña permanece como pregunta abierta del documento.</p></aside>'
    if section == 'necesidad':
        return '<figure class="cp-visual"><span class="eyebrow">Dos universos diferentes · Estudio de 2016</span><h3>La necesidad detectada en hospitales</h3>' + bar('Enfermedad crónica avanzada',29.5,'29,5%','Sobre los 704 pacientes estudiados.') + bar('NECPAL positivo',72.1,'72,1%','Entre quienes tenían enfermedad crónica avanzada.') + '<figcaption class="cp-source">Tripodoro y col., Medicina 2016. Muestra hospitalaria; cada barra tiene un denominador diferente. Estas proporciones no son una estimación poblacional actual.</figcaption></figure><figure class="cp-visual"><span class="eyebrow">Argentina · Atlas de las Américas 2025</span><h3>584 servicios especializados registrados</h3><div class="cp-three"><div><strong>513</strong><span>Adultos</span></div><div><strong>59</strong><span>Pediátricos</span></div><div><strong>12</strong><span>Mixtos</span></div></div><figcaption class="cp-source">Relevamiento abril–junio de 2024. Servicios registrados en el país; mide presencia institucional, con capacidad y pacientes atendidos sin cuantificar.</figcaption></figure>'
    if section == 'oferta':
        return '<aside class="cp-visual"><span class="eyebrow">Listado del Programa Estar · 31/05/2023</span><h3>Una red documentada, una capacidad por conocer</h3><div class="cp-two"><div class="cp-number"><strong>14</strong><span>hospitales</span></div><div class="cp-number"><strong>6</strong><span>CeSAC</span></div></div><p class="cp-source">El cuadro conserva los establecimientos y la evidencia del documento. El listado acredita equipos a esa fecha; su dotación y actividad actuales requieren un relevamiento.</p></aside>'
    if section == 'condiciones':
        return '<aside class="cp-visual"><span class="eyebrow">Condiciones del acceso efectivo</span><h3>Cuatro frentes que deben sostenerse juntos</h3><div class="cp-four"><div><b>01</b><strong>Medicamentos</strong><span>Prescripción, stock y dispensación.</span></div><div><b>02</b><strong>Domicilio</strong><span>Visitas, insumos y respaldo asistencial.</span></div><div><b>03</b><strong>Equipos</strong><span>Cargos, disciplinas y horas efectivas.</span></div><div><b>04</b><strong>Financiamiento</strong><span>Partidas, ejecución y metas físicas.</span></div></div></aside><figure class="cp-visual"><span class="eyebrow">Modelo económico · Río Negro · Publicado en 2023</span><h3>Muerte en el hogar en los escenarios modelados</h3>' + bar('Escenario de referencia',45.41,'45,41%') + bar('Con paliativos domiciliarios',55.73,'55,73%') + '<figcaption class="cp-source">Lamfre y col. (2023). Diferencia: 10,32 puntos porcentuales. Es un modelo para cáncer en el subsistema público de Río Negro. Su interpretación requiere considerar el cuidado informal; los valores no describen resultados observados en CABA.</figcaption></figure>'
    return ''

def main():
    data = json.loads((ROOT / 'datos/salud/cuidados-paliativos-texto.json').read_text())
    sections, current, table_i = [], None, 0
    for b in data['blocks']:
        if b.get('style') == 'Heading 1': continue
        if b.get('style') == 'Heading 2':
            current = {'id':SLUGS[len(sections)], 'title':b['text'], 'parts':[]}
            sections.append(current)
        elif b['type'] == 'table':
            table_i += 1
            rows = []
            for ri, row in enumerate(b['rows']):
                tag = 'th' if ri == 0 else 'td'
                cells = ''.join(f'<{tag}' + (' scope="col"' if ri == 0 else '') + '>' + '<br>'.join(rich(p) for p in cell['paragraphs']) + f'</{tag}>' for cell in row)
                rows.append('<tr>' + cells + '</tr>')
            titles = ['Instrumentos y lectura operativa', 'Oferta documentada y alcance de la evidencia', 'Brechas de información', 'Ocho indicadores propuestos para un tablero público']
            table = f'<div class="cp-table" role="region" tabindex="0" aria-label="{titles[table_i-1]}"><table><caption>{titles[table_i-1]}</caption><thead>{rows[0]}</thead><tbody>' + ''.join(rows[1:]) + '</tbody></table></div>'
            current['parts'].append(table)
        else:
            cls = ' class="cp-item"' if b.get('style') == 'List Paragraph' else ''
            current['parts'].append(f'<p{cls} data-document-paragraph>{rich(b["runs"])}</p>')
    toc = ''.join(f'<a href="#{s["id"]}"><span>{i:02d}</span>{e(s["title"])}</a>' for i,s in enumerate(sections,1))
    body = ''
    for i,s in enumerate(sections,1):
        parts = s['parts']
        # Visual summaries accompany the complete original section, without replacing text.
        body += f'<section id="{s["id"]}" class="cp-section"><span class="eyebrow">{i:02d} · Cuidados paliativos</span><h2>{e(s["title"])}</h2>' + ''.join(parts) + visual(s['id']) + '</section>'
    title=e(data['title'])
    description='Un derecho reconocido, una red documentada y los datos que faltan para controlar el acceso a los cuidados paliativos en CABA.'
    html=f'''<!doctype html><html lang="es" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — CEPOES</title><meta name="description" content="{description}"><meta name="cepoes:publication" content="report"><meta property="article:published_time" content="2026-10-20"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:type" content="article"><meta property="og:url" content="https://cepoes.org/salud/cuidados-paliativos/"><link rel="canonical" href="https://cepoes.org/salud/cuidados-paliativos/"><link rel="icon" href="/assets/favicon.svg"><link rel="stylesheet" href="/assets/site.css"><link rel="stylesheet" href="/assets/arquitectura.css"><link rel="stylesheet" href="/assets/cuidados-paliativos.css"><script defer src="/assets/common-r1.js?v=259"></script></head><body><main id="contenido" class="cp-page" data-related-tags="salud,cuidados,paliativos,presupuesto"><header class="cp-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">Inicio</a> / <a href="/salud/">Salud</a> / Cuidados paliativos</div><span class="eyebrow">Salud · Derechos y acceso a la atención</span><h1>{title}</h1><p class="cp-dek">Un derecho reconocido. Una red documentada. La información pendiente para controlar su cumplimiento.</p><p class="cp-meta">Documento completo · Octubre de 2026</p><div class="cp-hero-note"><strong>La pregunta central</strong><p>¿Cuántas personas necesitan cuidados paliativos, cuántas los reciben y con qué recursos?</p></div></div></header><div class="wrap cp-layout"><aside class="cp-toc"><nav aria-label="Índice del informe"><strong>En este informe</strong>{toc}</nav></aside><article class="cp-article">{body}<div class="cp-related"><a href="/salud/">Volver al eje Salud →</a><a href="/presupuesto/2027/salud/">Presupuesto 2027 · Salud →</a></div></article></div></main></body></html>'''
    dest=OUT/'salud/cuidados-paliativos/index.html'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(html,encoding='utf-8')
    print(f'{dest}: {len(sections)} secciones, {table_i} cuadros; texto completo.')

if __name__ == '__main__': main()
