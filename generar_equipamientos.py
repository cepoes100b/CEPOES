"""Genera archivos compactos de equipamientos territoriales para CEPOES.

Usa exactamente las mismas copias oficiales descargadas por el pipeline de
Territorio, pero conserva el detalle registro por registro para que la web pueda
mostrar listados de escuelas, efectores de salud y espacios verdes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import generar_territorio_runner as R

G = R.G
BASE = Path(__file__).resolve().parent
DIR = BASE / "badata"
OUT = BASE / "equipamientos"
OUT.mkdir(exist_ok=True)


def compact(v):
    s = G.clean_text(v)
    return s if s and s.lower() not in {"nan", "none"} else ""


def point_from_wkt(v):
    s = compact(v)
    m = re.search(r"POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)", s, re.I)
    if not m:
        return None
    x, y = float(m.group(1)), float(m.group(2))
    if -180 <= x <= 180 and -90 <= y <= 90:
        return [x, y]
    return None


def centroid_from_geometry(v):
    s = compact(v)
    if not s:
        return None
    pts = re.findall(r"(-?5\d\.\d+)\s+(-?3\d\.\d+)", s)
    if not pts:
        return None
    xy = [(float(x), float(y)) for x, y in pts]
    return [round(sum(x for x, _ in xy) / len(xy), 6), round(sum(y for _, y in xy) / len(xy), 6)]


def barrio(v, official):
    return G.canonical_barrio(v, official)


def commune_and_barrio(row, official, c_names=("comuna",), b_names=("barrio",)):
    c = G.parse_comuna(G.pick(row, *c_names))
    b = barrio(G.pick(row, *b_names), official)
    return c, b


def write(name, items, fuente):
    obj = {
        "version": 1,
        "generado": __import__("datetime").date.today().isoformat(),
        "fuente": fuente,
        "total": len(items),
        "items": items,
    }
    p = OUT / name
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  ✔ {name}: {len(items)} registros · {p.stat().st_size//1024} KB")
    return p


def main() -> int:
    datos = json.loads((BASE / "datos.json").read_text(encoding="utf-8"))
    _, _, official = G.base_output(datos)

    edu = []
    rows = G.read_csv(DIR / "establecimientos_educativos.csv")
    seen = set()
    for r in rows:
        estado = G.norm(G.pick(r, "estado", "estado_est", "estado_est_desc", "estado_loc_desc"))
        if estado in {"2", "3", "4"} or "inactiv" in estado or "baja" in estado:
            continue
        ident = compact(G.pick(r, "cueanexo", "cue", "cui", "OBJECTID"))
        c, b = commune_and_barrio(r, official)
        if not ident:
            ident = f"{c}|{b}|{compact(G.pick(r,'nombre_est','nombre_loc'))}"
        key = (ident, c, G.norm(b))
        if key in seen:
            continue
        seen.add(key)
        calle = compact(G.pick(r, "calle"))
        altura = compact(G.pick(r, "num", "altura"))
        direccion = " ".join(x for x in (calle, altura.removesuffix('.0')) if x)
        edu.append({
            "id": ident,
            "nombre": compact(G.pick(r, "nombre_est", "nombre_loc")),
            "sede": compact(G.pick(r, "nombre_loc")),
            "comuna": c,
            "barrio": b,
            "direccion": direccion,
            "sector": compact(G.pick(r, "sector_desc", "sector")),
            "tipo": compact(G.pick(r, "d_tipest", "tipest")),
            "oferta": compact(G.pick(r, "Oferta_CABA", "oferta_caba")),
            "distrito_escolar": compact(G.pick(r, "de")),
            "email": compact(G.pick(r, "email")),
            "cue": compact(G.pick(r, "cue")),
        })
    edu.sort(key=lambda x: (x.get("comuna") or 99, G.norm(x.get("barrio")), G.norm(x.get("nombre"))))

    salud = []
    seen = set()
    for r in G.read_xlsx(DIR / "hospitales.xlsx"):
        name = compact(G.pick(r, "fna", "NOMBRE", "nombre", "gna"))
        if not name or ("hospital", G.norm(name)) in seen:
            continue
        seen.add(("hospital", G.norm(name)))
        c, b = commune_and_barrio(r, official, ("com", "COMUNA", "comuna"), ("bar", "BARRIO", "barrio"))
        tel = compact(G.pick(r, "tel", "TELEFONO", "telefono"))
        guardia = compact(G.pick(r, "guardia", "GUARDIA"))
        if not guardia and "|" in tel:
            tel, guardia = [x.strip() for x in tel.split("|", 1)]
        salud.append({
            "id": "hospital-" + G.slug(name),
            "tipo": "Hospital",
            "nombre": name,
            "comuna": c,
            "barrio": b,
            "direccion": compact(G.pick(r, "dir", "DOM_NORMA", "direccion")),
            "especialidad": compact(G.pick(r, "esp", "TIPO_ESPEC")),
            "atencion": compact(G.pick(r, "ate", "MOD_AT_1")),
            "telefono": tel,
            "guardia": guardia,
            "web": compact(G.pick(r, "web", "WEB")),
            "dependencia": compact(G.pick(r, "sag", "DEPEND_ADM")),
            "coord": point_from_wkt(G.pick(r, "geometry", "WKT")),
        })
    for r in G.read_csv(DIR / "cesac.csv"):
        ident = compact(G.pick(r, "id"))
        name = compact(G.pick(r, "nombre"))
        if not ident or not name or ("cesac", ident) in seen:
            continue
        seen.add(("cesac", ident))
        c, b = commune_and_barrio(r, official)
        salud.append({
            "id": "cesac-" + ident,
            "tipo": "CeSAC",
            "nombre": name,
            "comuna": c,
            "barrio": b,
            "direccion": compact(G.pick(r, "direccion")),
            "telefono": compact(G.pick(r, "telefono")),
            "web": compact(G.pick(r, "web")),
            "area_programatica": compact(G.pick(r, "area_progr")),
            "especialidades": compact(G.pick(r, "especialid", "especialidad")),
            "coord": point_from_wkt(G.pick(r, "geometry")),
        })
    salud.sort(key=lambda x: (x.get("comuna") or 99, G.norm(x.get("barrio")), x.get("tipo"), G.norm(x.get("nombre"))))

    espacios = []
    seen = set()
    for r in G.read_xlsx(DIR / "espacios_verdes_publicos.xlsx"):
        ident = compact(G.pick(r, "id", "id_ev_pub", "nombre", "nombre_ev"))
        if not ident or ident in seen:
            continue
        seen.add(ident)
        c, b = commune_and_barrio(r, official, ("comuna", "COMUNA"), ("barrio", "BARRIO"))
        area = G.num(G.pick(r, "area", "SUP_TOTAL", "sup_total")) or 0.0
        espacios.append({
            "id": ident,
            "nombre": compact(G.pick(r, "nombre", "nombre_ev", "nom_mapa")),
            "comuna": c,
            "barrio": b,
            "ubicacion": compact(G.pick(r, "ubicacion")),
            "clasificacion": compact(G.pick(r, "clasificac", "clasificacion")),
            "superficie_m2": round(area, 1),
            "patio_juegos": compact(G.pick(r, "tiene_pati", "patio_de_j")),
            "canil": compact(G.pick(r, "Canil", "canil")),
            "posta_aerobica": compact(G.pick(r, "Posta_aero", "posta_aero")),
            "observaciones": compact(G.pick(r, "observacio", "observaciones")),
            "coord": centroid_from_geometry(G.pick(r, "geometry", "WKT")),
        })
    espacios.sort(key=lambda x: (x.get("comuna") or 99, G.norm(x.get("barrio")), G.norm(x.get("nombre"))))

    write("educacion.json", edu, "BA Data (GCBA) · Padrón de Establecimientos Educativos")
    write("salud.json", salud, "BA Data (GCBA) · Hospitales y Centros de Salud y Acción Comunitaria")
    write("espacios-verdes.json", espacios, "BA Data (GCBA) · Espacios Verdes Públicos")
    manifest = {
        "version": 1,
        "generado": __import__("datetime").date.today().isoformat(),
        "archivos": {
            "educacion": {"url": "equipamientos/educacion.json", "total": len(edu)},
            "salud": {"url": "equipamientos/salud.json", "total": len(salud)},
            "espacios-verdes": {"url": "equipamientos/espacios-verdes.json", "total": len(espacios)},
        },
    }
    (OUT / "index.json").write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
