#!/usr/bin/env python3
"""Seguimiento institucional exhaustivo de expedientes de Claudia Negri.

Primera corrida:
- solicita una ventana amplia de expedientes oficiales;
- exige que esa ventana alcance el 1/1 del año objetivo;
- revisa la ficha oficial de todos los expedientes del año para detectar a
  Claudia tanto como autora como coautora.

Corridas siguientes:
- conserva el inventario y los IDs ya revisados;
- inspecciona sólo los ingresos recientes no revisados.

No modifica `expedientes`, que conserva su semántica histórica de agenda.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from actualizar_sesiones import extract_nodes, expediente_basicos, post_xml
from actualizar_universo import iso_datetime, norm_num

DATA_PATH = Path("legislatura_publica.json")
TARGET_YEAR = int(os.getenv("CEPOES_INSTITUTIONAL_YEAR", "2026"))
FULL_LIMIT = int(os.getenv("CEPOES_INSTITUTIONAL_FULL_LIMIT", "10000"))
RECENT_LIMIT = int(os.getenv("CEPOES_INSTITUTIONAL_RECENT_LIMIT", "750"))
WORKERS = max(2, min(8, int(os.getenv("CEPOES_INSTITUTIONAL_WORKERS", "6"))))
TIMEOUT = 25
OFFICIAL_HOST = "parlamentaria.legislatura.gob.ar"
TARGET_CANONICAL = "NEGRI, CLAUDIA"
TARGET_NORM = "negri claudia"
_thread = threading.local()


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm(value) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def target_is(person: str) -> bool:
    return norm(person) in {TARGET_NORM, "claudia negri"}


def session() -> requests.Session:
    if not hasattr(_thread, "session"):
        s = requests.Session()
        s.headers.update({
            "User-Agent": "CEPOES-observatorio-legislativo/2.0 (+https://cepoes.org)",
            "Accept-Language": "es-AR,es;q=0.9",
        })
        _thread.session = s
    return _thread.session


def capture(text: str, start: str, end: str | None = None) -> str | None:
    pattern = re.escape(start) + r"\s*:\s*(.*?)"
    if end:
        pattern += r"\s*" + re.escape(end) + r"\s*:"
    else:
        pattern += r"(?:\s|$)"
    m = re.search(pattern, text, re.I)
    return clean(m.group(1)) if m else None


def split_people(value: str | None) -> list[str]:
    if not value:
        return []
    return [clean(x) for x in value.split("|") if clean(x)]


def fetch_detail(eid: str) -> dict:
    url = f"https://{OFFICIAL_HOST}/pages/expediente.aspx?id={eid}"
    try:
        r = session().get(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code != 200 or len(r.text) < 500:
            return {"id_expediente": eid, "ok": False, "error": f"HTTP {r.status_code}"}
        soup = BeautifulSoup(r.text, "html.parser")
        text = clean(soup.get_text(" ", strip=True))
        authors = split_people(capture(text, "Autor / Coautores", "Adherentes"))
        tipo = capture(text, "Proyecto de", "Fecha Inicio")
        fecha = capture(text, "Fecha Inicio", "Expedientes Hijos")
        ubicacion = capture(text, "Ubicación", "Origen")
        giros = capture(text, "Giros", "Ubicación")
        return {
            "id_expediente": eid,
            "ok": True,
            "url_expediente": r.url,
            "autores": authors,
            "tipo_oficial": clean(tipo).upper() or None,
            "fecha_inicio_texto": clean(fecha) or None,
            "ubicacion": clean(ubicacion) or None,
            "giros_texto": clean(giros) or None,
        }
    except requests.RequestException as exc:
        return {"id_expediente": eid, "ok": False, "error": type(exc).__name__}


def fetch_basics(http: requests.Session, ids: list[str], chunk: int = 100) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(ids), chunk):
        out.update(expediente_basicos(http, ids[i:i + chunk]))
    return out


def fecha_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def build_project(eid: str, raw: dict, basic: dict, detail: dict) -> dict:
    numero = norm_num(basic.get("numero") or raw.get("expediente"))
    authors = detail.get("autores") or []
    idx = next((i for i, p in enumerate(authors) if target_is(p)), None)
    role = "autora" if idx == 0 else "coautora"
    return {
        "id_expediente": eid,
        "numero": numero or None,
        "fecha_ingreso": iso_datetime(raw.get("fecha_ingreso")),
        "autor_reportado": clean(basic.get("autor") or raw.get("autor")) or None,
        "autores": authors,
        "rol_claudia": role,
        "sumario": clean(basic.get("sumario")) or None,
        "tipo_oficial": detail.get("tipo_oficial") or clean(basic.get("tipo")).upper() or None,
        "origen": clean(basic.get("origen")).upper() or None,
        "ubicacion": detail.get("ubicacion") or clean(raw.get("ubicacion")) or None,
        "url_expediente": detail.get("url_expediente")
            or clean(basic.get("url_ficha"))
            or f"https://{OFFICIAL_HOST}/pages/expediente.aspx?id={eid}",
        "documento": basic.get("documento"),
        "seguimiento_institucional": True,
        "persona_seguida": "Claudia Negri",
    }


def main() -> int:
    if not DATA_PATH.exists():
        print("✘ falta legislatura_publica.json")
        return 1

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    prev = data.get("seguimiento_institucional") or {}
    prev_cov = prev.get("cobertura") or {}
    already_complete = bool(prev_cov.get("completo")) and int(prev_cov.get("anio") or 0) == TARGET_YEAR
    requested_limit = RECENT_LIMIT if already_complete else FULL_LIMIT

    http = requests.Session()
    root = post_xml(http, "GetUltimosExpedientes", {"cantRegistros": str(requested_limit)})
    raw = extract_nodes(root, "ultimoExpediente")

    raw_by_id: dict[str, dict] = {}
    dates: list[dt.date] = []
    for row in raw:
        eid = clean(row.get("id_expediente"))
        if not eid:
            continue
        raw_by_id[eid] = row
        d = fecha_date(iso_datetime(row.get("fecha_ingreso")))
        if d:
            dates.append(d)

    if not raw_by_id:
        print("✘ GetUltimosExpedientes no devolvió expedientes")
        return 1

    oldest = min(dates) if dates else None
    newest = max(dates) if dates else None
    year_start = dt.date(TARGET_YEAR, 1, 1)
    temporal_complete = already_complete or bool(oldest and oldest <= year_start)

    # En la primera corrida no aceptamos una supuesta exhaustividad si la ventana
    # oficial no alcanza el comienzo del año objetivo.
    if not temporal_complete:
        data["seguimiento_institucional"] = {
            "schema": 1,
            "persona": "Claudia Negri",
            "actualizado": dt.datetime.now(dt.timezone.utc).isoformat(),
            "cobertura": {
                "anio": TARGET_YEAR,
                "completo": False,
                "motivo": "la ventana de GetUltimosExpedientes no alcanza el inicio del año",
                "limite_solicitado": requested_limit,
                "fecha_mas_antigua_obtenida": oldest.isoformat() if oldest else None,
                "fecha_mas_reciente_obtenida": newest.isoformat() if newest else None,
            },
            "expedientes": prev.get("expedientes") or [],
            "ids_revisados": prev.get("ids_revisados") or [],
        }
        DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(
            f"✘ cobertura institucional incompleta: la ventana más antigua es "
            f"{oldest}; se necesita alcanzar {year_start}. "
            f"Aumentar CEPOES_INSTITUTIONAL_FULL_LIMIT si el servicio lo admite."
        )
        return 2

    # Sólo son candidatos a revisar expedientes ingresados durante el año objetivo.
    year_rows = {
        eid: row for eid, row in raw_by_id.items()
        if (fecha_date(iso_datetime(row.get("fecha_ingreso"))) or dt.date.min).year == TARGET_YEAR
    }
    basics = fetch_basics(http, list(year_rows))

    reviewed = {str(x) for x in (prev.get("ids_revisados") or [])}
    to_review = [eid for eid in year_rows if eid not in reviewed]

    details: dict[str, dict] = {}
    failed: list[str] = []
    if to_review:
        print(f"Revisando {len(to_review)} fichas nuevas de {TARGET_YEAR} para autoría/coautoría…")
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futures = {ex.submit(fetch_detail, eid): eid for eid in to_review}
            for fut in as_completed(futures):
                result = fut.result()
                eid = result["id_expediente"]
                if result.get("ok"):
                    details[eid] = result
                else:
                    failed.append(eid)

    # Sólo se consideran revisados los que pudieron leerse correctamente.
    reviewed.update(details.keys())

    projects_by_id = {
        str(p.get("id_expediente")): p
        for p in (prev.get("expedientes") or [])
        if p.get("id_expediente")
    }

    detected_now = 0
    for eid, detail in details.items():
        authors = detail.get("autores") or []
        if not any(target_is(p) for p in authors):
            continue
        projects_by_id[eid] = build_project(
            eid, year_rows[eid], basics.get(eid) or {}, detail
        )
        detected_now += 1

    projects = sorted(
        projects_by_id.values(),
        key=lambda p: (
            p.get("fecha_ingreso") or "",
            int(str(p.get("id_expediente") or "0"))
        ),
        reverse=True,
    )

    complete = temporal_complete and not failed
    data["seguimiento_institucional"] = {
        "schema": 1,
        "persona": "Claudia Negri",
        "criterio": "autoría o coautoría publicada en la ficha oficial del expediente",
        "actualizado": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fuente": "Sistema de Consultas Parlamentarias de la Legislatura CABA",
        "cobertura": {
            "anio": TARGET_YEAR,
            "completo": complete,
            "limite_solicitado": requested_limit,
            "fecha_mas_antigua_obtenida": oldest.isoformat() if oldest else None,
            "fecha_mas_reciente_obtenida": newest.isoformat() if newest else None,
            "ids_del_anio_en_ventana": len(year_rows),
            "ids_revisados_acumulados": len(reviewed),
            "fichas_fallidas_en_corrida": failed,
        },
        "expedientes": projects,
        "ids_revisados": sorted(reviewed, key=lambda x: int(x) if x.isdigit() else x),
    }

    summary = data.setdefault("resumen", {})
    summary["claudia_expedientes_2026"] = len(projects)
    summary["claudia_autoria"] = sum(1 for p in projects if p.get("rol_claudia") == "autora")
    summary["claudia_coautoria"] = sum(1 for p in projects if p.get("rol_claudia") == "coautora")
    summary["claudia_cobertura_completa"] = complete

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Seguimiento Claudia · {len(projects)} expedientes acumulados "
        f"({summary['claudia_autoria']} autoría · {summary['claudia_coautoria']} coautoría) "
        f"· nuevos detectados: {detected_now}"
    )
    if failed:
        print(f"✘ {len(failed)} fichas no pudieron verificarse; la cobertura queda incompleta")
        return 3
    if not projects:
        print("✘ cobertura temporal completa pero no se detectó ningún expediente de Claudia; revisar parser/fuente")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
