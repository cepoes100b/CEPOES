#!/usr/bin/env python3
"""Boletín 6: fuente editorial única para PDF y HTML, con plantilla canónica."""
from pathlib import Path
from html import escape
import json, re, sys
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from reportlab.graphics import renderSVG
from plantilla_boletin_cepoes import (BOTTOM,CONTENT_W,GREEN,LEFT,LINE,MUTED,NAVY,ORANGE,PAGE_H,PAGE_W,PALE,PURPLE,RED,RIGHT,TEAL,TOP,YELLOW,FONT,FONT_BOLD,STYLES,agenda,kpi_band,make_page_decor,occupancy_guard,p,section_head,source,two_columns)
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'deploy/site-overlay'
SLUG='boletin-06-octubre-2026'
TITLE='El presupuesto frente a la Ciudad real'
DEK='El proyecto 2027 pierde inversión y participación sanitaria frente a una Ciudad con ingresos rezagados y fuertes desigualdades.'
CUT='19/10/2026'
URL='https://cepoes.org/publicaciones/boletines/'+SLUG+'/'
B=json.loads((SITE/'assets/data/presupuesto-2027.json').read_text())
F={x['nombre']:x for x in B['funciones']}
def num(v,d=1):return f'{v:,.{d}f}'.replace(',','X').replace('.',',').replace('X','.')
def pct(v):return ('+' if v>0 else '')+num(v)+'%'
def real(x):return (x['proyecto_2027']/x['vigente_2026_06_30']/1.2154-1)*100
def pair(h,t):return (h,t)
SOURCES={
'ipc':('IDECBA 2064 · IPCBA, septiembre de 2026','https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/10/ir_2026_2064.pdf'),
'canastas':('IDECBA 2065 · Canastas, septiembre de 2026','https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/10/ir_2026_2065.pdf'),
'empleo':('IDECBA 2058 · Mercado laboral, segundo trimestre de 2026','https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2058.pdf'),
'ingresos':('IDECBA 2059 · Ingresos, segundo trimestre de 2026','https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2059.pdf'),
'pobreza':('IDECBA 2060 · Pobreza, segundo trimestre de 2026','https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/09/ir_2026_2060.pdf'),
'presupuesto':('Proyecto PDLEY-2026-36, Mensaje y anexos · Sistematización y referencias CEPOES','https://cepoes.org/presupuesto/2027/')}
SECTIONS=[
 dict(id='resumen',eje='resumen',color=TEAL,kicker='RESUMEN EJECUTIVO',title=TITLE,dek='Un presupuesto casi empatado con los precios puede esconder cambios profundos en sus prioridades.',
 kpis=[('$24,094 B','Gasto total proyectado para 2027','B = billones de pesos'),('-11,8%','Variación real del gasto de capital','Frente al vigente a junio 2026'),('16,46%','Participación de Salud en el total','16,89% en el vigente 2026')],
 paragraphs=[pair('La discusión que abre octubre','El Gobierno porteño propone aumentar el gasto total 21,2% nominal para 2027. Frente a una inflación promedio estimada de 21,54%, el conjunto pierde 0,3% de capacidad de compra. El resultado agregado parece cercano al equilibrio, pero oculta diferencias: Salud, Educación, Vivienda y Trabajo quedan por debajo de ese escenario de precios.'),pair('Las prioridades cambian','El gasto de capital crece apenas 7,3% nominal y retrocede 11,8% real. Su participación baja del 20,29% al 17,95%. Salud reduce su peso del 16,89% al 16,46%. La discusión legislativa debe examinar qué programas absorben esas variaciones y qué servicios y proyectos se protegerán.'),pair('La Ciudad en la que se decide','En septiembre los precios porteños subieron 1,8% mensual. La Canasta Básica Total para el hogar propietario de referencia de cuatro integrantes llegó a $1.687.299. Los datos trimestrales ya analizados en septiembre siguen describiendo ingresos laborales rezagados y una pobreza que afecta más al sur y a los hogares con niñas y niños.'),pair('Recursos y derechos','El equilibrio de las cuentas es una condición de gestión. Evaluar el presupuesto requiere además conocer qué atención sanitaria, enseñanza, soluciones habitacionales y oportunidades de trabajo financiará. Un aumento nominal sólo preserva prestaciones si alcanza para sus costos y para la demanda que debe atender.')],
 quote='La discusión del presupuesto debe poner en el centro qué servicios, obras y derechos se sostienen y quiénes quedan relegados.',
 table=('Indicadores para leer el proyecto',['Asignación','Nominal','Real con 21,54%'],[[n,pct((F[n]['proyecto_2027']/F[n]['vigente_2026_06_30']-1)*100),pct(real(F[n]))] for n in ['Salud','Educación','Vivienda y Urbanismo','Trabajo']]),
 agenda=[('Abrir los programas','exigir metas de atención, cobertura y empleo junto con los montos.'),('Comparar correctamente','usar el vigente al 30 de junio de 2026 y explicitar el escenario de precios.')],sources=['presupuesto','ipc','canastas']),
 dict(id='precios',eje='condiciones',color=ORANGE,kicker='PRECIOS Y CONDICIONES DE VIDA',title='La inflación baja de ritmo y el costo de vivir sigue subiendo',dek='Los nuevos datos de septiembre actualizan el costo de vida. El diagnóstico social trimestral conserva su período de referencia.',
 kpis=[('1,8%','Inflación mensual porteña','Septiembre de 2026'),('32,9%','Variación interanual del IPCBA','Septiembre de 2026'),('$1.687.299','Línea de pobreza del hogar de referencia','Dos adultos y dos hijos, propietarios')],
 paragraphs=[pair('Los precios siguen aumentando','El IPCBA acumuló una suba de 23,7% entre enero y septiembre. La desaceleración mensual reduce la velocidad de aumento, pero las compras siguen realizándose a precios mayores. Para evaluar el poder adquisitivo hay que comparar ingresos y precios durante el mismo período.'),pair('Tres medidas distintas','La Canasta Básica Alimentaria define la línea de indigencia y la Básica Total, la de pobreza. La Canasta Total del sistema porteño de consumo es otra referencia y alcanzó $2.135.852. Cada umbral mide un conjunto distinto de necesidades; intercambiarlos cambia el diagnóstico.'),pair('La composición del hogar importa','El hogar de referencia es una pareja de 35 años con dos hijos de 9 y 6 años, propietaria de la vivienda. Los valores no describen por igual a todos los hogares. Para una familia inquilina deben considerarse su composición y el gasto habitacional específico.'),pair('La desigualdad sigue presente','En el segundo trimestre, la pobreza afectó al 21,9% de las personas y al 17,3% de los hogares. Entre los hogares del sur llegó al 24,9% y entre aquellos con menores de 14 años, al 28,2%. Son antecedentes trimestrales, no mediciones de septiembre.')],
 table=('Canastas del hogar de referencia · pesos corrientes',['Medida','Agosto 2026','Septiembre 2026'],[['Básica Alimentaria','$903.930','$925.941'],['Básica Total','$1.651.798','$1.687.299'],['Total del sistema porteño','$2.082.845','$2.135.852']]),
 chart=('Pobreza en hogares · segundo trimestre de 2026',[('CABA',17.3),('Zona sur',24.9),('Con menores de 14 años',28.2)],(0,35),'% de hogares de cada grupo'),
 agenda=[('Prioridad territorial','orientar apoyos y servicios hacia hogares con mayores necesidades.'),('Ingresos y servicios','combinar protección de ingresos con acceso efectivo a salud, educación y cuidados.')],sources=['ipc','canastas','pobreza']),
 dict(id='salud',eje='trabajo',color=RED,kicker='SALUD PÚBLICA Y CUIDADOS',title='Salud pierde peso en el presupuesto de la Ciudad',dek='El proyecto aumenta los pesos asignados, pero queda por debajo del escenario de precios y reduce su participación.',
 kpis=[('$3,966 B','Asignación de la función Salud','Proyecto 2027'),('-2,8%','Variación real de Salud','Inflación promedio estimada 21,54%'),('-0,43 pp','Cambio de participación en el gasto','16,89% a 16,46%')],
 paragraphs=[pair('El aumento nominal no alcanza','Salud crece 18,2% frente al presupuesto vigente de junio de 2026. Ese incremento supone una caída real de 2,8% bajo el escenario de precios utilizado. El proyecto reduce así su prioridad relativa dentro del gasto total. Abrir programas es indispensable para precisar dónde impactará esa pérdida.'),pair('La comparación debe ser consistente','La función Salud reúne gasto según su finalidad; el Ministerio de Salud organiza una jurisdicción administrativa. La lectura de créditos, personal e inversión debe conservar el mismo universo. El gasto de personal incluye dotaciones, carreras, cargas y otros componentes que requieren analizarse junto con las negociaciones salariales.'),pair('Obras que se conviertan en atención','El capital de la función suma $435.619 millones. Las obras previstas en hospitales y centros de salud necesitan cronogramas de habilitación, equipamiento y equipos para funcionar. La asignación presupuestaria es el punto de partida; el acceso mejora cuando la infraestructura se traduce en atención efectiva.'),pair('La agenda de octubre exige continuidad','Salud mental, prevención del cáncer de mama y cuidados paliativos ponen en primer plano acceso y continuidad de atención. Una campaña tiene alcance limitado sin turnos, diagnóstico, tratamientos y seguimiento. La discusión del presupuesto debe identificar recursos y metas para sostener esa respuesta durante todo el año.')],
 chart=('Salud dentro del gasto total',[('Vigente al 30/06/2026',16.89),('Proyecto 2027',16.46)],(0,20),'% del gasto total'),
 table=('Del crédito a la atención · controles propuestos',['Área','Qué seguir','Para qué'],[['Atención primaria','Equipos y continuidad','Acceso de cercanía'],['Hospitales','Turnos, insumos y habilitación','Capacidad efectiva'],['Cuidados','Cobertura y seguimiento','Continuidad de atención']]),
 quote='La pérdida de participación sanitaria exige discutir qué capacidad de atención se preservará y cómo se responderá a las necesidades de la población.',
 agenda=[('Proteger la atención','definir pisos de recursos y metas verificables para hospitales, atención primaria y cuidados.'),('Controlar el funcionamiento','seguir turnos, continuidad de tratamientos, equipos, insumos y ejecución física de obras.')],sources=['presupuesto']),
 dict(id='finanzas',eje='actividad',color=TEAL,kicker='FINANZAS PÚBLICAS',title='Menos inversión y un margen fiscal mínimo',dek='La composición del gasto importa tanto como su monto. El proyecto deja poco colchón frente a desvíos de recursos o costos.',
 kpis=[('-11,8%','Variación real del gasto de capital','Proyecto frente al vigente junio 2026'),('17,95%','Participación del capital en el gasto','20,29% en la base vigente'),('2,46%','Intereses dentro del gasto total','Proyecto 2027')],
 paragraphs=[pair('La inversión pierde prioridad','El gasto de capital pasa de $4,033 a $4,326 billones. El aumento nominal de 7,3% queda lejos del escenario de inflación promedio. Su caída real de 11,8% exige abrir los proyectos para conocer qué inversiones se sostienen y cuáles se postergan.'),pair('El equilibrio después de intereses','Los recursos previstos suman $24,096 billones y el gasto, $24,094 billones. El resultado primario ronda $593.204 millones; los intereses, $591.887 millones. El superávit financiero final es de $1.316 millones, apenas 0,0055% de los recursos. La cifra expresa un margen muy estrecho.'),pair('La exposición ante desvíos','Los intereses equivalen al 2,46% del gasto y absorben el 99,78% del resultado primario. Esa relación describe el equilibrio proyectado. Ante una recaudación menor o costos mayores, la respuesta debe explicitar qué prestaciones se protegerán y con qué instrumentos.'),pair('Precios y base de comparación','La comparación usa el crédito vigente al 30 de junio de 2026 del Mensaje, no la ley original aprobada en 2025. La inflación de 21,54% es una estimación promedio anual; con 23%, el gasto total caería aproximadamente 1,5% real. Son escenarios de asignaciones para 2027.')],
 chart=('Variación real de asignaciones seleccionadas',[('Transporte',real(F['Transporte'])),('Trabajo',real(F['Trabajo'])),('Salud',real(F['Salud'])),('Educación',real(F['Educación'])),('Industria y Comercio',real(F['Industria y Comercio']))],(-16,10),'% frente al vigente · inflación 21,54%'),
 agenda=[('Abrir riesgos','publicar escenarios de recaudación, precios, deuda y costos de servicios.'),('Controlar prioridades','hacer trazables las reasignaciones de crédito y su efecto sobre metas físicas.')],sources=['presupuesto']),
 dict(id='vivienda',eje='comercio',color=PURPLE,kicker='VIVIENDA Y EDUCACIÓN',title='El presupuesto debe responder a las brechas de los barrios',dek='Vivienda y Educación aumentan nominalmente, pero sus asignaciones quedan por debajo del escenario de inflación.',
 kpis=[('$826.690 M','Vivienda y Urbanismo','Proyecto 2027'),('$4,735 B','Educación','Proyecto 2027'),('-0,9%','Variación real de Vivienda','Escenario de precios 21,54%')],
 paragraphs=[pair('Soluciones habitacionales verificables','Vivienda y Urbanismo representa el 3,43% del gasto total. Su aumento nominal de 20,4% equivale a una caída real de 0,9%. El capital concentra $641.323 millones. Es necesario identificar obras, hogares alcanzados y fechas de puesta en servicio para evaluar la respuesta habitacional.'),pair('Alquilar requiere una lectura propia','Las canastas del hogar propietario de referencia no son una estimación completa de los gastos de una familia inquilina. La lectura de vivienda debe incorporar precios de alquiler, condiciones de acceso y composición familiar con fuentes y períodos comparables. El presupuesto debe dar cuenta de las herramientas concretas para atender esa presión.'),pair('Educación conserva el mayor monto','La asignación educativa alcanza $4,735 billones, el 19,65% del gasto. Crece 20,9% nominal y cae alrededor de 0,5% real con el primer escenario de precios. La discusión requiere abrir funcionamiento, mantenimiento, obras y condiciones de enseñanza; el agregado funcional no muestra por sí solo la situación de cada escuela.'),pair('Distribuir según necesidad','La localización administrativa del gasto y la población beneficiada son dimensiones distintas. El presupuesto de una entidad Comuna describe sus competencias, mientras inversiones de otras áreas pueden localizarse en el mismo territorio. Para evaluar equidad hay que vincular programas y necesidades con su cobertura efectiva.')],
 table=('Asignaciones comparables · proyecto 2027',['Concepto','Vivienda y Urbanismo','Educación'],[['Participación en gasto total','3,43%','19,65%'],['Variación nominal','+20,4%','+20,9%'],['Variación real · 21,54%','-0,9%','-0,5%'],['Gasto de capital','$641.323 M','$469.974 M']]),
 quote='Las prioridades territoriales deben evaluarse por las necesidades que atienden y las mejoras que llegan a los hogares y a las escuelas.',
 agenda=[('Vivienda','publicar proyectos, cobertura y cronogramas con prioridad en hogares y zonas más afectados.'),('Educación','seguir infraestructura, mantenimiento y recursos de funcionamiento junto con condiciones de acceso y enseñanza.')],sources=['presupuesto','canastas']),
 dict(id='trabajo',eje='trabajo',color=RED,kicker='TRABAJO Y DESARROLLO PRODUCTIVO',title='Ingresos rezagados y una política productiva que necesita escala',dek='Los antecedentes trimestrales muestran la fragilidad de los ingresos. El proyecto ofrece instrumentos que deben evaluarse por resultados.',
 kpis=[('7,2%','Desocupación en CABA','Segundo trimestre de 2026'),('14,8%','Presión sobre el mercado laboral','Segundo trimestre de 2026'),('-6,9%','Variación real de ingresos laborales','Interanual · segundo trimestre 2026')],
 paragraphs=[pair('Tener trabajo no resuelve todo','La tasa de desocupación se mantiene sin cambios significativos respecto de un año antes, pero la presión laboral alcanza al 14,8% de la población económicamente activa. Reúne personas desocupadas y ocupadas que buscan más horas u otra ocupación. La estabilidad de una tasa general convive con esa necesidad de ampliar ingresos.'),pair('Una pérdida que debe medirse bien','Los ingresos laborales aumentaron 23,6% interanual frente a un IPCBA de 32,7% en el período comparable. La diferencia es de 9,1 puntos porcentuales; la caída real, calculada como 1,236 / 1,327 - 1, es 6,9%. La brecha es mayor entre cuentapropistas y asalariados sin descuento jubilatorio.'),pair('Trabajo pierde y el apoyo productivo es pequeño','La función Trabajo crece 6,6% nominal y cae 12,3% real. Industria y Comercio aumenta 29,4% nominal y 6,4% real, pero representa 0,23% del gasto. Esta última función es una parte del esfuerzo económico: los programas de otras áreas y los beneficios tributarios requieren una evaluación complementaria.'),pair('Resultados para comercios y pymes','Crédito, asistencia tecnológica, compras públicas e incentivos pueden fortalecer producción y empleo si tienen objetivos y condiciones. Los beneficios fiscales deben evaluarse por inversión adicional, puestos formales y encadenamientos locales. Los umbrales tributarios también requieren distinguir aumentos de facturación por precios de aumentos de ventas reales.')],
 chart=('Ingresos y precios · variación interanual',[('IPCBA del período',32.7),('Ingresos laborales',23.6),('Cuenta propia',8.6),('Sin descuento jubilatorio',5.0)],(0,36),'% · segundo trimestre de 2026'),
 agenda=[('Empleo con derechos','articular formación, formalización y apoyo a actividades con ingresos más frágiles.'),('Producción territorial','vincular crédito y tecnología con metas de inversión, empleo y continuidad comercial.')],sources=['empleo','ingresos','presupuesto']),
 dict(id='agenda',eje='propuestas',color=GREEN,kicker='AGENDA PÚBLICA',title='Cinco prioridades para discutir el proyecto',dek='El presupuesto puede transformar capacidad fiscal en servicios, inversión y empleo. Es necesario definir compromisos que puedan controlarse.',
 paragraphs=[pair('Proteger salud, educación y cuidados','Identificar pisos de recursos, metas de atención y cobertura y mecanismos de protección ante cambios de costos. La discusión debe abrir programas, insumos y condiciones de funcionamiento para evaluar el alcance de cada asignación.'),pair('Orientar inversión hacia necesidades','Priorizar vivienda, infraestructura y movilidad según brechas territoriales y población beneficiada. Cada obra debe tener identificación, financiamiento, cronograma, avance físico y fecha de puesta en servicio.'),pair('Fortalecer producción y empleo','Articular crédito del Banco Ciudad, asistencia tecnológica, compras públicas y formación. Los instrumentos deben identificar costo, destinatarios, metas y evaluación de resultados, con prioridad en pymes, comercios y empleo formal.'),pair('Evaluar beneficios tributarios','Exigir información sobre objetivos, distribución, inversión adicional y empleo generado. Los gastos tributarios describen ingresos que el fisco deja de percibir; revisarlos requiere analizar su efecto y las condiciones jurídicas y económicas de cada régimen.'),pair('Controlar reasignaciones y resultados','Relacionar crédito aprobado y vigente, devengado, pagos y metas físicas. Publicar qué se modifica, por qué y con qué impacto. La ejecución financiera debe leerse junto con las prestaciones y obras que efectivamente se concretan.')],
 quote='Una alternativa de gobierno debe identificar prioridades, costos y financiamiento y rendir cuentas sobre sus resultados.',
 sources=['presupuesto','ipc','canastas','empleo','ingresos','pobreza'])]

def bars(title,values,domain,unit):
    width=CONTENT_W; row=25; height=40+len(values)*row
    d=Drawing(width,height)
    d.add(String(0,height-11,title,fontName=FONT_BOLD,fontSize=9.2,fillColor=NAVY))
    x0=174; x1=width-42; lo,hi=domain
    def x(v):return x0+(v-lo)/(hi-lo)*(x1-x0)
    ytop=height-29
    for i,(label,v) in enumerate(values):
        y=ytop-i*row
        d.add(String(0,y+1,label,fontName=FONT,fontSize=8.3,fillColor=NAVY))
        zero=x(0)
        d.add(Rect(min(zero,x(v)),y-3,max(abs(x(v)-zero),.5),11,fillColor=TEAL if v>=0 else RED,strokeColor=None))
        d.add(String(width-1,y+1,pct(v) if lo<0 else num(v,2 if title.startswith('Salud dentro') else 1)+'%',fontName=FONT_BOLD,fontSize=8.4,fillColor=NAVY,textAnchor='end'))
    d.add(Line(x(0),19,x(0),ytop+10,strokeColor=MUTED,strokeWidth=.5))
    for val in [lo,hi]:d.add(String(x(val),9,num(val,0),fontName=FONT,fontSize=7,fillColor=MUTED,textAnchor='middle'))
    d.add(String(0,0,unit,fontName=FONT,fontSize=7.4,fillColor=MUTED))
    return d

def tabular(data):
    title,heads,rows=data
    widths=[CONTENT_W*.46]+[CONTENT_W*.54/(len(heads)-1)]*(len(heads)-1)
    t=Table([[p(escape(x),'table_head') for x in heads]]+[[p(escape(str(x)),'table') for x in r] for r in rows],colWidths=widths,repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('LINEBELOW',(0,1),(-1,-1),.3,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
    return [p(title,'h2'),t]

def reference(ids,html=False):
    if html:return ' · '.join(f'<a href="{SOURCES[k][1]}">{SOURCES[k][0]}</a>' for k in ids)
    return ' · '.join(f'<link href="{SOURCES[k][1]}">{SOURCES[k][0]}</link>' for k in ids)

def build():
    pdf=SITE/f'publicaciones/files/{SLUG}.pdf';pdf.parent.mkdir(parents=True,exist_ok=True)
    meta={i+2:(s['color'],s['kicker']) for i,s in enumerate(SECTIONS)}
    cover=[(f'{i+2:02}',h,d) for i,(h,d) in enumerate([
      ('Resumen ejecutivo','La composición del gasto abre la discusión de prioridades.'),('Precios y condiciones de vida','Canastas de septiembre y desigualdad entre hogares.'),('Salud pública y cuidados','Menor capacidad de compra y participación sanitaria.'),('Finanzas públicas','La inversión cae en términos reales y el margen fiscal es mínimo.'),('Vivienda y educación','Recursos, cobertura y necesidades de los barrios.'),('Trabajo y producción','Ingresos rezagados, empleo y apoyo a comercios y pymes.'),('Agenda pública y fuentes','Cinco prioridades y referencias para discutir el proyecto.')])]
    decor=make_page_decor(6,'Octubre 2026',meta,cover,['El presupuesto frente a la Ciudad real: servicios públicos,','ingresos, inversión y prioridades para 2027.'])
    doc=BaseDocTemplate(str(pdf),pagesize=(PAGE_W,PAGE_H),leftMargin=LEFT,rightMargin=RIGHT,topMargin=TOP,bottomMargin=BOTTOM,title=TITLE,author='CEPOES',subject='La Ciudad que habitamos · N.º 6 · Octubre 2026',pageCompression=1)
    doc.addPageTemplates(PageTemplate(id='boletin',frames=[Frame(LEFT,BOTTOM,CONTENT_W,PAGE_H-TOP-BOTTOM,id='main')],onPage=decor))
    story=[PageBreak()]
    chartpaths={}
    for i,s in enumerate(SECTIONS):
        story+=section_head(s['kicker'],s['title'],s['dek'],s['color'])
        if s.get('kpis'):story += [kpi_band(s['kpis'],s['color']),Spacer(1,4*mm)]
        ps=s['paragraphs']
        if s['id']=='agenda':
            for j,(h,t) in enumerate(ps,1):story += [p(f'{j:02} · {h}','h2',textColor=s['color']),p(t)]
        else:
            mid=(len(ps)+1)//2
            story += [two_columns([f for h,t in ps[:mid] for f in [p(h,'h2',textColor=s['color']),p(t)]],[f for h,t in ps[mid:] for f in [p(h,'h2',textColor=s['color']),p(t)]])]
        story += [Spacer(1,3*mm)]
        if s.get('quote'):
            qt=Table([[p(s['quote'],'quote')]],colWidths=[CONTENT_W]);qt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('LINEBEFORE',(0,0),(0,0),2,YELLOW),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story += [qt,Spacer(1,3*mm)]
        if s.get('chart'):
            drawing=bars(*s['chart']);story += [drawing,Spacer(1,3*mm)]
            cp=SITE/f'assets/boletines/06-{s["id"]}.svg';cp.parent.mkdir(parents=True,exist_ok=True);cp.write_text(renderSVG.drawToString(drawing));chartpaths[s['id']]=cp
        if s.get('table'):story += tabular(s['table'])+[Spacer(1,3*mm)]
        if s.get('agenda'):story += [agenda(s['agenda'],s['color']),Spacer(1,2*mm)]
        if s['id']=='agenda':
            story += [p('Para profundizar el debate','h2'),p("<link href='https://cepoes.org/presupuesto/2027/'>Presupuesto 2027</link>: análisis integral de ingresos, gasto, deuda y prioridades. <link href='https://cepoes.org/presupuesto/2027/salud/'>Especial de Salud</link>: recursos y capacidades sanitarias. <link href='https://cepoes.org/presupuesto/2027/desarrollo-productivo/'>Desarrollo productivo</link>: empleo, comercios e incentivos."),Spacer(1,2*mm)]
            story += [p('Corte, método y referencias','h2'),p('Corte de información: 19/10/2026. Precios y canastas: septiembre. Empleo, ingresos y pobreza: segundo trimestre de 2026, usados como contexto. Presupuesto: proyecto presentado el 30/09/2026 frente al vigente del Mensaje al 30/06/2026.','small'),Spacer(1,2*mm),p('Variaciones reales de presupuesto: proyecto / (vigente × 1,2154) - 1. Ingresos laborales: 1,236 / 1,327 - 1. Cálculos sobre montos originales antes del redondeo. Los escenarios de precios son estimaciones y los créditos son asignaciones previstas.','small'),Spacer(1,2*mm)]
        story += [source(reference([k])) for k in s['sources']] if s['id']=='agenda' else [source(reference(s['sources']))]
        if i<len(SECTIONS)-1:story += [PageBreak()]
    doc.build(story)
    import fitz
    d=fitz.open(pdf)
    assert len(d)==8,f'Número inesperado de páginas: {len(d)}'
    occupancy_guard(pdf)
    coverpng=SITE/'assets/boletines/boletin-06.png';d[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(coverpng)
    build_html(chartpaths)
    print(pdf)

def build_html(chartpaths):
    template=(SITE/'publicaciones/boletines/boletin-05-septiembre-2026/index.html').read_text()
    head=template.split('<body')[0]
    head=re.sub(r'<title>.*?</title>',f'<title>{TITLE} — Boletín CEPOES N.º 6</title>',head)
    head=head.replace('boletin-05-septiembre-2026',SLUG).replace('boletin-05.svg','boletin-06.png')
    head=re.sub(r'(<meta[^>]*(?:name="description"|property="og:description")[^>]*content=")[^"]*',lambda m:m[1]+DEK,head)
    head=re.sub(r'(<meta property="og:title" content=")[^"]*',lambda m:m[1]+TITLE+' — Boletín CEPOES',head)
    # La fecha editorial corresponde al corte real; publicación se registra al desplegar.
    head=head.replace('</head>','<meta name="cepoes:content-date" content="2026-10-19"><meta name="cepoes:publication" content="newsletter"></head>')
    hero=template[template.index('<article class="bol">'):template.index('  <nav class="bol-riel"')]
    hero=hero[:hero.index('    <details')]
    hero=hero.replace('>05</span>','>06</span>').replace('La recuperación que no llega a los barrios',TITLE).replace('La economía porteña casi no crece y su impulso se concentra en las finanzas. Comercio, industria, consumo e ingresos muestran otra Ciudad.',DEK).replace('Septiembre 2026','Octubre 2026').replace('boletin-05-septiembre-2026',SLUG).replace('boletin-05.svg','boletin-06.png').replace('Tapa del N.º 5 del Boletín CEPOES, septiembre de 2026','Tapa del N.º 6 del Boletín CEPOES, octubre de 2026')
    items=''.join(f'<a class="bol-sumario__item" href="#{s["id"]}" data-eje="{s["eje"]}"><span class="bol-sumario__n">{i+2:02}</span><span class="bol-sumario__h">{escape(s["kicker"].capitalize())}</span><span class="bol-sumario__d">{escape(s["title"])}</span></a>' for i,s in enumerate(SECTIONS))
    hero+='<details class="bol-sumario-toggle"><summary>En este número · Ver sumario</summary><nav class="bol-sumario" aria-label="Sumario del número"><p class="bol-sumario__t bol-eyebrow">En este número</p>'+items+'</nav></details></div></header>'
    rail='<nav class="bol-riel" aria-label="Secciones del boletín"><div class="bol-wrap"><div class="bol-riel__lista">'+''.join(f'<a class="bol-riel__link" href="#{s["id"]}" data-eje="{s["eje"]}">{escape(s["kicker"].capitalize())}</a>' for s in SECTIONS)+'</div></div></nav>'
    bodies=[]
    for s in SECTIONS:
        body=f'<section class="bol-sec" id="{s["id"]}" data-eje="{s["eje"]}" aria-labelledby="t-{s["id"]}"><div class="bol-wrap"><header class="bol-sec__head"><span class="bol-sec__kicker bol-eyebrow">{s["kicker"]}</span><h2 class="bol-sec__title" id="t-{s["id"]}">{escape(s["title"])}</h2><p class="bol-sec__dek">{escape(s["dek"])}</p></header>'
        if s.get('kpis'):body+='<div class="bol-kpis">'+''.join(f'<div class="bol-kpi"><p class="bol-kpi__val">{v}</p><p class="bol-kpi__desc">{l}<span class="bol-kpi__src">{src}</span></p></div>' for v,l,src in s['kpis'])+'</div>'
        body+='<div class="bol-cuerpo bol-cuerpo--dos">'+''.join(f'<div class="bol-bloque"><h3 class="bol-bloque__h">{escape(h)}</h3><p>{escape(t)}</p></div>' for h,t in s['paragraphs'])+'</div>'
        if s.get('quote'):body+=f'<blockquote class="bol-quote">{escape(s["quote"])}</blockquote>'
        if s.get('chart'):
            title,vals,domain,unit=s['chart'];src='/'+str(chartpaths[s['id']].relative_to(SITE))
            alt=title+'. '+unit+'. '+'; '.join(f'{l}: {num(v)}%' for l,v in vals)
            body+=f'<figure class="graf"><img src="{src}" alt="{escape(alt)}" style="display:block;width:100%;height:auto;background:#fff" width="{int(CONTENT_W)}" height="{40+25*len(vals)}"><figcaption class="graf__fuente">{escape(unit)}. {reference(s["sources"],True)}</figcaption></figure>'
        if s.get('table'):
            title,heads,rows=s['table'];body+='<div class="bol-tabla-wrap"><p class="bol-tabla-wrap__t">'+escape(title)+'</p><table class="bol-tabla"><thead><tr>'+''.join('<th scope="col">'+escape(x)+'</th>' for x in heads)+'</tr></thead><tbody>'
            for r in rows:body+='<tr>'+''.join(f'<td class="{["bol-tabla__tema","bol-tabla__ind","bol-tabla__dato"][j]}">{escape(str(x))}</td>' for j,x in enumerate(r))+'</tr>'
            body+='</tbody></table></div>'
        if s.get('agenda'):body+='<ol class="bol5-proposals">'+''.join(f'<li><b>{escape(h)}</b><span>{escape(t)}</span></li>' for h,t in s['agenda'])+'</ol>'
        if s['id']=='agenda':body+='<div class="bol-prosa"><h3>Para profundizar el debate</h3><p><a href="https://cepoes.org/presupuesto/2027/">Presupuesto 2027</a>: análisis integral. <a href="https://cepoes.org/presupuesto/2027/salud/">Especial de Salud</a>: recursos y capacidades sanitarias. <a href="https://cepoes.org/presupuesto/2027/desarrollo-productivo/">Desarrollo productivo</a>: empleo, comercios e incentivos.</p></div>'
        if s['id']=='agenda':body+='<div class="bol-prosa"><h3>Corte y metodología</h3><p>Corte: 19/10/2026. Precios y canastas: septiembre; empleo, ingresos y pobreza: segundo trimestre. Presupuesto: proyecto presentado el 30/09/2026 frente al vigente al 30/06/2026 del Mensaje. Inflación promedio estimada de 21,54%. Las variaciones reales se calculan sobre montos originales antes del redondeo: proyecto / (vigente × 1,2154) - 1. Ingresos laborales: 1,236 / 1,327 - 1. Escenarios y asignaciones previstas se distinguen de los datos observados.</p></div>'
        body+='<p class="bol-fuentes"><b>Fuentes</b>'+reference(s['sources'],True)+'</p></div></section>';bodies.append(body)
    footer=template[template.index('  <footer class="bol-cierre"'):]
    footer=footer.replace('La recuperación que no llega a los barrios',TITLE).replace('N.º 5','N.º 6').replace('septiembre de 2026','octubre de 2026').replace('boletin-05-septiembre-2026',SLUG).replace('← N.º 04 · Agosto 2026','← N.º 05 · Septiembre 2026').replace('boletin-04-agosto-2026','boletin-05-septiembre-2026')
    out=SITE/f'publicaciones/boletines/{SLUG}/index.html';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('\n'.join(line.rstrip() for line in (head+'<body data-related-tags="publicaciones,boletines,presupuesto,salud">'+hero+rail+'<main>'+''.join(bodies)+'</main>'+footer).splitlines()).rstrip()+'\n')
if __name__=='__main__':build()
