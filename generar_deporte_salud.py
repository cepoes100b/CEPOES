#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
EQUIP = BASE / "equipamientos"
TERR = BASE / "territorio.json"
OUT = BASE / "deploy" / "site-overlay" / "assets" / "data" / "deporte-salud.json"

LAYERS = {
    "clubes": EQUIP / "clubes.json",
    "polideportivos": EQUIP / "polideportivos.json",
    "programas": EQUIP / "programas-deportivos.json",
    "estaciones": EQUIP / "estaciones-saludables.json",
    "salud": EQUIP / "salud.json",
}


def load(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Falta {path.relative_to(BASE)}")
    return json.loads(path.read_text(encoding="utf-8"))


def norm(value: object) -> str:
    txt = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", txt.lower()).strip()


def valid_coord(coord: object) -> list[float] | None:
    if not isinstance(coord, (list, tuple)) or len(coord) != 2:
        return None
    try:
        lon, lat = float(coord[0]), float(coord[1])
    except (TypeError, ValueError):
        return None
    if -58.7 <= lon <= -58.2 and -34.85 <= lat <= -34.45:
        return [round(lon, 6), round(lat, 6)]
    return None


def comuna(value: object) -> int | None:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if 1 <= n <= 15 else None


def split_terms(value: object) -> list[str]:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" -")
    if not text:
        return []
    return [x.strip() for x in re.split(r"\s+-\s+", text) if x.strip()]


def club_key(item: dict) -> str:
    raw = str(item.get("id") or "")
    m = re.fullmatch(r"(clubes-\d+)(?:-\d+)?", raw)
    if m:
        return m.group(1)
    return "club:" + norm(item.get("nombre")) + ":" + norm(item.get("telefono"))


def public_item(item: dict, layer: str, *, coord_override: list[float] | None = None, coord_note: str | None = None) -> dict:
    result = {
        "id": str(item.get("id") or ""),
        "capa": layer,
        "nombre": str(item.get("nombre") or "").strip(),
        "comuna": comuna(item.get("comuna")),
        "barrio": str(item.get("barrio") or "").strip(),
        "direccion": str(item.get("direccion") or "").strip(),
        "tipo": str(item.get("tipo") or "").strip(),
        "actividades": split_terms(item.get("detalle")),
        "instalaciones": split_terms(item.get("detalle2")) if layer == "clubes" else [],
        "horario": str(item.get("horario") or "").strip(),
        "telefono": str(item.get("telefono") or "").strip(),
        "web": str(item.get("web") or "").strip(),
        "coord": coord_override or valid_coord(item.get("coord")),
    }
    if layer == "programas":
        result["sede"] = str(item.get("detalle2") or "").strip()
    if coord_note:
        result["coord_nota"] = coord_note
    return result


def rate(value: int, pop: int) -> float | None:
    return round(value / pop * 10000, 2) if pop > 0 else None


def source_meta(obj: dict, key: str) -> dict:
    layer = obj.get("layer") or {}
    return {
        "id": key,
        "nombre": obj.get("fuente") or layer.get("label") or key,
        "url": layer.get("source_url"),
        "recurso": layer.get("source_resource_id"),
        "recurso_modificado": layer.get("source_last_modified"),
        "generado_cepoes": obj.get("generado"),
        "registros": int(obj.get("total") or len(obj.get("items") or [])),
    }


def main() -> int:
    territory = load(TERR)
    clubes = load(LAYERS["clubes"])
    polis = load(LAYERS["polideportivos"])
    programas = load(LAYERS["programas"])
    estaciones = load(LAYERS["estaciones"])
    salud = load(LAYERS["salud"])

    club_items = clubes.get("items") or []
    poli_items = polis.get("items") or []
    prog_items = programas.get("items") or []
    est_items = estaciones.get("items") or []
    cesac_items = [x for x in (salud.get("items") or []) if norm(x.get("tipo")) == "cesac"]

    unique_clubs: dict[str, dict] = {}
    for item in club_items:
        unique_clubs.setdefault(club_key(item), item)

    # El CSV de polideportivos hoy llega sin coordenadas. Para no inventarlas,
    # se reutiliza solo cuando hay coincidencia nominal inequívoca con una sede
    # del dataset georreferenciado de Programas Deportivos. La coordenada sirve
    # para ubicar infraestructura, no para afirmar vigencia del programa.
    prog_by_site: dict[str, list[list[float]]] = defaultdict(list)
    for item in prog_items:
        c = valid_coord(item.get("coord"))
        site = norm(item.get("detalle2"))
        if c and site:
            prog_by_site[site].append(c)

    public_polis = []
    for item in poli_items:
        c = valid_coord(item.get("coord"))
        note = None
        if not c:
            target = norm(item.get("nombre"))
            candidates: list[list[float]] = []
            for site, coords in prog_by_site.items():
                if target and (target in site or site in target):
                    candidates.extend(coords)
            if candidates:
                lon = sorted(x[0] for x in candidates)[len(candidates)//2]
                lat = sorted(x[1] for x in candidates)[len(candidates)//2]
                c = [lon, lat]
                note = "Referencia geográfica derivada de la sede homónima en Programas Deportivos"
        public_polis.append(public_item(item, "polideportivos", coord_override=c, coord_note=note))

    public_clubs = []
    for item in club_items:
        x = public_item(item, "clubes")
        x["institucion_id"] = club_key(item)
        public_clubs.append(x)

    public_est = [public_item(x, "estaciones") for x in est_items]
    public_prog = [public_item(x, "programas") for x in prog_items]
    public_cesac = []
    for x in cesac_items:
        public_cesac.append({
            "id": str(x.get("id") or ""), "capa": "cesac", "nombre": str(x.get("nombre") or "").strip(),
            "comuna": comuna(x.get("comuna")), "barrio": str(x.get("barrio") or "").strip(),
            "direccion": str(x.get("direccion") or "").strip(), "tipo": "CeSAC",
            "actividades": [], "instalaciones": [], "horario": "", "telefono": str(x.get("telefono") or "").strip(),
            "web": str(x.get("web") or "").strip(), "coord": valid_coord(x.get("coord")),
        })

    club_activity = Counter()
    program_activity = Counter()
    for item in public_clubs:
        for term in item["actividades"]:
            club_activity[term] += 1
    for item in public_prog:
        for term in item["actividades"]:
            program_activity[term] += 1

    by_comuna = {}
    for cid in range(1, 16):
        pop = int((territory.get("comunas") or {}).get(str(cid), {}).get("poblacion") or 0)
        sites = [x for x in public_clubs if x["comuna"] == cid]
        unique = {x["institucion_id"] for x in sites}
        p = [x for x in public_polis if x["comuna"] == cid]
        e = [x for x in public_est if x["comuna"] == cid]
        c = [x for x in public_cesac if x["comuna"] == cid]
        pr = [x for x in public_prog if x["comuna"] == cid]
        by_comuna[str(cid)] = {
            "poblacion": pop,
            "clubes": len(unique),
            "sedes_clubes": len(sites),
            "polideportivos": len(p),
            "estaciones_saludables": len(e),
            "cesac": len(c),
            "programas_registros": len(pr),
            "tasas_10k": {
                "clubes": rate(len(unique), pop),
                "sedes_clubes": rate(len(sites), pop),
                "polideportivos": rate(len(p), pop),
                "estaciones_saludables": rate(len(e), pop),
                "cesac": rate(len(c), pop),
            },
        }

    prog_last = (programas.get("layer") or {}).get("source_last_modified")
    stale_programs = bool(prog_last and str(prog_last)[:4].isdigit() and int(str(prog_last)[:4]) < dt.date.today().year - 1)

    out = {
        "version": 1,
        "generado": dt.date.today().isoformat(),
        "titulo": "Deporte y vida saludable en CABA",
        "metodologia": {
            "poblacion_base": "Censo 2022 · población en viviendas particulares",
            "unidad_tasas": "registros o instituciones cada 10.000 habitantes",
            "criterio_clubes": "Los puntos representan sedes; el indicador de clubes deduplica anexos/sedes de una misma institución por identificador de origen.",
            "criterio_salud": "CeSAC y Estaciones Saludables se muestran como contexto de atención primaria y promoción de hábitos saludables; no se infieren efectos causales sobre salud.",
            "criterio_programas": "Los programas son oferta/actividad y no infraestructura. Su fecha de recurso se expone por separado y no se presume vigencia cuando está desactualizada.",
        },
        "alertas": {
            "programas_desactualizados": stale_programs,
            "programas_recurso_modificado": prog_last,
            "programas_mensaje": "El dataset oficial figura con metadata actualizada, pero el recurso incorporado al pipeline conserva una fecha anterior; se presenta como referencia y no como agenda vigente." if stale_programs else "Recurso compatible con seguimiento vigente; verificar horarios antes de asistir.",
        },
        "resumen": {
            "clubes": len(unique_clubs),
            "sedes_clubes": len(public_clubs),
            "polideportivos": len(public_polis),
            "polideportivos_geolocalizados": sum(1 for x in public_polis if x["coord"]),
            "estaciones_saludables": len(public_est),
            "cesac": len(public_cesac),
            "programas_registros": len(public_prog),
        },
        "fuentes": [
            source_meta(clubes, "clubes"), source_meta(polis, "polideportivos"), source_meta(estaciones, "estaciones-saludables"),
            source_meta(programas, "programas-deportivos"),
            {"id": "salud", "nombre": salud.get("fuente"), "url": "https://data.buenosaires.gob.ar/", "generado_cepoes": salud.get("generado"), "registros": len(salud.get("items") or [])},
            {"id": "poblacion", "nombre": "INDEC · Censo 2022 / territorialización CEPOES", "url": "https://www.indec.gob.ar/", "generado_cepoes": territory.get("generado")},
        ],
        "comunas": by_comuna,
        "actividades": [
            {"nombre": name, "sedes_clubes": club_activity.get(name, 0), "programas_registros": program_activity.get(name, 0)}
            for name in sorted(set(club_activity) | set(program_activity), key=lambda n: (-club_activity.get(n, 0), -program_activity.get(n, 0), n))
        ],
        "capas": {
            "clubes": {"label": "Clubes y sedes", "estado": "actualizable", "items": public_clubs},
            "polideportivos": {"label": "Polideportivos", "estado": "actualizable", "items": public_polis},
            "estaciones": {"label": "Estaciones Saludables", "estado": "actualizable", "items": public_est},
            "cesac": {"label": "CeSAC", "estado": "actualizable", "items": public_cesac},
            "programas": {"label": "Programas deportivos", "estado": "referencia" if stale_programs else "actualizable", "items": public_prog},
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"deporte-salud.json · {OUT.stat().st_size//1024} KB · {len(unique_clubs)} clubes / {len(public_clubs)} sedes · "
        f"{len(public_polis)} polideportivos · {len(public_est)} estaciones · {len(public_cesac)} CeSAC"
    )
    if stale_programs:
        print(f"  · programas deportivos: referencia con fecha de recurso {prog_last}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
