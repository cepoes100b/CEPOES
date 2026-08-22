from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

CPA_CABA_RE = re.compile(r"^C\d{4}[A-Z]{3}$", re.I)
PERIODO_DEUDORES_RE = re.compile(r"(?:^|[^0-9])(\d{6})DEUDORES(?:[^A-Z]|$)", re.I)
MIN_CELDA_BARRIO = 30
CAMPOS_DEUDORES = 24


@dataclass(frozen=True)
class PadronPersona:
    tipo_tributario: str
    identificacion: str
    cpa: str


def leer_lineas(path: Path) -> Iterator[str]:
    """Lee en streaming. Los archivos del régimen BCRA se publican en ANSI-1252."""
    with path.open("r", encoding="cp1252", errors="strict", newline="") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if line.strip():
                yield line


def normalizar_cpa(value: str) -> str:
    return re.sub(r"\s+", "", (value or "").strip().upper())


def cargar_padron(path: Path) -> dict[tuple[str, str], PadronPersona]:
    """Reconstruye el estado del padrón reteniendo sólo PH con CPA de CABA.

    Diseño vigente BCRA PADRON.TXT: tipo id tributaria; número id tributaria;
    tipo id personal; número id personal; denominación; PEP; CPA; movimiento.
    Los campos de identificación personal distinguen a las personas humanas.
    """
    estado: dict[tuple[str, str], PadronPersona] = {}
    errores = 0
    for line in leer_lineas(path):
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
        if not tipo_personal or tipo_personal == "00":
            estado.pop(key, None)
            continue
        cpa_n = normalizar_cpa(cpa)
        if not CPA_CABA_RE.fullmatch(cpa_n):
            estado.pop(key, None)
            continue
        estado[key] = PadronPersona(tipo_trib, ident, cpa_n)
    if errores:
        print(f"Padrón: {errores} línea(s) descartadas por formato/código")
    if not estado:
        raise ValueError("El padrón no produjo personas humanas con CPA de CABA")
    return estado


def split_deudores(line: str) -> list[str]:
    """Parsea el diseño oficial deudores.txt: 24 campos delimitados por ';'."""
    row = [x.strip() for x in line.split(";")]
    if len(row) != CAMPOS_DEUDORES:
        raise ValueError(f"deudores.txt debe tener {CAMPOS_DEUDORES} campos; obtuvo {len(row)}")
    return row


def monto_a_pesos(raw: str) -> int:
    """Convierte un campo BCRA expresado en miles de pesos con un decimal a pesos.

    El diseño define once enteros y un decimal. Para tolerar exportaciones con el
    separador decimal explícito, también se acepta coma o punto.
    """
    s = (raw or "").strip().replace(" ", "")
    if not s:
        return 0
    if "," in s or "." in s:
        miles = float(s.replace(",", "."))
        if miles < 0:
            raise ValueError(f"monto negativo: {raw!r}")
        return int(round(miles * 1000))
    if not s.isdigit():
        raise ValueError(f"monto inválido: {raw!r}")
    # Sin separador explícito, la última posición es el decimal de miles.
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
            current = (barrio, comuna)
            prev = out.get(cpa)
            if prev and prev != current:
                raise ValueError(f"CPA con asignación territorial conflictiva: {cpa}: {prev} vs {current}")
            out[cpa] = current
    return out


def periodo_desde_archivo(path: Path) -> tuple[str, str]:
    m = PERIODO_DEUDORES_RE.search(path.name.upper())
    if not m:
        raise ValueError("El archivo mensual debe conservar el nombre AAAAMMDEUDORES.TXT")
    raw = m.group(1)
    datetime.strptime(raw, "%Y%m")
    return raw, f"{raw[:4]}-{raw[4:]}"


def metricas(items: Iterable[dict]) -> dict:
    total = mora = deuda = deuda_mora = 0
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


def procesar(archivo_deudores: Path, archivo_padron: Path, territorio_path: Path | None) -> dict:
    padron = cargar_padron(archivo_padron)
    territorio = cargar_territorio(territorio_path)
    periodo_raw, periodo = periodo_desde_archivo(archivo_deudores)

    por_persona: dict[tuple[str, str], dict] = {}
    registros = vinculados = 0
    for n, line in enumerate(leer_lineas(archivo_deudores), start=1):
        registros += 1
        try:
            row = split_deudores(line)
            # Diseño BCRA deudores.txt:
            # 1 entidad; 2 período; 3 tipo ID; 4 ID; 5 actividad; 6 situación;
            # 7 préstamos/garantías afrontadas; 8 sin uso; 9 garantías otorgadas;
            # 10 otros conceptos; 11..24 desagregaciones/atributos.
            _entidad, periodo_fila, tipo_trib, ident = row[:4]
            if periodo_fila != periodo_raw:
                raise ValueError(f"período de fila {periodo_fila!r} no coincide con {periodo_raw}")
            key = (tipo_trib, ident)
            persona_padron = padron.get(key)
            if not persona_padron:
                continue

            situacion = situacion_valida(row[5])
            if situacion == 0:
                continue

            # Equivale a 'Financiaciones y Otros conceptos' difundido por la CDSF:
            # componentes 2.1 + 2.2/2.3 + 3.1/3.2 del RI DSF.
            monto = sum(monto_a_pesos(row[i]) for i in (6, 8, 9))
            if monto <= 0:
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
            raise ValueError(f"DEUDORES línea {n}: {exc}") from exc

    personas = list(por_persona.values())
    caba = metricas(personas)

    barrio_items: dict[tuple[str, int], list[dict]] = defaultdict(list)
    cpa_mapeados: set[str] = set()
    personas_mapeadas = 0
    for p in personas:
        destino = territorio.get(p["cpa"])
        if destino:
            barrio_items[destino].append(p)
            cpa_mapeados.add(p["cpa"])
            personas_mapeadas += 1

    barrios = []
    celdas_suprimidas = 0
    personas_en_celdas_suprimidas = 0
    for (barrio, comuna), items in sorted(barrio_items.items(), key=lambda x: (x[0][1], x[0][0])):
        if len(items) < MIN_CELDA_BARRIO:
            celdas_suprimidas += 1
            personas_en_celdas_suprimidas += len(items)
            continue
        barrios.append({"barrio": barrio, "comuna": comuna, **metricas(items)})

    cobertura = round((personas_mapeadas / len(personas) * 100) if personas else 0, 2)
    return {
        "schema": 1,
        "producto": "endeudamiento_personas_humanas_caba",
        "periodo": periodo,
        "actualizado_utc": datetime.now(timezone.utc).isoformat(),
        "fuente": {
            "organismo": "Banco Central de la República Argentina",
            "base": "Central de Deudores del Sistema Financiero",
            "archivo_deuda": archivo_deudores.name,
            "archivo_padron": archivo_padron.name,
            "unidad_monto": "pesos corrientes",
            "composicion_monto": "préstamos/garantías afrontadas + garantías otorgadas + otros conceptos",
            "definicion_mora": "situaciones BCRA 3, 4 o 5 (más de 90 días de atraso)",
        },
        "metodologia": {
            "universo": "personas humanas con domicilio CPA de CABA presentes en el padrón BCRA y monto positivo en el archivo mensual DEUDORES",
            "unidad_publica": "agregados; nunca registros individuales",
            "criterio_persona_humana": "tipo de identificación personal del PADRON distinto de 00",
            "territorializacion": "CPA BCRA vinculado a una tabla CPA→barrio/comuna; el CPA individual no se publica",
            "minimo_publicacion_barrio": MIN_CELDA_BARRIO,
            "advertencias": [
                "El padrón aporta domicilio de la persona, no necesariamente el lugar donde contrajo la deuda.",
                "La fuente observa personas humanas, no hogares individualizados.",
                "Desde julio de 2024 el umbral mínimo de información a la Central de Deudores pasó de $1.000 a $25.000; las series de cantidad de deudores deben interpretar ese quiebre.",
            ],
        },
        "cobertura_procesamiento": {
            "registros_deudores_leidos": registros,
            "registros_entidad_vinculados_caba": vinculados,
            "personas_humanas_caba": len(personas),
            "personas_con_barrio_asignado": personas_mapeadas,
            "porcentaje_personas_con_barrio_asignado": cobertura,
            "cpa_territoriales_distintos_mapeados": len(cpa_mapeados),
            "celdas_barrio_suprimidas": celdas_suprimidas,
            "personas_en_celdas_suprimidas": personas_en_celdas_suprimidas,
        },
        "caba": caba,
        "barrios": barrios,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Agrega DEUDORES mensual + PADRON BCRA sin publicar datos personales")
    ap.add_argument("--deuda", required=True, type=Path, help="TXT extraído de AAAAMMDEUDORES.7Z, conservando AAAAMMDEUDORES.TXT")
    ap.add_argument("--padron", required=True, type=Path, help="PADRON.TXT extraído del .7Z, conservando AAAAMMDDPADRON.TXT")
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
        f"territorializados {cov['porcentaje_personas_con_barrio_asignado']}% · "
        f"barrios publicados {len(data['barrios'])}"
    )


if __name__ == "__main__":
    main()
