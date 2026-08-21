"""Genera capas ampliadas de Oferta territorial desde fuentes oficiales BA Data.

No reemplaza los tres listados históricos (educación, salud y espacios verdes):
los incorpora a un catálogo común y agrega nuevas capas normalizadas para que la
web pueda explorarlas con el mismo listado, filtros y ordenamiento.
"""
from __future__ import annotations

import datetime
import json
import math
import re
from pathlib import Path

import generar_territorio_runner as R
from fuentes_territorio import BA_DATA_BASE, DATASETS_TERRITORIO

G = R.G
BASE = Path(__file__).resolve().parent
DIR = BASE / "badata"
OUT = BASE / "equipamientos"
OUT.mkdir(exist_ok=True)
DATOS = BASE / "datos.json"
STATE = BASE / "estado_territorio.json"

CATEGORIES = [
    ("educacion", "Educación"),
    ("salud", "Salud y bienestar"),
    ("cultura", "Cultura y comunidad"),
    ("deporte", "Deporte"),
    ("cuidados", "Cuidados y desarrollo social"),
    ("seguridad", "Seguridad y emergencias"),
    ("movilidad", "Movilidad"),
    ("ambiente", "Ambiente y espacio público"),
    ("abastecimiento", "Abastecimiento"),
    ("gestion", "Gestión pública y trabajo"),
]

# Los tres primeros archivos ya son producidos por generar_equipamientos_runner.py.
CORE_LAYERS = [
    {"id":"educacion","label":"Establecimientos educativos","category":"educacion","file":"educacion.json","description":"Padrón de establecimientos educativos activos.","filter_label":"Gestión","filter_field":"sector"},
    {"id":"salud","label":"Hospitales y CeSAC","category":"salud","file":"salud.json","description":"Hospitales públicos y Centros de Salud y Acción Comunitaria.","filter_label":"Tipo","filter_field":"tipo"},
    {"id":"espacios-verdes","label":"Espacios verdes","category":"ambiente","file":"espacios-verdes.json","description":"Parques, plazas, plazoletas y otros espacios verdes públicos.","filter_label":"Tipo","filter_field":"clasificacion"},
]

# Configuración de normalización de nuevas capas. Cada entrada refiere a una clave
# de DATASETS_TERRITORIO. Los alias se resuelven sin distinguir mayúsculas ni tildes.
LAYERS = [
    {"id":"centros-medicos-barriales","source":"centros_medicos_barriales","label":"Centros Médicos Barriales","category":"salud","type":"Centro Médico Barrial","name":["nombre"],"address":["direccion"],"phone":["telefono"],"web":["web"],"detail":["esp"],"detail2":["area_progr"],"geometry":["geometry"],"description":"Centros médicos barriales del sistema de salud de la Ciudad."},
    {"id":"salud-privada","source":"salud_privada","label":"Centros de salud privados","category":"salud","type":"Centro privado","name":["nombre","fna","nam"],"address":["direccion","dir","dom_norma"],"phone":["telefono","tel"],"web":["web"],"detail":["tipo","tip","gna"],"geometry":["geometry"],"description":"Hospitales, sanatorios y clínicas privadas registrados en la Ciudad."},
    {"id":"estaciones-saludables","source":"estaciones_saludables","label":"Estaciones Saludables","category":"salud","type":["tipo","estructura"],"name":["nombre"],"address":["direccion","ubicacion"],"schedule":["horario","horarios","dias_horarios"],"detail":["servicio","servicios"],"geometry":["geometry"],"description":"Puntos de prevención y promoción de hábitos saludables."},

    {"id":"bibliotecas","source":"bibliotecas","label":"Bibliotecas","category":"cultura","type":["tip","tipo","gna"],"name":["fna","nombre","nam"],"address":["dir","direccion"],"phone":["tel","telefono"],"email":["ema","email"],"web":["web"],"detail":["sag","dependencia"],"geometry":["geometry"],"description":"Bibliotecas de la Red del Gobierno de la Ciudad."},
    {"id":"espacios-culturales","source":"espacios_culturales","label":"Espacios culturales","category":"cultura","type":["tipo","tip","gna"],"name":["nombre","fna","nam"],"address":["direccion","dir"],"phone":["telefono","tel"],"email":["email","ema"],"web":["web"],"detail":["actividad","actividade","subtipo"],"geometry":["geometry"],"description":"Espacios culturales públicos, privados e independientes."},
    {"id":"instituciones-colectividades","source":"instituciones_colectividades","label":"Instituciones de colectividades","category":"cultura","type":["tipo"],"name":["nombre","institucion"],"address":["direccion","domicilio"],"phone":["telefono"],"email":["email"],"web":["web"],"detail":["colectividad"],"geometry":["geometry"],"description":"Instituciones pertenecientes a colectividades de la Ciudad."},

    {"id":"polideportivos","source":"polideportivos","label":"Polideportivos","category":"deporte","type":"Polideportivo","name":["nombre","fna","nam"],"address":["direccion","dir"],"phone":["telefono","tel"],"schedule":["horario"],"web":["web"],"detail":["actividades","actividad"],"geometry":["geometry"],"description":"Polideportivos dependientes de la Subsecretaría de Deportes."},
    {"id":"programas-deportivos","source":"programas_deportivos","label":"Programas deportivos","category":"deporte","type":["actividad","tipo"],"name":["programa","nombre"],"address":["ubicacion","direccion"],"schedule":["horario"],"web":["web","instagram","facebook"],"detail":["actividad"],"detail2":["sede"],"geometry":["geometry"],"description":"Programas deportivos, actividades, sedes y horarios."},
    {"id":"clubes","source":"clubes","label":"Clubes","category":"deporte","type":["tipo","tipo_sede"],"name":["nombre"],"address":["direccion"],"phone":["telefono"],"email":["email"],"web":["web"],"detail":["actividade","actividades"],"detail2":["instalacio","instalaciones"],"geometry":["geometry"],"description":"Clubes de barrio y otras instituciones deportivas."},
    {"id":"estadios","source":"estadios","label":"Estadios","category":"deporte","type":["gna","tipo"],"name":["fna","nam","nombre"],"address":["dir","direccion"],"phone":["tel","telefono"],"email":["email"],"web":["web"],"detail":["aso","sag"],"geometry":["geometry"],"description":"Estadios de la Ciudad con ubicación e información de contacto."},

    {"id":"centros-primera-infancia","source":"cpi","label":"Centros de Primera Infancia","category":"cuidados","type":"Centro de Primera Infancia","name":["nombre"],"address":["direccion"],"phone":["telefono"],"email":["email"],"schedule":["horario"],"detail":["destinatar","destinatarios"],"detail2":["obs_dir","observaciones"],"geometry":["geometry"],"description":"Centros destinados a la primera infancia y sus familias."},
    {"id":"centros-accion-familiar","source":"caf","label":"Centros de Acción Familiar","category":"cuidados","type":["tipo","tipo_estab"],"name":["nombre"],"address":["direccion"],"phone":["telefono"],"email":["email"],"web":["web"],"detail":["organismo","responsable"],"geometry":["geometry"],"description":"Centros de acompañamiento integral para niñas, niños, adolescentes y familias."},
    {"id":"casas-nnya","source":"casas_nnya","label":"Casas de Niñas, Niños y Adolescentes","category":"cuidados","type":"Casa NNyA","name":["nombre"],"address":["direccion"],"phone":["telefono"],"email":["email"],"schedule":["horario"],"detail":["destinatar","destinatarios"],"geometry":["geometry"],"description":"Casas de atención, contención y desarrollo integral para niñas, niños y adolescentes."},
    {"id":"hogares-paradores","source":"hogares_paradores","label":"Hogares y paradores","category":"cuidados","type":["tipo"],"name":["nombre"],"address":["direccion"],"phone":["telefono"],"detail":["destinatar","destinatario"],"detail2":["observacio","observaciones"],"geometry":["geometry"],"description":"Hogares de tránsito, paradores y dispositivos de alojamiento social."},

    {"id":"comisarias","source":"comisarias","label":"Comisarías","category":"seguridad","type":["tipo","gna"],"name":["nombre","fna","nam"],"address":["direccion","calle"],"phone":["telefonos","telefono","tel"],"detail":["observaciones","observacio"],"geometry":["geometry"],"description":"Comisarías de la Policía de la Ciudad."},
    {"id":"bomberos","source":"bomberos","label":"Bomberos","category":"seguridad","type":["tipo","gna"],"name":["nombre","fna","nam"],"address":["direccion","dir"],"phone":["telefono","tel"],"web":["web"],"detail":["dependencia","sag"],"geometry":["geometry"],"description":"Cuarteles y destacamentos de Bomberos de la Ciudad."},

    {"id":"subte-bocas","source":"subte_bocas","label":"Subte · accesos","category":"movilidad","type":["linea"],"name":["estacion"],"address":["dom_norma","direccion","calle"],"detail":["destino_bo","destino"],"detail2":["lineas_de_","lineas"],"geometry":["geometry"],"extras":["ascensor","rampa","escalera_m","escalera_p","salvaescal","cierra_fin"],"description":"Bocas de acceso y salida de estaciones de Subte, con datos de accesibilidad."},
    {"id":"ecobici","source":"ecobici","label":"Estaciones Ecobici","category":"movilidad","type":["emplazamie","emplazamiento"],"name":["nombre","name"],"address":["direccion","address"],"detail":["nro_estacio","numero_de_","station"],"lat":["lat","latitud"],"lon":["long","lon","longitud"],"description":"Estaciones del sistema de bicicletas públicas."},
    {"id":"ferrocarril","source":"ferrocarril","label":"Estaciones de ferrocarril","category":"movilidad","type":["linea"],"name":["nombre"],"address":["direccion"],"detail":["ramal"],"lat":["lat"],"lon":["long","lon"],"description":"Estaciones ferroviarias localizadas en la Ciudad."},
    {"id":"paradas-taxis","source":"taxis","label":"Paradas de taxis","category":"movilidad","type":"Parada de taxi","name":["nombre","id"],"address":["dirreccion","direccion"],"detail":["cantidad","vehiculos"],"geometry":["geometry"],"description":"Paradas de taxis habilitadas en la Ciudad."},
    {"id":"bicicleteros","source":"bicicleteros","label":"Bicicleteros en vía pública","category":"movilidad","type":"Bicicletero","name":["nombre","id"],"address":["direccion","ubicacion"],"detail":["capacidad","cantidad"],"geometry":["geometry"],"description":"Bicicleteros instalados en la vía pública."},

    {"id":"puntos-verdes","source":"puntos_verdes","label":"Puntos Verdes","category":"ambiente","type":["tipo"],"name":["nombre"],"address":["direccion","ubicacion"],"schedule":["horario"],"detail":["materiales","residuos"],"geometry":["geometry"],"description":"Puntos de recepción de materiales reciclables y residuos especiales."},

    {"id":"fiab","source":"fiab","label":"Ferias Itinerantes de Abastecimiento Barrial","category":"abastecimiento","type":"FIAB","name":["nombre"],"address":["direccion","ubicacion"],"schedule":["horario"],"detail":["productos"],"detail2":["dia"],"geometry":["geometry"],"description":"Ferias Itinerantes de Abastecimiento Barrial, días, horarios y productos."},
    {"id":"mercados","source":"mercados","label":"Mercados","category":"abastecimiento","type":["tipo"],"name":["nombre"],"address":["direccion","ubicacion"],"phone":["telefono"],"schedule":["horario"],"detail":["productos","rubro"],"geometry":["geometry"],"description":"Mercados fijos de la Ciudad."},

    {"id":"sedes-comunales","source":"sedes_comunales","label":"Sedes Comunales","category":"gestion","type":["gna","tipo"],"name":["fna","nam","nombre"],"address":["dir","direccion"],"phone":["tel","telefono"],"web":["web"],"detail":["sag","dependencia"],"geometry":["geometry"],"description":"Sedes de atención de las Comunas."},
    {"id":"centros-integracion-laboral","source":"centros_integracion_laboral","label":"Centros de Integración Laboral","category":"gestion","type":"Centro de Integración Laboral","name":["nombre"],"address":["direccion"],"phone":["telefono"],"schedule":["horario"],"web":["web"],"detail":["servicios","atencion"],"geometry":["geometry"],"description":"Centros de orientación y acompañamiento para el empleo."},
]


def compact(v):
    s = G.clean_text(v)
    return s if s and s.lower() not in {"nan", "none", "null", "s/d"} else ""


def pick(row, names):
    if not names:
        return ""
    if isinstance(names, str):
        return names
    return compact(G.pick(row, *names))


def parse_point(v):
    s = compact(v)
    if not s:
        return None
    m = re.search(r"POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)", s, re.I)
    if m:
        x, y = float(m.group(1)), float(m.group(2))
        if -75 <= x <= -50 and -40 <= y <= -30:
            return [round(x, 6), round(y, 6)]
    # GeoJSON serializado dentro de una celda.
    try:
        o = json.loads(s)
        if isinstance(o, dict) and o.get("type") == "Point" and len(o.get("coordinates") or []) >= 2:
            x, y = map(float, o["coordinates"][:2])
            if -75 <= x <= -50 and -40 <= y <= -30:
                return [round(x, 6), round(y, 6)]
    except Exception:
        pass
    return None


def number_coord(v, axis):
    n = G.num(v)
    if n is None:
        return None
    # Algunos CSV históricos publican -3459xx / -5837xx sin separador decimal.
    while abs(n) > (90 if axis == "lat" else 180):
        n /= 10.0
    if axis == "lat" and -40 <= n <= -30:
        return n
    if axis == "lon" and -75 <= n <= -50:
        return n
    return None


def read_source(source):
    cfg = DATASETS_TERRITORIO[source]
    p = DIR / cfg["filename"]
    if not p.exists():
        raise FileNotFoundError(p.name)
    return G.read_xlsx(p) if p.suffix.lower() == ".xlsx" else G.read_csv(p)


def official_territory():
    datos = json.loads(DATOS.read_text(encoding="utf-8"))
    _, _, official = G.base_output(datos)
    barrio_comuna = {}
    for cid, c in datos["censo"]["comunas"].items():
        for b in c.get("barrios", {}):
            canon = G.BARRIO_ALIASES.get(G.norm(b), b)
            barrio_comuna[G.norm(canon)] = int(cid)
    return official, barrio_comuna


def infer_scope(row, cfg, official, barrio_comuna):
    c = G.parse_comuna(G.pick(row, "comuna", "com", "commune", "nro_comuna"))
    b = G.canonical_barrio(G.pick(row, "barrio", "bar", "barrio_nombre"), official)
    if b and not c:
        c = barrio_comuna.get(G.norm(b))
    return c, b


def make_id(layer_id, row, name, address, i):
    raw = compact(G.pick(row, "id", "objectid", "object_id", "codigo", "código", "cue", "nro_estacio", "numero"))
    if raw:
        return f"{layer_id}-{G.slug(raw)}"
    base = "-".join(x for x in (name, address) if x)
    return f"{layer_id}-{G.slug(base) or i}"


def normalized_item(row, cfg, official, barrio_comuna, i):
    c, b = infer_scope(row, cfg, official, barrio_comuna)
    name = pick(row, cfg.get("name"))
    address = pick(row, cfg.get("address"))
    typ = pick(row, cfg.get("type"))
    if isinstance(cfg.get("type"), str):
        typ = cfg["type"]
    if not name:
        # Etiquetas descriptivas explícitas: nunca se presentan como nombre oficial.
        name = f"{typ or cfg['label']} sin denominación"
        unnamed = True
    else:
        unnamed = False
    coord = None
    for field in cfg.get("geometry") or []:
        coord = parse_point(G.pick(row, field))
        if coord:
            break
    if not coord and (cfg.get("lat") or cfg.get("lon")):
        lat = number_coord(G.pick(row, *(cfg.get("lat") or [])), "lat")
        lon = number_coord(G.pick(row, *(cfg.get("lon") or [])), "lon")
        if lat is not None and lon is not None:
            coord = [round(lon, 6), round(lat, 6)]
    extras = {}
    for field in cfg.get("extras") or []:
        v = compact(G.pick(row, field))
        if v:
            extras[field] = v
    return {
        "id": make_id(cfg["id"], row, name, address, i),
        "nombre": name,
        "sin_denominacion": unnamed,
        "comuna": c,
        "barrio": b,
        "direccion": address,
        "tipo": typ,
        "detalle": pick(row, cfg.get("detail")),
        "detalle2": pick(row, cfg.get("detail2")),
        "telefono": pick(row, cfg.get("phone")),
        "email": pick(row, cfg.get("email")),
        "web": pick(row, cfg.get("web")),
        "horario": pick(row, cfg.get("schedule")),
        "coord": coord,
        "extras": extras,
    }


def write_layer(cfg, items, state):
    src = DATASETS_TERRITORIO[cfg["source"]]
    st = (state.get("datasets") or {}).get(cfg["source"], {})
    meta = {
        "id": cfg["id"],
        "label": cfg["label"],
        "category": cfg["category"],
        "description": cfg["description"],
        "filter_label": "Tipo",
        "filter_field": "tipo",
        "source_dataset": src["dataset"],
        "source_url": BA_DATA_BASE + src["dataset"],
        "source_resource_id": st.get("resource_id"),
        "source_last_modified": st.get("source_last_modified"),
    }
    obj = {
        "version": 2,
        "generado": datetime.date.today().isoformat(),
        "fuente": f"BA Data (GCBA) · {src['descripcion']}",
        "layer": meta,
        "total": len(items),
        "items": items,
    }
    p = OUT / f"{cfg['id']}.json"
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  ✔ {cfg['id']}: {len(items)} registros · {p.stat().st_size//1024} KB")
    return meta | {"file": p.name, "total": len(items)}


def main() -> int:
    official, barrio_comuna = official_territory()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"datasets": {}}
    errors = []
    generated = []
    for cfg in LAYERS:
        try:
            rows = read_source(cfg["source"])
            items, seen = [], set()
            for i, row in enumerate(rows, 1):
                item = normalized_item(row, cfg, official, barrio_comuna, i)
                # Dedupe conservador: mismo id y misma ubicación textual.
                key = (item["id"], G.norm(item.get("direccion")))
                if key in seen:
                    continue
                seen.add(key)
                items.append(item)
            items.sort(key=lambda x: (x.get("comuna") or 99, G.norm(x.get("barrio")), G.norm(x.get("nombre"))))
            generated.append(write_layer(cfg, items, state))
        except Exception as e:
            errors.append(f"{cfg['id']}: {type(e).__name__}: {e}")
            print("  ✘", errors[-1])

    # Incorporar las capas core al mismo catálogo sin duplicar sus archivos.
    catalog_layers = []
    for core in CORE_LAYERS:
        p = OUT / core["file"]
        total = 0
        if p.exists():
            try:
                total = len(json.loads(p.read_text(encoding="utf-8")).get("items") or [])
            except Exception:
                pass
        catalog_layers.append(core | {"total": total, "source_url": None})
    catalog_layers.extend(generated)

    cat_order = {k:i for i,(k,_) in enumerate(CATEGORIES)}
    catalog_layers.sort(key=lambda x: (cat_order.get(x["category"], 999), x["label"].lower()))
    catalog = {
        "version": 2,
        "generado": datetime.date.today().isoformat(),
        "fuente": "Fuentes oficiales del Gobierno de la Ciudad de Buenos Aires (BA Data)",
        "categories": [{"id": k, "label": v} for k,v in CATEGORIES],
        "layers": catalog_layers,
        "errores": errors,
    }
    (OUT / "catalogo.json").write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # index.json se mantiene como manifiesto liviano y retrocompatible.
    index = {
        "version": 2,
        "generado": catalog["generado"],
        "archivos": {x["id"]: {"url": f"equipamientos/{x['file']}", "total": x["total"]} for x in catalog_layers},
    }
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nOferta territorial: {len(catalog_layers)} capas · {sum(x['total'] for x in catalog_layers)} registros")
    if errors:
        print(f"  ~ {len(errors)} capa(s) con error; el verificador decidirá si se publica")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
