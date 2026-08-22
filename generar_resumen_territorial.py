"""Genera un resumen liviano de Oferta territorial por comuna y barrio.

El objetivo es permitir radiografias, comparaciones y mapas tematicos sin que el
navegador tenga que descargar las 62 capas individuales (mas de 100 mil registros).
Los conteos representan registros de las fuentes oficiales; no se suman como si
fueran una unica magnitud cuando las capas miden objetos de naturaleza distinta.

La territorializacion del resumen es jerarquica y consistente:
1) si el registro tiene coordenadas, se usa el cruce con los 48 barrios oficiales;
2) si no tiene coordenadas utilizables pero trae un barrio reconocido, la comuna
   se deriva de la relacion oficial barrio -> comuna de territorio.json;
3) solo cuando no hay barrio se conserva una comuna valida informada por la fuente.
Esto evita contradicciones internas de algunos datasets entre barrio y comuna.
"""
from __future__ import annotations

import datetime
import json
import re
import unicodedata
from pathlib import Path

import generar_oferta_ampliada_runner as SPATIAL

BASE = Path(__file__).resolve().parent
DIR = BASE / "equipamientos"
CAT = DIR / "catalogo.json"
TERR = BASE / "territorio.json"
OUT = DIR / "resumen-territorial.json"

FEATURED = {
    "educacion": {
        "label": "Educacion",
        "layers": ["educacion"],
        "unit": "establecimientos",
    },
    "salud": {
        "label": "Salud",
        "layers": ["salud", "salud-privada", "centros-medicos-barriales"],
        "unit": "establecimientos y centros",
    },
    "mayores": {
        "label": "Personas mayores",
        "layers": ["geriatricos", "centros-jubilados", "centros-dia", "hogares-permanentes"],
        "unit": "dispositivos y establecimientos",
    },
    "infancias": {
        "label": "Infancias y familias",
        "layers": ["centros-primera-infancia", "centros-desarrollo-infantil", "jardines-comunitarios", "juegotecas", "centros-accion-familiar"],
        "unit": "espacios y dispositivos",
    },
    "cultura": {
        "label": "Cultura y comunidad",
        "layers": ["bibliotecas", "espacios-culturales", "instituciones-colectividades", "lugares-culto"],
        "unit": "espacios e instituciones",
    },
    "deporte": {
        "label": "Deporte",
        "layers": ["clubes", "polideportivos", "estadios"],
        "unit": "instituciones e instalaciones",
    },
    "seguridad": {
        "label": "Seguridad y emergencias",
        "layers": ["comisarias", "bomberos"],
        "unit": "dependencias",
    },
    "movilidad": {
        "label": "Movilidad",
        "layers": ["subte-bocas", "ecobici", "ferrocarril", "paradas-taxis"],
        "unit": "puntos y nodos",
    },
    "servicios": {
        "label": "Servicios y tramites",
        "layers": ["registro-civil", "documentacion-rapida", "ministerio-publico-fiscal", "sedes-comunales"],
        "unit": "sedes y dependencias",
    },
}


def norm(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def slug(value: object) -> str:
    return norm(value).replace(" ", "-")


ALIASES = {
    "paternal": "la-paternal",
    "la-paternal": "la-paternal",
    "villa-gral-mitre": "villa-general-mitre",
    "villa-gral-mitre-": "villa-general-mitre",
    "villa-general-mitre": "villa-general-mitre",
    "montserrat": "monserrat",
    "monserrat": "monserrat",
    "boca": "la-boca",
    "la-boca": "la-boca",
    "villa-pueyrredon": "villa-pueyrredon",
}


def barrio_slug(value: object, barrios: dict) -> str | None:
    raw = slug(value)
    raw = ALIASES.get(raw, raw)
    if raw in barrios:
        return raw
    n = norm(value)
    for key, b in barrios.items():
        if norm(b.get("nombre")) == n:
            return key
    return None


def comuna_id(value: object) -> str | None:
    try:
        cid = int(value)
    except (TypeError, ValueError):
        return None
    return str(cid) if 1 <= cid <= 15 else None


def empty_scope(nombre: str, comuna: int | None, poblacion: int) -> dict:
    return {
        "nombre": nombre,
        "comuna": comuna,
        "poblacion": int(poblacion or 0),
        "capas": {},
        "categorias": {},
        "destacados": {},
    }


def add_count(scope: dict, layer_id: str, category: str) -> None:
    scope["capas"][layer_id] = scope["capas"].get(layer_id, 0) + 1
    scope["categorias"][category] = scope["categorias"].get(category, 0) + 1


def finish_scope(scope: dict, terr_scope: dict | None = None) -> None:
    pop = max(int(scope.get("poblacion") or 0), 0)
    for fid, cfg in FEATURED.items():
        count = sum(int(scope["capas"].get(lid, 0)) for lid in cfg["layers"])
        scope["destacados"][fid] = {
            "label": cfg["label"],
            "valor": count,
            "tasa_10k": round(count / pop * 10000, 2) if pop else None,
            "unit": cfg["unit"],
            "layers": cfg["layers"],
        }
    if terr_scope:
        verde = terr_scope.get("espacio_verde") or {}
        scope["destacados"]["ambiente"] = {
            "label": "Espacio verde",
            "valor": int(verde.get("espacios") or 0),
            "m2_hab": verde.get("m2_hab"),
            "m2": verde.get("m2"),
            "unit": "espacios verdes",
            "layers": ["espacios-verdes"],
        }


def main() -> int:
    if not CAT.exists() or not TERR.exists():
        raise SystemExit("Faltan catalogo.json o territorio.json")
    catalog = json.loads(CAT.read_text(encoding="utf-8"))
    territory = json.loads(TERR.read_text(encoding="utf-8"))
    barrios_t = territory.get("barrios") or {}
    comunas_t = territory.get("comunas") or {}
    spatial_index = SPATIAL.load_spatial_index()

    comunas = {
        str(cid): empty_scope(f"Comuna {cid}", int(cid), c.get("poblacion") or 0)
        for cid, c in comunas_t.items()
    }
    barrios = {
        key: empty_scope(b.get("nombre") or key, int(b.get("comuna") or 0), b.get("poblacion") or 0)
        for key, b in barrios_t.items()
    }

    layer_meta = {}
    unmapped = {}
    adjustments = {}
    total_records = 0
    for meta in catalog.get("layers") or []:
        lid = meta.get("id")
        if not lid:
            continue
        fn = meta.get("file") or f"{lid}.json"
        path = DIR / fn
        if not path.exists():
            continue
        obj = json.loads(path.read_text(encoding="utf-8"))
        items = obj.get("items") or []
        total_records += len(items)
        category = meta.get("category") or "otros"
        assigned_barrio = 0
        assigned_comuna = 0
        spatial_used = 0
        conflicts_fixed = 0

        for item in items:
            source_cid = comuna_id(item.get("comuna"))
            source_bkey = barrio_slug(item.get("barrio"), barrios) if item.get("barrio") else None
            cid = source_cid
            bkey = source_bkey

            # Coordenadas + limites oficiales tienen prioridad. Esto corrige tanto
            # ausencias como contradicciones barrio/comuna presentes en la fuente.
            loc = SPATIAL.locate(item.get("coord"), spatial_index) if item.get("coord") else None
            if loc:
                loc_cid, loc_barrio = loc
                loc_cid = str(int(loc_cid))
                loc_bkey = barrio_slug(loc_barrio, barrios)
                if loc_bkey:
                    if source_cid != loc_cid or (source_bkey and source_bkey != loc_bkey):
                        conflicts_fixed += 1
                    cid = loc_cid
                    bkey = loc_bkey
                    spatial_used += 1
            elif bkey:
                # Sin coordenada util, un barrio canonico determina una unica comuna.
                canonical_cid = str(int(barrios[bkey].get("comuna") or 0))
                if canonical_cid in comunas:
                    if source_cid and source_cid != canonical_cid:
                        conflicts_fixed += 1
                    cid = canonical_cid

            if cid in comunas:
                add_count(comunas[cid], lid, category)
                assigned_comuna += 1
            if bkey:
                add_count(barrios[bkey], lid, category)
                assigned_barrio += 1

        unmapped[lid] = {
            "total": len(items),
            "sin_comuna": len(items) - assigned_comuna,
            "sin_barrio": len(items) - assigned_barrio,
        }
        adjustments[lid] = {
            "territorializados_por_coordenadas": spatial_used,
            "conflictos_fuente_corregidos": conflicts_fixed,
        }
        last = meta.get("source_last_modified")
        layer_meta[lid] = {
            "label": meta.get("label") or lid,
            "category": category,
            "total": len(items),
            "source_last_modified": last,
            "source_url": meta.get("source_url"),
            "historico": lid in {"rampas-accesibilidad-2016", "atencion-veterinaria"},
        }

    for cid, scope in comunas.items():
        finish_scope(scope, comunas_t.get(cid))
    for key, scope in barrios.items():
        finish_scope(scope, barrios_t.get(key))

    out = {
        "version": 1,
        "generado": datetime.date.today().isoformat(),
        "fuente": "Fuentes oficiales primarias procesadas por CEPOES",
        "catalogo_generado": catalog.get("generado"),
        "total_capas": len(catalog.get("layers") or []),
        "total_registros": total_records,
        "featured": FEATURED,
        "layers": layer_meta,
        "comunas": comunas,
        "barrios": barrios,
        "control": {
            "no_territorializados": unmapped,
            "ajustes_territoriales": adjustments,
            "criterio": "Coordenadas con limites oficiales > barrio canonico > comuna informada",
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    corrected = sum(x["conflictos_fuente_corregidos"] for x in adjustments.values())
    print(f"resumen-territorial.json · {OUT.stat().st_size//1024} KB · {len(comunas)} comunas · {len(barrios)} barrios · {len(layer_meta)} capas")
    print(f"  · inconsistencias barrio/comuna corregidas con criterio territorial: {corrected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())