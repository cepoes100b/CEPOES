#!/usr/bin/env python3
"""Detecta si BCRA publicó un nuevo período mensual de Central de Deudores.

No descarga microdatos. Lee únicamente la página pública de archivos del BCRA,
extrae los nombres AAAAMMDEUDORES.7Z y AAAAMMDDPADRON.7Z y los compara con el
último período agregado ya publicado por CEPOES.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://www5.bcra.gob.ar/ChequesyDeudores/Deudores"
MANIFEST = Path("datos/endeudamiento/manifest.json")
OUT = Path("novedad_bcra.json")
UA = "Mozilla/5.0 (compatible; CEPOES-endeudamiento/1.0; +https://cepoes.org)"


def periodo_iso(aaaamm: str) -> str:
    if not re.fullmatch(r"\d{6}", aaaamm):
        raise ValueError(f"Período inválido: {aaaamm!r}")
    return f"{aaaamm[:4]}-{aaaamm[4:]}"


def fecha_iso(aaaammdd: str) -> str:
    dt = datetime.strptime(aaaammdd, "%Y%m%d")
    return dt.date().isoformat()


def main() -> int:
    r = requests.get(URL, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    html = r.text.upper()

    deuda = sorted(set(re.findall(r"(\d{6})DEUDORES\.7Z", html)))
    padron = sorted(set(re.findall(r"(\d{8})PADRON\.7Z", html)))
    if not deuda:
        raise SystemExit("BCRA no expuso ningún archivo AAAAMMDEUDORES.7Z")
    if not padron:
        raise SystemExit("BCRA no expuso ningún archivo AAAAMMDDPADRON.7Z")

    ym = deuda[-1]
    pd = padron[-1]
    periodo = periodo_iso(ym)
    padron_fecha = fecha_iso(pd)

    ultimo = None
    if MANIFEST.exists():
        try:
            obj = json.loads(MANIFEST.read_text(encoding="utf-8"))
            ultimo = obj.get("ultimo_periodo") or obj.get("periodo")
        except Exception as exc:
            raise SystemExit(f"Manifest local inválido: {exc}")

    hay_novedad = ultimo is None or periodo > str(ultimo)
    salida = {
        "schema": "cepoes-bcra-novedad-v1",
        "consultado_utc": datetime.now(timezone.utc).isoformat(),
        "fuente": URL,
        "periodo": periodo,
        "archivo_deudores": f"{ym}DEUDORES.7Z",
        "padron_fecha": padron_fecha,
        "archivo_padron": f"{pd}PADRON.7Z",
        "ultimo_periodo_local": ultimo,
        "hay_novedad": hay_novedad,
        "motivo": "nuevo_periodo" if hay_novedad else "sin_cambios",
    }
    OUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
