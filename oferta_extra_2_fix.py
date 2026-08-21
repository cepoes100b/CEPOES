"""Ajustes verificados de la segunda ampliación y una capa adicional oficial.

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

# Representaciones consulares: fuente oficial de Jefatura de Gabinete, actualizada
# trimestralmente y con ubicación/datos de contacto.
X.EXTRA_DATASETS["consulados"] = {
    "dataset": "consulados",
    "resource_pattern": r"^Consulados \(CSV\)$",
    "format": "csv",
    "filename": "consulados.csv",
    "descripcion": "Consulados con sede en la Ciudad",
}
X.EXTRA_LAYERS.append({
    "id": "consulados",
    "source": "consulados",
    "label": "Consulados",
    "category": "servicios",
    "type": "Consulado",
    "name": ["nombre", "pais", "representacion"],
    "address": ["direccion", "domicilio"],
    "phone": ["telefono", "tel"],
    "email": ["email", "mail"],
    "web": ["web", "sitio_web"],
    "geometry": ["geometry", "wkt"],
    "lat": ["lat", "latitud"],
    "lon": ["long", "lon", "longitud"],
    "description": "Consulados con sede en la Ciudad y datos de contacto oficiales.",
})
