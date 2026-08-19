"""Catálogo de fuentes oficiales del observatorio CEPOES.

Cada entrada apunta a una página del Banco de Datos de IDECBA. Esas URLs son
ESTABLES: cuando el instituto publica un período nuevo, reescribe el mismo post
y sólo cambia la ruta del .xlsx adjunto (que vive bajo /wp-content/uploads/AAAA/MM/).
Por eso alcanza con guardar la URL de la página y leer de ahí el link al archivo.

Si alguna vez IDECBA reorganiza el banco de datos y una URL deja de existir, el
descargador lo reporta y conserva la última copia commiteada del xlsx, así el
observatorio nunca se queda sin datos.
"""

# Las entradas marcadas "verificada" se comprobaron contra el sitio. El resto
# se armaron por patrón y pueden estar mal: correr  python verificar_fuentes.py
# para saber cuáles responden y corregir acá las que fallen. Una URL inexistente
# no devuelve 404 rápido: el servidor se cuelga hasta el timeout, así que una
# entrada mal escrita se parece mucho a un problema de red.
BASE = "https://www.estadisticaciudad.gob.ar/eyc/banco-datos/"

# archivo local -> (URL de la página del dataset, descripción legible)
DATASETS = {
    "ipcba_evol.xlsx": (
        # verificada
        BASE + "ipcba-base-2021-100-evolucion-del-nivel-general-estacionales-regulados-y-resto-ipcba-indices-y-variaciones-porcentuales-respecto-del-mes-anterior-ciudad-de-buenos-aires-febrero-de-2022-ago/",
        "IPCBA base 2021=100 · nivel general, estacionales, regulados y resto",
    ),
    "canastas.xlsx": (
        BASE + "canastas-de-consumo-del-hogar-de-referencia-evolucion-de-su-valor-y-de-sus-componentes-ciudad-de-buenos-aires-enero-de-2013-junio-de-2/",
        "Canastas de consumo del hogar de referencia",
    ),
    "empleo.xlsx": (
        # verificada
        BASE + "tasas-de-actividad-empleo-desocupacion-subocupacion-horaria-ciudad-de-buenos-aires-3er-trimestre-de-2014-2do-trimestre-de-2024/",
        "ETOI · tasas de actividad, empleo, desocupación y subocupación",
    ),
    "pobreza_tasas.xlsx": (
        BASE + "distribucion-de-hogares-y-personas-segun-situacion-de-pobreza-e-indigencia-ciudad-de-buenos-aires-2015-2/",
        "Líneas de pobreza e indigencia · hogares y personas",
    ),
    "comex_tot.xlsx": (
        BASE + "exportaciones-dolares-y-participacion-en-el-producto-geografico-bruto-ciudad-de-buenos-aires-1993-2/",
        "Exportaciones en dólares y participación en el PGB",
    ),
    "industria_ing.xlsx": (
        BASE + "ingresos-fabriles-por-rama-de-actividad-industrial-ciudad-de-buenos-aires-octubre-de-2001-2/",
        "Encuesta Industrial · ingresos fabriles por rama",
    ),
    "masa_salarial.xlsx": (
        BASE + "masa-salarial-por-rama-de-actividad-industrial-ciudad-de-buenos-aires-octubre-de-2001-2/",
        "Encuesta Industrial · masa salarial por rama",
    ),
    "locales.xlsx": (
        BASE + "tasa-de-ocupacion-de-locales-por-eje-comercial-ciudad-de-buenos-aires-2do-cuatrimestre-de-2022-2/",
        "Tasa de ocupación de locales por eje comercial (48 ejes)",
    ),
    "ejes48_comuna_tasas.xlsx": (
        BASE + "locales-relevados-ocupados-y-tasa-de-ocupacion-por-comuna-ciudad-de-buenos-aires-2/",
        "Locales relevados, ocupados y tasa de ocupación por comuna",
    ),
}

# Archivos que IDECBA publica con nombre fijo bajo /wp-content/uploads/.
# Se intenta la URL directa y, si falla, se conserva la copia local.
DIRECTOS = {
    "pgb_var.xlsx": (
        "https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2025/12/PGB_K_variacion_porcentual.xlsx",
        "PGB a precios constantes · variación porcentual interanual por sector",
    ),
    "ipcba_aperturas.xlsx": (
        "https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/02/IPCBA_base_2021100-Principales_aperturas_indices.xlsx",
        "IPCBA · índices por división COICOP",
    ),
}

CALENDARIO_URL = "https://www.estadisticaciudad.gob.ar/eyc/calendario-listado/"

FUENTE_TEXTO = "IDECBA — Instituto de Estadística y Censos de la Ciudad Autónoma de Buenos Aires"
