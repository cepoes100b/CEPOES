#!/usr/bin/env python3
"""Actualiza la estructura institucional pública de la Legislatura CABA.

Fuentes oficiales:
- páginas de las 27 comisiones permanentes de legislatura.gob.ar;
- página oficial del bloque Fuerza por Buenos Aires;
- Resolución 60/2026 como padrón normativo y cantidad de integrantes.

La salida no contiene análisis político ni información privada: sólo composición,
autoridades y metadatos institucionales públicos.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

OUT = Path("estructura_legislativa.json")
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
BASE = "https://www.legislatura.gob.ar"
BLOCK_URL = f"{BASE}/bloque/fuerzaporbuenosaires"
RESOLUTION_URL = "https://parlamentaria.legislatura.gob.ar/pages/download.aspx?IdDoc=223084"
UA = "cepoes-estructura-legislativa/1.0 (+https://github.com/cepoes100b/CEPOES)"

# Resolución 60/2026, arts. 1, 4 y 5. El slug sólo resuelve la URL oficial;
# composición y autoridades se leen de la web en cada ejecución.
COMMISSION_REGISTRY = [
    ("Asuntos Constitucionales", "asuntosconstitucionales", 15, True),
    ("Legislación General", "legislaciongeneral", 9, True),
    ("Legislación del Trabajo y Políticas de Empleo", "legislaciondeltrabajoypoliticasdeempleo", 9, True),
    ("Presupuesto, Hacienda, Administración Financiera y Política Tributaria", "presupuestohaciendaadministracionfinancieraypoliticatributaria", 23, True),
    ("Derechos Humanos, Garantías y Antidiscriminación", "derechoshumanosgarantiasyantidiscriminacion", 13, False),
    ("Justicia", "justicia", 13, False),
    ("Seguridad", "seguridad", 13, False),
    ("Salud", "salud", 15, True),
    ("Educación, Ciencia y Tecnología", "educacioncienciaytecnologia", 15, True),
    ("Cultura", "cultura", 13, False),
    ("Comunicación Social", "comunicacionsocial", 7, False),
    ("Políticas de Promoción e Integración Social", "politicasdepromocioneintegracionsocial", 11, False),
    ("Obras y Servicios Públicos", "obrasyserviciospublicos", 15, False),
    ("Planeamiento Urbano", "planeamientourbano", 15, False),
    ("Desarrollo Económico y Mercosur", "desarrolloeconomicoymercosur", 13, False),
    ("Descentralización y Participación Ciudadana", "descentralizacionyparticipacionciudadana", 13, False),
    ("Discapacidad", "discapacidad", 7, False),
    ("Mujeres, Géneros y Diversidades", "mujeresgenerosydiversidades", 13, False),
    ("Niñez, Adolescencia y Juventud", "ninezadolescenciayjuventud", 13, False),
    ("Defensa de los Consumidores y Usuarios", "defensadeconsumidoresyusuarios", 7, False),
    ("Asuntos Metropolitanos y Relaciones Interjurisdiccionales", "asuntosmetropolitanosyrelacionesinterjurisdiccionales", 9, False),
    ("Protección y Uso del Espacio Público", "proteccionyusodelespaciopublico", 9, False),
    ("Ambiente", "ambiente", 11, False),
    ("Vivienda", "vivienda", 13, False),
    ("Tránsito y Transporte", "transitoytransporte", 9, False),
    ("Turismo y Deportes", "turismoydeportes", 9, False),
    ("Personas Mayores", "personasmayores", 11, False),
]


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def norm(value: str | None) -> str:
    s = unicodedata.normalize("NFKD", clean(value)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def request(session: requests.Session, url: str) -> requests.Response:
    last = None
    for attempt in range(1, 4):
        try:
            r = session.get(url, headers={"User-Agent": UA}, timeout=45)
            r.raise_for_status()
            if len(r.text) < 1000:
                raise RuntimeError(f"respuesta demasiado breve ({len(r.text)} bytes)")
            return r
        except Exception as exc:
            last = exc
            if attempt == 3:
                break
    raise RuntimeError(f"no se pudo descargar {url}: {last}")


def row_cells(tr) -> list[str]:
    """Devuelve todas las celdas preservando columnas vacías (incluida imagen)."""
    return [clean(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"], recursive=False)]


def parse_member_table(soup: BeautifulSoup) -> list[dict]:
    """Lee la tabla Integrantes por nombre de columna, nunca por posición fija.

    La web oficial antepone una columna de imagen sin encabezado, por lo que
    asumir que Diputado es la columna 0 genera un corrimiento silencioso.
    """
    best: list[dict] = []
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        header_index = None
        positions: dict[str, int] = {}
        for i, tr in enumerate(trs):
            cells = row_cells(tr)
            normalized = [norm(x) for x in cells]
            if "diputado" in normalized and "bloque" in normalized and "cargo" in normalized:
                positions = {
                    "nombre": normalized.index("diputado"),
                    "bloque": normalized.index("bloque"),
                    "cargo": normalized.index("cargo"),
                }
                if "integrante desde" in normalized:
                    positions["desde"] = normalized.index("integrante desde")
                header_index = i
                break
        if header_index is None:
            continue

        rows: list[dict] = []
        need = max(positions.values())
        for tr in trs[header_index + 1:]:
            cells = row_cells(tr)
            if len(cells) <= need:
                continue
            name = cells[positions["nombre"]]
            block = cells[positions["bloque"]]
            role = cells[positions["cargo"]]
            since = cells[positions["desde"]] if "desde" in positions and len(cells) > positions["desde"] else ""
            if not name or not block or norm(name) in {"diputado", "nombre"}:
                continue
            rows.append({
                "nombre": name,
                "bloque": block,
                "cargo": role or "Vocal",
                "integrante_desde": since or None,
            })
        if len(rows) > len(best):
            best = rows
    return best


def parse_commission(session: requests.Session, official_name: str, slug: str, expected: int, weekly: bool) -> dict:
    url = f"{BASE}/comision/{slug}"
    r = request(session, url)
    soup = BeautifulSoup(r.text, "html.parser")
    members = parse_member_table(soup)
    if len(members) != expected:
        raise RuntimeError(f"{official_name}: esperaba {expected} integrantes y encontré {len(members)} en {url}")

    authorities = [m for m in members if norm(m.get("cargo")) != "vocal"]
    if not any(norm(m.get("cargo")) == "presidente" for m in members):
        raise RuntimeError(f"{official_name}: no se identificó presidencia")

    h1 = soup.find("h1")
    page_name = clean(h1.get_text(" ", strip=True)) if h1 else official_name
    return {
        "nombre": official_name,
        "nombre_fuente": page_name,
        "slug": slug,
        "url": url,
        "integrantes_normativos": expected,
        "frecuencia_minima": "semanal" if weekly else "dos_reuniones_mensuales",
        "autoridades": authorities,
        "integrantes": members,
    }


def parse_block_count(session: requests.Session) -> int | None:
    r = request(session, BLOCK_URL)
    soup = BeautifulSoup(r.text, "html.parser")
    text = clean(soup.get_text(" ", strip=True))
    m = re.search(r"Integrantes\s+(\d+)", text, flags=re.I)
    return int(m.group(1)) if m else None


def person_key(name: str) -> str:
    parts = norm(name).split()
    return " ".join(sorted(parts))


def block_members_from_commissions(commissions: list[dict], block_name: str) -> list[dict]:
    out: dict[str, dict] = {}
    for c in commissions:
        for member in c["integrantes"]:
            if norm(member.get("bloque")) != norm(block_name):
                continue
            key = person_key(member["nombre"])
            rec = out.setdefault(key, {"nombre": member["nombre"], "bloque": block_name, "comisiones": []})
            rec["comisiones"].append({"nombre": c["nombre"], "cargo": member.get("cargo") or "Vocal"})
    return sorted(out.values(), key=lambda x: norm(x["nombre"]))


def find_claudia(commissions: list[dict]) -> dict:
    roles = []
    canonical_name = "Claudia Negri"
    for c in commissions:
        for m in c["integrantes"]:
            n = norm(m["nombre"])
            if "negri" in n and "claudia" in n:
                canonical_name = m["nombre"]
                roles.append({"comision": c["nombre"], "cargo": m.get("cargo") or "Vocal", "url": c["url"]})
    if not roles:
        raise RuntimeError("Claudia Negri no aparece en ninguna comisión oficial")
    salud = [x for x in roles if norm(x["comision"]) == "salud"]
    if not salud or "vicepresidente 1" not in norm(salud[0].get("cargo")):
        raise RuntimeError(f"Salud: no se confirmó a Claudia Negri como Vicepresidente 1; roles={roles}")
    return {"nombre": canonical_name, "bloque": "Fuerza por Buenos Aires", "comisiones": roles}


def main() -> None:
    session = requests.Session()
    commissions = [parse_commission(session, *row) for row in COMMISSION_REGISTRY]

    fpba = block_members_from_commissions(commissions, "Fuerza por Buenos Aires")
    official_block_count = parse_block_count(session)
    if official_block_count is not None and len(fpba) != official_block_count:
        raise RuntimeError(
            f"Fuerza por Buenos Aires: la página oficial informa {official_block_count} integrantes "
            f"pero la unión de las 27 comisiones recuperó {len(fpba)}"
        )

    claudia = find_claudia(commissions)
    now = datetime.now(TZ).isoformat(timespec="seconds")
    dataset = {
        "schema": "cepoes-estructura-legislativa-v1",
        "actualizado_en": now,
        "fuente": {
            "organismo": "Legislatura de la Ciudad Autónoma de Buenos Aires",
            "comisiones": f"{BASE}/seccion/comisiones-y-juntas.html",
            "bloque_fuerza_por_buenos_aires": BLOCK_URL,
            "resolucion_60_2026": RESOLUTION_URL,
        },
        "marco_normativo": {
            "resolucion": "60/2026",
            "comisiones_permanentes": 27,
            "criterio_integracion": "artículo 132 del Reglamento Interno, texto según Resolución 60/2026",
        },
        "comisiones": commissions,
        "bloques": {
            "fuerza_por_buenos_aires": {
                "nombre": "Fuerza por Buenos Aires",
                "url": BLOCK_URL,
                "integrantes_informados": official_block_count,
                "integrantes": fpba,
            }
        },
        "referentes": {"claudia_negri": claudia},
    }
    OUT.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{OUT} · {len(commissions)} comisiones · FPBA {len(fpba)} integrantes · Claudia {len(claudia['comisiones'])} comisiones")


if __name__ == "__main__":
    main()
