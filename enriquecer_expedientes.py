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
    "User-Agent": "CEPOES-observatorio-legislativo/1.3 (+https://cepoes.org)",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.5",
})


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm(value: object) -> str:
    import unicodedata
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
    bits = []
    txt = clean(cell.get_text(" ", strip=True))
    if txt:
        bits.append(txt)
    for inp in cell.find_all("input"):
        v = clean(inp.get("value"))
        if v and v not in bits:
            bits.append(v)
    return clean(" ".join(bits))


def table_rows(soup: BeautifulSoup, required: set[str]) -> list[dict]:
    """Devuelve filas de la primera tabla cuyos encabezados contienen required."""
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if not trs:
            continue
        headers = [norm(cell_text(x)) for x in trs[0].find_all(["th", "td"])]
        if not headers or not all(any(req in h for h in headers) for req in required):
            continue
        out = []
        for tr in trs[1:]:
            cells = tr.find_all(["th", "td"])
            values = [cell_text(x) for x in cells]
            if not any(values):
                continue
            row = {}
            for i, value in enumerate(values):
                key = headers[i] if i < len(headers) and headers[i] else f"col_{i+1}"
                row[key] = value
                a = cells[i].find("a", href=True) if i < len(cells) else None
                if a:
                    row[f"{key}_url"] = requests.compat.urljoin(SESSION.headers.get("Referer", ""), a["href"])
            out.append(row)
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


def parse_sanctions(soup: BeautifulSoup) -> list[dict]:
    rows = table_rows(soup, {"tipo", "aprobacion"})
    out = []
    for row in rows:
        numero = pick(row, "nro") or pick(row, "numero")
        tipo = pick(row, "tipo")
        aprobacion = pick(row, "aprobacion")
        fecha = iso_date(pick(row, "f", "aprob"))
        if numero or (tipo and aprobacion):
            out.append({"numero": numero, "tipo": tipo, "aprobacion": aprobacion, "fecha_aprobacion": fecha})
    return out


def parse_dictamenes(soup: BeautifulSoup) -> list[dict]:
    rows = table_rows(soup, {"fecha", "tipo", "comision"})
    out = []
    for row in rows:
        fecha = iso_date(pick(row, "fecha"))
        tipo = pick(row, "tipo")
        comision = pick(row, "comision")
        # Evita confundir la tabla de reuniones, que también tiene fecha/tipo/comisión.
        if any("hora" in norm(k) for k in row):
            continue
        if fecha and (tipo or comision):
            out.append({"fecha": fecha, "tipo": tipo, "comision": comision})
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


def derive_stage(ubicacion: str | None, ultimo: dict | None, sanctions: list[dict], dictamenes: list[dict]) -> str:
    text = norm(" ".join([
        ubicacion or "",
        (ultimo or {}).get("oficina") or "",
        (ultimo or {}).get("descripcion") or "",
    ]))
    if sanctions or "sancionad" in text:
        return "sancionado"
    if "archivo" in text:
        return "archivado"
    if "despacho" in text or dictamenes:
        return "con_dictamen"
    if "comision" in text:
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
    giros = capture(text, "Giros", "Ubicación")
    ubicacion = capture(text, "Ubicación", "Origen")
    origen = capture(text, "Origen", "Proyecto de")
    tipo = capture(text, "Proyecto de", "Fecha Inicio")
    fecha_inicio_raw = capture(text, "Fecha Inicio", "Expedientes Hijos")

    movements = parse_movements(soup)
    sanctions = parse_sanctions(soup)
    dictamenes = parse_dictamenes(soup)
    meetings = parse_meetings(soup)
    events = parse_events(soup)
    sessions = parse_sessions(soup)

    ultimo = None
    m = re.search(r"Último Movimiento\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.*?)\s+\[\s*(.*?)\s*\]\s+Sumario\s*:", text, re.I)
    if m:
        ultimo = {"fecha": iso_date(m.group(1)), "oficina": clean(m.group(2)), "descripcion": clean(m.group(3))}
    elif movements:
        ultimo = movements[0]

    official_type = clean(tipo).upper() if tipo else None
    result = {
        "consultada_en": dt.datetime.now(dt.timezone.utc).isoformat(),
        "expediente_id": expediente_id(r.url),
        "url": r.url,
        "tipo_proyecto": official_type,
        "origen": clean(origen).upper() if origen else None,
        "fecha_inicio": iso_date(fecha_inicio_raw),
        "ubicacion": ubicacion,
        "giros": split_giros(giros),
        "autores": split_people(authors),
        "adherentes": split_people(adherents),
        "ultimo_movimiento": ultimo,
        "movimientos": movements,
        "sanciones": sanctions,
        "dictamenes": dictamenes,
        "reuniones": meetings,
        "eventos_documentales": events,
        "sesiones": sessions,
    }
    result["etapa"] = derive_stage(ubicacion, ultimo, sanctions, dictamenes)
    return result


def main() -> int:
    if not DATA_PATH.exists():
        print("✘ falta legislatura_publica.json")
        return 1
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    projects = data.get("expedientes") or []
    enriched = failed = 0
    stages = Counter()
    official_types = Counter()

    for project in projects:
        ficha = parse_official_file(project)
        if ficha:
            project["ficha_oficial"] = ficha
            project["tipo_oficial"] = ficha.get("tipo_proyecto")
            project["etapa"] = ficha.get("etapa")
            project["fecha_inicio"] = ficha.get("fecha_inicio")
            project["ultimo_movimiento"] = ficha.get("ultimo_movimiento")
            enriched += 1
            stages[ficha.get("etapa") or "sin_etapa"] += 1
            official_types[ficha.get("tipo_proyecto") or "SIN_TIPO"] += 1
        elif project.get("url_expediente"):
            failed += 1
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    summary = data.setdefault("resumen", {})
    summary["expedientes_enriquecidos"] = enriched
    summary["expedientes_ficha_no_disponible"] = failed
    summary["expedientes_con_dictamen"] = sum(1 for p in projects if (p.get("ficha_oficial") or {}).get("dictamenes"))
    summary["expedientes_sancionados"] = sum(1 for p in projects if p.get("etapa") == "sancionado")
    summary["expedientes_con_sesion"] = sum(1 for p in projects if (p.get("ficha_oficial") or {}).get("sesiones"))
    data["version"] = 4
    data["ciclo_legislativo"] = {
        "fuente": "Sistema de Consultas Parlamentarias de la Legislatura CABA",
        "actualizado": dt.datetime.now(dt.timezone.utc).isoformat(),
        "campos": ["tipo oficial", "origen", "fecha de inicio", "giros", "ubicación", "movimientos", "dictámenes", "reuniones", "sanciones", "sesiones"],
    }
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"Ciclo legislativo · {enriched}/{len(projects)} expedientes enriquecidos · fallas: {failed}")
    print("  etapas: " + " · ".join(f"{k} {v}" for k, v in sorted(stages.items())))
    print("  tipos oficiales: " + " · ".join(f"{k} {v}" for k, v in sorted(official_types.items())))
    print(f"  con dictamen: {summary['expedientes_con_dictamen']} · sancionados: {summary['expedientes_sancionados']} · con sesión: {summary['expedientes_con_sesion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
