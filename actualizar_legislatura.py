"""Actualiza el núcleo público del seguimiento legislativo de CEPOES.

Fuentes: sitios oficiales de la Legislatura de la Ciudad Autónoma de Buenos Aires.
El archivo resultante contiene sólo información parlamentaria pública y clasificación
 temática descriptiva. No contiene recomendaciones políticas, posiciones de voto ni
notas internas de CEPOES.
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
SEED_AGENDA_ID = 4790  # agenda oficial del 20/08/2026; el estado luego avanza solo
PAST_DAYS = 21
FUTURE_DAYS = 35
KEEP_DAYS = 180
REQUEST_TIMEOUT = 25

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}

TOPICS = {
    "presupuesto": ["presupuesto", "credito", "tribut", "impuesto", "fiscal", "hacienda", "financ"],
    "salud": ["salud", "hospital", "cesac", "sanitari", "medic", "enfermed", "farmac", "vacun"],
    "educacion": ["educacion", "escuela", "escolar", "docent", "univers", "jardin", "estudiant"],
    "trabajo": ["trabajo", "empleo", "laboral", "licencia", "sindical", "formacion profesional"],
    "produccion": ["desarrollo econom", "pyme", "comerc", "industr", "productiv", "emprend", "economia"],
    "vivienda": ["vivienda", "alquiler", "inquilin", "habitacional", "urbaniz", "inmueble"],
    "urbanismo": ["planeamiento", "codigo urbanistico", "urbanismo", "uso del suelo", "edific"],
    "movilidad": ["transporte", "subte", "colectivo", "movilidad", "transito", "biciclet", "ferrocarr"],
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
    "User-Agent": "CEPOES-observatorio-legislativo/1.1 (+https://cepoes.org)",
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
    if not m:
        return None
    month = MONTHS.get(m.group(2))
    if not month:
        return None
    try:
        return dt.date(int(m.group(3)), month, int(m.group(1)))
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
    topics = []
    for topic, terms in TOPICS.items():
        if any(term in s for term in terms):
            topics.append(topic)
    if typ in {"ley", "pedido_informes"} and topics:
        prio = "alta"
    elif typ in {"ley", "pedido_informes"} or topics:
        prio = "media"
    else:
        prio = "baja"
    return typ, topics, prio


def parse_detail(meeting: dict) -> tuple[dict, list[dict]]:
    """Completa una reunión desde su página de detalle oficial.

    La agenda pública cambió su estructura HTML: los datos de la reunión y el enlace
    al detalle no son necesariamente hermanos directos del encabezado H3. Por eso la
    página de agenda se usa sólo para descubrir URLs/IDs y esta función toma el detalle
    como fuente canónica de comisión, tipo, hora, cantidad y expedientes.
    """
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

    # Comisión / organismo: el primer H3 del cuerpo de detalle es el rótulo oficial.
    detail_h3 = None
    for h3 in soup.find_all("h3"):
        t = clean(h3.get_text(" ", strip=True))
        nt = norm(t)
        if t and ("comision" in nt or "junta" in nt or "labor parlamentaria" in nt or "direccion general" in nt):
            detail_h3 = h3
            break
    if detail_h3:
        title = clean(detail_h3.get_text(" ", strip=True))
        commission = re.sub(r"^Comisión:\s*", "", title, flags=re.I).strip()
        meeting["comision"] = commission

    for pat, label in [
        (r"Reunión de Asesores", "asesores"),
        (r"Reunión de Diputados", "diputados"),
        (r"Reunión Especial", "especial"),
        (r"Audiencia Pública", "audiencia_publica"),
        (r"\bOtros\b", "otros"),
    ]:
        if re.search(pat, full_text, re.I):
            meeting["tipo_reunion"] = label
            break

    mt = re.search(r"Hora Reunión\s*:\s*(\d{1,2}:\d{2})", full_text, re.I)
    if mt:
        meeting["hora"] = mt.group(1)
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
        rows = table.find_all("tr")
        for tr in rows[1:]:
            tds = tr.find_all(["td", "th"])
            cells = [clean(td.get_text(" ", strip=True)) for td in tds]
            if len(cells) < 2:
                continue
            number, summary = cells[0], cells[1]
            author = cells[2] if len(cells) > 2 else ""
            if not re.search(r"\d", number) or not summary:
                continue
            typ, topics, prio = classify_project(number, summary)
            project_url = None
            if tds:
                a = tds[0].find("a", href=True)
                if a:
                    project_url = urljoin(r.url, a["href"])
            projects.append({
                "numero": number,
                "sumario": summary,
                "autor": author,
                "tipo_estimado": typ,
                "temas": topics,
                "prioridad_tecnica": prio,
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
    """Descubre las reuniones por sus enlaces de detalle, no por la jerarquía visual.

    Esto evita depender de la estructura de tarjetas/divs de la agenda, que puede cambiar
    sin que cambien las URLs estables AgendaLCABADetalle/<agenda>/<reunion>.
    """
    r = get(AGENDA_TMPL.format(agenda_id))
    if not r:
        return None, []
    soup = BeautifulSoup(r.text, "html.parser")
    h2 = soup.find("h2")
    adate = parse_spanish_date(h2.get_text(" ", strip=True) if h2 else soup.get_text(" ", strip=True)[:1600])
    if not adate:
        return None, []

    seen = set()
    meetings = []
    for a in soup.find_all("a", href=True):
        u = urljoin(r.url, a["href"])
        aid, mid = detail_ids_from_url(u)
        if aid != agenda_id or not mid or mid in seen:
            continue
        seen.add(mid)
        # El detalle será la fuente canónica; aquí sólo guardamos una pista del H3 previo.
        h3 = a.find_previous("h3")
        title = clean(h3.get_text(" ", strip=True)) if h3 else ""
        commission = re.sub(r"^Comisión:\s*", "", title, flags=re.I).strip() if title else "Sin identificar"
        meetings.append({
            "id": mid,
            "agenda_id": agenda_id,
            "fecha": adate.isoformat(),
            "comision": commission,
            "tipo_reunion": None,
            "hora": None,
            "expedientes_anunciados": None,
            "url": u,
            "seguimiento_cepoes": any(k in norm(commission) for k in PRIORITY_COMMISSION_TERMS),
        })

    day = {
        "agenda_id": agenda_id,
        "fecha": adate.isoformat(),
        "url": r.url,
        "reuniones": len(meetings),
    }
    return day, meetings


def merge_previous(current_days: list[dict], current_meetings: list[dict], current_projects: list[dict], previous: dict) -> tuple[list, list, list]:
    cutoff = dt.date.today() - dt.timedelta(days=KEEP_DAYS)
    day_map = {x["agenda_id"]: x for x in previous.get("agendas") or [] if x.get("agenda_id")}
    for x in current_days:
        day_map[x["agenda_id"]] = x
    days = [x for x in day_map.values() if dt.date.fromisoformat(x["fecha"]) >= cutoff]
    days.sort(key=lambda x: x["fecha"])

    meet_map = {}
    for x in previous.get("reuniones") or []:
        k = x.get("id") or f"{x.get('agenda_id')}:{x.get('comision')}:{x.get('hora')}"
        meet_map[k] = x
    for x in current_meetings:
        k = x.get("id") or f"{x.get('agenda_id')}:{x.get('comision')}:{x.get('hora')}"
        meet_map[k] = x
    meetings = [x for x in meet_map.values() if dt.date.fromisoformat(x["fecha"]) >= cutoff]
    meetings.sort(key=lambda x: (x["fecha"], x.get("hora") or "99:99", x.get("comision") or ""))

    proj_map = {}
    for x in previous.get("expedientes") or []:
        proj_map[(x.get("numero"), x.get("reunion_id"), x.get("fecha_reunion"))] = x
    for x in current_projects:
        proj_map[(x.get("numero"), x.get("reunion_id"), x.get("fecha_reunion"))] = x
    projects = [x for x in proj_map.values() if x.get("fecha_reunion") and dt.date.fromisoformat(x["fecha_reunion"]) >= cutoff]
    projects.sort(key=lambda x: (x.get("fecha_reunion") or "", x.get("numero") or ""), reverse=True)
    return days, meetings, projects


def main() -> int:
    previous = {}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            previous = {}
    state = {}
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

    days, meetings = [], []
    max_seen = int(state.get("ultimo_agenda_id") or 0)
    for aid in candidate_ids:
        day, ms = parse_agenda_page(aid)
        if not day:
            continue
        max_seen = max(max_seen, aid)
        d = dt.date.fromisoformat(day["fecha"])
        if lo <= d <= hi:
            days.append(day)
            meetings.extend(ms)
        time.sleep(0.03)

    parsed_meetings, projects = [], []
    for m in meetings:
        mm, pp = parse_detail(m)
        parsed_meetings.append(mm)
        projects.extend(pp)
        time.sleep(0.04)

    days, parsed_meetings, projects = merge_previous(days, parsed_meetings, projects, previous)
    upcoming = [m for m in parsed_meetings if m["fecha"] >= today.isoformat()]
    high_projects = [p for p in projects if p.get("prioridad_tecnica") == "alta" and p.get("fecha_reunion") >= today.isoformat()]

    out = {
        "version": 2,
        "generado": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fuente": "Legislatura de la Ciudad Autónoma de Buenos Aires · fuentes oficiales",
        "alcance": "Agenda de comisiones y expedientes incluidos en reuniones oficiales detectadas. No sustituye el expediente parlamentario completo.",
        "privacidad": "Sólo datos públicos. Notas, posiciones y estrategia interna no se almacenan en este archivo.",
        "ventana_actualizacion": {"desde": lo.isoformat(), "hasta": hi.isoformat()},
        "fuentes": [MAIN_AGENDA, CALENDAR, "https://parlamentaria.legislatura.gob.ar/pages/ExpedienteBusqueda.aspx", f"{HOST}/InfoSesion/"],
        "resumen": {
            "agendas_en_ventana": len(days),
            "reuniones_total": len(parsed_meetings),
            "reuniones_proximas": len(upcoming),
            "reuniones_con_expedientes_anunciados": sum(1 for m in parsed_meetings if (m.get("expedientes_anunciados") or 0) > 0),
            "expedientes_en_reuniones": len(projects),
            "expedientes_prioridad_tecnica_alta_proximos": len(high_projects),
        },
        "agendas": days,
        "reuniones": parsed_meetings,
        "expedientes": projects,
        "taxonomia_tematica": sorted(TOPICS.keys()),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    STATE.write_text(json.dumps({
        "version": 2,
        "actualizado": out["generado"],
        "ultimo_agenda_id": max_seen or anchor,
        "agendas_detectadas_en_corrida": len(days),
        "reuniones_detectadas_en_corrida": len(meetings),
        "expedientes_detectados_en_corrida": len(projects),
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"legislatura_publica.json · {OUT.stat().st_size//1024} KB")
    print(f"  agendas: {len(days)} · reuniones: {len(parsed_meetings)} · expedientes: {len(projects)}")
    print(f"  con expedientes anunciados: {out['resumen']['reuniones_con_expedientes_anunciados']} · próximas: {len(upcoming)} · prioridad técnica alta: {len(high_projects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
