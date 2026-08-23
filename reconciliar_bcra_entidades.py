#!/usr/bin/env python3
"""Reconcilia el universo CABA de CENDEU por entidad informante.

Objetivos:
- medir deudores, morosos y montos por código de entidad;
- clasificar exclusivamente las SGR y FGCP identificadas en los registros oficiales
  vigentes del BCRA;
- recalcular el agregado CABA excluyendo esas dos categorías, sin inferir todavía
  ninguna categoría de "mercado secundario";
- no persistir ni publicar CUIT/CUIL/CDI ni filas individuales.

Los microdatos de PADRON ARCA y DEUDORES se leen desde los .7z en streaming.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

LONG_PADRON = 220
LONG_DEUDORES = 171
MORA = {b"3", b"4", b"5"}

# Listas copiadas de los registros públicos vigentes del BCRA al 2026-08-22.
# No se infiere la pertenencia por nombre ni por rango: sólo se etiquetan estos códigos.
SGR_OFICIALES = {
    "50001", "50020", "50002", "50003", "50041", "50004", "50046", "50021",
    "50005", "50024", "50007", "50025", "50028", "50009", "50035", "50030",
    "50026", "50033", "50011", "50012", "50037", "50029", "50039", "50013",
    "50014", "50038", "50015", "50040", "50036", "50043", "50010", "50018",
    "50017", "50032", "50034", "50042", "50044", "50023", "50048",
}
FGCP_OFICIALES = {
    "51007", "51009", "51015", "51011", "51012", "51006", "51004", "51003",
    "51001", "51014", "51017", "51002", "51010", "51008", "51013", "51016",
    "51005",
}
EXCLUIR_SGR_FGCP = SGR_OFICIALES | FGCP_OFICIALES

FUENTES_CLASIFICACION = {
    "sgr": "https://www.bcra.gob.ar/sociedades-de-garantia-reciproca/",
    "fgcp": "https://www.bcra.gob.ar/fondos-de-garantia-de-caracter-publico/",
}

REFERENCIA = {
    "deudores": 1_877_802,
    "personas_mora": 255_805,
    "incidencia_mora_pct": 13.62,
    "deuda_total_pesos": 13_390_000_000_000,
    "deuda_mora_pesos": 1_570_000_000_000,
    "tasa_mora_pct": 11.71,
}


def sevenzip() -> str:
    exe = shutil.which("7z") or shutil.which("7zz")
    if not exe:
        raise RuntimeError("Falta 7z/7zz")
    return exe


def internos(archivo: Path) -> list[str]:
    r = subprocess.run([sevenzip(), "l", "-slt", str(archivo)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, errors="replace")
    nombres: list[str] = []
    actual: dict[str, str] = {}
    for linea in r.stdout.splitlines() + [""]:
        if not linea.strip():
            if actual.get("Path") and actual.get("Folder") != "+":
                nombres.append(actual["Path"])
            actual = {}
            continue
        if " = " in linea:
            k, v = linea.split(" = ", 1)
            actual[k.strip()] = v.strip()
    return nombres


def buscar_interno(archivo: Path, nombre: str) -> str:
    objetivo = nombre.lower()
    for item in internos(archivo):
        if Path(item).name.lower() == objetivo:
            return item
    raise RuntimeError(f"No se encontró {nombre} dentro de {archivo.name}")


def stream_lineas(archivo: Path, interno: str):
    proc = subprocess.Popen([sevenzip(), "x", "-so", str(archivo), interno],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            bufsize=1024 * 1024)
    assert proc.stdout is not None
    try:
        for raw in proc.stdout:
            yield raw.rstrip(b"\r\n")
    finally:
        proc.stdout.close()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"7z terminó con código {rc} leyendo {interno}")


def cargar_maestro(deudores_7z: Path) -> dict[str, str]:
    interno = buscar_interno(deudores_7z, "Maeent.txt")
    salida: dict[str, str] = {}
    for raw in stream_lineas(deudores_7z, interno):
        if len(raw) < 5:
            continue
        codigo = raw[:5].decode("ascii", errors="replace").strip()
        nombre = raw[5:75].decode("cp1252", errors="replace").strip()
        if codigo:
            salida[codigo] = nombre
    return salida


def categoria(codigo: str) -> str:
    if codigo in SGR_OFICIALES:
        return "SGR"
    if codigo in FGCP_OFICIALES:
        return "FGCP"
    return "otra_no_clasificada_en_esta_etapa"


def monto_u100(raw: bytes) -> int | None:
    valor = raw.strip().replace(b",", b"").replace(b".", b"")
    if not valor:
        return 0
    if not valor.isdigit():
        return None
    return int(valor)


def resumen(ids: set[int], mora_ids: set[int], deuda_u100: int, deuda_mora_u100: int) -> dict:
    deuda = deuda_u100 * 100
    deuda_mora = deuda_mora_u100 * 100
    incidencia = (len(mora_ids) / len(ids) * 100) if ids else 0.0
    tasa = (deuda_mora / deuda * 100) if deuda else 0.0
    return {
        "deudores": len(ids),
        "personas_mora": len(mora_ids),
        "incidencia_mora_pct": round(incidencia, 4),
        "deuda_total_pesos": deuda,
        "deuda_mora_pesos": deuda_mora,
        "tasa_mora_pct": round(tasa, 4),
    }


def desviacion(valor: float, referencia: float) -> float | None:
    return round((valor / referencia - 1) * 100, 3) if referencia else None


def reconciliacion(ind: dict) -> dict:
    return {
        "deudores_pct": desviacion(ind["deudores"], REFERENCIA["deudores"]),
        "personas_mora_pct": desviacion(ind["personas_mora"], REFERENCIA["personas_mora"]),
        "incidencia_mora_pct_relativa": desviacion(ind["incidencia_mora_pct"], REFERENCIA["incidencia_mora_pct"]),
        "incidencia_mora_diferencia_pp": round(ind["incidencia_mora_pct"] - REFERENCIA["incidencia_mora_pct"], 4),
        "deuda_total_pct": desviacion(ind["deuda_total_pesos"], REFERENCIA["deuda_total_pesos"]),
        "deuda_mora_pct": desviacion(ind["deuda_mora_pesos"], REFERENCIA["deuda_mora_pesos"]),
        "tasa_mora_pct_relativa": desviacion(ind["tasa_mora_pct"], REFERENCIA["tasa_mora_pct"]),
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
    maestro = cargar_maestro(deudores)

    ids_caba: set[int] = set()
    padron_leidos = 0
    caba_mf = 0
    print("[1/2] Construyendo universo CABA desde PADRON ARCA", flush=True)
    for raw in stream_lineas(padron, p_int):
        if not raw:
            continue
        padron_leidos += 1
        if len(raw) != LONG_PADRON or raw[210:212] != b"00":
            continue
        if raw[199:200].strip().upper() not in (b"M", b"F"):
            continue
        ident = raw[0:11].strip()
        if len(ident) == 11 and ident.isdigit():
            ids_caba.add(int(ident))
            caba_mf += 1
        if padron_leidos % 10_000_000 == 0:
            print(f"  PADRON {padron_leidos:,}; humanos CABA únicos {len(ids_caba):,}", flush=True)

    if not ids_caba:
        raise SystemExit("Universo CABA vacío")

    base_ids: set[int] = set()
    base_mora: set[int] = set()
    ajust_ids: set[int] = set()
    ajust_mora: set[int] = set()
    base_deuda = base_deuda_mora = 0
    ajust_deuda = ajust_deuda_mora = 0

    ent_ids: dict[str, set[int]] = defaultdict(set)
    ent_mora: dict[str, set[int]] = defaultdict(set)
    ent_deuda: Counter[str] = Counter()
    ent_deuda_mora: Counter[str] = Counter()
    ent_registros: Counter[str] = Counter()
    situaciones: Counter[str] = Counter()
    montos_invalidos = 0
    registros_leidos = 0
    registros_caba = 0

    print("[2/2] Recorriendo CENDEU y agregando por entidad", flush=True)
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
        if ident not in ids_caba:
            continue
        registros_caba += 1
        codigo = raw[0:5].decode("ascii", errors="replace").strip()
        situ = raw[27:29].strip()
        situ_txt = situ.decode("ascii", errors="replace") or "vacio"
        situaciones[situ_txt] += 1
        m7 = monto_u100(raw[29:41])
        m10 = monto_u100(raw[65:77])
        if m7 is None or m10 is None:
            montos_invalidos += 1
            continue
        deuda = m7 + m10

        base_ids.add(ident)
        base_deuda += deuda
        if situ in MORA:
            base_mora.add(ident)
            base_deuda_mora += deuda

        ent_ids[codigo].add(ident)
        ent_registros[codigo] += 1
        ent_deuda[codigo] += deuda
        if situ in MORA:
            ent_mora[codigo].add(ident)
            ent_deuda_mora[codigo] += deuda

        if codigo not in EXCLUIR_SGR_FGCP:
            ajust_ids.add(ident)
            ajust_deuda += deuda
            if situ in MORA:
                ajust_mora.add(ident)
                ajust_deuda_mora += deuda

        if registros_leidos % 10_000_000 == 0:
            print(f"  CENDEU {registros_leidos:,}; registros CABA {registros_caba:,}", flush=True)

    base = resumen(base_ids, base_mora, base_deuda, base_deuda_mora)
    sin_sgr_fgcp = resumen(ajust_ids, ajust_mora, ajust_deuda, ajust_deuda_mora)

    entidades = []
    for cod in sorted(ent_ids):
        r = resumen(ent_ids[cod], ent_mora[cod], ent_deuda[cod], ent_deuda_mora[cod])
        entidades.append({
            "codigo": cod,
            "nombre": maestro.get(cod, ""),
            "categoria_documentada": categoria(cod),
            "registros_caba": ent_registros[cod],
            **r,
        })
    entidades.sort(key=lambda x: x["deuda_total_pesos"], reverse=True)

    prefijos_candidatos_no_listados = sorted(
        cod for cod in ent_ids
        if (cod.startswith("500") or cod.startswith("510")) and cod not in EXCLUIR_SGR_FGCP
    )

    salida = {
        "schema": "cepoes-bcra-reconciliacion-entidades-v1",
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "fuentes": {
            "padron": padron.name,
            "deudores": deudores.name,
            "clasificacion_oficial": FUENTES_CLASIFICACION,
        },
        "universo": {
            "criterio_persona_caba": "provincia ARCA=00, sexo ARCA=M/F, identificación fiscal CENDEU=11",
            "padron_registros_leidos": padron_leidos,
            "padron_caba_mf_registros": caba_mf,
            "padron_caba_humanos_unicos": len(ids_caba),
            "cendeu_registros_leidos": registros_leidos,
            "cendeu_registros_caba": registros_caba,
            "montos_invalidos": montos_invalidos,
            "situaciones": dict(sorted(situaciones.items())),
        },
        "escenarios": {
            "base_todos_informantes": {
                "indicadores": base,
                "reconciliacion_v228": reconciliacion(base),
            },
            "sin_sgr_fgcp_oficiales": {
                "descripcion": "Excluye únicamente códigos presentes en los registros oficiales BCRA de SGR y FGCP consultados el 2026-08-22.",
                "codigos_sgr": sorted(SGR_OFICIALES),
                "codigos_fgcp": sorted(FGCP_OFICIALES),
                "indicadores": sin_sgr_fgcp,
                "reconciliacion_v228": reconciliacion(sin_sgr_fgcp),
            },
        },
        "entidades": entidades,
        "control_clasificacion": {
            "codigos_500xx_510xx_presentes_no_listados": prefijos_candidatos_no_listados,
            "mercado_secundario": "pendiente de identificación documental; no se excluye en esta corrida",
        },
        "referencia_v228": REFERENCIA,
        "privacidad": {
            "microdatos_publicados": False,
            "identificadores_en_salida": False,
            "nombres_de_personas_en_salida": False,
            "nombres_de_entidades_en_salida": True,
            "microdatos_descomprimidos_en_disco": False,
            "identificadores_solo_en_memoria": True,
        },
    }
    Path("diagnostico_bcra_entidades.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"escenarios": salida["escenarios"],
                      "top_10_entidades_por_deuda": entidades[:10],
                      "control_clasificacion": salida["control_clasificacion"]},
                     ensure_ascii=False, indent=2), flush=True)
    print("OK -> diagnostico_bcra_entidades.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
