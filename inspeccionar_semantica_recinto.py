#!/usr/bin/env python3
"""Sonda temporal v2.25: compara asuntos considerados vs. item de asunto de sesión."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import requests

from actualizar_sesiones import clean, extract_nodes, post_xml

DATA = Path("sesiones_publicas.json")


def key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        clean(row.get("id_expediente")),
        clean(row.get("nro_de_expediente")),
        clean(row.get("descripcion")),
    )


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    http = requests.Session()
    for sesion in data.get("sesiones") or []:
        sid = clean(sesion.get("id_sesion"))
        asuntos = extract_nodes(
            post_xml(http, "GetAsuntosConsideradosByIdSesion", {"IdSesion": sid}),
            "asuntosConsiderados",
        )
        items = extract_nodes(
            post_xml(http, "GetAsuntoConsideradoItemByIdSesion", {"idSesion": sid}),
            "asuntoconsideradoitem",
        )
        ka = {key(x) for x in asuntos}
        ki = {key(x) for x in items}
        tipos = Counter(clean(x.get("asunto_considerado_item_tipo_des")) or "(vacío)" for x in items)
        print(f"sesión {sid}: asuntos={len(asuntos)} items={len(items)} intersección={len(ka & ki)} iguales={ka == ki}")
        print("  tipos item:", dict(sorted(tipos.items())))
        if items:
            print("  claves item:", sorted(items[0].keys()))
            muestra = {
                k: v for k, v in items[0].items()
                if any(t in k.lower() for t in ("exped", "tipo", "aprob", "sanc", "result", "descripcion"))
            }
            print("  muestra semántica:", muestra)


if __name__ == "__main__":
    main()
