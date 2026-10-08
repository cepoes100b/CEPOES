"""Gráficos HTML accesibles: escalas desde cero, fuente y universo visibles."""
import html,math
def n(x,d=1):return f'{x:,.{d}f}'.replace(',','X').replace('.',',').replace('X','.')
def e(x):return html.escape(str(x),quote=True)
def figure(id,title,desc,content,source):
 return f'<figure class="p27-visual" aria-labelledby="{id}-title"><figcaption><span class="p27-kicker">EL PRESUPUESTO EN GRÁFICOS</span><h3 id="{id}-title">{title}</h3><p>{desc}</p></figcaption>{content}<p class="p27-source">{source}</p></figure>'
def stack(id,rows,total,title,desc,source):
 segments=''.join(f'<span style="width:{value/total*100:.8f}%;background:var(--p27-color-{i+1})"></span>' for i,(name,value) in enumerate(rows))
 legend=''.join(f'<li><i style="background:var(--p27-color-{i+1})" aria-hidden="true"></i><div><strong>{e(name)}</strong><span>{n(value/total*100)} de cada $100</span><small>${n(value/1e6)} millones</small></div></li>' for i,(name,value) in enumerate(rows))
 return figure(id,title,desc,f'<div class="p27-stack" aria-hidden="true">{segments}</div><div class="p27-stack-axis" aria-hidden="true"><span>$0</span><span>$50</span><span>$100</span></div><ul class="p27-chart-legend">{legend}</ul>',source)
def bars(id,rows,maximum,title,desc,source,unit='',decimals=1):
 # El ancho de las barras parte de cero. Las etiquetas nunca están dentro de la barra.
 chart=''.join(f'<div class="p27-chart-row"><div class="p27-chart-label">{e(name)}</div><div class="p27-chart-track" aria-hidden="true"><i style="width:{value/maximum*100:.8f}%"></i></div><strong class="p27-chart-value">{n(value,decimals)}{unit}</strong></div>' for name,value in rows)
 axis=f'<div class="p27-chart-axis" aria-hidden="true"><span>0</span><span>{n(maximum/2,0)}</span><span>{n(maximum,0)}{unit}</span></div>'
 return figure(id,title,desc,'<div class="p27-bars">'+chart+axis+'</div>',source)
def priorities(d):
 rows=sorted(d['funciones'],key=lambda r:r['proyecto_2027'],reverse=True)
 content='<div class="p27-key"><span><i class="p27-before"></i>Vigente 2026</span><span><i class="p27-after"></i>Proyecto 2027</span></div>'
 for r in rows:
  a=r['vigente_2026_06_30']/d['vigente_2026_06_30']*100;b=r['proyecto_2027']/d['total_2027']*100
  content+=f'<div class="p27-paired-row"><strong>{e(r["nombre"])}</strong><div class="p27-paired-tracks" aria-hidden="true"><i class="p27-before" style="width:{a/20*100:.8f}%"></i><i class="p27-after" style="width:{b/20*100:.8f}%"></i></div><span>{n(a,2)}% → <b>{n(b,2)}%</b></span></div>'
 content+='<div class="p27-paired-axis" aria-hidden="true"><span>0%</span><span>10%</span><span>20%</span></div>'
 return figure('prioridades-visual','Dónde se concentra el presupuesto','Participación de las veinte funciones. Una misma escala permite comparar su peso, aunque los montos en pesos aumenten.',content,'Cuadro 2.4 del Mensaje y Planilla 1. Base vigente al 30/06/2026 frente a proyecto 2027. Escala de barras 0–20%; no se suman subtotales.')
def changes(d):
 rows=sorted(enumerate(d['funciones']),key=lambda pair:pair[1]['proyecto_2027']/pair[1]['vigente_2026_06_30'])
 content='<div class="p27-key"><span><i class="p27-loss"></i>Pierde poder de compra</span><span><i class="p27-gain"></i>Gana poder de compra</span></div><div class="p27-change-summary" id="change-summary" aria-live="polite">12 de 20 funciones quedan debajo del escenario de precios de 21,54%.</div>'
 for index,r in rows:
  v=(r['proyecto_2027']/r['vigente_2026_06_30']/1.2154-1)*100;left=20+min(v,0);width=abs(v)
  content+=f'<div class="p27-diverging-row"><span>{e(r["nombre"])}</span><div class="p27-diverging-track" aria-hidden="true"><i data-change-bar="{index}" class="{"p27-loss" if v<0 else "p27-gain"}" style="left:{left:.8f}%;width:{width:.8f}%"></i></div><strong data-change-value="{index}">{"+" if v>0 else ""}{n(v)}%</strong></div>'
 content+='<div class="p27-change-axis" aria-hidden="true"><span>−20%</span><span>0%</span><span>+40%</span><span>+80%</span></div>'
 return figure('cambios-visual','Qué partidas ganan y cuáles pierden capacidad de compra','Variación real del proyecto frente al vigente de 2026. El gráfico cambia con el escenario de inflación seleccionado arriba.',content,'Cálculo sobre Cuadro 2.4 y Planilla 1. Escenario inicial: inflación promedio 21,54%. Escala fija −20% a +80%, con línea de cero. Son escenarios de créditos, no prestaciones observadas.')
def fiscal(d):
 f=d['fiscal'];content='<div class="p27-fiscal-equation">'
 for i,(name,value,symbol) in enumerate([('Resultado primario',f['resultado_primario'],''),('Intereses',f['intereses'],'−'),('Resultado financiero',f['resultado_financiero'],'=')]):
  content+=f'<div class="p27-fiscal-step"><span class="p27-math-symbol" aria-hidden="true">{symbol}</span><span class="p27-step-index">0{i+1}</span><strong>${n(value/1e6,0)} M</strong><span>{name}</span></div>'
 content+='</div><div class="p27-fiscal-share"><div><strong>99,78%</strong><span>del superávit primario se destina a intereses</span></div><div><strong>2,46%</strong><span>del gasto total corresponde a intereses</span></div></div>'
 return figure('balance-visual','El margen que queda después de intereses','El resultado financiero se obtiene restando intereses al resultado primario. La relación cambia según el denominador: no confundir superávit con presupuesto total.',content,'Planilla 16, Ahorro–Inversión–Financiamiento. Proyecto 2027. M = millones de pesos. Tarjetas sin escala de tamaño: representan la operación aritmética, no áreas proporcionales.')
def investment(d):
 a=d['fiscal']['capital_2026']/d['vigente_2026_06_30']*100;b=d['fiscal']['capital_2027']/d['total_2027']*100
 return bars('capital-visual',[('Vigente 2026',a),('Proyecto 2027',b)],25,'La inversión pierde peso dentro del total','De cada $100 de gasto, la porción destinada a capital baja. Los anuncios de obras deben leerse junto con este cambio del conjunto.','Cuadro 2.3 del Mensaje y Planilla 16. Participación del capital en gasto total; universo comparable. No es avance físico de obras.','%',2)
def health_priority(d):
 h=next(r for r in d['funciones'] if r['nombre']=='Salud');old=h['vigente_2026_06_30']/d['vigente_2026_06_30']*100;new=h['proyecto_2027']/d['total_2027']*100
 chart=bars('salud-prioridad-visual',[('Vigente 2026',old),('Proyecto 2027',new)],20,'Salud recibe una porción menor del presupuesto','El gasto sanitario crece en pesos, pero menos que el conjunto. Por eso pierde prioridad relativa.','Función Salud. Cuadro 2.4 y Planilla 1. Participación en gasto total, no porcentaje ejecutado.','%',2)
 ref=d['total_2027']*old/100-h['proyecto_2027']
 return chart+f'<aside class="p27-visual-takeaway"><strong>−{n(old-new,2)} puntos porcentuales</strong><p>La diferencia para conservar el peso anterior equivale a <b>${n(ref/1e6,0)} millones</b>. Es una referencia distributiva: no una partida eliminada.</p></aside>'
def staffing(d):
 rows=[(r['nombre'],r['cargos']) for r in d['salud']['dotacion']]
 return bars('salud-dotacion-visual',rows,20000,'Los equipos que sostienen la atención','42.395 cargos presupuestados en el Ministerio de Salud. La red combina profesiones, enfermería, apoyo administrativo y formación.','Planilla 17. Cargos presupuestados, no personas efectivamente ocupadas, ni salarios individuales.','',0)
def works(d):
 types=[('hospital','Hospitales generales'),('salud-mental','Salud mental'),('atencion-primaria','Atención primaria'),('equipamiento','Equipamiento')]
 rows=[]
 for key,title in types:
  values=[w for w in d['obras_seleccionadas'] if w['tipo']==key]
  rows.append((title+' · '+str(len(values))+' partidas',sum(w['proyecto_2027'] for w in values)/1e6))
 maximum=math.ceil(max(v for _,v in rows)/10000)*10000
 return bars('salud-obras-visual',rows,maximum,'Cómo se distribuyen las 30 inversiones seleccionadas','Montos 2027 agrupados por tipo de inversión. Este gráfico describe la selección del informe, no la totalidad del presupuesto hospitalario.','PPI 2027–2029, filas seleccionadas y páginas en la tabla de detalle. Montos en millones de pesos. Una fila por partida, sin sumar cabeceras padre.',' M',0)
def care_path():
 content='<ol class="p27-care-path">'
 for i,(name,desc) in enumerate([('Obra habilitada','Espacios y conexiones listos para usar'),('Equipamiento','Equipos instalados y en funcionamiento'),('Personal','Dotación, turnos y condiciones de trabajo'),('Insumos','Medicamentos y provisión continua'),('Atención','Prestaciones efectivas y continuidad de cuidados')]):
  content+=f'<li><b>{i+1:02}</b><strong>{name}</strong><span>{desc}</span></li>'
 content+='</ol>'
 return figure('salud-atencion-visual','Una obra no se convierte sola en atención','Para evaluar una inversión sanitaria hay que seguir cada condición de puesta en servicio.',content,'Esquema de seguimiento propuesto por 100 Barrios. No representa metas cumplidas ni partidas que deban sumarse.')
def inject_general(body,d):
 rows=[(r['nombre'],r['proyecto_2027']) for r in d['economica']]
 mix=stack('gasto-visual',rows,d['total_2027'],'Por cada $100, qué financia la Ciudad','Composición económica del gasto. Cinco destinos distintos: sostener equipos y servicios, transferir recursos, invertir y pagar intereses.','Planilla 16. Proyecto 2027. Consumo incluye otros gastos corrientes primarios según la apertura del AIF.')
 positions=[('<h3>Qué pasa si la recaudación no alcanza</h3>',fiscal(d))]
 # La composición abre la lectura visual, después del primer capítulo, antes de metodología.
 body=body.replace('<section id="metodo">',mix+'<section id="metodo">',1)
 for marker,visual in positions:body=body.replace(marker,visual+marker,1)
 for marker,visual in [('<h2>Veinte funciones, una misma comparación</h2>',priorities(d)+changes(d)),('<h2>La inversión requiere calendario y capacidad de funcionamiento</h2>',investment(d))]:
  body=body.replace(marker,marker+visual,1)
 return body
def inject_health(body,d):
 comp=stack('salud-composicion-visual',[(r['nombre'],r['monto']) for r in d['salud']['composicion_economica']],d['salud']['funcion_total'],'Por cada $100 de Salud, cómo se usan los recursos','El gasto corriente sostiene atención cotidiana; la inversión amplía y renueva capacidad. Ambos son necesarios.','Planilla 1. Función Salud, proyecto 2027. No equivale al total administrativo del Ministerio.')
 for marker,visual in [('<h3>El poder de compra depende de los precios del año</h3>',health_priority(d)),('<h3>Presupuestar una obra es el comienzo del control</h3>',care_path())]:
  body=body.replace(marker,visual+marker,1)
 for marker,visual in [('<h2>Personal, insumos y equipamiento funcionan juntos</h2>',comp+staffing(d)),('<h2>Qué inversiones sanitarias aparecen en el proyecto</h2>',works(d))]:
  body=body.replace(marker,marker+visual,1)
 return body
