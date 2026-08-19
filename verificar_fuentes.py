"""Diagnóstico del catálogo: comprueba que cada dataset se pueda localizar.

Recorre las categorías de fuentes.py, busca el post que coincide con cada
patrón y verifica que tenga un .xlsx adjunto. Imprime el resultado dataset por
dataset. Es informativo: nunca corta el workflow.

    python verificar_fuentes.py
"""
import re
import sys
import time

try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:
    pass

from descargar import buscar_post, link_xlsx
from fuentes import DATASETS, CALENDARIO_URL, CAT_BASE
import descargar


def main():
    print("Comprobando el catálogo de fuentes\n")
    malas = []
    for nombre, (categoria, patron, desc) in DATASETS.items():
        t0 = time.time()
        try:
            post = buscar_post(categoria, patron)
            url = link_xlsx(post)
            print(f"  ✔ {nombre:26} {url.split('/')[-1][:52]}  ({time.time()-t0:.1f}s)")
        except Exception as e:
            print(f"  ✘ {nombre:26} {str(e)[:70]}  ({time.time()-t0:.1f}s)")
            malas.append((nombre, categoria, patron, getattr(e, "disponibles", [])))
        time.sleep(4)

    try:
        r = descargar._get(CALENDARIO_URL)
        n = len(re.findall(r"<h[1-6][^>]*>", r.text))
        print(f"\n  ✔ {'calendario':26} la página responde ({n} encabezados)")
    except Exception as e:
        print(f"\n  ✘ {'calendario':26} {type(e).__name__}")

    if malas:
        print(f"\n{len(malas)} dataset(s) sin localizar:")
        for nombre, cat, pat, disponibles in malas:
            print(f"\n  · {nombre}")
            print(f"      categoría: {CAT_BASE}{cat}/")
            print(f"      patrón:    {pat}")
            if disponibles:
                print(f"      datasets que SÍ hay en esa categoría ({len(disponibles)}):")
                for d in disponibles[:15]:
                    print(f"        - {d[:110]}")
                if len(disponibles) > 15:
                    print(f"        … y {len(disponibles)-15} más")
            else:
                print("      la categoría no devolvió ningún dataset: revisá el slug de la categoría")
        print("\nCopiá un fragmento distintivo del slug correcto y usalo como patrón en fuentes.py.")
    else:
        print("\n✔ los 11 datasets se localizan correctamente")
    return 0


if __name__ == "__main__":
    sys.exit(main())
