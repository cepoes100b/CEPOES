#!/usr/bin/env python3
"""Build the public methodology hub and its product-specific technical sheets."""

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "site-overlay" / "cepoes" / "metodologia"
REVIEWED = "28 de septiembre de 2026"
BASE = "/cepoes/metodologia/"


def a(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def table(rows):
    return '<div class="method-table-wrap"><table class="method-table"><thead><tr><th>Dato o fuente</th><th>Uso y alcance</th></tr></thead><tbody>' + ''.join(f'<tr><td>{x}</td><td>{y}</td></tr>' for x, y in rows) + '</tbody></table></div>'


def section(anchor, title, body):
    return f'<section class="method-rule" id="{anchor}"><h2>{title}</h2>{body}</section>'


SHEETS = [
    dict(slug="observatorio", title="Observatorio económico y social", tag="Series estadísticas", deck="Cómo se incorporan las series del IDECBA y qué significan los períodos, las transformaciones y los datos faltantes.", product="/observatorio/", source="IDECBA · Banco de Datos", scale="Ciudad de Buenos Aires; algunas series incluyen comunas", frequency="Según cada publicación oficial", sections=[
        ("fuentes", "Fuentes y cobertura", table([
            (a("https://www.estadisticaciudad.gob.ar/eyc/categoria-banco-datos/indice-mensual-base-2021/", "IPCBA base 2021: nivel general y aperturas"), "Índices mensuales y principales divisiones; el período disponible se lee en cada gráfico."),
            (a("https://www.estadisticaciudad.gob.ar/eyc/categoria-banco-datos/canastas-de-consumo-de-la-ciudad/", "Canastas de consumo"), "Valor mensual en pesos del hogar de referencia publicado en la serie."),
            (a("https://www.estadisticaciudad.gob.ar/eyc/categoria-banco-datos/tasas-de-actividad-empleo-y-desocupacion/", "ETOI: actividad y empleo"), "Tasas de actividad, empleo, desocupación y subocupación; verificar trimestre y universo."),
            (a("https://www.estadisticaciudad.gob.ar/eyc/categoria-banco-datos/linea-de-pobreza-e-indigencia/", "Pobreza e indigencia"), "Distribución de personas y hogares por estrato de ingresos."),
            (a("https://www.estadisticaciudad.gob.ar/eyc/categoria-banco-datos/producto-geografico-bruto-pgb/", "Producto Geográfico Bruto"), "Variación trimestral interanual del PGB."),
            (a("https://www.estadisticaciudad.gob.ar/eyc/categoria-banco-datos/industria/", "Encuesta Industrial"), "Ingresos y masa salarial por rama, según cada planilla."),
            (a("https://www.estadisticaciudad.gob.ar/eyc/categoria-banco-datos/comercio-exterior/", "Comercio exterior"), "Monto FOB exportado y relación con el producto, según la serie."),
            (a("https://www.estadisticaciudad.gob.ar/eyc/categoria-banco-datos/ejes-comerciales/", "Ejes comerciales"), "Locales relevados, ocupados y tasas por comuna en los 48 ejes analizados."),
            (a("https://www.estadisticaciudad.gob.ar/eyc/calendario-listado/", "Calendario oficial"), "Referencia para las próximas publicaciones; una fecha de calendario no equivale a un dato disponible."),
            (a("https://www.indec.gob.ar/", "INDEC · Censo 2022"), "Población censal utilizada en las fichas territoriales; tiene una vigencia distinta de las series coyunturales.")
        ])),
        ("calculo", "Tratamiento y cálculos", "<p>El catálogo identifica las categorías y los nombres de las series del Banco de Datos. El procesamiento interpreta planillas con convenciones locales: coma decimal, marcas provisorias y signos de dato faltante. La variación interanual del IPCBA se calcula comparando el índice del mes con el del mismo mes del año anterior. Las exportaciones se expresan en millones de dólares cuando el gráfico así lo señala.</p>"),
        ("control", "Actualización y controles", "<p>La generación y verificación están automatizadas. Antes de publicar se comprueban longitudes mínimas, consistencia entre series, rangos plausibles y que no se acorten series previamente publicadas. Un error de descarga o procesamiento conserva la última versión válida del bloque afectado. La fecha de generación del archivo y el período estadístico son conceptos distintos.</p>"),
        ("limites", "Cómo leerlos", "<p>Las series tienen frecuencias, coberturas y revisiones diferentes. Una comparación exige mirar la unidad, el período y la población de referencia de cada gráfico. Un valor provisorio conserva ese carácter; un dato ausente no se interpreta como cero.</p>"),
    ]),
    dict(slug="territorio", title="Oferta y perfiles territoriales", tag="Registros geográficos", deck="Origen de las capas, asignación a barrios y comunas, deduplicación y población usada como denominador.", product="/territorio/equipamientos/", source="BA Data · INDEC", scale="15 comunas y 48 barrios", frequency="Según fecha de relevamiento de cada capa", sections=[
        ("fuentes", "Fuentes y cobertura", table([
            (a("https://data.buenosaires.gob.ar/dataset/establecimientos-educativos", "BA Data · Establecimientos educativos"), "Sedes identificadas por CUE y anexo, con identificador alternativo si falta; se excluyen los estados de baja o inactividad reconocidos por la fuente."),
            (a("https://data.buenosaires.gob.ar/dataset/centros-salud-accion-comunitaria-cesac", "BA Data · CeSAC"), "Registros de centros de salud con comuna y barrio cuando constan en la fuente."),
            (a("https://data.buenosaires.gob.ar/dataset/espacios-verdes", "BA Data · Espacios verdes"), "Superficie relevada en metros cuadrados; se utiliza para calcular m² por habitante."),
            (a("https://www.indec.gob.ar/", "INDEC · Censo 2022"), "Población de referencia por barrio o comuna para las comparaciones por habitantes.")
        ])),
        ("calculo", "Construcción territorial", "<p>Las capas conservan el registro individual identificable de la fuente. Se normalizan nombres territoriales y se eliminan duplicados según los identificadores disponibles para cada conjunto. Cuando hay coordenadas y falta el barrio, puede utilizarse un cruce espacial con límites oficiales; el registro sin localización suficiente no se asigna arbitrariamente.</p><p>Los perfiles reúnen una selección de capas: establecimientos educativos, CeSAC, hospitales y espacios verdes, entre otras. Cada dimensión conserva su unidad y cobertura; sus conteos no se suman como si midieran la misma oferta.</p>"),
        ("control", "Vigencia y controles", "<p>La página de cada capa debe informar su fecha de fuente o relevamiento. El proceso verifica la estructura y cobertura territorial del conjunto publicado. La fecha en que CEPOES procesa un archivo puede ser posterior a la fecha en que se relevaron sus establecimientos.</p>"),
        ("limites", "Cómo leerlos", "<p>El número de registros aproxima presencia territorial. No mide por sí solo cupos, capacidad, calidad, horarios, accesibilidad ni necesidad insatisfecha. Las capas históricas describen el relevamiento indicado; no deben leerse como un inventario de apertura actual. Cuando una ficha muestra un indicador comunal en el contexto de un barrio, corresponde a toda la comuna.</p>"),
    ]),
    dict(slug="brechas", title="Brechas territoriales", tag="Comparación entre barrios", deck="Definiciones de tasas, referencia CABA, percentiles y grupos de posición para comparar los 48 barrios.", product="/territorio/brechas/", source="BA Data · Censo 2022", scale="48 barrios, con filtro por comuna", frequency="Según el resumen territorial publicado", sections=[
        ("fuentes", "Universo y dimensiones", "<p>Se comparan diez dimensiones seleccionadas del resumen territorial: educación, salud, personas mayores, infancias, cultura, deporte, seguridad, movilidad, servicios y ambiente. La selección de registros de cada dimensión es una aproximación de disponibilidad; sus contenidos no equivalen entre sí.</p>"),
        ("calculo", "Fórmulas y posiciones", table([
            ("Tasa por población", "Registros seleccionados del barrio ÷ población del barrio del Censo 2022 × 10.000. Para ambiente se utiliza superficie relevada en m² ÷ población del barrio."),
            ("Referencia CABA", "Suma de registros de las comunas ÷ suma de población comunal × 10.000; para ambiente, suma de m² ÷ población. Se calcula para la dimensión seleccionada."),
            ("Índice CABA = 100", "Tasa del barrio ÷ tasa de referencia CABA × 100, cuando la referencia es válida. Mide relación de valores, no calidad de servicio."),
            ("Posición, percentil y quintil", "Se ordenan los barrios con valor disponible de mayor a menor. El percentil mostrado es 100 × (n − posición + 1) ÷ n, redondeado. El grupo Alto–Bajo divide la posición relativa en cinco tramos; con 48 barrios los grupos pueden no tener exactamente el mismo tamaño.")
        ])),
        ("control", "Filtros y comparación", "<p>El filtro de comuna cambia los barrios visibles y el resumen de esa selección. El orden, percentil y quintil se calculan antes de aplicar ese filtro, sobre todos los barrios con dato de la dimensión elegida. La mediana es la del conjunto visible. Se puede alternar entre conteos y medidas por población.</p>"),
        ("limites", "Cómo leerlos", "<p>Un valor más alto puede significar mayor presencia de un registro, pero su interpretación depende de lo que mide la dimensión. La disponibilidad territorial no prueba que las personas residentes accedan al servicio. La población de 2022 se mantiene como denominador aun cuando las capas tengan fechas posteriores.</p>"),
    ]),
    dict(slug="endeudamiento", title="Endeudamiento por barrio", tag="Estimación territorial", deck="Universo BCRA/ARCA, indicadores de mora y distribución estadística de agregados CP4 a barrios.", product="/territorio/endeudamiento/", source="Central de Deudores BCRA · Padrón ARCA distribuido por BCRA", scale="Total CABA observado; 48 barrios estimados", frequency="Mensual, según último período procesado", sections=[
        ("fuentes", "Universo y fuente primaria", table([
            (a("https://www5.bcra.gob.ar/ChequesyDeudores/Deudores", "BCRA · Descarga de Deudores y Padrón"), "Central de Deudores y padrón ARCA distribuido por el BCRA. El universo CABA se identifica con provincia ARCA 00; para la capa territorial se exige además CP4 porteño válido."),
            (a("/datos/estado/", "Estado de los datos CEPOES"), "Permite consultar el último conjunto procesado. El tablero informa el período de deuda y sus coberturas; la fecha del padrón puede diferir.")
        ])),
        ("calculo", "Definiciones e indicadores", table([
            ("Personas deudoras", "Personas únicas incluidas en el universo CABA del período, según las entidades informantes de la Central."),
            ("Personas en mora", "Personas con situación 3, 4 o 5. Incidencia de mora = personas en mora ÷ personas deudoras × 100."),
            ("Tasa de mora por monto", "Monto en mora ÷ monto total adeudado × 100; mide dinero y no proporción de personas."),
            ("Monto", "Pesos corrientes del período. Una misma persona puede figurar en más de una categoría de acreedor; esas categorías no se suman como personas únicas.")
        ])),
        ("territorializacion", "Del CP4 al barrio", "<p>El total CABA se calcula sobre el universo provincial identificado por ARCA. La capa barrial parte de agregados por CP4 dentro del rango porteño y los distribuye mediante una matriz fija de ponderaciones CP4 → barrio. Por ejemplo, si la matriz asigna a un CP4 60 % a un barrio y 40 % a otro, un agregado de 100 personas de ese CP4 aporta estadísticamente 60 y 40 a cada barrio. Es un ejemplo ilustrativo de la regla, no la asignación de un CP4 concreto.</p><p>Los CP4 sin soporte geográfico observado permanecen en el total CABA, pero no se reparten a barrios. Las celdas demográficas o por acreedor con menos de diez personas deudoras se suprimen antes de la distribución. La matriz se mantiene fija entre meses; cambian los agregados del nuevo período.</p>"),
        ("control", "Cobertura y controles", "<p>La capa incluye un porcentaje de cobertura del mapa respecto del total CABA para personas deudoras, personas en mora y montos. En la generación se exige que la cobertura de personas y de deuda total sea al menos 90 %, que existan 48 barrios y que las ponderaciones de cada CP4 admitido sumen uno. El porcentaje exacto debe consultarse en el período seleccionado; no se traslada automáticamente el de un mes a otro.</p>"),
        ("limites", "Cómo leerlos", "<p>Los valores barriales son estimaciones estadísticas agregadas: admiten fracciones antes del redondeo y no localizan el domicilio de una persona. Una variación entre barrios puede reflejar distribución postal, composición del crédito o cobertura. La Central de Deudores informa situación y monto financiero, pero no permite deducir para qué se utilizó cada préstamo.</p>"),
    ]),
    dict(slug="presupuesto", title="Presupuesto de la Ciudad", tag="Finanzas públicas", deck="Lectura del presupuesto sancionado y ejecutado, crédito vigente, devengado y clasificación geográfica.", product="/presupuesto/", source="BA Data · GCBA", scale="Ciudad; clasificaciones oficiales, incluida geografía presupuestaria", frequency="Trimestral para ejecución", sections=[
        ("fuentes", "Fuentes y período", table([
            (a("https://data.buenosaires.gob.ar/dataset/presupuesto-ejecutado", "BA Data · Presupuesto Ejecutado"), "Se selecciona el CSV del último trimestre disponible y se conservan sus metadatos de recurso."),
            (a("https://data.buenosaires.gob.ar/dataset/presupuesto-sancionado", "BA Data · Presupuesto Sancionado"), "CSV del mismo ejercicio que el ejecutado; sirve de referencia y control de consistencia.")
        ])),
        ("calculo", "Indicadores y clasificación", table([
            ("Crédito sancionado", "Monto aprobado para el ejercicio según la clasificación de la fuente."),
            ("Crédito vigente", "Crédito tras las modificaciones registradas. Modificación = vigente − sancionado."),
            ("Gasto devengado y ejecución", "Gasto reconocido por la fuente; ejecución porcentual = devengado ÷ crédito vigente × 100, si el denominador es distinto de cero."),
            ("Geografía presupuestaria", "Clasificación geográfica publicada en el presupuesto. Una asignación a comuna no prueba que la totalidad del gasto se materialice físicamente allí.")
        ])),
        ("control", "Controles", "<p>El procesamiento comprueba la presencia de columnas, filas y totales, y contrasta el sancionado incorporado en el ejecutado con el archivo sancionado anual del mismo ejercicio. Se publica el período oficial (ejercicio y trimestre) junto con la fecha en que se generó el conjunto.</p>"),
        ("limites", "Cómo leerlos", "<p>Los importes se publican en pesos corrientes. El total procesado incluye gastos corrientes, de capital y aplicaciones financieras según la distribución de BA Data; no corresponde compararlo sin ajustes con un subtotal legal de distinto alcance. Un trimestre no se anualiza ni representa una proyección del cierre.</p>"),
    ]),
    dict(slug="legislatura", title="Monitor Legislativo", tag="Seguimiento institucional", deck="Origen y alcance de expedientes, reuniones, comisiones y sesiones, con estados respaldados por fuentes oficiales.", product="/legislatura/", source="Legislatura de CABA", scale="Legislatura porteña", frequency="Actualizaciones periódicas; fecha visible en el monitor", sections=[
        ("fuentes", "Fuentes oficiales", table([
            (a("https://www.legislatura.gob.ar/AgendaLCABA", "Agenda de la Legislatura"), "Reuniones parlamentarias publicadas y expedientes de sus temarios cuando constan."),
            (a("https://parlamentaria.legislatura.gob.ar/pages/ExpedienteBusqueda.aspx", "Sistema de Consultas Parlamentarias"), "Fichas, estados y movimientos de expedientes de la fuente pública."),
            (a("https://www.legislatura.gob.ar/InfoSesion/", "Información de sesiones"), "Sesiones y documentos de recinto cuando la fuente los publica.")
        ])),
        ("calculo", "Criterios de inclusión", "<p>El núcleo de agenda identifica reuniones de comisiones, juntas, audiencias y Labor Parlamentaria; deja fuera actos protocolares y administrativos detectados. Los expedientes se enriquecen con su ficha oficial y movimientos del ciclo parlamentario. Las clasificaciones temáticas ayudan a explorar y no modifican el estado del expediente.</p>"),
        ("control", "Controles y actualización", "<p>Los procesos de agenda, expedientes y sesiones se verifican antes de publicar. La capa de sesiones se mantiene separada del núcleo de agenda para que una variación en una fuente no invalide necesariamente la otra. Las 27 comisiones permanentes se muestran aun cuando no tengan actividad en la ventana reciente.</p>"),
        ("limites", "Cómo leerlos", "<p>Un proyecto sin movimiento capturado no equivale a falta de actividad política; depende del registro oficial y de la ventana de actualización. Las etapas sólo se muestran si tienen sustento documental. La prioridad editorial del seguimiento de determinados temas o actores se distingue de la información parlamentaria descriptiva.</p>"),
    ]),
    dict(slug="migraciones", title="Migraciones", tag="Población y territorio", deck="Diferencia entre lugar de nacimiento, población extranjera y movilidad interna en las fuentes disponibles.", product="/territorio/migraciones/", source="INDEC · IDECBA · EAH", scale="Ciudad y, para algunas series, comunas", frequency="Censal o según encuesta e indicador", sections=[
        ("fuentes", "Fuentes y unidades", table([
            (a("https://www.indec.gob.ar/", "INDEC · Censo 2022"), "Referencia censal de población por lugar de nacimiento según la desagregación disponible."),
            (a("https://www.estadisticaciudad.gob.ar/eyc/arbol-tematico/", "IDECBA · Banco de Datos y EAH"), "Series de población por lugar de nacimiento y características sociodemográficas; cada tabla conserva su universo, período y escala.")
        ])),
        ("calculo", "Definiciones y comparación", "<p>“Nacida en el extranjero” y “nacida en otra provincia argentina” son categorías distintas. La primera aproxima migración internacional por lugar de nacimiento; la segunda aproxima migración interna. Lugar de nacimiento tampoco equivale a nacionalidad, residencia legal ni fecha de llegada. Se conserva el año y el universo de cada fuente cuando se comparan porcentajes.</p>"),
        ("control", "Actualización", "<p>El proceso exige estructura, cobertura de las comunas esperadas cuando corresponde y consistencia de la fuente. Una nueva corrida no reemplaza los datos válidos si falla esa validación.</p>"),
        ("limites", "Cómo leerlos", "<p>Las encuestas tienen error muestral y no reproducen el universo del censo. Una cifra de ciudad no se atribuye a barrios ni se interpreta como un flujo de ingreso reciente. La desagregación comunal sólo se muestra para las series que la fuente permite.</p>"),
    ]),
    dict(slug="salud-mental", title="Salud mental", tag="Indicadores y red de atención", deck="Serie de suicidios consumados del SNIC, fuentes complementarias y alcance de los indicadores de la Ciudad.", product="/observatorio/salud-mental/", source="SNIC · fuentes sanitarias oficiales", scale="País y jurisdicciones; red de atención en CABA", frequency="Anual para la serie SNIC", sections=[
        ("fuentes", "Fuentes y alcance", table([
            (a("https://cloud-snic.minseg.gob.ar/Bases/SNIC/snic-provincias.csv", "SNIC · Base por jurisdicción"), "Serie oficial de suicidios consumados para la comparación de CABA con otras jurisdicciones."),
            (a("https://cloud-snic.minseg.gob.ar/Bases/SNIC/Manual_de_usuario_Base_SNIC.pdf", "SNIC · Manual de usuario"), "Definiciones y notas de la fuente principal."),
            (a("https://datos.salud.gob.ar/", "DEIS · Estadísticas vitales"), "Serie de contraste separada; no se fusiona con SNIC para crear una serie única.")
        ])),
        ("calculo", "Indicadores", "<p>La serie principal corresponde a suicidios consumados, código 31 del SNIC, con sus tasas oficiales. Los indicadores de intentos, de atención y de red de servicios responden a fuentes y unidades diferentes: se presentan por separado y con su propia fecha.</p>"),
        ("control", "Validación", "<p>La actualización de SNIC verifica años, jurisdicciones, duplicados y consistencia contra totales oficiales. Si la fuente principal no supera esos controles, no se publica como nueva serie válida. La fuente DEIS se conserva como contraste independiente.</p>"),
        ("limites", "Cómo leerlos", "<p>Un suicidio consumado no informa por sí mismo la prevalencia de trastornos de salud mental ni la calidad causal de un servicio. La comparación de tasas requiere conservar denominador, año y definiciones de cada fuente; la localización de servicios no mide acceso efectivo.</p>"),
    ]),
]

CODE_PATHS = {
    "observatorio": "generar_datos.py",
    "territorio": "generar_territorio.py",
    "brechas": "deploy/site-overlay/assets/brechas.js",
    "endeudamiento": "generar_endeudamiento_barrios.py",
    "presupuesto": "generar_presupuesto.py",
    "legislatura": "actualizar_legislatura.py",
    "migraciones": "actualizar_migraciones.py",
    "salud-mental": "actualizar_salud_mental.py",
}


def frame(title, description, path, body):
    return f'''<!doctype html><html data-theme="light" lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#16232f"><title>{escape(title)} — CEPOES</title><meta name="description" content="{escape(description, quote=True)}"><link rel="canonical" href="https://cepoes.org{path}"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&amp;family=Inter:wght@400;500;600;700&amp;display=swap" rel="stylesheet"><link href="/assets/site.css" rel="stylesheet"><link href="/assets/arquitectura.css" rel="stylesheet"><link href="/assets/metodologia.css?v=1" rel="stylesheet"><script defer src="/assets/common-r1.js?v=259"></script></head><body><nav class="site-nav"><div class="wrap nav-in"><a class="brand" href="/"><span class="logo">CEP<b>OES</b></span><span class="brand-sub"><strong>SOMOS 100 BARRIOS</strong></span></a><div class="nav-links"><a href="/observatorio/">Observatorio</a><a href="/balance/">Balance</a><a href="/presupuesto/">Presupuesto</a><a href="/territorio/">Territorio</a><a href="/legislatura/">Legislatura</a><a href="/publicaciones/">Publicaciones</a><a href="/propuestas/">Propuestas</a><a href="/prensa/">Prensa</a><a href="/lo-nuevo/">Lo nuevo</a><a class="active" href="/cepoes/">CEPOES</a></div><button aria-label="Buscar en CEPOES" class="search-btn" data-search-open>⌕</button><button aria-label="Cambiar tema" class="theme-btn" data-theme-toggle>◐</button><button aria-label="Abrir menú" class="menu-btn" data-menu-toggle>☰</button></div></nav><main id="contenido" class="method-page">{body}</main><footer class="footer"><div class="wrap footer-grid"><div><a class="logo" href="/">CEP<b>OES</b></a><p>Datos, investigación y propuestas para CABA, desde los barrios.</p><strong>SOMOS 100 BARRIOS</strong></div><div><h5>CEPOES</h5><a href="/cepoes/">Quiénes somos</a><a href="{BASE}">Metodología y fuentes</a><a href="mailto:contacto@cepoes.org">contacto@cepoes.org</a></div></div><div class="wrap footer-copy">© 2026 CEPOES · Somos 100 Barrios</div></footer></body></html>'''


def hero(title, deck, slug=""):
    crumb = f' / {escape(title)}' if slug else ''
    return f'<header class="page-hero"><div class="wrap"><div class="breadcrumbs">{a("/", "CEPOES")} / {a("/cepoes/", "Institucional")} / {a(BASE, "Metodología y fuentes")}{crumb}</div><span class="eyebrow">Transparencia · CEPOES</span><h1>{escape(title)}</h1><p class="method-lead">{escape(deck)}</p><div class="method-meta"><span>Revisión metodológica: <strong>{REVIEWED}</strong></span><span>Período del dato: <strong>ver cada producto</strong></span></div></div></header>'


def sheet_page(d):
    toc = ''.join(a('#' + key, title) for key, title, _ in d['sections'])
    content = ''.join(section(*item) for item in d['sections'])
    code_url = 'https://github.com/cepoes100b/CEPOES/blob/main/' + CODE_PATHS[d['slug']]
    content += section('trazabilidad', 'Consultar el producto y sus fuentes', f'<p>La fecha de esta ficha indica cuándo se revisaron sus reglas; el último período disponible se consulta en el producto. El código público permite examinar la transformación utilizada. Si detectás una diferencia entre esta ficha y una visualización, escribí a {a("mailto:contacto@cepoes.org", "contacto@cepoes.org")} con el enlace y período.</p><div class="method-links">{a(d["product"], "Explorar el producto →")}{a(code_url, "Ver transformación en GitHub ↗")}{a("/datos/estado/", "Estado de los datos →")}{a(BASE, "Todas las metodologías →")}</div>')
    body = hero(d['title'], d['deck'], d['slug']) + f'<div class="section"><div class="wrap method-layout"><article><p class="method-kicker">Ficha técnica · {escape(d["tag"])}</p><div class="method-note"><p><strong>Fuente:</strong> {escape(d["source"])}<br><strong>Escala:</strong> {escape(d["scale"])}<br><strong>Frecuencia:</strong> {escape(d["frequency"])}</p></div>{content}</article><aside class="method-index" aria-label="Contenido de la ficha"><strong>En esta ficha</strong>{toc}{a("#trazabilidad", "Producto y consultas")}{a(BASE, "Volver al índice")}</aside></div></div>'
    return frame('Ficha técnica: ' + d['title'], d['deck'], BASE + d['slug'] + '/', body)


def hub_page():
    cards = ''.join(f'<a class="method-card" href="{BASE}{d["slug"]}/"><span class="eyebrow">{escape(d["tag"])}</span><strong>{escape(d["title"])}</strong><span>{escape(d["deck"])}</span><em>Leer ficha técnica →</em></a>' for d in SHEETS)
    rows = ''.join(f'<tr><td>{a(BASE + d["slug"] + "/", d["title"])}</td><td>{escape(d["source"])}</td><td>{escape(d["scale"])}</td><td>{escape(d["frequency"])}</td></tr>' for d in SHEETS)
    body = hero('Metodología y fuentes', 'Cómo se obtiene, transforma y publica la evidencia que usamos para analizar la Ciudad. Cada ficha explica el indicador y sus límites antes de usarlo para una interpretación o propuesta.')
    body += f'''<div class="section"><div class="wrap method-layout"><article>
    {section('criterios', 'Tres reglas para leer nuestros datos', '<div class="method-cards"><div class="method-card"><span class="eyebrow">01 · Dato observado</span><strong>Lo que informa la fuente</strong><span>Conservamos unidad, universo, escala y período. Una ausencia de dato no se convierte en cero.</span></div><div class="method-card"><span class="eyebrow">02 · Elaboración o estimación</span><strong>Lo que calcula CEPOES</strong><span>Explicamos fórmulas, denominadores, cruces y cobertura. La estimación por barrio del endeudamiento se identifica expresamente.</span></div><div class="method-card"><span class="eyebrow">03 · Análisis</span><strong>Lo que interpreta CEPOES</strong><span>Las lecturas críticas y propuestas tienen autoría editorial. Los gráficos descriptivos conservan su fuente y no prueban por sí solos causalidad.</span></div></div>')}
    {section('recorrido', 'Del archivo oficial a la publicación', '<ol><li><strong>Selección:</strong> identificamos la fuente primaria y la versión o período de cada recurso.</li><li><strong>Procesamiento:</strong> normalizamos formatos, unidades y geografía, y documentamos los indicadores derivados.</li><li><strong>Verificación:</strong> controlamos estructura, cobertura y coherencia antes de publicar; si falla una actualización, se conserva el último conjunto válido según las reglas del producto.</li><li><strong>Lectura pública:</strong> el producto muestra su período y enlaza una ficha técnica con fórmulas y límites.</li></ol><p>La fecha de la fuente describe cuándo se relevó el fenómeno; la fecha de procesamiento indica cuándo CEPOES preparó el archivo; la fecha de revisión metodológica informa cuándo se verificó este texto. No son intercambiables.</p>')}
    {section('fichas', 'Fichas técnicas por producto', '<div class="method-cards">' + cards + '</div>')}
    {section('catalogo', 'Catálogo de fuentes y escalas', '<p>Estas son las familias de fuentes efectivamente usadas en los productos documentados. Los enlaces al conjunto o sistema primario, las definiciones y el período específico están en cada ficha.</p><div class="method-table-wrap"><table class="method-table"><thead><tr><th>Producto</th><th>Fuente principal</th><th>Escala</th><th>Actualización</th></tr></thead><tbody>' + rows + '</tbody></table></div>')}
    {section('actualizacion', 'Vigencia, correcciones y consultas', '<p>La disponibilidad de un archivo no significa que sus registros representen un inventario actual. Las fuentes censales, anuales, trimestrales y mensuales se publican con su período propio. Las comparaciones entre años o territorios deben respetar ese período y los cambios de definición de la fuente.</p><p>El <a href="/datos/estado/">estado de los datos</a> informa el último conjunto incorporado de varios productos. Si una fuente corrige una serie o cambia su estructura, la versión publicada se revisa antes de reemplazarla. Para comunicar errores o pedir detalles de un cálculo: <a href="mailto:contacto@cepoes.org">contacto@cepoes.org</a>.</p><div class="method-note"><p>Esta página explica reglas comunes; cada ficha prevalece para la definición y alcance de su producto. Revisión metodológica: ' + REVIEWED + '.</p></div>')}
    </article><aside class="method-index" aria-label="Índice de metodología"><strong>En esta página</strong><a href="#criterios">Reglas de lectura</a><a href="#recorrido">Proceso y controles</a><a href="#fichas">Fichas por producto</a><a href="#catalogo">Catálogo de fuentes</a><a href="#actualizacion">Actualización y consultas</a></aside></div></div>'''
    return frame('Metodología y fuentes', 'Fuentes, indicadores, controles y fichas técnicas de los productos de datos de CEPOES.', BASE, body)


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'index.html').write_text(hub_page(), encoding='utf-8')
    for sheet in SHEETS:
        target = ROOT / sheet['slug'] / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(sheet_page(sheet), encoding='utf-8')
    print(f'Metodología: portada y {len(SHEETS)} fichas técnicas generadas')


if __name__ == '__main__':
    main()
