"""Fuentes territoriales de BA Data usadas por CEPOES.

Se resuelven por dataset + nombre de recurso mediante la API CKAN. No se guardan
URLs de descarga fijas porque BA Data puede reemplazar el archivo sin conservar
la misma ruta.
"""

BA_DATA_API = "https://data.buenosaires.gob.ar/api/3/action/package_show"
BA_DATA_BASE = "https://data.buenosaires.gob.ar/dataset/"

# clave -> configuración del recurso preferido
DATASETS_TERRITORIO = {
    "educacion": {
        "dataset": "establecimientos-educativos",
        "resource_pattern": r"^Establecimientos Educativos \(CSV\)$",
        "format": "csv",
        "filename": "establecimientos_educativos.csv",
        "descripcion": "Establecimientos educativos con comuna y barrio",
    },
    "cesac": {
        "dataset": "centros-salud-accion-comunitaria-cesac",
        "resource_pattern": r"^Centros de Salud y Acci[oó]n Comunitaria \(CSV\)$",
        "format": "csv",
        "filename": "cesac.csv",
        "descripcion": "Centros de Salud y Acción Comunitaria (CeSAC)",
    },
    "hospitales": {
        "dataset": "hospitales",
        "resource_pattern": r"^Hospitales \(XLSX\)$",
        "format": "xlsx",
        "filename": "hospitales.xlsx",
        "descripcion": "Hospitales de la Ciudad con localización territorial",
    },
    "espacios_verdes": {
        "dataset": "espacios-verdes",
        "resource_pattern": r"^Espacios Verdes P[uú]blicos \(XLSX\)$",
        "format": "xlsx",
        "filename": "espacios_verdes_publicos.xlsx",
        "descripcion": "Espacios verdes públicos con superficie, comuna y barrio",
    },
}
