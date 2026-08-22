#!/usr/bin/env python3
"""Diagnóstico integral de universo y territorio para Endeudamiento CEPOES v2.29.

Una sola pasada sobre PADRON ARCA + CENDEU permite:
- construir el universo de acreedores desde los registros JSON vigentes del BCRA
  (entidades financieras + emisoras no financieras + otros PNFC);
- comparar tres reglas territoriales sin forzar coincidencia con el benchmark v2.28;
- producir agregados reutilizables por código postal tradicional, sexo y franja etaria;
- mantener todos los identificadores personales exclusivamente en RAM.

La salida contiene sólo agregados. No se escriben CUIT/CUIL/CDI, nombres de personas
ni filas individuales. Los archivos crudos permanecen comprimidos y se leen por
streaming mediante 7z.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from reconciliar_bcra_entidades import (
    LONG_DEUDORES,
    LONG_PADRON,
    MORA,
    REFERENCIA,
    buscar_interno,
    monto_u100,
    stream_lineas,
)

OUT = Path("diagnostico_universo_territorial_integral.json")
SIT_1_5 = {b"1", b"2", b"3", b"4", b"5"}
FECHA_CORTE_EDAD = date(2026, 6, 30)
UMBRAL_PUBLICACION_CELDA = 10

ENDPOINTS = {
    "entidad_financiera": {
        "url": "https://www.bcra.gob.ar/api/endpoints/nomina-entidades.php?action=nomina_AAA00&lang=es",
        "lista": "entidades",
        "minimo": 60,
    },
    "enf_emisora_tarjeta": {
        "url": "https://www.bcra.gob.ar/api/endpoints/emisoras-tarjetas-credito.php",
        "lista": "data",
        "minimo": 80,
    },
    "otro_pnfc": {
        "url": "https://www.bcra.gob.ar/api/endpoints/proveedores-no-financieros.php?lang=es",
        "lista": "data",
        "minimo": 400,
    },
}

# Bit packing del valor del diccionario personas. El identificador es la clave y
# nunca se serializa. Esto evita mantener múltiples sets de millones de personas.
CP_BITS = 14
CP_MASK = (1 << CP_BITS) - 1
BIT_PROV00 = 1 << 14
BIT_SEXO_M = 1 << 15
SHIFT_EDAD = 16
EDAD_MASK = 0xF << SHIFT_EDAD
BIT_SEEN = 1 << 20
BIT_MORA = 1 << 21

EDAD_LABELS = {
    0: "desconocida",
    1: "le25",
    2: "26_35",
    3: "36_45",
    4: "46_55",
    5: "56_65",
    6: "66_75",
    7: "gt75",
}

SCENARIOS = (
    "A_eeff_pnfc_prov00",
    "B_eeff_pnfc_cp1000_1499_cualquier_provincia",
    "C_eeff_pnfc_prov00_y_cp1000_1499",
    "D_eeff_pnfc_prov00_y_cp4_informado",
    "E_eeff_pnfc_cp1000_1499_fuera_prov00",
)


def codigo5(x) -> str:
    s = str(x).strip()
    if not s.isdigit():
        raise ValueError(f"Código institucional no numérico: {x!r}")
    return s.zfill(5)


def cargar_acreedores() -> tuple[set[str], dict, dict[str, set[str]]]:
    seleccion: set[str] = set()
    meta: dict = {}
    por_categoria: dict[str, set[str]] = {}
    for categoria, cfg in ENDPOINTS.items():
        r = requests.get(
            cfg["url"],
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; CEPOES-validacion-metodologica/1.0)",
                "Accept": "application/json,text/plain,*/*",
            },
            timeout=60,
        )
        r.raise_for_status()
        obj = r.json()
        filas = obj.get(cfg["lista"])
        if not isinstance(filas, list):
            raise RuntimeError(f"Respuesta sin lista {cfg['lista']!r}: {cfg['url']}")
        codigos = {
            codigo5(f["codigo"])
            for f in filas
            if isinstance(f, dict) and "codigo" in f
        }
        if len(codigos) < cfg["minimo"]:
            raise RuntimeError(
                f"Registro {categoria} inesperadamente corto: {len(codigos)} < {cfg['minimo']}"
            )
        por_categoria[categoria] = codigos
        seleccion |= codigos
        meta[categoria] = {
            "url": cfg["url"],
            "ruta_lista": f"$.{cfg['lista']}",
            "filas": len(filas),
            "codigos_unicos": len(codigos),
        }
        print(f"Registro {categoria}: {len(codigos)} códigos", flush=True)
    meta["union_eeff_pnfc"] = {
        "codigos_unicos": len(seleccion),
        "solapamiento_emisoras_opnfc": len(
            por_categoria["enf_emisora_tarjeta"] & por_categoria["otro_pnfc"]
        ),
    }
    return seleccion, meta, por_categoria


def cp4(raw: bytes) -> int:
    s = raw.strip()
    if len(s) != 4 or not s.isdigit():
        return 0
    n = int(s)
    return n if 1 <= n <= 9999 else 0


def banda_edad(raw: bytes) -> int:
    s = raw.strip()
    if len(s) != 8 or not s.isdigit() or s == b"19010101":
        return 0
    try:
        nac = date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except ValueError:
        return 0
    edad = FECHA_CORTE_EDAD.year - nac.year - (
        (FECHA_CORTE_EDAD.month, FECHA_CORTE_EDAD.day) < (nac.month, nac.day)
    )
    if edad < 0 or edad > 120:
        return 0
    if edad <= 25:
        return 1
    if edad <= 35:
        return 2
    if edad <= 45:
        return 3
    if edad <= 55:
        return 4
    if edad <= 65:
        return 5
    if edad <= 75:
        return 6
    return 7


def pack(cp: int, prov00: bool, sexo_m: bool, edad: int) -> int:
    return (
        cp
        | (BIT_PROV00 if prov00 else 0)
        | (BIT_SEXO_M if sexo_m else 0)
        | ((edad & 0xF) << SHIFT_EDAD)
    )


def attrs(v: int) -> tuple[int, bool, str, int]:
    cp = v & CP_MASK
    prov00 = bool(v & BIT_PROV00)
    sexo = "M" if v & BIT_SEXO_M else "F"
    edad = (v & EDAD_MASK) >> SHIFT_EDAD
    return cp, prov00, sexo, edad


def nuevo_acum() -> dict:
    return {
        "registros": 0,
        "deuda_u100": 0,
        "deuda_mora_u100": 0,
        "deudores": 0,
        "personas_mora": 0,
    }


def add_record(ac: dict, deuda_u100: int, es_mora: bool) -> None:
    ac["registros"] += 1
    ac["deuda_u100"] += deuda_u100
    if es_mora:
        ac["deuda_mora_u100"] += deuda_u100


def indicadores(ac: dict) -> dict:
    deuda = ac["deuda_u100"] * 100
    deuda_mora = ac["deuda_mora_u100"] * 100
    deudores = ac["deudores"]
    morosos = ac["personas_mora"]
    return {
        "deudores": deudores,
        "personas_mora": morosos,
        "incidencia_mora_pct": round(morosos / deudores * 100, 4) if deudores else 0.0,
        "deuda_total_pesos": deuda,
        "deuda_mora_pesos": deuda_mora,
        "tasa_mora_pct": round(deuda_mora / deuda * 100, 4) if deuda else 0.0,
        "registros_incluidos": ac["registros"],
    }


def desv(valor: float, ref: float) -> float | None:
    return round((valor / ref - 1) * 100, 3) if ref else None


def comparar(ind: dict) -> dict:
    return {
        "deudores_pct": desv(ind["deudores"], REFERENCIA["deudores"]),
        "personas_mora_pct": desv(ind["personas_mora"], REFERENCIA["personas_mora"]),
        "incidencia_mora_diferencia_pp": round(
            ind["incidencia_mora_pct"] - REFERENCIA["incidencia_mora_pct"], 4
        ),
        "deuda_total_pct": desv(ind["deuda_total_pesos"], REFERENCIA["deuda_total_pesos"]),
        "deuda_mora_pct": desv(ind["deuda_mora_pesos"], REFERENCIA["deuda_mora_pesos"]),
        "tasa_mora_diferencia_pp": round(
            ind["tasa_mora_pct"] - REFERENCIA["tasa_mora_pct"], 4
        ),
    }


def scenario_flags(cp: int, prov00: bool) -> dict[str, bool]:
    cp_rango = 1000 <= cp <= 1499
    cp_informado = cp > 0
    return {
        "A_eeff_pnfc_prov00": prov00,
        "B_eeff_pnfc_cp1000_1499_cualquier_provincia": cp_rango,
        "C_eeff_pnfc_prov00_y_cp1000_1499": prov00 and cp_rango,
        "D_eeff_pnfc_prov00_y_cp4_informado": prov00 and cp_informado,
        "E_eeff_pnfc_cp1000_1499_fuera_prov00": cp_rango and not prov00,
    }


def serializar_celdas(celdas: dict, unique_d: Counter, unique_m: Counter) -> tuple[list[dict], int]:
    salida: list[dict] = []
    suprimidas = 0
    for key in sorted(celdas, key=str):
        ac = celdas[key]
        d = unique_d[key]
        m = unique_m[key]
        if d < UMBRAL_PUBLICACION_CELDA:
            suprimidas += 1
            continue
        deuda = ac["deuda_u100"] * 100
        mora = ac["deuda_mora_u100"] * 100
        row = {
            "clave": key,
            "deudores": d,
            "personas_mora": m,
            "incidencia_mora_pct": round(m / d * 100, 4) if d else 0.0,
            "deuda_total_pesos": deuda,
            "deuda_mora_pesos": mora,
            "tasa_mora_pct": round(mora / deuda * 100, 4) if deuda else 0.0,
            "registros": ac["registros"],
        }
        salida.append(row)
    return salida, suprimidas


def main() -> int:
    acreedores, fuentes, _ = cargar_acreedores()

    carpeta = Path("bcra_deudores")
    padrones = sorted(carpeta.glob("*PADRON.7Z"))
    deudores_arch = sorted(carpeta.glob("*DEUDORES.7Z"))
    if not padrones or not deudores_arch:
        raise SystemExit("Se requieren PADRON.7Z y DEUDORES.7Z")
    padron = padrones[-1]
    deudores = deudores_arch[-1]
    p_int = buscar_interno(padron, "Padron_ARCA.txt")
    d_int = buscar_interno(deudores, "deudores.txt")

    # Sólo se conservan en RAM personas M/F que pueden entrar en al menos uno de
    # los escenarios relevantes: provincia 00 o CP tradicional 1000-1499.
    personas: dict[int, int] = {}
    padron_leidos = 0
    padron_mf = 0
    guardados_prov00 = 0
    guardados_cp_rango = 0
    duplicados = 0
    conflictos = 0

    print("[1/3] PADRON: construyendo universo compacto", flush=True)
    for raw in stream_lineas(padron, p_int):
        if not raw:
            continue
        padron_leidos += 1
        if len(raw) != LONG_PADRON:
            continue
        sexo_b = raw[199:200].strip().upper()
        if sexo_b not in (b"M", b"F"):
            continue
        padron_mf += 1
        ident_b = raw[0:11].strip()
        if len(ident_b) != 11 or not ident_b.isdigit():
            continue
        prov00 = raw[210:212] == b"00"
        cp = cp4(raw[200:210])
        cp_rango = 1000 <= cp <= 1499
        if not (prov00 or cp_rango):
            continue
        if prov00:
            guardados_prov00 += 1
        if cp_rango:
            guardados_cp_rango += 1
        ident = int(ident_b)
        valor = pack(cp, prov00, sexo_b == b"M", banda_edad(raw[189:199]))
        anterior = personas.get(ident)
        if anterior is not None:
            duplicados += 1
            if (anterior & ((1 << 20) - 1)) != valor:
                conflictos += 1
            # Preferir una fila con provincia 00; en igualdad se mantiene la primera.
            if (valor & BIT_PROV00) and not (anterior & BIT_PROV00):
                personas[ident] = valor
        else:
            personas[ident] = valor
        if padron_leidos % 10_000_000 == 0:
            print(f"  PADRON {padron_leidos:,}; personas guardadas {len(personas):,}", flush=True)

    escenarios = {s: nuevo_acum() for s in SCENARIOS}
    cp_cells = defaultdict(nuevo_acum)
    cross_cells = defaultdict(nuevo_acum)
    cendeu_leidos = 0
    seleccionados = 0
    montos_invalidos = 0
    fuera_personas_guardadas = 0
    situaciones = Counter()
    acreedores_presentes = set()

    print("[2/3] CENDEU: universo EEFF+PNFC y agregación", flush=True)
    for raw in stream_lineas(deudores, d_int):
        if not raw:
            continue
        cendeu_leidos += 1
        if len(raw) != LONG_DEUDORES or raw[11:13].strip() != b"11":
            continue
        codigo = raw[0:5].decode("ascii", errors="replace").strip().zfill(5)
        if codigo not in acreedores:
            continue
        situ = raw[27:29].strip()
        if situ not in SIT_1_5:
            continue
        m7 = monto_u100(raw[29:41])
        m10 = monto_u100(raw[65:77])
        if m7 is None or m10 is None:
            montos_invalidos += 1
            continue
        deuda = m7 + m10
        if deuda <= 0:
            continue
        ident_b = raw[13:24].strip()
        if not ident_b.isdigit():
            continue
        seleccionados += 1
        situaciones[situ.decode("ascii")] += 1
        acreedores_presentes.add(codigo)
        ident = int(ident_b)
        valor = personas.get(ident)
        if valor is None:
            fuera_personas_guardadas += 1
            continue
        cp, prov00, sexo, edad = attrs(valor)
        es_mora = situ in MORA
        nuevo_valor = valor | BIT_SEEN | (BIT_MORA if es_mora else 0)
        if nuevo_valor != valor:
            personas[ident] = nuevo_valor

        for nombre, entra in scenario_flags(cp, prov00).items():
            if entra:
                add_record(escenarios[nombre], deuda, es_mora)

        if 1000 <= cp <= 1499:
            add_record(cp_cells[cp], deuda, es_mora)
            add_record(cross_cells[f"{cp}|{sexo}|{EDAD_LABELS.get(edad, 'desconocida')}"], deuda, es_mora)

        if cendeu_leidos % 10_000_000 == 0:
            print(f"  CENDEU {cendeu_leidos:,}; registros seleccionados {seleccionados:,}", flush=True)

    print("[3/3] Conteos únicos desde flags en RAM", flush=True)
    cp_unique_d = Counter()
    cp_unique_m = Counter()
    cross_unique_d = Counter()
    cross_unique_m = Counter()
    edad_unique_d = Counter()
    edad_unique_m = Counter()
    sexo_unique_d = Counter()
    sexo_unique_m = Counter()

    for valor in personas.values():
        if not (valor & BIT_SEEN):
            continue
        cp, prov00, sexo, edad = attrs(valor)
        es_mora = bool(valor & BIT_MORA)
        flags = scenario_flags(cp, prov00)
        for nombre, entra in flags.items():
            if entra:
                escenarios[nombre]["deudores"] += 1
                if es_mora:
                    escenarios[nombre]["personas_mora"] += 1
        if 1000 <= cp <= 1499:
            cp_unique_d[cp] += 1
            if es_mora:
                cp_unique_m[cp] += 1
            cross_key = f"{cp}|{sexo}|{EDAD_LABELS.get(edad, 'desconocida')}"
            cross_unique_d[cross_key] += 1
            edad_label = EDAD_LABELS.get(edad, "desconocida")
            edad_unique_d[edad_label] += 1
            sexo_unique_d[sexo] += 1
            if es_mora:
                cross_unique_m[cross_key] += 1
                edad_unique_m[edad_label] += 1
                sexo_unique_m[sexo] += 1

    escenarios_out = {}
    for nombre in SCENARIOS:
        ind = indicadores(escenarios[nombre])
        escenarios_out[nombre] = {
            "indicadores": ind,
            "reconciliacion_v228": comparar(ind),
        }

    cp_rows, cp_suprimidos = serializar_celdas(cp_cells, cp_unique_d, cp_unique_m)
    cross_rows, cross_suprimidos = serializar_celdas(cross_cells, cross_unique_d, cross_unique_m)

    # Resúmenes demográficos únicos para el escenario CP 1000-1499.
    edad_rows = []
    for label in ["le25", "26_35", "36_45", "46_55", "56_65", "66_75", "gt75", "desconocida"]:
        edad_rows.append({
            "franja_edad": label,
            "deudores": edad_unique_d[label],
            "personas_mora": edad_unique_m[label],
        })
    sexo_rows = [
        {"sexo": s, "deudores": sexo_unique_d[s], "personas_mora": sexo_unique_m[s]}
        for s in ("F", "M")
    ]

    salida = {
        "schema": "cepoes-bcra-universo-territorial-integral-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "periodo_deuda": "2026-06",
        "padron_fecha": "2026-07-31",
        "fuentes_microdatos": {"padron": padron.name, "deudores": deudores.name},
        "fuentes_acreedores_bcra": fuentes,
        "criterios": {
            "persona_operativa": "sexo ARCA M/F",
            "acreedores_incluidos": "union por codigo de entidades financieras + emisoras no financieras + otros PNFC en endpoints oficiales vigentes BCRA",
            "situaciones": [1, 2, 3, 4, 5],
            "mora": [3, 4, 5],
            "deuda": "campo 7 + campo 10; deuda positiva",
            "cp": "campo ARCA 200:210; se reconoce CP tradicional sólo si contiene exactamente 4 dígitos",
            "cp_1000_1499": "escenario de validación territorial; no se adopta todavía como regla definitiva de CABA/barrio",
            "edad_fecha_corte": FECHA_CORTE_EDAD.isoformat(),
            "edad_19010101": "desconocida",
        },
        "escenarios": escenarios_out,
        "agregado_cp_1000_1499": {
            "filas": cp_rows,
            "umbral_minimo_deudores": UMBRAL_PUBLICACION_CELDA,
            "celdas_suprimidas": cp_suprimidos,
        },
        "agregado_cp_sexo_edad_1000_1499": {
            "filas": cross_rows,
            "umbral_minimo_deudores": UMBRAL_PUBLICACION_CELDA,
            "celdas_suprimidas": cross_suprimidos,
        },
        "resumen_edad_cp1000_1499": edad_rows,
        "resumen_sexo_cp1000_1499": sexo_rows,
        "controles": {
            "padron_registros_leidos": padron_leidos,
            "padron_registros_mf": padron_mf,
            "personas_guardadas_unicas": len(personas),
            "filas_guardables_prov00": guardados_prov00,
            "filas_guardables_cp1000_1499": guardados_cp_rango,
            "ids_duplicados_guardados": duplicados,
            "ids_duplicados_con_conflicto_atributos": conflictos,
            "cendeu_registros_leidos": cendeu_leidos,
            "registros_eeff_pnfc_sit1_5_deuda_positiva": seleccionados,
            "registros_seleccionados_fuera_universos_guardados": fuera_personas_guardadas,
            "montos_invalidos": montos_invalidos,
            "situaciones_registros_seleccionados": dict(sorted(situaciones.items())),
            "acreedores_seleccionados_presentes_en_cendeu": len(acreedores_presentes),
        },
        "referencia_v228_qa_no_ground_truth": REFERENCIA,
        "privacidad": {
            "microdatos_publicados": False,
            "identificadores_personales_en_salida": False,
            "nombres_de_personas_en_salida": False,
            "filas_individuales_en_salida": False,
            "identificadores_personales_solo_en_ram": True,
            "microdatos_descomprimidos_en_disco": False,
            "supresion_celdas_demograficas_menores_a": UMBRAL_PUBLICACION_CELDA,
        },
    }
    OUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "fuentes_acreedores": fuentes,
        "controles": salida["controles"],
        "escenarios": escenarios_out,
        "cp_publicados": len(cp_rows),
        "cross_publicados": len(cross_rows),
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
