#!/usr/bin/env python3
"""Actualiza sesiones_publicas.json desde servicios oficiales de la Legislatura.

Capa exclusivamente pública: sesiones, documentos, presentismo, asuntos
considerados, sanciones y votaciones nominales. No contiene análisis político,
recomendaciones, responsables ni notas internas.
"""

from __future__ import annotations

import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests

BASE = "https://parlamentaria.legislatura.gob.ar/"
WS = urljoin(BASE, "webservices/Json.asmx/")
OUT = Path("sesiones_publicas.json")
UA = "cepoes-legislatura-sesiones/2.24 (+https://github.com/cepoes100b/CEPOES)"
TZ = ZoneInfo("America/Argentina/Buenos_Aires")

PRIVATE_KEYS = {
    "prioridad_interna", "posicion", "recomendacion", "responsable",
    "notas_internas", "analisis_tecnico", "argumentos", "preguntas",
    "oportunidad", "modificaciones",
}


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def norm(value: str | None) -> str:
    s = unicodedata.normalize("NFKD", clean(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def int_or_none(value: str | None):
    value = clean(value)
    if not value or not re.fullmatch(r"-?\d+", value):
        return None
    return int(value)


def boolish(value: str | None) -> bool:
    return norm(value) in {"true", "1", "si", "yes"}


def doc_link(doc_id: str | None):
    doc_id = clean(doc_id)
    if not doc_id or doc_id == "0":
        return None
    return {
        "id_documento": doc_id,
        "url": urljoin(BASE, f"pages/download.aspx?IdDoc={doc_id}"),
    }


def page_links(id_sesion: str):
    return {
        "votaciones": urljoin(BASE, f"pages/sesion_votaciones.aspx?IdSesion={id_sesion}"),
        "info_sesion": urljoin(BASE, f"InfoSesion/{id_sesion}"),
        "reporte_presentismo": urljoin(BASE, f"ReportesPDFGen/VisualizadorReportes.aspx?iTipoReporte=100&IdSesion={id_sesion}"),
    }


def node_dict(node: ET.Element) -> dict[str, str]:
    return {child.tag.split("}")[-1]: clean(child.text) for child in list(node)}


def extract_nodes(root: ET.Element, local_name: str) -> list[dict[str, str]]:
    wanted = local_name.lower()
    return [node_dict(n) for n in root.iter() if n.tag.split("}")[-1].lower() == wanted]


def post_xml(session: requests.Session, method: str, data: dict) -> ET.Element:
    url = urljoin(WS, method)
    r = session.post(
        url,
        headers={
            "User-Agent": UA,
            "Referer": urljoin(BASE, "pages/ExpedienteBusqueda.aspx"),
            "X-Requested-With": "XMLHttpRequest",
        },
        data=data,
        timeout=60,
    )
    r.raise_for_status()
    return ET.fromstring(r.content)


def expediente_basicos(session: requests.Session, ids: list[str]) -> dict[str, dict]:
    ids = sorted({clean(x) for x in ids if clean(x)})
    if not ids:
        return {}
    root = post_xml(session, "GetExpedienteDatosBasicos", {
        "IdExpediente": 0,
        "NumeroOrden": 0,
        "AnoParlamentario": 0,
        "IdExpedientes": ",".join(ids),
    })
    rows = extract_nodes(root, "expedienteBasicos")
    out = {}
    for row in rows:
        eid = clean(row.get("id_expediente"))
        if not eid:
            continue
        out[eid] = {
            "id_expediente": eid,
            "numero": clean(row.get("nro_de_expediente")),
            "nro_orden": clean(row.get("nro_de_orden")),
            "ano_parlamentario": clean(row.get("ano_parlamentario")),
            "tipo": clean(row.get("proyecto_tipo_des")),
            "origen": clean(row.get("proyecto_origen_tipo_des")),
            "sumario": clean(row.get("sumario")),
            "autor": clean(row.get("autor_des")),
            "fecha_inicio": clean(row.get("fch_inicio")),
            "url_ficha": urljoin(BASE, f"pages/expediente.aspx?id={eid}"),
            "documento": doc_link(row.get("urlDoc")),
        }
    return out


def normalizar_presentismo(rows: list[dict[str, str]]) -> dict:
    registros = []
    presentes = 0
    ausentes = 0
    presidente = ""
    secretarios = ""
    for row in rows:
        tipo = clean(row.get("id_presentes_tipo"))
        if tipo == "1":
            presentes += 1
        else:
            ausentes += 1
        presidente = presidente or clean(row.get("presidente_sesion"))
        secretarios = secretarios or clean(row.get("secretarios_sesion"))
        registros.append({
            "id_legislador": clean(row.get("id_legislador")),
            "nombre": clean(row.get("legislador_nombre")),
            "apellido": clean(row.get("legislador_apellido")),
            "bloque": clean(row.get("bloque_nombre")),
            "id_estado": tipo,
            "estado": clean(row.get("presente_descripcion")),
        })
    total = presentes + ausentes
    porcentaje = round((presentes * 100 / total), 2) if total else None
    return {
        "total": total,
        "presentes": presentes,
        "ausentes": ausentes,
        "porcentaje_asistencia": porcentaje,
        "presidente": presidente,
        "secretarios": secretarios,
        "registros": registros,
    }


def normalizar_asuntos(rows: list[dict[str, str]]) -> list[dict]:
    out = []
    for row in rows:
        out.append({
            "id_expediente": clean(row.get("id_expediente")),
            "numero_expediente": clean(row.get("nro_de_expediente")),
            "procesado": boolish(row.get("esta_procesado")),
            "tipo": clean(row.get("asunto_considerado_item_tipo_des")),
            "descripcion": clean(row.get("descripcion")),
        })
    return out


def normalizar_sanciones(rows: list[dict[str, str]]) -> list[dict]:
    out = []
    for row in rows:
        out.append({
            "id_expediente": clean(row.get("id_expediente")),
            "numero_expediente": clean(row.get("nro_de_expediente")),
            "tipo": clean(row.get("asunto_considerado_item_tipo_des")),
            "descripcion": clean(row.get("descripcion")),
        })
    return out


def detalle_votacion(session: requests.Session, id_votacion: str) -> list[dict]:
    if not id_votacion:
        return []
    root = post_xml(session, "GetVotaciones", {
        "IdVotacionAsunto": id_votacion,
        "IdExpediente": "",
        "IdSesion": "",
        "IdLegislador": "",
    })
    rows = extract_nodes(root, "clsVotacionExpediente")
    return [{
        "id_legislador": clean(row.get("id_legislador")),
        "nombre": clean(row.get("legislador_nombre")),
        "apellido": clean(row.get("legislador_apellido")),
        "bloque": clean(row.get("bloque_nombre")),
        "voto": clean(row.get("votacion_tipo_descripcion")),
    } for row in rows]


def normalizar_votaciones(session: requests.Session, id_sesion: str) -> list[dict]:
    root = post_xml(session, "GetVotacionesAsuntos", {"IdExpediente": 0, "IdSesion": id_sesion})
    rows = extract_nodes(root, "clsVotacionAsuntos")
    exp_ids = []
    pre = []
    for row in rows:
        eid = clean(row.get("id_expediente")) or clean(row.get("id_expediente_despacho"))
        if eid:
            exp_ids.append(eid)
        pre.append((row, eid))
    basicos = expediente_basicos(session, exp_ids)
    out = []
    for row, eid in pre:
        id_votacion = clean(row.get("id_votacion"))
        positivos = int_or_none(row.get("positivos")) or 0
        negativos = int_or_none(row.get("negativos")) or 0
        abstenciones = int_or_none(row.get("abstenciones")) or 0
        out.append({
            "id_votacion": id_votacion,
            "id_sesion": clean(row.get("id_sesion")) or id_sesion,
            "id_expediente": eid,
            "expediente": basicos.get(eid),
            "asunto": clean(row.get("asunto")),
            "resultado": {
                "afirmativos": positivos,
                "negativos": negativos,
                "abstenciones": abstenciones,
                "total_emitidos": positivos + negativos + abstenciones,
            },
            "detalle_nominal": detalle_votacion(session, id_votacion),
        })
    return out


def cargar_sesion(session: requests.Session, raw: dict[str, str]) -> dict:
    id_sesion = clean(raw.get("id_sesion_lp"))
    detalle_root = post_xml(session, "GetSesionById", {"idSesionLabor": id_sesion})
    detalle_rows = extract_nodes(detalle_root, "sesiones")
    detalle = detalle_rows[0] if detalle_rows else raw

    present_root = post_xml(session, "GetPresentismo", {
        "IdBloque": 0,
        "IdSesion": id_sesion,
        "IdLegislador": 0,
        "FechaDesde": "",
        "Fechahasta": "",
    })
    presentismo = normalizar_presentismo(extract_nodes(present_root, "clsPresentesSesion"))

    asuntos_root = post_xml(session, "GetAsuntosConsideradosByIdSesion", {"IdSesion": id_sesion})
    asuntos = normalizar_asuntos(extract_nodes(asuntos_root, "asuntosConsiderados"))

    sanc_root = post_xml(session, "GetAsuntoConsideradoItemByIdSesion", {"idSesion": id_sesion})
    sanciones = normalizar_sanciones(extract_nodes(sanc_root, "asuntoconsideradoitem"))

    votaciones = normalizar_votaciones(session, id_sesion)

    labor = doc_link(detalle.get("labor_documento") or raw.get("labor_documento"))
    prelabor = doc_link(detalle.get("prelabor_documento") or raw.get("prelabor_documento"))
    vt = doc_link(detalle.get("archivo_vt") or raw.get("archivo_vt"))
    asuntos_doc = doc_link(detalle.get("asuntos_considerados_documento") or raw.get("asuntos_considerados_documento"))

    if presentismo["total"]:
        realizada = presentismo["presentes"] >= 30
        criterio = "presentismo_quorum"
    else:
        realizada = bool(labor)
        criterio = "documento_labor"

    return {
        "id_sesion": id_sesion,
        "nro_orden_lp": clean(detalle.get("nro_orden_lp") or raw.get("nro_orden_lp")),
        "ano_parlamentario": clean(detalle.get("ano_parlamentario") or raw.get("ano_parlamentario")),
        "fecha": clean(detalle.get("fch_sesion_lp") or raw.get("fch_sesion_lp")),
        "tipo": {
            "id": clean(detalle.get("id_sesion_tipo") or raw.get("id_sesion_tipo")),
            "abreviatura": clean(detalle.get("abrev_sesion_tipo") or raw.get("abrev_sesion_tipo")),
            "descripcion": clean(detalle.get("dsc_sesion_tipo") or raw.get("dsc_sesion_tipo")),
        },
        "datos_recinto": {
            "id_sesion_recinto": clean(detalle.get("ve_idsesion")),
            "periodo": clean(detalle.get("ve_periodosesion")),
            "fecha": clean(detalle.get("ve_fechasesion")),
            "reunion": clean(detalle.get("ve_reunion")),
        },
        "realizada": realizada,
        "criterio_realizada": criterio,
        "documentos": {
            "acuerdo_labor": labor,
            "informe_prelabor": prelabor,
            "version_taquigrafica": vt,
            "asuntos_considerados": asuntos_doc,
        },
        "urls": page_links(id_sesion),
        "presentismo": presentismo,
        "asuntos_considerados": asuntos,
        "sanciones": sanciones,
        "votaciones_nominales": votaciones,
    }


def contains_private_keys(obj) -> bool:
    if isinstance(obj, dict):
        if PRIVATE_KEYS.intersection(obj):
            return True
        return any(contains_private_keys(v) for v in obj.values())
    if isinstance(obj, list):
        return any(contains_private_keys(v) for v in obj)
    return False


def main() -> None:
    now = datetime.now(TZ)
    desde = f"01/01/{now.year}"
    hasta = now.strftime("%d/%m/%Y")
    session = requests.Session()

    root = post_xml(session, "GetSesionesAvanzado", {"FechaDesde": desde, "FechaHasta": hasta})
    raw_sessions = extract_nodes(root, "sesiones")
    by_id = {clean(x.get("id_sesion_lp")): x for x in raw_sessions if clean(x.get("id_sesion_lp"))}

    sesiones = []
    fallas = []
    for sid, raw in by_id.items():
        try:
            sesiones.append(cargar_sesion(session, raw))
        except Exception as exc:  # no ocultar una sesión incompleta
            fallas.append({"id_sesion": sid, "error": f"{type(exc).__name__}: {exc}"})

    sesiones.sort(key=lambda x: (x.get("fecha", ""), int_or_none(x.get("id_sesion")) or 0))

    total_presentismo = sum(s["presentismo"]["total"] for s in sesiones)
    total_asuntos = sum(len(s["asuntos_considerados"]) for s in sesiones)
    total_sanciones = sum(len(s["sanciones"]) for s in sesiones)
    votos_asuntos = sum(len(s["votaciones_nominales"]) for s in sesiones)
    votos_nominales = sum(len(v["detalle_nominal"]) for s in sesiones for v in s["votaciones_nominales"])
    exp_votados = {
        v.get("id_expediente")
        for s in sesiones for v in s["votaciones_nominales"]
        if v.get("id_expediente")
    }

    dataset = {
        "version": 1,
        "actualizado_en": now.isoformat(timespec="seconds"),
        "fuente": {
            "organismo": "Legislatura de la Ciudad Autónoma de Buenos Aires",
            "sistema": "Sistema de Consultas Parlamentarias",
            "busqueda_sesiones": urljoin(BASE, "pages/ExpedienteBusqueda.aspx#sesiones-avanzado"),
            "servicio_sesiones": urljoin(WS, "GetSesionesAvanzado"),
            "pagina_votaciones": urljoin(BASE, "pages/sesion_votaciones.aspx"),
        },
        "periodo_consultado": {"desde": desde, "hasta": hasta},
        "resumen": {
            "sesiones": len(sesiones),
            "sesiones_realizadas": sum(1 for s in sesiones if s["realizada"]),
            "registros_presentismo": total_presentismo,
            "asuntos_considerados": total_asuntos,
            "items_sanciones": total_sanciones,
            "votaciones_asuntos": votos_asuntos,
            "votos_nominales": votos_nominales,
            "expedientes_votados_unicos": len(exp_votados),
            "fallas": len(fallas),
        },
        "fallas": fallas,
        "sesiones": sesiones,
    }

    if contains_private_keys(dataset):
        raise SystemExit("Se detectaron claves privadas prohibidas en el dataset público")

    OUT.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{OUT} · {OUT.stat().st_size // 1024} KB")
    print(
        "Sesiones 2026 · "
        f"{len(sesiones)} sesiones · {dataset['resumen']['sesiones_realizadas']} realizadas · "
        f"{votos_asuntos} asuntos votados · {votos_nominales} votos nominales · "
        f"fallas: {len(fallas)}"
    )

    if fallas:
        for item in fallas:
            print(f"  ✘ sesión {item['id_sesion']}: {item['error']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
