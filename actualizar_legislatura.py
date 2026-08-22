"""Actualiza el núcleo público del seguimiento legislativo de CEPOES.

Fuentes: sitios oficiales de la Legislatura de la Ciudad Autónoma de Buenos Aires.
El resultado contiene sólo información parlamentaria pública y clasificación temática
descriptiva. No contiene recomendaciones políticas, posiciones de voto ni notas internas.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent
OUT = BASE / "legislatura_publica.json"
STATE = BASE / "estado_legislatura.json"

HOST = "https://www.legislatura.gob.ar"
MAIN_AGENDA = f"{HOST}/AgendaLCABA"
HOME = f"{HOST}/"
CALENDAR = "https://parlamentaria.legislatura.gob.ar/pages/calendar.aspx"
AGENDA_TMPL = f"{HOST}/AgendaLCABA/{{}}"
SEED_AGENDA_ID = 4790
PAST_DAYS = 21
FUTURE_DAYS = 35
KEEP_DAYS = 180
REQUEST_TIMEOUT = 25

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}

# Términos deliberadamente conservadores: se evita, por ejemplo, usar "fiscal" a secas
# (puede referir a un fiscal judicial) o "colectivo" a secas (puede ser un grupo social).
TOPICS = {
    "presupuesto": ["presupuesto", "credito presupuest", "tribut", "impuesto", "hacienda", "financ", "agip", "deuda publica"],
    "salud": ["salud", "hospital", "cesac", "sanitari", "medic", "enfermed", "farmac", "vacun"],
    "educacion": ["educacion", "escuela", "escolar", "docent", "univers", "jardin", "estudiant", "beca estudiantil"],
    "trabajo": ["trabajo", "empleo", "laboral", "licencia", "sindical", "formacion profesional"],
    "produccion": ["desarrollo econom", "pyme", "comerc", "industr", "productiv", "emprend", "economia"],
    "vivienda": ["vivienda", "alquiler", "inquilin", "habitacional", "urbaniz", "inmueble"],
    "urbanismo": ["planeamiento", "codigo urbanistico", "urbanismo", "uso del suelo", "edific"],
    "movilidad": ["transporte", "subte", "movilidad", "transito", "biciclet", "ferrocarr", "linea de colectivo", "colectivos de pasajeros"],
    "ambiente": ["ambient", "residuo", "recicl", "arbol", "espacio verde", "higiene urbana"],
    "seguridad": ["seguridad", "policia", "delito", "emergencia", "bombero", "prevencion"],
    "desarrollo_social": ["promocion social", "desarrollo humano", "asistencia", "vulnerab", "pobreza"],
    "infancias": ["niñez", "ninez", "niño", "nino", "adolesc", "infancia"],
    "mayores": ["personas mayores", "jubilad", "geriatr", "vejez", "adulto mayor"],
    "discapacidad": ["discapacidad", "accesibilidad", "inclusion"],
    "generos": ["genero", "mujer", "diversidad", "violencia de genero"],
    "cultura": ["cultura", "libro", "museo", "teatro", "patrimonio", "artistic"],
    "institucional": ["constitucional", "organismo de control", "defensor", "auditoria", "ministerio publico", "electoral"],
}

PRIORITY_COMMISSION_TERMS = [
    "presupuesto", "hacienda", "salud", "educacion", "ciencia", "tecnologia",
    "trabajo", "empleo", "desarrollo econom", "vivienda", "planeamiento",
    "ambiente", "discapacidad", "asuntos constitucionales",
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "CEPOES-observatorio-legislativo/1.2 (+https://cepoes.org)",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.5",
})


def norm(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%+./ -]+", " ", s)).strip()


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def get(url: str) -> requests.Response | None:
    try:
        r = SESSION.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 300:
            return r
    except requests.RequestException:
        pass
    return None


def parse_spanish_date(text: str) -> dt.date | None:
    t = norm(text)
    m = re.search(r"(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)?\s*(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(20\d{2})", t)
    if not m or m.group(2) not in MONTHS:
        return None
    try:
        return dt.date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    except ValueError:
        return None


def agenda_id_from_url(url: str) -> int | None:
    m = re.search(r"/AgendaLCABA/(\d+)(?:$|[/?#])", url or "", re.I)
    return int(m.group(1)) if m else None


def detail_ids_from_url(url: str) -> tuple[int | None, int | None]:
    m = re.search(r"/AgendaLCABADetalle/(\d+)/(\d+)(?:$|[/?#])", url or "", re.I)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def discover_anchor_ids(previous_state: dict) -> set[int]:
    ids = {int(previous_state.get("ultimo_agenda_id") or SEED_AGENDA_ID), SEED_AGENDA_ID}
    for url in (MAIN_AGENDA, HOME, CALENDAR):
        r = get(url)
        if not r:
            continue
        aid = agenda_id_from_url(r.url)
        if aid:
            ids.add(aid)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            aid = agenda_id_from_url(urljoin(r.url, a["href"]))
            if aid:
                ids.add(aid)
    return ids


def classify_project(number: str, summary: str) -> tuple[str, list[str], str]:
    s = norm(summary)
    if "informes" in s or s.startswith("informe"):
        typ = "pedido_informes"
    elif any(k in s for k in ["modificase", "modifica la ley", "creacion", "crease", "crea ", "establece", "ley "]):
        typ = "ley"
    elif "resolucion" in s:
        typ = "resolucion"
    elif any(k in s for k in ["declarase", "declara de interes", "beneplacito", "conmemorase", "personalidad destacada"]):
        typ = "declaracion"
    else:
        typ = "otro"
    topics = [topic for topic, terms in TOPICS.items() if any(term in s for term in terms)]
    if typ in {"ley", "pedido_informes"} and topics:
        priority = "alta"
    elif typ in {"ley", "pedido_informes"} or topics:
        priority = "media"
    else:
        priority = "baja"
    return typ, topics, priority


def is_parliamentary_meeting(meeting: dict) -> bool:
    """Deja sólo actividad parlamentaria: comisiones/juntas/audiencias/Labor.

    La agenda institucional incluye también protocolo, actos, programas y reuniones
    administrativas. Esos eventos son reales, pero no pertenecen al radar legislativo.
    """
    name = norm(meeting.get("comision"))
    kind = meeting.get("tipo_reunion")
    if not name or name == "sin identificar":
        return False
    if name.startswith("direccion general") or name.startswith("programa la legislatura"):
        return False
    if "labor parlamentaria" in name or name.startswith("junta "):
        return True
    return kind in {"asesores", "diputados", "audiencia_publica"}


def parse_detail(meeting: dict) -> tuple[dict, list[dict]]:
    url = meeting.get("url")
    if not url:
        meeting["detalle_disponible"] = False
        meeting["expedientes_detallados"] = 0
        return meeting, []
    r = get(url)
    if not r:
        meeting["detalle_disponible"] = False
        meeting["expedientes_detallados"] = 0
        return meeting, []

    soup = BeautifulSoup(r.text, "html.parser")
    meeting["detalle_disponible"] = True
    full_text = clean(soup.get_text(" ", strip=True))
    aid, mid = detail_ids_from_url(r.url)
    if aid:
        meeting["agenda_id"] = aid
    if mid:
        meeting["id"] = mid

    detail_h3 = None
    for h3 in soup.find_all("h3"):
        t = clean(h3.get_text(" ", strip=True))
        nt = norm(t)
        if t and ("comision" in nt or "junta" in nt or "labor parlamentaria" in nt or "direccion general" in nt or "programa la legislatura" in nt):
            detail_h3 = h3
            break
    if detail_h3:
        title = clean(detail_h3.get_text(" ", strip=True))
        meeting["comision"] = re.sub(r"^Comisión:\s*", "", title, flags=re.I).strip()

    meeting["tipo_reunion"] = None
    for pat, label in [
        (r"Reunión de Asesores", "asesores"),
        (r"Reunión de Diputados", "diputados"),
        (r"Audiencia Pública", "audiencia_publica"),
        (r"Reunión Especial", "especial"),
        (r"\bOtros\b", "otros"),
    ]:
        if re.search(pat, full_text, re.I):
            meeting["tipo_reunion"] = label
            break

    mt = re.search(r"Hora Reunión\s*:\s*(\d{1,2}:\d{2})", full_text, re.I)
    meeting["hora"] = mt.group(1) if mt else None
    mc = re.search(r"Esta reunión tratará\s+(\d+)\s+Expedientes?", full_text, re.I)
    meeting["expedientes_anunciados"] = int(mc.group(1)) if mc else 0
    meeting["seguimiento_cepoes"] = any(k in norm(meeting.get("comision")) for k in PRIORITY_COMMISSION_TERMS)

    projects = []
    for table in soup.find_all("table"):
        first = table.find("tr")
        if not first:
            continue
        headers = [norm(x.get_text(" ", strip=True)) for x in first.find_all(["td", "th"])]
        if not (any("numero" in h for h in headers) and any("sumario" in h for h in headers)):
            continue
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all(["td", "th"])
            cells = [clean(td.get_text(" ", strip=True)) for td in tds]
            if len(cells) < 2:
                continue
            number, summary = cells[0], cells[1]
            author = cells[2] if len(cells) > 2 else ""
            if not re.search(r"\d", number) or not summary:
                continue
            typ, topics, priority = classify_project(number, summary)
            project_url = None
            a = tds[0].find("a", href=True) if tds else None
            if a:
                project_url = urljoin(r.url, a["href"])
            projects.append({
                "numero": number,
                "sumario": summary,
                "autor": author,
                "tipo_estimado": typ,
                "temas": topics,
                "prioridad_tecnica": priority,
                "url_expediente": project_url,
                "fuente_reunion": r.url,
                "reunion_id": meeting.get("id"),
                "comision": meeting.get("comision"),
                "fecha_reunion": meeting.get("fecha"),
            })
        break
    meeting["expedientes_detallados"] = len(projects)
    return meeting, projects


def parse_agenda_page(agenda_id: int) -> tuple[dict | None, list[dict]]:
    r = get(AGENDA_TMPL.format(agenda_id))
    if not r:
        return None, []
    soup = BeautifulSoup(r.text, "html.parser")
    h2 = soup.find("h2")
    adate = parse_spanish_date(h2.get_text(" ", strip=True) if h2 else soup.get_text(" ", strip=True)[:1600])
    if not adate:
        return None, []

    seen, candidates = set(), []
    for a in soup.find_all("a", href=True):
        u = urljoin(r.url, a["href"])
        aid, mid = detail_ids_from_url(u)
        if aid != agenda_id or not mid or mid in seen:
            continue
        seen.add(mid)
        h3 = a.find_previous("h3")
        title = clean(h3.get_text(" ", strip=True)) if h3 else ""
        candidates.append({
            "id": mid,
            "agenda_id": agenda_id,
            "fecha": adate.isoformat(),
            "comision": re.sub(r"^Comisión:\s*", "", title, flags=re.I).strip() if title else "Sin identificar",
            "tipo_reunion": None,
            "hora": None,
            "expedientes_anunciados": None,
            "url": u,
            "seguimiento_cepoes": False,
        })
    return {"agenda_id": agenda_id, "fecha": adate.isoformat(), "url": r.url, "reuniones": 0}, candidates


def merge_previous(current_days: list[dict], current_meetings: list[dict], current_projects: list[dict], previous: dict) -> tuple[list, list, list]:
    """Reemplaza por completo los datos de las agendas refrescadas.

    Esto impide que sobrevivan registros incompletos de corridas anteriores cuando el
    parser mejora o cambia la estructura de la fuente.
    """
    cutoff = dt.date.today() - dt.timedelta(days=KEEP_DAYS)
    refreshed = {int(x["agenda_id"]) for x in current_days if x.get("agenda_id")}

    day_map = {x["agenda_id"]: x for x in previous.get("agendas") or [] if x.get("agenda_id") and int(x["agenda_id"]) not in refreshed}
    for x in current_days:
        day_map[x["agenda_id"]] = x
    days = [x for x in day_map.values() if dt.date.fromisoformat(x["fecha"]) >= cutoff]
    days.sort(key=lambda x: x["fecha"])

    previous_meetings = previous.get("reuniones") or []
    previous_meeting_agenda = {x.get("id"): x.get("agenda_id") for x in previous_meetings if x.get("id")}
    meet_map = {}
    for x in previous_meetings:
        if not x.get("id") or not x.get("url") or int(x.get("agenda_id") or 0) in refreshed or not is_parliamentary_meeting(x):
            continue
        meet_map[x["id"]] = x
    for x in current_meetings:
        meet_map[x["id"]] = x
    meetings = [x for x in meet_map.values() if dt.date.fromisoformat(x["fecha"]) >= cutoff]
    meetings.sort(key=lambda x: (x["fecha"], x.get("hora") or "99:99", x.get("comision") or ""))

    proj_map = {}
    for x in previous.get("expedientes") or []:
        rid = x.get("reunion_id")
        old_agenda = previous_meeting_agenda.get(rid)
        if not rid or (old_agenda is not None and int(old_agenda) in refreshed):
            continue
        proj_map[(x.get("numero"), rid, x.get("fecha_reunion"))] = x
    for x in current_projects:
        proj_map[(x.get("numero"), x.get("reunion_id"), x.get("fecha_reunion"))] = x
    projects = [x for x in proj_map.values() if x.get("fecha_reunion") and dt.date.fromisoformat(x["fecha_reunion"]) >= cutoff]
    projects.sort(key=lambda x: (x.get("fecha_reunion") or "", x.get("numero") or ""), reverse=True)
    return days, meetings, projects


def main() -> int:
    previous, state = {}, {}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            previous = {}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            state = {}

    today = dt.date.today()
    lo, hi = today - dt.timedelta(days=PAST_DAYS), today + dt.timedelta(days=FUTURE_DAYS)
    anchors = discover_anchor_ids(state)
    anchor = max(anchors) if anchors else SEED_AGENDA_ID
    candidate_ids = sorted(set(range(max(1, anchor - 28), anchor + 46)) | anchors)

    current_days, raw_candidates = [], []
    max_seen = int(state.get("ultimo_agenda_id") or 0)
    for aid in candidate_ids:
        day, candidates = parse_agenda_page(aid)
        if not day:
            continue
        max_seen = max(max_seen, aid)
        d = dt.date.fromisoformat(day["fecha"])
        if lo <= d <= hi:
            current_days.append(day)
            raw_candidates.extend(candidates)
        time.sleep(0.03)

    current_meetings, current_projects = [], []
    counts_by_agenda: dict[int, int] = {}
    for candidate in raw_candidates:
        meeting, projects = parse_detail(candidate)
        if is_parliamentary_meeting(meeting):
            current_meetings.append(meeting)
            current_projects.extend(projects)
            aid = int(meeting.get("agenda_id") or 0)
            counts_by_agenda[aid] = counts_by_agenda.get(aid, 0) + 1
        time.sleep(0.04)
    for day in current_days:
        day["reuniones"] = counts_by_agenda.get(int(day["agenda_id"]), 0)

    days, meetings, projects = merge_previous(current_days, current_meetings, current_projects, previous)
    upcoming = [m for m in meetings if m["fecha"] >= today.isoformat()]
    high_projects = [p for p in projects if p.get("prioridad_tecnica") == "alta" and p.get("fecha_reunion") >= today.isoformat()]
    announced_meetings = sum(1 for m in meetings if int(m.get("expedientes_anunciados") or 0) > 0)

    out = {
        "version": 3,
        "generado": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fuente": "Legislatura de la Ciudad Autónoma de Buenos Aires · fuentes oficiales",
        "alcance": "Agenda parlamentaria de comisiones, juntas, audiencias y Labor Parlamentaria; expedientes incluidos en reuniones oficiales detectadas. Se excluyen actos y eventos administrativos/protocolarios.",
        "privacidad": "Sólo datos públicos. Notas, posiciones y estrategia interna no se almacenan en este archivo.",
        "ventana_actualizacion": {"desde": lo.isoformat(), "hasta": hi.isoformat()},
        "fuentes": [MAIN_AGENDA, CALENDAR, "https://parlamentaria.legislatura.gob.ar/pages/ExpedienteBusqueda.aspx", f"{HOST}/InfoSesion/"],
        "resumen": {
            "agendas_en_ventana": len(days),
            "reuniones_parlamentarias": len(meetings),
            "reuniones_proximas": len(upcoming),
            "reuniones_con_expedientes_anunciados": announced_meetings,
            "expedientes_en_reuniones": len(projects),
            "expedientes_prioridad_tecnica_alta_proximos": len(high_projects),
        },
        "agendas": days,
        "reuniones": meetings,
        "expedientes": projects,
        "taxonomia_tematica": sorted(TOPICS.keys()),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    STATE.write_text(json.dumps({
        "version": 3,
        "actualizado": out["generado"],
        "ultimo_agenda_id": max_seen or anchor,
        "agendas_detectadas_en_corrida": len(current_days),
        "reuniones_parlamentarias_detectadas_en_corrida": len(current_meetings),
        "expedientes_detectados_en_corrida": len(current_projects),
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"legislatura_publica.json · {OUT.stat().st_size//1024} KB")
    print(f"  agendas: {len(days)} · reuniones parlamentarias: {len(meetings)} · expedientes: {len(projects)}")
    print(f"  con expedientes anunciados: {announced_meetings} · próximas: {len(upcoming)} · prioridad técnica alta: {len(high_projects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
