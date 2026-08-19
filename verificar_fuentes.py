"""Diagnóstico de las fuentes: comprueba una por una si las URLs del catálogo
existen y devuelven un .xlsx.

Sirve para dejar de adivinar. Corre solo cuando se lo pide (paso opcional del
workflow o a mano) e imprime, para cada dataset, qué respondió el servidor y
qué archivo encontró. Con esa salida se corrigen las entradas de fuentes.py
que estén mal.

    python verificar_fuentes.py
"""
import re
import sys
import time

try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:
    pass

from descargar import SESION, TIMEOUT, RE_XLSX
from fuentes import DATASETS, DIRECTOS, CALENDARIO_URL


def probar(nombre, url, espera_xlsx_directo=False):
    t0 = time.time()
    try:
        r = SESION.get(url, timeout=TIMEOUT, allow_redirects=True)
        seg = time.time() - t0
        estado = r.status_code
        if estado != 200:
            return f"✘ HTTP {estado}  ({seg:.1f}s)"
        if espera_xlsx_directo:
            ok = r.content[:2] == b"PK"
            return (f"✔ xlsx {len(r.content)//1024} KB  ({seg:.1f}s)" if ok
                    else f"✘ responde 200 pero no es un xlsx  ({seg:.1f}s)")
        enlaces = [u for u in RE_XLSX.findall(r.text) if "wp-content/uploads" in u]
        if not enlaces:
            return f"✘ la página existe pero no tiene .xlsx  ({seg:.1f}s)"
        return f"✔ {enlaces[0].split('/')[-1]}  ({seg:.1f}s)"
    except Exception as e:
        return f"✘ {type(e).__name__}  ({time.time()-t0:.1f}s)"


def main():
    print("Comprobando las fuentes declaradas en fuentes.py\n")
    malas = []

    for nombre, (url, desc) in DATASETS.items():
        res = probar(nombre, url)
        print(f"  {nombre:26} {res}")
        if res.startswith("✘"):
            malas.append((nombre, url))
        time.sleep(4)

    for nombre, (url, desc) in DIRECTOS.items():
        res = probar(nombre, url, espera_xlsx_directo=True)
        print(f"  {nombre:26} {res}")
        if res.startswith("✘"):
            malas.append((nombre, url))
        time.sleep(4)

    print(f"\n  {'calendario':26} {probar('calendario', CALENDARIO_URL)}")

    if malas:
        print(f"\n{len(malas)} fuente(s) a corregir en fuentes.py:")
        for nombre, url in malas:
            print(f"  · {nombre}\n      {url}")
        print("\nBuscá el dataset en https://www.estadisticaciudad.gob.ar/eyc/arbol-tematico/")
        print("copiá la URL de la página y reemplazala en fuentes.py.")
    else:
        print("\n✔ todas las fuentes responden")
    return 0        # informativo: nunca corta el workflow


if __name__ == "__main__":
    sys.exit(main())
