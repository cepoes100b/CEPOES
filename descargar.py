"""Baja las planillas de IDECBA y el calendario de publicaciones.

Criterio de diseño: nunca romper. Si una descarga falla, se conserva la copia
commiteada del .xlsx y el generador sigue trabajando con ella. Un dato viejo es
mucho mejor que un observatorio caído, y el indicador de antigüedad de la página
ya avisa cuándo los datos se están quedando atrás.

Cómo encuentra los archivos: cada dataset tiene una URL de página estable en el
Banco de Datos. IDECBA reescribe ese mismo post cuando publica un período nuevo
y sólo cambia la ruta del adjunto, así que alcanza con leer la página y quedarse
con el primer enlace a .xlsx que aparezca.
"""
import os
import re
import sys
import time

import requests

from fuentes import DATASETS, DIRECTOS, CALENDARIO_URL

# En GitHub Actions stdout no es una terminal, así que Python la bufferiza y el
# paso queda mudo hasta terminar. Con esto cada línea sale en el momento.
try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_XLSX = os.path.join(BASE, "idecba")
os.makedirs(DIR_XLSX, exist_ok=True)

# Cabeceras de navegador: varios firewalls de sitios públicos rechazan o
# demoran indefinidamente a los clientes que no se presentan como uno.
CABECERAS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Connection": "close",
}
TIMEOUT = (10, 25)          # (conexión, lectura)
REINTENTOS = 2
PRESUPUESTO_SEG = 420       # tope total: si se pasa, corta y usa las copias locales
RE_XLSX = re.compile(r'https?://[^"\'\s>]+?\.xlsx', re.I)


ARRANQUE = time.time()


def queda_tiempo():
    return time.time() - ARRANQUE < PRESUPUESTO_SEG


def _get(url, **kw):
    ultimo = None
    for intento in range(REINTENTOS):
        if not queda_tiempo():
            raise RuntimeError("se agotó el presupuesto de tiempo")
        try:
            r = requests.get(url, headers=CABECERAS, timeout=TIMEOUT, **kw)
            if r.status_code == 200:
                return r
            ultimo = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            ultimo = type(e).__name__
        time.sleep(2)
    raise RuntimeError(ultimo or "sin respuesta")


def link_xlsx(url_pagina):
    """Devuelve la URL del .xlsx publicado en una página del Banco de Datos."""
    html = _get(url_pagina).text
    encontrados = RE_XLSX.findall(html)
    if not encontrados:
        raise RuntimeError("la página no tiene ningún enlace .xlsx")
    # se prioriza el que cuelga de wp-content/uploads (el adjunto real)
    for u in encontrados:
        if "wp-content/uploads" in u:
            return u.replace("http://", "https://")
    return encontrados[0].replace("http://", "https://")


def bajar_archivo(url, destino):
    r = _get(url, stream=True)
    ct = r.headers.get("Content-Type", "")
    contenido = r.content
    if len(contenido) < 4000 or contenido[:2] != b"PK":
        raise RuntimeError(f"no parece un xlsx (Content-Type={ct}, {len(contenido)} bytes)")
    tmp = destino + ".parcial"
    with open(tmp, "wb") as f:
        f.write(contenido)
    os.replace(tmp, destino)
    return len(contenido)


def main():
    ok, conservados, fallas = [], [], []

    pendientes = [(n, u, d, True) for n, (u, d) in DATASETS.items()]
    pendientes += [(n, u, d, False) for n, (u, d) in DIRECTOS.items()]

    for nombre, url, desc, via_pagina in pendientes:
        destino = os.path.join(DIR_XLSX, nombre)
        existia = os.path.exists(destino)
        print(f"  … {nombre:26} consultando", flush=True)
        if not queda_tiempo():
            conservados.append(nombre)
            print(f"  ~ {nombre:26} sin tiempo, se conserva la copia anterior")
            continue
        try:
            url_archivo = link_xlsx(url) if via_pagina else url
            n = bajar_archivo(url_archivo, destino)
            ok.append(nombre)
            print(f"  ✔ {nombre:26} {n//1024:5} KB  {url_archivo.split('/')[-1]}")
        except Exception as e:
            if existia:
                conservados.append(nombre)
                print(f"  ~ {nombre:26} se conserva la copia anterior ({e})")
            else:
                fallas.append(nombre)
                print(f"  ✘ {nombre:26} SIN COPIA LOCAL ({e})")
        time.sleep(0.5)

    try:
        n = bajar_calendario()
        print(f"  ✔ {'calendario.json':26} {n} publicaciones")
    except Exception as e:
        print(f"  ~ {'calendario.json':26} se conserva el anterior ({e})")

    print(f"\nDescargados {len(ok)} · conservados {len(conservados)} · sin copia {len(fallas)}")
    if fallas:
        print("  (los que no tienen copia local se heredan del datos.json anterior)")
    # Nunca se corta acá: quien decide si el resultado sirve es verificar.py.
    # Cortar en este punto sólo ensuciaría el log con un rojo que no significa nada.
    return 0


# ---------------------------------------------------------------- calendario

RE_ITEM = re.compile(
    r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})(.{0,400}?)(?=\d{1,2}[/-]\d{1,2}[/-]\d{4}|$)',
    re.S)
RE_TAG = re.compile(r"<[^>]+>")


def bajar_calendario():
    """Extrae el cronograma de publicaciones de IDECBA.

    La página lista cada publicación con su fecha. Se toma el texto plano y se
    parten los items por fecha, que es lo más estable frente a rediseños del
    sitio: si cambian las clases CSS esto sigue funcionando.
    """
    import json
    html = _get(CALENDARIO_URL).text
    texto = RE_TAG.sub(" ", html)
    texto = re.sub(r"&[a-z]+;|&#\d+;", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    items, vistos = [], set()
    for d, m, a, resto in RE_ITEM.findall(texto):
        try:
            f = f"{int(a):04d}-{int(m):02d}-{int(d):02d}"
        except ValueError:
            continue
        if not (2020 <= int(a) <= 2100):
            continue
        titulo = resto.strip(" .·-–|")[:180].strip()
        if len(titulo) < 12:
            continue
        clave = (f, titulo[:60])
        if clave in vistos:
            continue
        vistos.add(clave)
        periodo = ""
        mp = re.search(
            r"((?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|"
            r"setiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?\d{4}|"
            r"\d(?:er|do|to)\.?\s*trimestre\s*(?:de\s*)?\d{4})", titulo, re.I)
        if mp:
            periodo = mp.group(1)
        items.append({"f": f, "t": titulo, "p": periodo})

    if len(items) < 5:
        raise RuntimeError(f"sólo {len(items)} publicaciones, el layout debe haber cambiado")

    items.sort(key=lambda x: x["f"])
    salida = os.path.join(BASE, "calendario.json")
    json.dump({"items": items}, open(salida, "w", encoding="utf-8"), ensure_ascii=False)
    return len(items)


if __name__ == "__main__":
    print("Descargando fuentes oficiales de IDECBA\n")
    sys.exit(main())
