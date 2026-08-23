#!/usr/bin/env python3
"""Procesamiento productivo mensual de Endeudamiento CEPOES sobre BCRA/ARCA.

Principios:
- fuente primaria mensual: Central de Deudores BCRA + Padrón ARCA distribuido por BCRA;
- el período se detecta desde AAAAMMDEUDORES.7Z y la fecha del padrón desde AAAAMMDDPADRON.7Z;
- la base territorial utiliza exclusivamente provincia ARCA=00 Y CP4 1000-1499;
- genera agregados por CP4, sexo, edad y tipo de acreedor para aplicar luego la matriz CP4->barrio;
- ningún identificador personal ni microdato se serializa.
"""
from __future__ import annotations

import calendar
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import procesar_universo_territorial_integral as base

OUT = Path("diagnostico_endeudamiento_productivo.json")

CATEGORIAS = ("entidad_financiera", "emisora_tarjeta", "otro_pnfc")
CAT_SEEN_SHIFT = 22
CAT_MORA_SHIFT = 25


def parse_deudores(path: Path) -> tuple[str, date]:
    m = re.search(r"(\d{6})DEUDORES\.7Z$", path.name, re.I)
    if not m:
        raise ValueError(f"Nombre DEUDORES inesperado: {path.name}")
    ym = m.group(1)
    y, mo = int(ym[:4]), int(ym[4:])
    last = calendar.monthrange(y, mo)[1]
    return f"{y:04d}-{mo:02d}", date(y, mo, last)


def parse_padron(path: Path) -> str:
    m = re.search(r"(\d{8})PADRON\.7Z$", path.name, re.I)
    if not m:
        raise ValueError(f"Nombre PADRON inesperado: {path.name}")
    return datetime.strptime(m.group(1), "%Y%m%d").date().isoformat()


def categoria_codigo(codigo: str, por_categoria: dict[str, set[str]]) -> str:
    if codigo in por_categoria["entidad_financiera"]:
        return "entidad_financiera"
    if codigo in por_categoria["enf_emisora_tarjeta"]:
        return "emisora_tarjeta"
    if codigo in por_categoria["otro_pnfc"]:
        return "otro_pnfc"
    raise KeyError(codigo)


def bit_seen(cat: str) -> int:
    return 1 << (CAT_SEEN_SHIFT + CATEGORIAS.index(cat))


def bit_mora(cat: str) -> int:
    return 1 << (CAT_MORA_SHIFT + CATEGORIAS.index(cat))


def ratio_pct(n: float, d: float) -> float:
    return round(n / d * 100, 4) if d else 0.0


def main() -> int:
    carpeta = Path("bcra_deudores")
    padrones = sorted(carpeta.glob("*PADRON.7Z"))
    deudores_arch = sorted(carpeta.glob("*DEUDORES.7Z"))
    if not padrones or not deudores_arch:
        raise SystemExit("Se requieren PADRON.7Z y DEUDORES.7Z")

    padron = padrones[-1]
    deudores = deudores_arch[-1]
    periodo, fecha_corte = parse_deudores(deudores)
    padron_fecha = parse_padron(padron)
    base.FECHA_CORTE_EDAD = fecha_corte

    acreedores, fuentes, por_categoria = base.cargar_acreedores()
    p_int = base.buscar_interno(padron, "Padron_ARCA.txt")
    d_int = base.buscar_interno(deudores, "deudores.txt")

    personas: dict[int, int] = {}
    padron_leidos = padron_mf = duplicados = conflictos = 0
    guardados_prov00 = guardados_cp_rango = 0

    print(f"[1/3] PADRON: período deuda {periodo}; corte edad {fecha_corte}", flush=True)
    for raw in base.stream_lineas(padron, p_int):
        if not raw:
            continue
        padron_leidos += 1
        if len(raw) != base.LONG_PADRON:
            continue
        sexo_b = raw[199:200].strip().upper()
        if sexo_b not in (b"M", b"F"):
            continue
        padron_mf += 1
        ident_b = raw[0:11].strip()
        if len(ident_b) != 11 or not ident_b.isdigit():
            continue
        prov00 = raw[210:212] == b"00"
        cp = base.cp4(raw[200:210])
        cp_rango = 1000 <= cp <= 1499
        if not (prov00 or cp_rango):
            continue
        guardados_prov00 += int(prov00)
        guardados_cp_rango += int(cp_rango)
        ident = int(ident_b)
        valor = base.pack(cp, prov00, sexo_b == b"M", base.banda_edad(raw[189:199]))
        anterior = personas.get(ident)
        if anterior is not None:
            duplicados += 1
            if (anterior & ((1 << 20) - 1)) != valor:
                conflictos += 1
            if (valor & base.BIT_PROV00) and not (anterior & base.BIT_PROV00):
                personas[ident] = valor
        else:
            personas[ident] = valor
        if padron_leidos % 10_000_000 == 0:
            print(f"  PADRON {padron_leidos:,}; personas guardadas {len(personas):,}", flush=True)

    escenarios = {s: base.nuevo_acum() for s in base.SCENARIOS}
    cp_cells = defaultdict(base.nuevo_acum)
    cross_cells = defaultdict(base.nuevo_acum)
    cat_cells = defaultdict(base.nuevo_acum)
    cat_cross_cells = defaultdict(base.nuevo_acum)

    cendeu_leidos = seleccionados = montos_invalidos = fuera_personas_guardadas = 0
    situaciones = Counter()
    acreedores_presentes = set()

    print("[2/3] CENDEU: agregación propia CABA + CP4", flush=True)
    for raw in base.stream_lineas(deudores, d_int):
        if not raw:
            continue
        cendeu_leidos += 1
        if len(raw) != base.LONG_DEUDORES or raw[11:13].strip() != b"11":
            continue
        codigo = raw[0:5].decode("ascii", errors="replace").strip().zfill(5)
        if codigo not in acreedores:
            continue
        situ = raw[27:29].strip()
        if situ not in base.SIT_1_5:
            continue
        m7 = base.monto_u100(raw[29:41])
        m10 = base.monto_u100(raw[65:77])
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

        cp, prov00, sexo, edad = base.attrs(valor)
        es_mora = situ in base.MORA
        valor |= base.BIT_SEEN
        if es_mora:
            valor |= base.BIT_MORA

        cat = categoria_codigo(codigo, por_categoria)
        valor |= bit_seen(cat)
        if es_mora:
            valor |= bit_mora(cat)
        personas[ident] = valor

        for nombre, entra in base.scenario_flags(cp, prov00).items():
            if entra:
                base.add_record(escenarios[nombre], deuda, es_mora)

        # Regla productiva territorial: sólo intersección provincia 00 + CP porteño válido.
        if prov00 and 1000 <= cp <= 1499:
            edad_label = base.EDAD_LABELS.get(edad, "desconocida")
            base.add_record(cp_cells[cp], deuda, es_mora)
            base.add_record(cross_cells[f"{cp}|{sexo}|{edad_label}"], deuda, es_mora)
            base.add_record(cat_cells[f"{cp}|{cat}"], deuda, es_mora)
            base.add_record(cat_cross_cells[f"{cp}|{sexo}|{edad_label}|{cat}"], deuda, es_mora)

        if cendeu_leidos % 10_000_000 == 0:
            print(f"  CENDEU {cendeu_leidos:,}; seleccionados {seleccionados:,}", flush=True)

    print("[3/3] Conteos únicos y salida agregada", flush=True)
    cp_unique_d, cp_unique_m = Counter(), Counter()
    cross_unique_d, cross_unique_m = Counter(), Counter()
    cat_unique_d, cat_unique_m = Counter(), Counter()
    cat_cross_unique_d, cat_cross_unique_m = Counter(), Counter()
    edad_unique_d, edad_unique_m = Counter(), Counter()
    sexo_unique_d, sexo_unique_m = Counter(), Counter()

    for valor in personas.values():
        if not (valor & base.BIT_SEEN):
            continue
        cp, prov00, sexo, edad = base.attrs(valor)
        es_mora = bool(valor & base.BIT_MORA)
        for nombre, entra in base.scenario_flags(cp, prov00).items():
            if entra:
                escenarios[nombre]["deudores"] += 1
                escenarios[nombre]["personas_mora"] += int(es_mora)

        if not (prov00 and 1000 <= cp <= 1499):
            continue
        edad_label = base.EDAD_LABELS.get(edad, "desconocida")
        cp_unique_d[cp] += 1
        cross_key = f"{cp}|{sexo}|{edad_label}"
        cross_unique_d[cross_key] += 1
        edad_unique_d[edad_label] += 1
        sexo_unique_d[sexo] += 1
        if es_mora:
            cp_unique_m[cp] += 1
            cross_unique_m[cross_key] += 1
            edad_unique_m[edad_label] += 1
            sexo_unique_m[sexo] += 1

        for cat in CATEGORIAS:
            if valor & bit_seen(cat):
                ck = f"{cp}|{cat}"
                cx = f"{cp}|{sexo}|{edad_label}|{cat}"
                cat_unique_d[ck] += 1
                cat_cross_unique_d[cx] += 1
                if valor & bit_mora(cat):
                    cat_unique_m[ck] += 1
                    cat_cross_unique_m[cx] += 1

    escenarios_out = {}
    for nombre in base.SCENARIOS:
        ind = base.indicadores(escenarios[nombre])
        escenarios_out[nombre] = {"indicadores": ind, "reconciliacion_v228": base.comparar(ind)}

    cp_rows, cp_sup = base.serializar_celdas(cp_cells, cp_unique_d, cp_unique_m)
    cross_rows, cross_sup = base.serializar_celdas(cross_cells, cross_unique_d, cross_unique_m)
    cat_rows, cat_sup = base.serializar_celdas(cat_cells, cat_unique_d, cat_unique_m)
    cat_cross_rows, cat_cross_sup = base.serializar_celdas(cat_cross_cells, cat_cross_unique_d, cat_cross_unique_m)

    caba = escenarios_out["A_eeff_pnfc_prov00"]["indicadores"]
    territorial = escenarios_out["C_eeff_pnfc_prov00_y_cp1000_1499"]["indicadores"]
    cobertura = {
        "deudores_pct": ratio_pct(territorial["deudores"], caba["deudores"]),
        "personas_mora_pct": ratio_pct(territorial["personas_mora"], caba["personas_mora"]),
        "deuda_total_pct": ratio_pct(territorial["deuda_total_pesos"], caba["deuda_total_pesos"]),
        "deuda_mora_pct": ratio_pct(territorial["deuda_mora_pesos"], caba["deuda_mora_pesos"]),
    }

    edad_rows = [{"franja_edad": e, "deudores": edad_unique_d[e], "personas_mora": edad_unique_m[e]}
                 for e in ["le25", "26_35", "36_45", "46_55", "56_65", "66_75", "gt75", "desconocida"]]
    sexo_rows = [{"sexo": s, "deudores": sexo_unique_d[s], "personas_mora": sexo_unique_m[s]} for s in ("F", "M")]

    salida = {
        "schema": "cepoes-bcra-endeudamiento-productivo-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "periodo_deuda": periodo,
        "padron_fecha": padron_fecha,
        "fuentes_microdatos": {"padron": padron.name, "deudores": deudores.name},
        "fuentes_acreedores_bcra": fuentes,
        "criterios": {
            "persona_operativa": "sexo ARCA M/F",
            "territorio_caba": "provincia ARCA=00 y CP tradicional 1000-1499 para la capa barrial",
            "acreedores_incluidos": "entidades financieras + emisoras no financieras de tarjetas + otros PNFC según registros oficiales vigentes BCRA",
            "prioridad_categoria_acreedor": list(CATEGORIAS),
            "situaciones": [1, 2, 3, 4, 5],
            "mora": [3, 4, 5],
            "deuda": "campo 7 + campo 10; deuda positiva",
            "edad_fecha_corte": fecha_corte.isoformat(),
            "umbral_publicacion_celda": base.UMBRAL_PUBLICACION_CELDA,
        },
        "escenarios": escenarios_out,
        "cobertura_territorial_cp4_sobre_caba": cobertura,
        "agregado_cp_caba_1000_1499": {"filas": cp_rows, "celdas_suprimidas": cp_sup},
        "agregado_cp_sexo_edad_caba_1000_1499": {"filas": cross_rows, "celdas_suprimidas": cross_sup},
        "agregado_cp_categoria_caba_1000_1499": {"filas": cat_rows, "celdas_suprimidas": cat_sup},
        "agregado_cp_sexo_edad_categoria_caba_1000_1499": {"filas": cat_cross_rows, "celdas_suprimidas": cat_cross_sup},
        "resumen_edad_territorial": edad_rows,
        "resumen_sexo_territorial": sexo_rows,
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
        "privacidad": {
            "microdatos_publicados": False,
            "identificadores_personales_en_salida": False,
            "nombres_de_personas_en_salida": False,
            "filas_individuales_en_salida": False,
            "identificadores_personales_solo_en_ram": True,
            "microdatos_descomprimidos_en_disco": False,
            "salida_solo_agregada": True,
        },
    }
    OUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "periodo": periodo,
        "padron_fecha": padron_fecha,
        "caba": caba,
        "territorializable": territorial,
        "cobertura": cobertura,
        "cp_publicados": len(cp_rows),
        "segmentos": len(cross_rows),
        "segmentos_categoria": len(cat_cross_rows),
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
