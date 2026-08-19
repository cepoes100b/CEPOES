"""Arma datos.json, el archivo que consume el observatorio CEPOES.

Regla central: bloque que no se puede regenerar, bloque que se conserva del
datos.json anterior. Nunca se escribe un archivo con un bloque vacío o roto.
Al final el script informa qué se actualizó, qué se conservó y por qué, para
que quede en el log de GitHub Actions.

Dos bloques no salen de las planillas de IDECBA y siempre se conservan:
  · presupuesto — BA Data, cierre anual, se actualiza a mano por trimestre
  · censo       — INDEC Censo 2022, no cambia
"""
import json
import os
import sys
import datetime

import parsers as P
from fuentes import FUENTE_TEXTO

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_XLSX = os.path.join(BASE, "idecba")
SALIDA = os.path.join(BASE, "datos.json")

CONSERVADOS = ("presupuesto", "censo", "poblacion")
OBLIGATORIOS = ("ipcba", "empleo", "pobreza", "pgb", "presupuesto", "censo")


def xlsx(nombre):
    return os.path.join(DIR_XLSX, nombre)


def cargar_previo():
    if os.path.exists(SALIDA):
        try:
            return json.load(open(SALIDA, encoding="utf-8"))
        except Exception as e:
            print(f"  aviso: datos.json previo ilegible ({e})")
    return {}


def main():
    previo = cargar_previo()
    datos = {}
    nuevos, heredados, errores = [], [], []

    def bloque(clave, fn, requiere=None):
        """Corre un parser; si falla, hereda el bloque anterior."""
        if requiere and not os.path.exists(xlsx(requiere)):
            if clave in previo:
                datos[clave] = previo[clave]
                heredados.append(f"{clave} (falta {requiere})")
            else:
                errores.append(f"{clave}: falta {requiere} y no hay versión previa")
            return
        try:
            v = fn()
            if not v:
                raise ValueError("el parser devolvió vacío")
            datos[clave] = v
            nuevos.append(clave)
        except Exception as e:
            if clave in previo:
                datos[clave] = previo[clave]
                heredados.append(f"{clave} ({type(e).__name__}: {e})")
            else:
                errores.append(f"{clave}: {e}")

    bloque("ipcba",           lambda: P.ipcba(xlsx("ipcba_evol.xlsx")), "ipcba_evol.xlsx")
    bloque("canastas",        lambda: P.canastas(xlsx("canastas.xlsx")), "canastas.xlsx")
    bloque("empleo",          lambda: P.empleo(xlsx("empleo.xlsx")), "empleo.xlsx")
    bloque("pobreza",         lambda: P.pobreza(xlsx("pobreza_tasas.xlsx")), "pobreza_tasas.xlsx")
    bloque("comex",           lambda: P.comex(xlsx("comex_tot.xlsx")), "comex_tot.xlsx")
    bloque("masa_salarial",   lambda: P.masa_salarial(xlsx("masa_salarial.xlsx")), "masa_salarial.xlsx")
    bloque("locales_evo",     lambda: P.locales_evo(xlsx("locales.xlsx")), "locales.xlsx")
    bloque("comunas_locales", lambda: P.comunas_locales(xlsx("ejes48_comuna_tasas.xlsx")),
                              "ejes48_comuna_tasas.xlsx")
    bloque("pgb",             lambda: P.pgb(xlsx("pgb_var.xlsx")), "pgb_var.xlsx")

    # las divisiones del IPCBA van adentro del bloque ipcba
    try:
        div = P.ipcba_divisiones(xlsx("ipcba_aperturas.xlsx"))
        datos.setdefault("ipcba", {})["divisiones"] = div
        nuevos.append("ipcba.divisiones")
    except Exception as e:
        anterior = (previo.get("ipcba") or {}).get("divisiones")
        if anterior:
            datos.setdefault("ipcba", {})["divisiones"] = anterior
            heredados.append(f"ipcba.divisiones ({type(e).__name__})")
        else:
            errores.append(f"ipcba.divisiones: {e}")

    # la industria se deflacta con el IPCBA ya parseado
    bloque("industria",
           lambda: P.industria(xlsx("industria_ing.xlsx"), datos.get("ipcba")),
           "industria_ing.xlsx")

    # calendario: lo deja descargar.py en calendario.json
    cal = os.path.join(BASE, "calendario.json")
    try:
        items = json.load(open(cal, encoding="utf-8"))["items"]
        if len(items) < 5:
            raise ValueError(f"sólo {len(items)} publicaciones")
        datos["calendario"] = {"hoy": datetime.date.today().isoformat(), "items": items}
        nuevos.append("calendario")
    except Exception as e:
        if "calendario" in previo:
            datos["calendario"] = previo["calendario"]
            heredados.append(f"calendario ({type(e).__name__})")
        else:
            errores.append(f"calendario: {e}")

    for clave in CONSERVADOS:
        if clave in previo:
            datos[clave] = previo[clave]
            heredados.append(f"{clave} (se mantiene por diseño)")
        else:
            errores.append(f"{clave}: no está en el datos.json previo")

    datos["generado"] = datetime.date.today().isoformat()
    datos["fuente"] = FUENTE_TEXTO

    # ---------------------------------------------------------- verificación
    faltan = [k for k in OBLIGATORIOS if k not in datos]
    if faltan:
        print("\nABORTA: faltan bloques obligatorios:", ", ".join(faltan))
        for e in errores:
            print("   ·", e)
        return 1

    tmp = SALIDA + ".parcial"
    json.dump(datos, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    if os.path.getsize(tmp) < 8000:
        os.remove(tmp)
        print("\nABORTA: el archivo generado es sospechosamente chico")
        return 1
    os.replace(tmp, SALIDA)

    print(f"\ndatos.json · {os.path.getsize(SALIDA)//1024} KB · generado {datos['generado']}")
    print(f"  actualizados ({len(nuevos)}): {', '.join(nuevos)}")
    if heredados:
        print(f"  conservados ({len(heredados)}):")
        for h in heredados:
            print("     ·", h)
    if errores:
        print(f"  con problemas ({len(errores)}):")
        for e in errores:
            print("     ·", e)
    print("\n  último dato por serie:")
    for k, campo in [("ipcba", "meses"), ("empleo", "trimestres"), ("pobreza", "periodos"),
                     ("canastas", "meses"), ("comex", "anios"), ("industria", "periodos"),
                     ("masa_salarial", "periodos"), ("locales_evo", "periodos")]:
        v = (datos.get(k) or {}).get(campo)
        if v:
            print(f"     {k:16} {v[-1]}")
    if datos.get("comunas_locales"):
        print(f"     {'comunas':16} {datos['comunas_locales']['periodo']}")
    if datos.get("pgb"):
        print(f"     {'pgb':16} {datos['pgb']['ultimo_trim']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
