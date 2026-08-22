#!/usr/bin/env python3
"""Diagnóstico agregado del campo código postal del Padrón ARCA para CABA.

Objetivos:
- describir el formato real del campo código_postal entre personas M/F con provincia=00;
- medir cuánto del universo deudor queda con código postal informado, numérico, de 4 dígitos
  y dentro del rango 1000-1499 como hipótesis de sensibilidad;
- identificar los códigos postales más frecuentes sólo mediante conteos agregados;
- no publicar ni persistir CUIT/CUIL/CDI ni filas individuales.

La regla 1000-1499 es exclusivamente diagnóstica. No se adopta como definición territorial
hasta contar con una correspondencia oficial/reproducible para CABA.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from reconciliar_bcra_entidades import (
    EXCLUIR_SGR_FGCP,
    LONG_DEUDORES,
    LONG_PADRON,
    MORA,
    REFERENCIA,
    buscar_interno,
    monto_u100,
    stream_lineas,
)

SIT_1_5 = {b"1", b"2", b"3", b"4", b"5"}

CLASE_CUALQUIER_CP = 1
CLASE_CP_INFORMADO = 2
CLASE_CP_NUMERICO = 4
CLASE_CP_4_DIGITOS = 8
CLASE_CP_1000_1499 = 16


def clases_cp(cp: bytes) -> int:
    cp = cp.strip()
    bits = CLASE_CUALQUIER_CP
    if not cp:
        return bits
    bits |= CLASE_CP_INFORMADO
    if cp.isdigit():
        bits |= CLASE_CP_NUMERICO
        if len(cp) == 4:
            bits |= CLASE_CP_4_DIGITOS
            valor = int(cp)
            if 1000 <= valor <= 1499:
                bits |= CLASE_CP_1000_1499
    return bits


def nuevo_stats() -> dict:
    return {
        "deudores": 0,
        "personas_mora": 0,
        "deuda_u100": 0,
        "deuda_mora_u100": 0,
        "registros": 0,
    }


def sumar_registro(stats: dict, deuda_u100: int, es_mora: bool) -> None:
    stats["deuda_u100"] += deuda_u100
    stats["registros"] += 1
    if es_mora:
        stats["deuda_mora_u100"] += deuda_u100


def resumen(stats: dict) -> dict:
    deuda = stats["deuda_u100"] * 100
    deuda_mora = stats["deuda_mora_u100"] * 100
    deudores = stats["deudores"]
    morosos = stats["personas_mora"]
    return {
        "deudores": deudores,
        "personas_mora": morosos,
        "incidencia_mora_pct": round(morosos / deudores * 100, 4) if deudores else 0.0,
        "deuda_total_pesos": deuda,
        "deuda_mora_pesos": deuda_mora,
        "tasa_mora_pct": round(deuda_mora / deuda * 100, 4) if deuda else 0.0,
        "registros_incluidos": stats["registros"],
    }


def desv(valor: float, ref: float) -> float | None:
    return round((valor / ref - 1) * 100, 3) if ref else None


def contra_referencia(ind: dict) -> dict:
    return {
        "deudores_pct": desv(ind["deudores"], REFERENCIA["deudores"]),
        "personas_mora_pct": desv(ind["personas_mora"], REFERENCIA["personas_mora"]),
        "incidencia_mora_diferencia_pp": round(ind["incidencia_mora_pct"] - REFERENCIA["incidencia_mora_pct"], 4),
        "deuda_total_pct": desv(ind["deuda_total_pesos"], REFERENCIA["deuda_total_pesos"]),
        "deuda_mora_pct": desv(ind["deuda_mora_pesos"], REFERENCIA["deuda_mora_pesos"]),
        "tasa_mora_diferencia_pp": round(ind["tasa_mora_pct"] - REFERENCIA["tasa_mora_pct"], 4),
    }


def main() -> int:
    carpeta = Path("bcra_deudores")
    padrones = sorted(carpeta.glob("*PADRON.7Z"))
    deudores_arch = sorted(carpeta.glob("*DEUDORES.7Z"))
    if not padrones or not deudores_arch:
        raise SystemExit("Se requieren PADRON.7Z y DEUDORES.7Z")

    padron = padrones[-1]
    deudores = deudores_arch[-1]
    p_int = buscar_interno(padron, "Padron_ARCA.txt")
    d_int = buscar_interno(deudores, "deudores.txt")

    # id -> (bitmask de clase postal, CP numérico o -1). El CP se conserva sólo en RAM
    # durante esta ejecución para construir agregados geográficos; nunca se publica por persona.
    universo: dict[int, tuple[int, int]] = {}
    formato = Counter()
    cp_padron = Counter()
    padron_leidos = 0

    print("[1/2] PADRON: perfilando código postal para provincia 00", flush=True)
    for raw in stream_lineas(padron, p_int):
        if not raw:
            continue
        padron_leidos += 1
        if len(raw) != LONG_PADRON or raw[210:212] != b"00":
            continue
        if raw[199:200].strip().upper() not in (b"M", b"F"):
            continue
        ident_b = raw[0:11].strip()
        if len(ident_b) != 11 or not ident_b.isdigit():
            continue

        cp = raw[200:210].strip()
        bits = clases_cp(cp)
        cp_num = int(cp) if cp and cp.isdigit() else -1
        universo[int(ident_b)] = (bits, cp_num)

        if not cp:
            formato["vacio"] += 1
        elif cp.isdigit():
            formato["numerico"] += 1
            formato[f"numerico_longitud_{len(cp)}"] += 1
            if len(cp) == 4:
                valor = int(cp)
                cp_padron[str(valor)] += 1
                if 1000 <= valor <= 1499:
                    formato["numerico_4d_1000_1499"] += 1
                else:
                    formato["numerico_4d_fuera_1000_1499"] += 1
        else:
            formato["no_numerico"] += 1
            formato[f"no_numerico_longitud_{len(cp)}"] += 1

        if padron_leidos % 10_000_000 == 0:
            print(f"  PADRON {padron_leidos:,}; IDs M/F provincia 00 {len(universo):,}", flush=True)

    if not universo:
        raise SystemExit("Universo provincia 00 vacío")

    nombres = {
        "A_prov00_cualquier_cp": CLASE_CUALQUIER_CP,
        "B_prov00_cp_informado": CLASE_CP_INFORMADO,
        "C_prov00_cp_numerico": CLASE_CP_NUMERICO,
        "D_prov00_cp_4_digitos": CLASE_CP_4_DIGITOS,
        "E_prov00_cp_1000_1499": CLASE_CP_1000_1499,
    }
    escenarios = {nombre: nuevo_stats() for nombre in nombres}

    # Un solo set global alcanza para deduplicar personas: cada ID tiene una única clase postal
    # en el PADRON usado. Luego se incrementan los escenarios compatibles cuando aparece por
    # primera vez en CENDEU.
    vistos: set[int] = set()
    morosos: set[int] = set()
    cp_deudores = Counter()
    cp_morosos = Counter()
    cp_deuda_u100 = Counter()
    cp_deuda_mora_u100 = Counter()
    registros_leidos = 0
    registros_validos_caba = 0
    montos_invalidos = 0

    print("[2/2] CENDEU: midiendo sensibilidad por disponibilidad/formato postal", flush=True)
    for raw in stream_lineas(deudores, d_int):
        if not raw:
            continue
        registros_leidos += 1
        if len(raw) != LONG_DEUDORES or raw[11:13].strip() != b"11":
            continue
        ident_b = raw[13:24].strip()
        if not ident_b.isdigit():
            continue
        ident = int(ident_b)
        info = universo.get(ident)
        if info is None:
            continue

        situ = raw[27:29].strip()
        if situ not in SIT_1_5:
            continue
        codigo = raw[0:5].decode("ascii", errors="replace").strip()
        if codigo in EXCLUIR_SGR_FGCP:
            continue
        m7 = monto_u100(raw[29:41])
        m10 = monto_u100(raw[65:77])
        if m7 is None or m10 is None:
            montos_invalidos += 1
            continue
        deuda = m7 + m10
        if deuda <= 0:
            continue

        registros_validos_caba += 1
        bits, cp_num = info
        es_mora = situ in MORA

        for nombre, mascara in nombres.items():
            if bits & mascara:
                sumar_registro(escenarios[nombre], deuda, es_mora)

        es_nuevo = ident not in vistos
        if es_nuevo:
            vistos.add(ident)
            for nombre, mascara in nombres.items():
                if bits & mascara:
                    escenarios[nombre]["deudores"] += 1
            if cp_num >= 0:
                cp_deudores[str(cp_num)] += 1

        if es_mora and ident not in morosos:
            morosos.add(ident)
            for nombre, mascara in nombres.items():
                if bits & mascara:
                    escenarios[nombre]["personas_mora"] += 1
            if cp_num >= 0:
                cp_morosos[str(cp_num)] += 1

        if cp_num >= 0:
            k = str(cp_num)
            cp_deuda_u100[k] += deuda
            if es_mora:
                cp_deuda_mora_u100[k] += deuda

        if registros_leidos % 10_000_000 == 0:
            print(f"  CENDEU {registros_leidos:,}; deudores únicos prov00 {len(vistos):,}", flush=True)

    salida_esc = {}
    for nombre, stats in escenarios.items():
        ind = resumen(stats)
        salida_esc[nombre] = {
            "indicadores": ind,
            "reconciliacion_v228": contra_referencia(ind),
        }

    # Sólo códigos con al menos 100 deudores; salida agregada, nunca vinculada a individuos.
    cp_rows = []
    for cp, ndeu in cp_deudores.most_common():
        if ndeu < 100:
            break
        nmora = cp_morosos[cp]
        deuda_pesos = cp_deuda_u100[cp] * 100
        deuda_mora_pesos = cp_deuda_mora_u100[cp] * 100
        cp_rows.append({
            "codigo_postal": cp,
            "deudores": ndeu,
            "personas_mora": nmora,
            "incidencia_mora_pct": round(nmora / ndeu * 100, 4) if ndeu else 0.0,
            "deuda_total_pesos": deuda_pesos,
            "deuda_mora_pesos": deuda_mora_pesos,
            "tasa_mora_pct": round(deuda_mora_pesos / deuda_pesos * 100, 4) if deuda_pesos else 0.0,
        })

    top_padron = [
        {"codigo_postal": cp, "personas_padron_mf_prov00": n}
        for cp, n in cp_padron.most_common(100)
    ]

    salida = {
        "schema": "cepoes-bcra-diagnostico-postal-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "fuentes": {"padron": padron.name, "deudores": deudores.name},
        "criterio_base_cendeu": {
            "persona": "sexo ARCA M/F y provincia ARCA=00",
            "situaciones": [1, 2, 3, 4, 5],
            "mora": [3, 4, 5],
            "deuda_positiva": True,
            "excluye_sgr_fgcp": True,
            "mercado_secundario": "no excluido por falta de regla documental validada",
        },
        "controles_padron": {
            "registros_leidos": padron_leidos,
            "ids_mf_prov00": len(universo),
            "formato_codigo_postal": dict(sorted(formato.items())),
            "top_100_cp_4_digitos_en_padron": top_padron,
        },
        "controles_cendeu": {
            "registros_leidos": registros_leidos,
            "registros_validos_prov00": registros_validos_caba,
            "montos_invalidos": montos_invalidos,
            "cp_con_al_menos_100_deudores": cp_rows,
        },
        "escenarios": salida_esc,
        "referencia_v228": REFERENCIA,
        "nota_metodologica": "Los escenarios por CP son pruebas de sensibilidad. El rango 1000-1499 no se adopta como regla de CABA ni de barrio sin validación geográfica externa.",
        "privacidad": {
            "microdatos_publicados": False,
            "identificadores_en_salida": False,
            "nombres_en_salida": False,
            "filas_individuales_en_salida": False,
            "codigos_postales_solo_agregados": True,
            "umbral_minimo_deudores_por_cp_publicado": 100,
            "microdatos_descomprimidos_en_disco": False,
        },
    }

    Path("diagnostico_codigo_postal_caba.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "formato_codigo_postal": salida["controles_padron"]["formato_codigo_postal"],
        "escenarios": salida_esc,
        "top_20_cp_deudores": cp_rows[:20],
    }, ensure_ascii=False, indent=2), flush=True)
    print("OK -> diagnostico_codigo_postal_caba.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
