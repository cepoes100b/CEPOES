#!/usr/bin/env python3
"""Diagnóstico de sensibilidad del universo CABA para CENDEU.

Contrasta decisiones metodológicas que pueden explicar la brecha con la referencia v2.28:
- incluir o no situación 11;
- exigir deuda positiva (campo 7 + campo 10 > 0);
- excluir SGR/FGCP documentadas;
- territorializar por provincia ARCA=00, por CPA con prefijo C, o por ambas.

Privacidad: PADRON y DEUDORES se leen en streaming desde los .7z; la salida contiene
sólo agregados y nunca identificadores ni filas individuales.
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
BIT_PROV00 = 1
BIT_CPA_C = 2


def agregar(esc: dict, ident: int, deuda_u100: int, es_mora: bool) -> None:
    esc["ids"].add(ident)
    esc["deuda_u100"] += deuda_u100
    esc["registros"] += 1
    if es_mora:
        esc["mora_ids"].add(ident)
        esc["deuda_mora_u100"] += deuda_u100


def nuevo_escenario() -> dict:
    return {
        "ids": set(),
        "mora_ids": set(),
        "deuda_u100": 0,
        "deuda_mora_u100": 0,
        "registros": 0,
    }


def resumir(esc: dict) -> dict:
    deudores = len(esc["ids"])
    morosos = len(esc["mora_ids"])
    deuda = esc["deuda_u100"] * 100
    deuda_mora = esc["deuda_mora_u100"] * 100
    incidencia = morosos / deudores * 100 if deudores else 0.0
    tasa = deuda_mora / deuda * 100 if deuda else 0.0
    return {
        "deudores": deudores,
        "personas_mora": morosos,
        "incidencia_mora_pct": round(incidencia, 4),
        "deuda_total_pesos": deuda,
        "deuda_mora_pesos": deuda_mora,
        "tasa_mora_pct": round(tasa, 4),
        "registros_incluidos": esc["registros"],
    }


def desviacion(valor: float, ref: float) -> float | None:
    return round((valor / ref - 1) * 100, 3) if ref else None


def reconciliar(ind: dict) -> dict:
    return {
        "deudores_pct": desviacion(ind["deudores"], REFERENCIA["deudores"]),
        "personas_mora_pct": desviacion(ind["personas_mora"], REFERENCIA["personas_mora"]),
        "incidencia_mora_diferencia_pp": round(ind["incidencia_mora_pct"] - REFERENCIA["incidencia_mora_pct"], 4),
        "deuda_total_pct": desviacion(ind["deuda_total_pesos"], REFERENCIA["deuda_total_pesos"]),
        "deuda_mora_pct": desviacion(ind["deuda_mora_pesos"], REFERENCIA["deuda_mora_pesos"]),
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

    # Sólo guardamos IDs de personas M/F que pueden pertenecer a CABA por alguno de
    # los dos criterios territoriales. El valor es un bitmask, no conserva CP ni domicilio.
    flags: dict[int, int] = {}
    padron_leidos = 0
    control_cp = Counter()
    print("[1/2] PADRON: construyendo flags territoriales agregables", flush=True)
    for raw in stream_lineas(padron, p_int):
        if not raw:
            continue
        padron_leidos += 1
        if len(raw) != LONG_PADRON:
            continue
        if raw[199:200].strip().upper() not in (b"M", b"F"):
            continue
        ident_b = raw[0:11].strip()
        if len(ident_b) != 11 or not ident_b.isdigit():
            continue
        prov00 = raw[210:212] == b"00"
        cp = raw[200:210].strip().upper()
        cpa_c = cp.startswith(b"C")
        if prov00:
            if not cp:
                control_cp["prov00_cp_vacio"] += 1
            elif cpa_c:
                control_cp["prov00_cp_prefijo_C"] += 1
            elif cp.isdigit():
                control_cp["prov00_cp_numerico"] += 1
            else:
                control_cp["prov00_cp_otro"] += 1
        bit = (BIT_PROV00 if prov00 else 0) | (BIT_CPA_C if cpa_c else 0)
        if bit:
            ident = int(ident_b)
            flags[ident] = flags.get(ident, 0) | bit
        if padron_leidos % 10_000_000 == 0:
            print(f"  PADRON {padron_leidos:,}; IDs territoriales {len(flags):,}", flush=True)

    if not flags:
        raise SystemExit("No se construyó universo territorial")

    escenarios = {
        "A_prov00_todas_situaciones_cualquier_monto": nuevo_escenario(),
        "B_prov00_situaciones_1_5_cualquier_monto": nuevo_escenario(),
        "C_prov00_situaciones_1_5_deuda_positiva": nuevo_escenario(),
        "D_prov00_sit_1_5_deuda_pos_sin_sgr_fgcp": nuevo_escenario(),
        "E_cpa_C_sit_1_5_deuda_pos_sin_sgr_fgcp": nuevo_escenario(),
        "F_prov00_y_cpa_C_sit_1_5_deuda_pos_sin_sgr_fgcp": nuevo_escenario(),
    }
    situaciones = Counter()
    monto_cero = Counter()
    registros_leidos = 0
    montos_invalidos = 0

    print("[2/2] CENDEU: calculando escenarios", flush=True)
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
        bit = flags.get(ident, 0)
        if not bit:
            continue
        codigo = raw[0:5].decode("ascii", errors="replace").strip()
        situ = raw[27:29].strip()
        situaciones[situ.decode("ascii", errors="replace") or "vacio"] += 1
        m7 = monto_u100(raw[29:41])
        m10 = monto_u100(raw[65:77])
        if m7 is None or m10 is None:
            montos_invalidos += 1
            continue
        deuda = m7 + m10
        es_mora = situ in MORA
        if deuda == 0:
            monto_cero["registros_deuda_cero"] += 1
            if situ in SIT_1_5:
                monto_cero["registros_deuda_cero_sit_1_5"] += 1

        prov00 = bool(bit & BIT_PROV00)
        cpa_c = bool(bit & BIT_CPA_C)

        if prov00:
            agregar(escenarios["A_prov00_todas_situaciones_cualquier_monto"], ident, deuda, es_mora)
        if prov00 and situ in SIT_1_5:
            agregar(escenarios["B_prov00_situaciones_1_5_cualquier_monto"], ident, deuda, es_mora)
            if deuda > 0:
                agregar(escenarios["C_prov00_situaciones_1_5_deuda_positiva"], ident, deuda, es_mora)
                if codigo not in EXCLUIR_SGR_FGCP:
                    agregar(escenarios["D_prov00_sit_1_5_deuda_pos_sin_sgr_fgcp"], ident, deuda, es_mora)
        if situ in SIT_1_5 and deuda > 0 and codigo not in EXCLUIR_SGR_FGCP:
            if cpa_c:
                agregar(escenarios["E_cpa_C_sit_1_5_deuda_pos_sin_sgr_fgcp"], ident, deuda, es_mora)
            if prov00 and cpa_c:
                agregar(escenarios["F_prov00_y_cpa_C_sit_1_5_deuda_pos_sin_sgr_fgcp"], ident, deuda, es_mora)

        if registros_leidos % 10_000_000 == 0:
            print(f"  CENDEU {registros_leidos:,}", flush=True)

    salida_esc = {}
    for nombre, esc in escenarios.items():
        ind = resumir(esc)
        salida_esc[nombre] = {
            "indicadores": ind,
            "reconciliacion_v228": reconciliar(ind),
        }

    salida = {
        "schema": "cepoes-bcra-diagnostico-universo-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "fuentes": {"padron": padron.name, "deudores": deudores.name},
        "criterios": {
            "persona_humana_operativa": "sexo ARCA M/F; no se infiere por CUIT",
            "situaciones_mapa_publicadas": [1, 2, 3, 4, 5],
            "mora": [3, 4, 5],
            "deuda": "campo 7 + campo 10, importes BCRA en miles de pesos con un decimal",
            "cpa_caba_sensibilidad": "prefijo C del campo código postal ARCA; se contrasta con provincia 00 y no se adopta aún como regla final",
        },
        "controles_padron": {
            "registros_leidos": padron_leidos,
            "ids_mf_prov00_o_cpa_C": len(flags),
            "distribucion_cp_entre_prov00_mf": dict(sorted(control_cp.items())),
        },
        "controles_cendeu": {
            "registros_leidos": registros_leidos,
            "situaciones_en_universo_territorial": dict(sorted(situaciones.items())),
            "montos_invalidos": montos_invalidos,
            **dict(sorted(monto_cero.items())),
        },
        "escenarios": salida_esc,
        "referencia_v228": REFERENCIA,
        "privacidad": {
            "microdatos_publicados": False,
            "identificadores_en_salida": False,
            "codigos_postales_en_salida": False,
            "microdatos_descomprimidos_en_disco": False,
        },
    }
    Path("diagnostico_universo_caba.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"escenarios": salida_esc, "controles_padron": salida["controles_padron"]}, ensure_ascii=False, indent=2))
    print("OK -> diagnostico_universo_caba.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
