"""Enriquece legislatura_publica.json con la ficha oficial de cada expediente.

Sólo incorpora información pública publicada por el Sistema de Consultas Parlamentarias
(SLP) de la Legislatura de la Ciudad Autónoma de Buenos Aires. No contiene análisis,
posiciones, recomendaciones ni notas internas.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent
DATA_PATH = BASE / "legislatura_publica.json"
REQUEST_TIMEOUT = 25
SLEEP_BETWEEN_REQUESTS = 0.04
OFFICIAL_HOST = "parlamentaria.legislatura.gob.ar"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "CEPOES-observatorio-legislativo/1.5 (+https://cepoes.org)",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.5",
})


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%+./ -]+", " ", s)).strip()


def get(url: str) -> requests.Response | None:
    try:
        r = SESSION.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 500 and urlparse(r.url).hostname == OFFICIAL_HOST:
            return r
    except requests.RequestException:
        pass
    return None


def expediente_id(url: str | None) -> int | None:
    if not url:
        return None
    try:
        value = (parse_qs(urlparse(url).query).get("id") or [None])[0]
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def iso_date(value: str | None) -> str | None:
    if not value:
        return None
    value = clean(value)
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            parsed = dt.datetime.strptime(value, fmt)
            return parsed.isoformat() if "%H" in fmt else parsed.date().isoformat()
        except ValueError:
            continue
    return None


def capture(text: str, start: str, end: str | None = None) -> str | None:
    pattern = re.escape(start) + r"\s*:\s*(.*?)"
    if end:
        pattern += r"\s*" + re.escape(end) + r"\s*:"
    else:
        pattern += r"(?:\s|$)"
    m = re.search(pattern, text, re.I)
    return clean(m.group(1)) if m else None


def split_people(value: str | None) -> list[str]:
    if not value or "sin adherentes" in norm(value):
        return []
    return [clean(x) for x in value.split("|") if clean(x)]


def split_giros(value: str | None) -> list[str]:
    if not value:
        return []
    value = value.replace("⇒", "|").replace("=>", "|")
    return [clean(x) for x in value.split("|") if clean(x)]


def cell_text(cell) -> str:
    bits: list[str] = []
    txt = clean(cell.get_text(" ", strip=True))
    if txt:
        bits.append(txt)
    for inp in cell.find_all("input"):
        v = clean(inp.get("value"))
        if v and v not in bits:
            bits.append(v)
    return clean(" ".join(bits))


def direct_rows(table) -> list:
    """Evita que una tabla contenedora absorba filas de tablas internas del SLP."""
    return [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]


def direct_cells(tr) -> list:
    """Devuelve sólo celdas cuyo padre de fila efectivo es el <tr> recibido."""
    return [
        cell
        for cell in tr.find_all(["th", "td"])
        if cell.find_parent("tr") is tr
    ]


def _header_matches(headers: list[str], required: set[str], forbidden: set[str]) -> bool:
    if not headers:
        return False
    if not all(any(req in h for h in headers) for req in required):
        return False
    return not any(any(term in h for h in headers) for term in forbidden)


def table_rows(
    soup: BeautifulSoup,
    required: set[str],
    forbidden: set[str] | None = None,
) -> list[dict]:
    """Devuelve filas de la primera tabla cuyo encabezado directo sea inequívoco.

    El SLP usa tablas contenedoras y tablas anidadas. La versión anterior buscaba
    <tr>/<td> de modo recursivo y podía confundir la tabla exterior con la tabla
    real de dictámenes. Aquí cada fila y cada celda deben pertenecer directamente
    a la tabla/filas analizadas.
    """
    forbidden = forbidden or set()
    for table in soup.find_all("table"):
        trs = direct_rows(table)
        if not trs:
            continue

        header_index = None
        headers: list[str] = []
        for idx, tr in enumerate(trs[:16]):
            cells = direct_cells(tr)
            candidate = [norm(cell_text(x)) for x in cells]
            if _header_matches(candidate, required, forbidden):
                header_index = idx
                headers = candidate
                break
        if header_index is None:
            continue

        out: list[dict] = []
        for tr in trs[header_index + 1:]:
            cells = direct_cells(tr)
            values = [cell_text(x) for x in cells]
            if not any(values):
                continue
            normalized_values = [norm(v) for v in values]
            if _header_matches(normalized_values, required, forbidden):
                continue

            row: dict = {}
            for i, value in enumerate(values):
                key = headers[i] if i < len(headers) and headers[i] else f"col_{i+1}"
                row[key] = value
                a = cells[i].find("a", href=True) if i < len(cells) else None
                if a:
                    row[f"{key}_url"] = requests.compat.urljoin(
                        SESSION.headers.get("Referer", ""), a["href"]
                    )
            out.append(row)
        if out:
            return out
    return []


def pick(row: dict, *needles: str) -> str | None:
    for key, value in row.items():
        if key.endswith("_url"):
            continue
        nk = norm(key)
        if all(x in nk for x in needles):
            return clean(value) or None
    return None


def pick_url(row: dict, *needles: str) -> str | None:
    for key, value in row.items():
        if not key.endswith("_url"):
            continue
        nk = norm(key[:-4])
        if all(x in nk for x in needles):
            return clean(value) or None
    return None


def parse_movements(soup: BeautifulSoup) -> list[dict]:
    rows = table_rows(soup, {"fecha", "oficina", "descripcion"})
    out = []
    for row in rows:
        fecha = iso_date(pick(row, "fecha"))
        oficina = pick(row, "oficina")
        descripcion = pick(row, "descripcion")
        if fecha and (oficina or descripcion):
            out.append({"fecha": fecha, "oficina": oficina, "descripcion": descripcion})
    return out


def parse_events(soup: BeautifulSoup) -> list[dict]:
    rows = table_rows(soup, {"fecha", "tipo", "subtipo", "notas"})
    out = []
    for row in rows:
        fecha = iso_date(pick(row, "fecha"))
        tipo = pick(row, "tipo")
        subtipo = pick(row, "subtipo")
        notas = pick(row, "notas")
        if fecha and tipo:
            out.append({"fecha": fecha, "tipo": tipo, "subtipo": subtipo, "notas": notas})
    return out


def parse_dictamenes(soup: BeautifulSoup) -> list[dict]:
    rows = table_rows(
        soup,
        {"fecha", "tipo", "documento", "firmas", "comision"},
        forbidden={"hora"},
    )
    out = []
    for row in rows:
        fecha = iso_date(pick(row, "fecha"))
        tipo = pick(row, "tipo")
        comision = pick(row, "comision")
        if fecha and tipo and comision:
            out.append({
                "fecha": fecha,
                "tipo": tipo,
                "comision": comision,
                "documento_url": pick_url(row, "documento"),
                "firmas_url": pick_url(row, "firmas"),
            })
    return out


def parse_meetings(soup: BeautifulSoup) -> list[dict]:
    rows = table_rows(soup, {"fecha", "hora", "tipo", "comision"})
    out = []
    for row in rows:
        fecha = iso_date(pick(row, "fecha"))
        if not fecha:
            continue
        out.append({
            "fecha": fecha,
            "hora": pick(row, "hora"),
            "tipo": pick(row, "tipo"),
            "descripcion": pick(row, "descripcion") or pick(row, "desripcion"),
            "comision": pick(row, "comision"),
            "salon": pick(row, "salon"),
        })
    return out


def parse_sessions(soup: BeautifulSoup) -> list[dict]:
    rows = table_rows(soup, {"fecha sesion", "tipo sesion", "afirmativos", "negativos"})
    out = []
    for row in rows:
        fecha = iso_date(pick(row, "fecha", "sesion"))
        if not fecha:
            continue

        def as_int(value: str | None) -> int | None:
            if value and re.fullmatch(r"\d+", value.strip()):
                return int(value)
            return None

        out.append({
            "fecha": fecha,
            "tipo": pick(row, "tipo", "sesion"),
            "descripcion": pick(row, "descripcion"),
            "presidente": pick(row, "presidente"),
            "asunto": pick(row, "asunto"),
            "afirmativos": as_int(pick(row, "afirmativos")),
            "negativos": as_int(pick(row, "negativos")),
            "abstenciones": as_int(pick(row, "abstenciones")),
            "sin_votar": as_int(pick(row, "sin votar")),
        })
    return out


def parse_sanctions(soup: BeautifulSoup) -> list[dict]:
    rows = table_rows(soup, {"tipo", "aprobacion"}, forbidden={"fecha sesion"})
    out = []
    for row in rows:
        numero = pick(row, "nro") or pick(row, "numero")
        tipo = pick(row, "tipo")
        aprobacion = pick(row, "aprobacion")
        fecha = iso_date(pick(row, "fecha", "aprob")) or iso_date(pick(row, "f", "aprob"))
        if numero or (tipo and aprobacion):
            out.append({
                "numero": numero,
                "tipo": tipo,
                "aprobacion": aprobacion,
                "fecha_aprobacion": fecha,
                "documento_url": pick_url(row, "documento"),
                "fuente": "tabla_sanciones",
            })
    return out


def has_event(events: list[dict], needle: str) -> bool:
    n = norm(needle)
    return any(
        n in norm(" ".join([
            event.get("tipo") or "",
            event.get("subtipo") or "",
            event.get("notas") or "",
        ]))
        for event in events
    )


def has_movement(movements: list[dict], needle: str) -> bool:
    n = norm(needle)
    return any(
        n in norm(" ".join([
            movement.get("oficina") or "",
            movement.get("descripcion") or "",
        ]))
        for movement in movements
    )


def sanction_evidence(sanctions: list[dict], events: list[dict], movements: list[dict]) -> bool:
    return bool(sanctions) or has_event(events, "sancion") or has_movement(movements, "sancionad")


def dictamen_evidence(dictamenes: list[dict], events: list[dict], movements: list[dict]) -> bool:
    return bool(dictamenes) or has_event(events, "dictamen") or has_movement(movements, "dictamen")


def current_text(ubicacion: str | None, ultimo: dict | None) -> str:
    return norm(" ".join([
        ubicacion or "",
        (ultimo or {}).get("oficina") or "",
        (ultimo or {}).get("descripcion") or "",
    ]))


def derive_current_state(
    ubicacion: str | None,
    ultimo: dict | None,
    giros: list[str],
) -> str:
    """Deriva el estado ACTUAL sólo de ubicación y último movimiento oficiales."""
    text = current_text(ubicacion, ultimo)
    if "sancionad" in text:
        return "sancionado"
    if "archiv" in text:
        return "archivado"
    if "despacho" in text:
        return "despacho"
    if "dictamen" in text:
        return "con_dictamen"
    if "esperando envio a comision" in text:
        return "ingresado"
    if "comision" in text:
        return "en_comision"

    ubicacion_n = norm(ubicacion)
    if ubicacion_n and any(ubicacion_n == norm(giro) for giro in giros):
        return "en_comision"
    return "ingresado"


def derive_cycle_stage(
    estado_actual: str,
    giros: list[str],
    sanctions: list[dict],
    dictamenes: list[dict],
    events: list[dict],
    movements: list[dict],
) -> str:
    """Máximo hito alcanzado, separado del estado actual."""
    if estado_actual == "archivado":
        return "archivado"
    if sanction_evidence(sanctions, events, movements):
        return "sancionado"
    if (
        dictamen_evidence(dictamenes, events, movements)
        or has_event(events, "despacho")
        or has_movement(movements, "despacho")
    ):
        return "con_dictamen"
    if estado_actual == "en_comision" or giros:
        return "en_comision"
    return "ingresado"


def parse_official_file(project: dict) -> dict | None:
    url = project.get("url_expediente")
    if not url or urlparse(url).hostname != OFFICIAL_HOST:
        return None

    r = get(url)
    if not r:
        return None

    SESSION.headers["Referer"] = r.url
    soup = BeautifulSoup(r.text, "html.parser")
    text = clean(soup.get_text(" ", strip=True))

    authors = capture(text, "Autor / Coautores", "Adherentes")
    adherents = capture(text, "Adherentes", "Giros")
    giros_raw = capture(text, "Giros", "Ubicación")
    ubicacion = capture(text, "Ubicación", "Origen")
    origen = capture(text, "Origen", "Proyecto de")
    tipo = capture(text, "Proyecto de", "Fecha Inicio")
    fecha_inicio_raw = capture(text, "Fecha Inicio", "Expedientes Hijos")

    giros = split_giros(giros_raw)
    movements = parse_movements(soup)
    events = parse_events(soup)
    dictamenes = parse_dictamenes(soup)
    sanctions = parse_sanctions(soup)
    meetings = parse_meetings(soup)
    sessions = parse_sessions(soup)

    ultimo = None
    m = re.search(
        r"Último Movimiento\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.*?)\s+\[\s*(.*?)\s*\]\s+Sumario\s*:",
        text,
        re.I,
    )
    if m:
        ultimo = {
            "fecha": iso_date(m.group(1)),
            "oficina": clean(m.group(2)),
            "descripcion": clean(m.group(3)),
        }
    elif movements:
        ultimo = movements[0]

    official_type = clean(tipo).upper() if tipo else None
    estado_actual = derive_current_state(ubicacion, ultimo, giros)
    evidencia_dictamen = dictamen_evidence(dictamenes, events, movements)
    evidencia_sancion = sanction_evidence(sanctions, events, movements)
    hitos = {
        "tuvo_dictamen": evidencia_dictamen,
        "tuvo_despacho": has_event(events, "despacho") or has_movement(movements, "despacho"),
        "tuvo_sesion": bool(sessions),
        "tuvo_sancion": evidencia_sancion,
        "fue_archivado": estado_actual == "archivado",
    }
    etapa_ciclo = derive_cycle_stage(
        estado_actual, giros, sanctions, dictamenes, events, movements
    )

    return {
        "consultada_en": dt.datetime.now(dt.timezone.utc).isoformat(),
        "expediente_id": expediente_id(r.url),
        "url": r.url,
        "tipo_proyecto": official_type,
        "origen": clean(origen).upper() if origen else None,
        "fecha_inicio": iso_date(fecha_inicio_raw),
        "ubicacion": ubicacion,
        "giros": giros,
        "autores": split_people(authors),
        "adherentes": split_people(adherents),
        "ultimo_movimiento": ultimo,
        "movimientos": movements,
        "sanciones": sanctions,
        "dictamenes": dictamenes,
        "reuniones": meetings,
        "eventos_documentales": events,
        "sesiones": sessions,
        "hitos": hitos,
        "evidencia_dictamen": evidencia_dictamen,
        "evidencia_sancion": evidencia_sancion,
        "estado_actual": estado_actual,
        "etapa_ciclo": etapa_ciclo,
        # Alias de compatibilidad: desde schema 5 "etapa" equivale al estado actual.
        "etapa": estado_actual,
    }


def main() -> int:
    if not DATA_PATH.exists():
        print("✘ falta legislatura_publica.json")
        return 1

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    projects = data.get("expedientes") or []
    enriched = failed = 0
    current_states = Counter()
    cycle_stages = Counter()
    official_types = Counter()

    for project in projects:
        ficha = parse_official_file(project)
        if ficha:
            project["ficha_oficial"] = ficha
            project["tipo_oficial"] = ficha.get("tipo_proyecto")
            project["estado_actual"] = ficha.get("estado_actual")
            project["etapa_ciclo"] = ficha.get("etapa_ciclo")
            project["etapa"] = ficha.get("estado_actual")
            project["fecha_inicio"] = ficha.get("fecha_inicio")
            project["ultimo_movimiento"] = ficha.get("ultimo_movimiento")
            enriched += 1
            current_states[ficha.get("estado_actual") or "sin_estado"] += 1
            cycle_stages[ficha.get("etapa_ciclo") or "sin_etapa"] += 1
            official_types[ficha.get("tipo_proyecto") or "SIN_TIPO"] += 1
        elif project.get("url_expediente"):
            failed += 1
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    summary = data.setdefault("resumen", {})
    summary["expedientes_enriquecidos"] = enriched
    summary["expedientes_ficha_no_disponible"] = failed
    summary["expedientes_con_dictamen"] = sum(
        1 for p in projects if ((p.get("ficha_oficial") or {}).get("hitos") or {}).get("tuvo_dictamen")
    )
    summary["dictamenes_detallados"] = sum(
        len((p.get("ficha_oficial") or {}).get("dictamenes") or []) for p in projects
    )
    summary["expedientes_con_sancion"] = sum(
        1 for p in projects if ((p.get("ficha_oficial") or {}).get("hitos") or {}).get("tuvo_sancion")
    )
    summary["expedientes_sancionados"] = sum(
        1 for p in projects if (p.get("ficha_oficial") or {}).get("estado_actual") == "sancionado"
    )
    summary["expedientes_con_sesion"] = sum(
        1 for p in projects if ((p.get("ficha_oficial") or {}).get("hitos") or {}).get("tuvo_sesion")
    )
    summary["estados_actuales"] = dict(sorted(current_states.items()))
    summary["etapas_ciclo"] = dict(sorted(cycle_stages.items()))
    # Compatibilidad con consumidores v4: ahora representa estados actuales.
    summary["etapas_legislativas"] = dict(sorted(current_states.items()))

    data["version"] = 5
    data["ciclo_legislativo"] = {
        "fuente": "Sistema de Consultas Parlamentarias de la Legislatura CABA",
        "actualizado": dt.datetime.now(dt.timezone.utc).isoformat(),
        "schema": 5,
        "campos": [
            "tipo oficial", "origen", "fecha de inicio", "giros", "ubicación",
            "movimientos", "dictámenes", "reuniones", "sanciones", "sesiones",
            "estado actual", "etapa de ciclo", "hitos",
        ],
        "regla_estado_actual": (
            "se deriva sólo de ubicación y último movimiento; la existencia histórica "
            "de un dictamen o sanción no redefine el estado actual"
        ),
        "regla_etapa_ciclo": "máximo hito parlamentario alcanzado a partir de evidencia oficial",
    }

    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(
        f"Ciclo legislativo · {enriched}/{len(projects)} expedientes enriquecidos"
        f" · fallas: {failed}"
    )
    print("  estado actual: " + " · ".join(
        f"{k} {v}" for k, v in sorted(current_states.items())
    ))
    print("  etapa ciclo: " + " · ".join(
        f"{k} {v}" for k, v in sorted(cycle_stages.items())
    ))
    print("  tipos oficiales: " + " · ".join(
        f"{k} {v}" for k, v in sorted(official_types.items())
    ))
    print(
        f"  con dictamen: {summary['expedientes_con_dictamen']}"
        f" · dictámenes detallados: {summary['dictamenes_detallados']}"
        f" · con sanción: {summary['expedientes_con_sancion']}"
        f" · estado sancionado: {summary['expedientes_sancionados']}"
        f" · con sesión: {summary['expedientes_con_sesion']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
