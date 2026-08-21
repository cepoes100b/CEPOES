"""Ajustes verificados de la segunda ampliación y capas oficiales adicionales.

Se mantiene separado para no reescribir la configuración extensa mientras se
valida la primera corrida real. Una vez estabilizada, puede consolidarse.
"""
from __future__ import annotations

import oferta_extra_2 as X

# Nombres/slugs contrastados contra el catálogo público vigente de BA Data.
X.EXTRA_DATASETS["murales"].update({
    "dataset": "murales",
    "resource_pattern": r"^Murales \(CSV\)$",
    "format": "csv",
})
X.EXTRA_DATASETS["licencias_conducir"].update({
    "dataset": "licencias-conducir",
    "resource_pattern": r"^Licencias de conducir$",
    "format": "csv",
})
X.EXTRA_DATASETS["puestos_flores"].update({
    "dataset": "puestos-de-flores",
    "resource_pattern": r"^Permisos de uso del espacio público - Puestos de Flores \(CSV\)$",
    "format": "csv",
})
X.EXTRA_DATASETS["puestos_diarios"].update({
    "dataset": "puestos-de-diarios",
    "resource_pattern": r"^Puestos de Diario$",
    "format": "csv",
})
X.EXTRA_DATASETS["nido"].update({
    "dataset": "portales-inclusivos",
    "resource_pattern": r"^N[uú]cleo de Inclusi[oó]n y Desarrollo de Oportunidades$",
    "format": "csv",
})
X.EXTRA_DATASETS["embajadas"].update({
    "dataset": "embajadas",
    "resource_pattern": r"^Embajadas \(CSV\)$",
    "format": "csv",
})

# Representaciones consulares.
X.EXTRA_DATASETS["consulados"] = {
    "dataset": "consulados",
    "resource_pattern": r"^Consulados \(CSV\)$",
    "format": "csv",
    "filename": "consulados.csv",
    "descripcion": "Consulados con sede en la Ciudad",
}
X.EXTRA_LAYERS.append({
    "id": "consulados", "source": "consulados", "label": "Consulados",
    "category": "servicios", "type": "Consulado",
    "name": ["nombre", "pais", "representacion"],
    "address": ["direccion", "domicilio"], "phone": ["telefono", "tel"],
    "email": ["email", "mail"], "web": ["web", "sitio_web"],
    "geometry": ["geometry", "wkt"], "lat": ["lat", "latitud"],
    "lon": ["long", "lon", "longitud"],
    "description": "Consulados con sede en la Ciudad y datos de contacto oficiales.",
})

# Patrimonio inmobiliario del GCBA: dependencias públicas con barrio/comuna y coordenadas.
X.EXTRA_DATASETS["edificios_publicos"] = {
    "dataset": "edificios-publicos",
    "resource_pattern": r"^Edificios Publicos del GCBA$",
    "format": "csv",
    "filename": "edificios_publicos.csv",
    "descripcion": "Edificios públicos del Gobierno de la Ciudad",
}
X.EXTRA_LAYERS.append({
    "id": "edificios-publicos", "source": "edificios_publicos",
    "label": "Edificios públicos del GCBA", "category": "gestion",
    "type": ["nivel_gest"],
    "name": ["nivel_get_2", "nivel_get_1", "nivel_gest"],
    "address": ["dom_norma", "direccion", "calle"],
    "detail": ["nivel_get_1"], "detail2": ["nivel_get_2"],
    "lat": ["lat"], "lon": ["long"],
    "description": "Inmuebles utilizados como dependencias públicas del Gobierno de la Ciudad.",
})

# Infraestructura de accesibilidad. La última capa tabular disponible corresponde
# al relevamiento 2016; se explicita el año para no presentarla como inventario actual.
X.EXTRA_DATASETS["rampas_accesibilidad"] = {
    "dataset": "rampas-accesibilidad",
    "resource_pattern": r"^Rampas de accesibilidad - Relevamiento 2016$",
    "format": "csv",
    "filename": "rampas_accesibilidad_2016.csv",
    "descripcion": "Rampas de accesibilidad - relevamiento 2016",
}
X.EXTRA_LAYERS.append({
    "id": "rampas-accesibilidad-2016", "source": "rampas_accesibilidad",
    "label": "Rampas de accesibilidad (relevamiento 2016)",
    "category": "movilidad", "type": "Rampa de accesibilidad",
    "name": ["dom_norma", "calle", "id"],
    "address": ["dom_norma", "dom_geo", "calle"],
    "detail": ["estado"], "detail2": ["zona"],
    "lat": ["y"], "lon": ["x"],
    "description": "Rampas para personas con movilidad reducida registradas en el relevamiento oficial 2016.",
})
