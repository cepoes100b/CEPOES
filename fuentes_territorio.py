"""Fuentes territoriales oficiales usadas por CEPOES.

Se resuelven por dataset + nombre de recurso mediante la API CKAN de BA Data.
No se guardan URLs de descarga fijas porque BA Data puede reemplazar el archivo
sin conservar la misma ruta. La fuente pública de CEPOES es siempre el organismo
oficial productor; estos recursos se usan para construir la Oferta territorial.
"""

BA_DATA_API = "https://data.buenosaires.gob.ar/api/3/action/package_show"
BA_DATA_BASE = "https://data.buenosaires.gob.ar/dataset/"

# clave -> configuración del recurso preferido. Las cuatro primeras fuentes
# alimentan además los agregados de territorio.json; las restantes se publican
# como capas explorables registro por registro.
DATASETS_TERRITORIO = {
    "educacion": {
        "dataset": "establecimientos-educativos",
        "resource_pattern": r"^Padr[oó]n de Establecimientos Educativos \(CSV\)$",
        "format": "csv",
        "filename": "establecimientos_educativos.csv",
        "descripcion": "Padrón de establecimientos educativos con comuna y barrio",
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

    # Salud y bienestar
    "centros_medicos_barriales": {
        "dataset": "centros-medicos-barriales",
        "resource_pattern": r"^Centros m[eé]dicos barriales \(CSV\)$",
        "format": "csv",
        "filename": "centros_medicos_barriales.csv",
        "descripcion": "Centros Médicos Barriales",
    },
    "salud_privada": {
        "dataset": "centros-salud-privados",
        # Se prefiere XLSX: conserva de manera más consistente la comuna.
        "resource_pattern": r"^Centros de Salud Privados \(XLSX\)$",
        "format": "xlsx",
        "filename": "centros_salud_privados.xlsx",
        "descripcion": "Hospitales, sanatorios y clínicas privadas",
    },
    "estaciones_saludables": {
        "dataset": "estaciones-saludables",
        "resource_pattern": r"^Estaciones Saludables \(CSV\)$",
        "format": "csv",
        "filename": "estaciones_saludables.csv",
        "descripcion": "Estaciones Saludables",
    },

    # Cultura y comunidad
    "bibliotecas": {
        "dataset": "bibliotecas",
        "resource_pattern": r"^Bibliotecas \(CSV\)$",
        "format": "csv",
        "filename": "bibliotecas.csv",
        "descripcion": "Bibliotecas de la Red del GCBA",
    },
    "espacios_culturales": {
        "dataset": "espacios-culturales",
        "resource_pattern": r"^Espacios culturales \(CSV\)$",
        "format": "csv",
        "filename": "espacios_culturales.csv",
        "descripcion": "Espacios culturales públicos, privados e independientes",
    },
    "instituciones_colectividades": {
        "dataset": "instituciones-colectividades",
        "resource_pattern": r"^Instituciones de Colectividades$",
        "format": "csv",
        "filename": "instituciones_colectividades.csv",
        "descripcion": "Instituciones de colectividades",
    },

    # Deporte
    "polideportivos": {
        "dataset": "polideportivos",
        "resource_pattern": r"^Polideportivos \(CSV\)$",
        "format": "csv",
        "filename": "polideportivos.csv",
        "descripcion": "Polideportivos de la Ciudad",
    },
    "programas_deportivos": {
        "dataset": "programas-deportivos",
        "resource_pattern": r"^Programas deportivos$",
        "format": "csv",
        "filename": "programas_deportivos.csv",
        "descripcion": "Programas deportivos y sedes",
    },
    "clubes": {
        "dataset": "clubes",
        "resource_pattern": r"^Clubes \(CSV\)$",
        "format": "csv",
        "filename": "clubes.csv",
        "descripcion": "Clubes de barrio y deportivos",
    },
    "estadios": {
        "dataset": "estadios",
        "resource_pattern": r"^Estadios \(CSV\)$",
        "format": "csv",
        "filename": "estadios.csv",
        "descripcion": "Estadios de la Ciudad",
    },

    # Cuidados y desarrollo social
    "cpi": {
        "dataset": "centros-primera-infancia",
        "resource_pattern": r"^Centros de Primera Infancia \(CSV\)$",
        "format": "csv",
        "filename": "centros_primera_infancia.csv",
        "descripcion": "Centros de Primera Infancia",
    },
    "caf": {
        "dataset": "centros-de-accion-familiar",
        "resource_pattern": r"^Centros de acci[oó]n familiar \(CSV\)$",
        "format": "csv",
        "filename": "centros_accion_familiar.csv",
        "descripcion": "Centros de Acción Familiar",
    },
    "casas_nnya": {
        "dataset": "casas-ninas-ninos-adolescentes",
        "resource_pattern": r"^Casas de Ni[nñ]as, Ni[nñ]os y/o Adolescentes \(CSV\)$",
        "format": "csv",
        "filename": "casas_nnya.csv",
        "descripcion": "Casas de Niñas, Niños y Adolescentes",
    },
    "hogares_paradores": {
        "dataset": "hogares-paradores",
        "resource_pattern": r"^Hogares y paradores \(CSV\)$",
        "format": "csv",
        "filename": "hogares_paradores.csv",
        "descripcion": "Hogares y paradores de la Ciudad",
    },

    # Seguridad y emergencias
    "comisarias": {
        "dataset": "comisarias-policia-ciudad",
        "resource_pattern": r"^Comisar[ií]as Polic[ií]a de la Ciudad$",
        "format": "csv",
        "filename": "comisarias.csv",
        "descripcion": "Comisarías de la Policía de la Ciudad",
    },
    "bomberos": {
        "dataset": "cuarteles-destacamentos-bomberos",
        "resource_pattern": r"^Cuarteles y Destacamentos de Bomberos \(CSV\)$",
        "format": "csv",
        "filename": "bomberos.csv",
        "descripcion": "Cuarteles y destacamentos de Bomberos",
    },

    # Movilidad
    "subte_bocas": {
        "dataset": "bocas-subte",
        "resource_pattern": r"^Bocas de Subte$",
        "format": "csv",
        "filename": "bocas_subte.csv",
        "descripcion": "Bocas de acceso y salida del Subte",
    },
    "ecobici": {
        "dataset": "estaciones-bicicletas-publicas",
        "resource_pattern": r"^Estaciones de bicicletas p[uú]blicas \(nuevo sistema\)$",
        "format": "csv",
        "filename": "estaciones_ecobici.csv",
        "descripcion": "Estaciones de bicicletas públicas",
    },
    "ferrocarril": {
        "dataset": "estaciones-ferrocarril",
        "resource_pattern": r"^Estaciones de Ferrocarril \(CSV\)$",
        "format": "csv",
        "filename": "estaciones_ferrocarril.csv",
        "descripcion": "Estaciones de ferrocarril",
    },
    "taxis": {
        "dataset": "paradas-taxis",
        "resource_pattern": r"^Paradas de Taxis \(CSV\)$",
        "format": "csv",
        "filename": "paradas_taxis.csv",
        "descripcion": "Paradas de taxis habilitadas",
    },
    "bicicleteros": {
        "dataset": "bicicleteros-via-publica",
        "resource_pattern": r"^Bicicleteros$",
        "format": "csv",
        "filename": "bicicleteros.csv",
        "descripcion": "Bicicleteros instalados en vía pública",
    },

    # Ambiente y reciclado
    "puntos_verdes": {
        "dataset": "puntos-verdes",
        "resource_pattern": r"^Puntos Verdes \(CSV\)$",
        "format": "csv",
        "filename": "puntos_verdes.csv",
        "descripcion": "Puntos Verdes para recepción de reciclables",
    },

    # Abastecimiento y economía cotidiana
    "fiab": {
        "dataset": "ferias-mercados",
        "resource_pattern": r"^Ferias Itinerantes de Abastecimiento Barrial$",
        "format": "csv",
        "filename": "fiab.csv",
        "descripcion": "Ferias Itinerantes de Abastecimiento Barrial (FIAB)",
    },
    "mercados": {
        "dataset": "ferias-mercados",
        "resource_pattern": r"^Mercados$",
        "format": "csv",
        "filename": "mercados.csv",
        "descripcion": "Mercados fijos de la Ciudad",
    },

    # Gestión pública y trabajo
    "sedes_comunales": {
        "dataset": "sedes-comunales",
        "resource_pattern": r"^Sedes Comunales$",
        "format": "csv",
        "filename": "sedes_comunales.csv",
        "descripcion": "Sedes Comunales",
    },
    "centros_integracion_laboral": {
        "dataset": "centros-integracion-laboral",
        "resource_pattern": r"^Centros de Integraci[oó]n Laboral \(CSV\)$",
        "format": "csv",
        "filename": "centros_integracion_laboral.csv",
        "descripcion": "Centros de Integración Laboral",
    },
}
