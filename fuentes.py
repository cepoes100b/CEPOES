"""Catálogo de fuentes oficiales del observatorio CEPOES.

Cómo se localiza cada dataset
-----------------------------
IDECBA organiza el Banco de Datos en categorías. Las **categorías** son
estables; los **posts** de adentro rotan: cada vez que se publica un período
nuevo aparece un post con un slug distinto, y el viejo queda relegado.

Por eso acá no se guarda la URL del dataset —eso se rompe en cuanto IDECBA
publica— sino dos cosas que sí aguantan:

  categoria : el slug de la página de categoría
  patron    : una expresión que identifica al dataset dentro de esa categoría

El descargador baja la página de categoría, busca el primer post cuyo slug
coincide con el patrón (la categoría lista de más nuevo a más viejo, así que el
primero es el vigente) y de ahí saca el enlace al .xlsx.

Un catálogo con URLs fijas fallaba de un modo confuso: el servidor de IDECBA no
devuelve 404 rápido en rutas inexistentes, se cuelga hasta agotar el timeout, y
eso se parece mucho a un problema de red. Con categorías eso desaparece.
"""

CAT_BASE = "https://www.estadisticaciudad.gob.ar/eyc/categoria-banco-datos/"

# archivo local -> (categoría, patrón del slug, descripción)
DATASETS = {
    "ipcba_evol.xlsx": (
        "indice-mensual-base-2021",
        r"evolucion-del-nivel-general-estacionales-regulados-y-resto",
        "IPCBA base 2021=100 · nivel general, estacionales, regulados y resto",
    ),
    "empleo.xlsx": (
        "tasas-de-actividad-empleo-y-desocupacion",
        r"tasas-de-actividad-empleo-desocupacion-subocupacion-horaria",
        "ETOI · tasas de actividad, empleo, desocupación y subocupación",
    ),
    "comex_tot.xlsx": (
        "comercio-exterior",
        r"exportaciones-monto-fob-en-dolares-y-participacion",
        "Exportaciones en dólares y participación en el PGB",
    ),
    "masa_salarial.xlsx": (
        "industria",
        r"masa-salarial-por-rama-de-actividad-indice-base-octubre-2001",
        "Encuesta Industrial · masa salarial por rama",
    ),
    "ejes48_comuna_tasas.xlsx": (
        "ejes-comerciales",
        r"locales-relevados-ocupados-densidad-comercial-tasa-de-ocupacion.*por-comuna-48-ejes",
        "Locales relevados, ocupados y tasa de ocupación por comuna (48 ejes)",
    ),
    "locales.xlsx": (
        "ejes-comerciales",
        r"tasa-de-ocupacion.*eje-comercial",
        "Tasa de ocupación de locales por eje comercial",
    ),
    "industria_ing.xlsx": (
        "industria",
        r"ingresos.*por-rama-de-actividad",
        "Encuesta Industrial · ingresos fabriles por rama",
    ),
    "canastas.xlsx": (
        "canastas-de-consumo-de-la-ciudad",
        r"canastas-de-consumo.*evolucion-de-su-valor-en-pesos-hogar-1",
        "Canastas de consumo · hogar 1, evolución del valor",
    ),
    "pobreza_tasas.xlsx": (
        "pobreza-e-indigencia",
        r"hogares-y-personas.*pobreza-e-indigencia",
        "Líneas de pobreza e indigencia · hogares y personas",
    ),
    "pgb_var.xlsx": (
        "producto-geografico-bruto-pgb",
        r"variacion-porcentual.*(sector|rama)",
        "PGB a precios constantes · variación interanual por sector",
    ),
    "ipcba_aperturas.xlsx": (
        "indice-mensual-base-2021",
        r"principales-aperturas",
        "IPCBA · índices por división COICOP",
    ),
}

CALENDARIO_URL = "https://www.estadisticaciudad.gob.ar/eyc/calendario-listado/"

FUENTE_TEXTO = ("IDECBA — Instituto de Estadística y Censos de la Ciudad "
                "Autónoma de Buenos Aires")
