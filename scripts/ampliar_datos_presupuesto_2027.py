#!/usr/bin/env python3
"""Extensión primaria del snapshot: Mensaje cuadros 2.2/2.3/3.2/3.4/3.5 y Planillas 1/16."""
from pathlib import Path
import json,re,csv
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'deploy/site-overlay/assets/data/presupuesto-2027.json'
d=json.loads(path.read_text())
d['ingresos_corrientes']=[dict(nombre=n,vigente_2026_06_30=a*1000000,proyecto_2027=b,pagina_mensaje=69) for n,a,b in [
('Tributarios',15791387.3,19094214003433),('No tributarios',461777.1,663825629989),('Venta de bienes y servicios',277535.7,365617417614),('Rentas de la propiedad',599312.9,951290901460),('Transferencias corrientes',2744696.2,3017533491405)]]
d['tributos']=[dict(nombre=n,vigente_2026_06_30=round(a*1000000),proyecto_2027=round(b*1000000),pagina_mensaje=70,precision='millones con una décima') for n,a,b in [
('Ingresos Brutos',10938684.6,13279892.3),('Inmuebles',1146137.4,1454917.6),('Vehículos',615803.9,491794.8),('Sellos',1127797.7,1448901.0),('Electricidad',101854.0,131857.4),('Contribución ferroviaria',37644.0,48732.9),('Publicidad',12462.0,11428.3),('Grandes generadores de residuos',707.0,704.7),('Coparticipación federal',1810296.6,2225985.0)]]
d['economica']=[dict(nombre=n,vigente_2026_06_30=round(a*1000000),proyecto_2027=b,devengado_2026_06_30=round(c*1000000),fuente='Cuadro 2.3 del Mensaje (p. 52) y Planilla 16 (p. 22 del anexo)') for n,a,b,c in [
('Remuneraciones al personal',8105637.6,9950480728332,3509818.0),('Consumo y otros gastos corrientes primarios',5170366.0,6428377453576,1602744.2),('Transferencias corrientes',2289396.2,2797877991872,911698.6),('Gasto de capital',4033207.4,4325717119862,989030.3),('Intereses',278544.8,591887305621,90814.8)]]
# AIF agrupa en consumo partidas que la Planilla 1 distingue como otros gastos corrientes.
d['gasto_tributario_seleccionado']=[dict(nombre=n,millones_2027=v,fuente='Mensaje, pp. 66–67') for n,v in [('ABL',230230.9),('Patentes',93889.1),('Distrito Tecnológico',192515),('Distrito Audiovisual y de las Artes',9161),('Distrito del Diseño',5839),('Microcentro',101402),('Distrito del Vino',2789),('Economía del conocimiento',42291),('Mecenazgo',17634)]]
d['fiscal'].update(recursos_corrientes=24092481443901,recursos_capital=3175598228,aplicaciones_financieras=919674000329,incremento_inversion_financiera=305757726563,disminucion_inversion_financiera=162781198566)
d['macro']={'crecimiento_pib_nacional':4,'inflacion_diciembre_diciembre':18,'tipo_cambio_diciembre_2027':1847.6,'fuente':'Presentación de Hacienda del 7/10/2026; hipótesis, no resultados observados'}
# Composición sectorial transcrita de Planilla 1, sin sumar subtotales padre/hijo.
d['composicion_funciones']=[dict(nombre=n,personal=p,consumo=c,transferencias=t,otros=o,capital=k) for n,p,c,t,o,k in [
('Educación',2800605694226,759198758558,705717321877,0,469974376564),
('Promoción y acción social',232638622849,311495204564,1678591566149,0,11797258165),
('Vivienda y Urbanismo',100789380542,78944304971,5633061899,0,641323087377),
('Transporte',26045446928,37729679277,50744434932,0,1133777549879),
('Seguridad interior',2136832658610,858750082315,36659821951,0,423098752666),
('Sistema penal',38951071214,27302446494,2858306770,0,69987965947),
('Cultura',156260865147,142039262075,28994792785,271809614,22961535711),
('Trabajo',34734935063,78797883821,72554473567,0,10568315673),
('Ecología',57249554399,147653317838,2727039881,0,313238777124),
('Servicios Urbanos',34633494891,1683553727229,0,0,365035475842),
('Agua potable y alcantarillado',15350717671,3887293875,0,0,189380265899),
('Turismo',4118083195,77169413014,0,0,41601461),
('Industria y Comercio',9328851181,35862105187,10315800799,0,162606078)]]
d['limites'].append('Los gastos tributarios son conceptos seleccionados, no inventario completo ni ahorro recuperable automáticamente. No se suman regímenes potencialmente superpuestos.') if 'Los gastos tributarios son conceptos seleccionados, no inventario completo ni ahorro recuperable automáticamente. No se suman regímenes potencialmente superpuestos.' not in d['limites'] else None
path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
for key,suffix in [('tributos','tributos'),('economica','economica'),('composicion_funciones','composicion-sectorial')]:
 rows=d[key]
 with path.with_name('presupuesto-2027-'+suffix+'.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('Extensión primaria de datos y tres CSV generados')
