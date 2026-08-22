#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

PATH = Path("sesiones_publicas.json")


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm(value) -> str:
    s = unicodedata.normalize("NFKD", clean(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def alcance_sancion(descripcion: str) -> str:
    text = norm(descripcion)
    if "sancion inicial" in text:
        return "inicial"
    if "sancion definitiva" in text:
        return "definitiva"
    if re.match(r"^(ley|declaracion|resolucion)\s+nro\.?\s*\d", text):
        return "definitiva"
    return "no_especificada"


def main() -> int:
    if not PATH.exists():
        print("✘ falta sesiones_publicas.json")
        return 1

    data = json.loads(PATH.read_text(encoding="utf-8"))
    sesiones = data.get("sesiones") or []
    total_items = total_exp = total_despacho = total_giro = 0
    alcances = Counter()
    tipos = Counter()

    for sesion in sesiones:
        raw = sesion.get("items_recinto")
        if raw is None:
            raw = sesion.get("sanciones") or []
        raw = list(raw)
        sesion["items_recinto"] = raw

        sanciones = []
        despachos = []
        giros = []
        for item in raw:
            tipo = norm(item.get("tipo"))
            tipos[tipo or "(vacio)"] += 1
            if tipo == "sancion de un expediente":
                row = dict(item)
                row["alcance"] = alcance_sancion(clean(item.get("descripcion")))
                sanciones.append(row)
                alcances[row["alcance"]] += 1
            elif tipo == "sancion de un despacho":
                despachos.append(dict(item))
            elif tipo == "cambio de giro":
                giros.append(dict(item))

        sesion["sanciones"] = sanciones
        sesion["sanciones_despacho"] = despachos
        sesion["cambios_giro"] = giros
        sesion["resumen_items_recinto"] = {
            "total": len(raw),
            "sanciones_expediente": len(sanciones),
            "sanciones_despacho": len(despachos),
            "cambios_giro": len(giros),
        }
        total_items += len(raw)
        total_exp += len(sanciones)
        total_despacho += len(despachos)
        total_giro += len(giros)

    resumen = data.setdefault("resumen", {})
    resumen.pop("items_sanciones", None)
    resumen.update({
        "items_recinto": total_items,
        "sanciones_expediente": total_exp,
        "sanciones_despacho": total_despacho,
        "cambios_giro": total_giro,
        "sanciones_por_alcance": dict(sorted(alcances.items())),
    })
    data["version"] = 2
    data["normalizacion_recinto"] = {
        "schema": 1,
        "regla": "Solo SANCION DE UN EXPEDIENTE alimenta sanciones del expediente",
        "tipos_oficiales_observados": dict(sorted(tipos.items())),
        "alcance_sancion": "inicial, definitiva o no_especificada según descripción oficial",
    }

    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Normalización sesiones · items {total_items} · sanciones expediente {total_exp} · "
        f"sanciones despacho {total_despacho} · cambios giro {total_giro}"
    )
    print("  alcance sanciones: " + " · ".join(f"{k} {v}" for k, v in sorted(alcances.items())))
    print("  tipos oficiales: " + " · ".join(f"{k} {v}" for k, v in sorted(tipos.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
