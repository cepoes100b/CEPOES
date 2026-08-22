from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

CPA_VALUE_RE = re.compile(r"\bC\d{4}[A-Z]{3}\b", re.I)
ID11_VALUE_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
PERIODO_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
FORBIDDEN_KEYS = {
    "identificacion", "identificador", "cuit", "cuil", "cdi", "documento",
    "documento_personal", "denominacion", "nombre_persona", "domicilio",
    "calle", "altura", "cpa",
}
METRIC_KEYS = {
    "deudores", "deudores_en_mora", "porcentaje_deudores_en_mora",
    "deuda_pesos", "deuda_en_mora_pesos", "tasa_mora_deuda",
    "deudores_por_situacion_maxima",
}


def fail(msg: str) -> None:
    raise ValueError(msg)


def pct(num: int, den: int) -> float:
    return round((num / den * 100) if den else 0, 2)


def walk_privacy(value: Any, path: str = "$", parent_key: str | None = None) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            lk = str(k).strip().lower()
            if lk in FORBIDDEN_KEYS:
                fail(f"clave individual prohibida en salida pública: {path}.{k}")
            walk_privacy(v, f"{path}.{k}", lk)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            walk_privacy(v, f"{path}[{i}]", parent_key)
    elif isinstance(value, str):
        # Evitar falsos positivos en metadatos documentales que contienen 11 dígitos
        # sólo si son nombres de archivo o fechas; un CPA completo nunca debe aparecer.
        if CPA_VALUE_RE.search(value):
            fail(f"CPA individual detectado en salida pública: {path}")
        if parent_key not in {"archivo_deuda", "archivo_padron", "actualizado_utc"} and ID11_VALUE_RE.search(value):
            fail(f"identificador de 11 dígitos detectado en salida pública: {path}")


def validate_metrics(obj: dict, label: str, min_deudores: int = 0) -> None:
    missing = METRIC_KEYS - set(obj)
    if missing:
        fail(f"{label}: faltan métricas {sorted(missing)}")
    d = obj["deudores"]
    m = obj["deudores_en_mora"]
    deuda = obj["deuda_pesos"]
    deuda_mora = obj["deuda_en_mora_pesos"]
    if not all(isinstance(x, int) and x >= 0 for x in (d, m, deuda, deuda_mora)):
        fail(f"{label}: cantidades/montos deben ser enteros no negativos")
    if d < min_deudores:
        fail(f"{label}: deudores {d} por debajo del mínimo público {min_deudores}")
    if m > d:
        fail(f"{label}: deudores en mora supera total")
    if deuda_mora > deuda:
        fail(f"{label}: deuda en mora supera deuda total")
    if obj["porcentaje_deudores_en_mora"] != pct(m, d):
        fail(f"{label}: porcentaje de deudores en mora inconsistente")
    if obj["tasa_mora_deuda"] != pct(deuda_mora, deuda):
        fail(f"{label}: tasa de mora de deuda inconsistente")
    situ = obj["deudores_por_situacion_maxima"]
    if set(situ) != {"1", "2", "3", "4", "5"}:
        fail(f"{label}: distribución de situación debe contener 1..5")
    if not all(isinstance(v, int) and v >= 0 for v in situ.values()):
        fail(f"{label}: distribución de situación inválida")
    if sum(situ.values()) != d:
        fail(f"{label}: distribución de situación no suma deudores")
    if sum(situ[str(i)] for i in (3, 4, 5)) > d:
        fail(f"{label}: situaciones de mora inválidas")


def verificar(data: dict) -> None:
    if data.get("schema") != 1:
        fail("schema de endeudamiento debe ser 1")
    if data.get("producto") != "endeudamiento_personas_humanas_caba":
        fail("producto inesperado")
    if not PERIODO_RE.fullmatch(str(data.get("periodo", ""))):
        fail("periodo debe ser YYYY-MM")

    fuente = data.get("fuente") or {}
    if fuente.get("organismo") != "Banco Central de la República Argentina":
        fail("organismo fuente inesperado")
    if not re.search(r"24DSF\d{6}", str(fuente.get("archivo_deuda", "")), re.I):
        fail("archivo de deuda no identifica 24DSF y período")
    if not re.search(r"\d{8}PADRON", str(fuente.get("archivo_padron", "")), re.I):
        fail("archivo padrón no conserva fecha/nombre oficial")

    metodologia = data.get("metodologia") or {}
    minimo = metodologia.get("minimo_publicacion_barrio")
    if not isinstance(minimo, int) or minimo < 30:
        fail("mínimo de publicación territorial debe ser >=30")

    cobertura = data.get("cobertura_procesamiento") or {}
    ph = cobertura.get("personas_humanas_caba")
    mapped = cobertura.get("personas_con_barrio_asignado")
    suppressed = cobertura.get("personas_en_celdas_suprimidas")
    if not all(isinstance(x, int) and x >= 0 for x in (ph, mapped, suppressed)):
        fail("cobertura: cantidades inválidas")
    if mapped > ph:
        fail("cobertura: territorializados supera personas CABA")
    expected_cov = pct(mapped, ph)
    if cobertura.get("porcentaje_personas_con_barrio_asignado") != expected_cov:
        fail("cobertura: porcentaje territorial inconsistente")
    if suppressed > mapped:
        fail("cobertura: personas suprimidas supera territorializadas")

    caba = data.get("caba")
    if not isinstance(caba, dict):
        fail("falta agregado CABA")
    validate_metrics(caba, "CABA")
    if caba["deudores"] != ph:
        fail("CABA: deudores no coincide con personas_humanas_caba")

    barrios = data.get("barrios")
    if not isinstance(barrios, list):
        fail("barrios debe ser lista")
    seen: set[str] = set()
    pub_deudores = 0
    pub_deuda = 0
    pub_mora = 0
    pub_deuda_mora = 0
    for b in barrios:
        if not isinstance(b, dict):
            fail("barrio no es objeto")
        nombre = str(b.get("barrio", "")).strip()
        comuna = b.get("comuna")
        if not nombre or nombre in seen:
            fail(f"barrio vacío o duplicado: {nombre!r}")
        seen.add(nombre)
        if not isinstance(comuna, int) or not 1 <= comuna <= 15:
            fail(f"{nombre}: comuna inválida")
        validate_metrics(b, f"barrio {nombre}", min_deudores=minimo)
        pub_deudores += b["deudores"]
        pub_mora += b["deudores_en_mora"]
        pub_deuda += b["deuda_pesos"]
        pub_deuda_mora += b["deuda_en_mora_pesos"]

    if pub_deudores + suppressed > mapped:
        fail("barrios: publicados + suprimidos supera personas territorializadas")
    if pub_mora > caba["deudores_en_mora"] or pub_deuda > caba["deuda_pesos"] or pub_deuda_mora > caba["deuda_en_mora_pesos"]:
        fail("barrios: suma publicada supera agregado CABA")

    walk_privacy(data)


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "endeudamiento_caba.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    verificar(data)
    print(
        f"✔ endeudamiento verificado · período {data['periodo']} · "
        f"{data['caba']['deudores']} deudores · {len(data['barrios'])} barrios publicados · sin datos individuales"
    )


if __name__ == "__main__":
    main()
