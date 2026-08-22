from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

CPA_CABA_RE = re.compile(r"^C\d{4}[A-Z]{3}$", re.I)
PERIODO_RE = re.compile(r"24DSF(\d{6})", re.I)


@dataclass(frozen=True)
class PadronPersona:
    tipo_tributario: str
    identificacion: str
    cpa: str


def leer_lineas(path: Path) -> Iterable[str]:
    # Los regímenes BCRA usan ANSI/Windows-1252. utf-8-sig queda como tolerancia
    # para fixtures o futuras publicaciones que cambien de codificación.
    data = path.read_bytes()
    for enc in ("cp1252", "utf-8-sig"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"No se pudo decodificar {path}")
    for line in text.splitlines():
        if line.strip():
            yield line.rstrip("\r\n")


def normalizar_cpa(value: str) -> str:
    return re.sub(r"\s+", "", (value or "").strip().upper())


def cargar_padron(path: Path) -> dict[tuple[str, str], PadronPersona]:
    """Reconstruye el estado del padrón sin conservar denominaciones ni documentos personales.

    Layout BCRA vigente: tipo id tributaria; nro id tributaria; tipo id personal;
    nro id personal; denominación; PEP; CPA; tipo movimiento.
    Tipo de identificación personal distinto de 00 identifica persona humana según
    la especificación del padrón. Movimientos 10/30 actualizan; 20 elimina.
    """
    estado: dict[tuple[str, str], PadronPersona] = {}
    errores = 0
    for n, line in enumerate(leer_lineas(path), start=1):
        row = [x.strip() for x in line.split(";")]
        if len(row) != 8:
            errores += 1
            continue
        tipo_trib, ident, tipo_personal, _doc_personal, _denom, _pep, cpa, mov = row
        key = (tipo_trib, ident)
        if not ident:
            continue
        if mov == "20":
            estado.pop(key, None)
            continue
        if mov not in {"10", "30", ""}:
            errores += 1
            continue
        # La identificación personal sólo es obligatoria para personas humanas.
        if not tipo_personal or tipo_personal == "00":
            estado.pop(key, None)
            continue
        cpa_n = normalizar_cpa(cpa)
        if not CPA_CABA_RE.fullmatch(cpa_n):
            # No es un domicilio de CABA bajo el esquema CPA.
            estado.pop(key, None)
            continue
        estado[key] = PadronPersona(tipo_trib, ident, cpa_n)
    if errores:
        print(f"Padrón: {errores} línea(s) descartadas por formato/código")
    if not estado:
        raise ValueError("El padrón no produjo personas humanas con CPA de CABA")
    return estado


def split_24dsf(line: str) -> list[str]:
    """Acepta publicación delimitada o diseño de ancho fijo documentado por BCRA."""
    if ";" in line:
        return [x.strip() for x in line.split(";")]
    widths = [5, 2, 11] + [w for _ in range(24) for w in (2, 12, 1)]
    expected = sum(widths)
    if len(line) < expected:
        raise ValueError(f"registro 24DSF demasiado corto: {len(line)} < {expected}")
    out, pos = [], 0
    for width in widths:
        out.append(line[pos:pos + width].strip())
        pos += width
    return out


def monto_a_pesos(raw: str) -> int:
    """BCRA expresa montos en miles de pesos con un decimal."""
    s = (raw or "").strip().replace(" ", "")
    if not s:
        return 0
    if "," in s or "." in s:
        miles = float(s.replace(",", "."))
        return int(round(miles * 1000))
    if not s.isdigit():
        raise ValueError(f"monto inválido: {raw!r}")
    # Campo de 12 posiciones: once enteros y un decimal implícito.
    return int(s) * 100


def situacion_valida(raw: str) -> int:
    s = (raw or "").strip()
    if not s:
        return 0
    value = int(s)
    if value not in {1, 2, 3, 4, 5}:
        raise ValueError(f"situación BCRA fuera de 1..5: {value}")
    return value


def cargar_territorio(path: Path | None) -> dict[str, tuple[str, int]]:
    if path is None:
        return {}
    out: dict[str, tuple[str, int]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        expected = {"cpa", "barrio", "comuna"}
        if not expected.issubset(set(reader.fieldnames or [])):
            raise ValueError("cpa_territorio.csv debe contener cpa,barrio,comuna")
        for row in reader:
            cpa = normalizar_cpa(row["cpa"])
            if not CPA_CABA_RE.fullmatch(cpa):
                continue
            barrio = row["barrio"].strip()
            comuna = int(str(row["comuna"]).replace("Comuna", "").strip())
            if not barrio or not 1 <= comuna <= 15:
                continue
            prev = out.get(cpa)
            current = (barrio, comuna)
            if prev and prev != current:
                raise ValueError(f"CPA con asignación territorial conflictiva: {cpa}: {prev} vs {current}")
            out[cpa] = current
    return out


def periodo_desde_archivo(path: Path) -> str:
    m = PERIODO_RE.search(path.name)
    if not m:
        raise ValueError("El archivo 24DSF debe conservar AAAAMM en el nombre")
    raw = m.group(1)
    datetime.strptime(raw, "%Y%m")
    return f"{raw[:4]}-{raw[4:]}"


def métricas(items: Iterable[dict]) -> dict:
    total = 0
    mora = 0
    deuda = 0
    deuda_mora = 0
    sit = {str(i): 0 for i in range(1, 6)}
    for item in items:
        total += 1
        deuda += item["deuda_pesos"]
        worst = item["situacion_max"]
        sit[str(worst)] += 1
        if item["en_mora"]:
            mora += 1
        deuda_mora += item["deuda_mora_pesos"]
    return {
        "deudores": total,
        "deudores_en_mora": mora,
        "porcentaje_deudores_en_mora": round((mora / total * 100) if total else 0, 2),
        "deuda_pesos": deuda,
        "deuda_en_mora_pesos": deuda_mora,
        "tasa_mora_deuda": round((deuda_mora / deuda * 100) if deuda else 0, 2),
        "deudores_por_situacion_maxima": sit,
    }


def procesar(archivo_24dsf: Path, archivo_padron: Path, territorio_path: Path | None) -> dict:
    padron = cargar_padron(archivo_padron)
    territorio = cargar_territorio(territorio_path)
    periodo = periodo_desde_archivo(archivo_24dsf)

    por_persona: dict[tuple[str, str], dict] = {}
    registros = 0
    vinculados = 0
    for n, line in enumerate(leer_lineas(archivo_24dsf), start=1):
        registros += 1
        try:
            row = split_24dsf(line)
            if len(row) < 6:
                raise ValueError("faltan campos")
            _entidad, tipo_trib, ident = row[:3]
            key = (tipo_trib, ident)
            persona_padron = padron.get(key)
            if not persona_padron:
                continue
            situacion = situacion_valida(row[3])
            monto = monto_a_pesos(row[4])
            if situacion == 0 or monto <= 0:
                continue
            vinculados += 1
            p = por_persona.setdefault(key, {
                "cpa": persona_padron.cpa,
                "deuda_pesos": 0,
                "deuda_mora_pesos": 0,
                "situacion_max": 0,
                "en_mora": False,
            })
            p["deuda_pesos"] += monto
            p["situacion_max"] = max(p["situacion_max"], situacion)
            if situacion in {3, 4, 5}:
                p["en_mora"] = True
                p["deuda_mora_pesos"] += monto
        except Exception as exc:
            raise ValueError(f"24DSF línea {n}: {exc}") from exc

    personas = list(por_persona.values())
    caba = métricas(personas)

    barrio_items: dict[tuple[str, int], list[dict]] = defaultdict(list)
    cpa_mapeados = set()
    personas_mapeadas = 0
    for p in personas:
        destino = territorio.get(p["cpa"])
        if destino:
            barrio_items[destino].append(p)
            cpa_mapeados.add(p["cpa"])
            personas_mapeadas += 1

    barrios = []
    for (barrio, comuna), items in sorted(barrio_items.items(), key=lambda x: (x[0][1], x[0][0])):
        barrios.append({"barrio": barrio, "comuna": comuna, **métricas(items)})

    # Nunca se publican los CPA ni identificadores individuales. Sólo métricas de cobertura.
    cobertura = round((personas_mapeadas / len(personas) * 100) if personas else 0, 2)
    return {
        "schema": 1,
        "producto": "endeudamiento_personas_humanas_caba",
        "periodo": periodo,
        "actualizado_utc": datetime.now(timezone.utc).isoformat(),
        "fuente": {
            "organismo": "Banco Central de la República Argentina",
            "base": "Central de Deudores del Sistema Financiero",
            "archivo_deuda": archivo_24dsf.name,
            "archivo_padron": archivo_padron.name,
            "unidad_monto": "pesos corrientes",
            "definicion_mora": "situaciones BCRA 3, 4 o 5 (más de 90 días de atraso)",
        },
        "metodologia": {
            "universo": "personas humanas con domicilio CPA de CABA presentes en el padrón BCRA y deuda positiva en 24DSF",
            "unidad_publica": "agregados; nunca registros individuales",
            "criterio_persona_humana": "tipo de identificación personal del PADRON distinto de 00",
            "territorializacion": "CPA BCRA vinculado a una tabla CPA→barrio/comuna; el CPA individual no se publica",
            "advertencias": [
                "El padrón aporta domicilio de la persona, no necesariamente el lugar donde contrajo la deuda.",
                "Desde julio de 2024 el umbral mínimo de información a la Central de Deudores pasó de $1.000 a $25.000; las series de cantidad de deudores deben interpretar ese quiebre.",
            ],
        },
        "cobertura_procesamiento": {
            "registros_24dsf_leidos": registros,
            "registros_entidad_vinculados_caba": vinculados,
            "personas_humanas_caba": len(personas),
            "personas_con_barrio_asignado": personas_mapeadas,
            "porcentaje_personas_con_barrio_asignado": cobertura,
            "cpa_territoriales_distintos_mapeados": len(cpa_mapeados),
        },
        "caba": caba,
        "barrios": barrios,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Agrega 24DSF + PADRON BCRA sin publicar datos personales")
    ap.add_argument("--deuda", required=True, type=Path, help="TXT extraído de 24DSFAAAAMM.7Z")
    ap.add_argument("--padron", required=True, type=Path, help="PADRON.TXT extraído del .7Z")
    ap.add_argument("--territorio", type=Path, help="CSV cpa,barrio,comuna")
    ap.add_argument("--salida", type=Path, default=Path("endeudamiento_caba.json"))
    args = ap.parse_args()
    data = procesar(args.deuda, args.padron, args.territorio)
    args.salida.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    c = data["caba"]
    cov = data["cobertura_procesamiento"]
    print(
        f"Endeudamiento {data['periodo']} · {c['deudores']} deudores PH CABA · "
        f"{c['deudores_en_mora']} en mora ({c['porcentaje_deudores_en_mora']}%) · "
        f"territorializados {cov['porcentaje_personas_con_barrio_asignado']}%"
    )


if __name__ == "__main__":
    main()
