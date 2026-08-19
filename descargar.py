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

import socket

import requests

from fuentes import CAT_BASE, DATASETS, CALENDARIO_URL

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
}

SESION = requests.Session()
SESION.headers.update(CABECERAS)
# El servidor de IDECBA acepta el primer pedido y después empieza a rechazar
# conexiones (ConnectTimeout, ni siquiera completa el saludo TCP). Parece un
# límite por IP. Dos medidas: forzar IPv4 —el sitio anuncia IPv6 pero no
# responde por ahí, y los runners de GitHub lo intentan primero— y bajar pocos
# archivos por corrida, espaciados, rotando cuáles (ver COLA más abajo).
TIMEOUT = (8, 60)           # (conexión, lectura): si no conecta en 8s, no va a conectar
REINTENTOS = 3
ESPERA = [5, 15]            # backoff entre reintentos
ENTRE_ARCHIVOS = 6          # pausa entre datasets, para no gatillar el límite
POR_CORRIDA = 4             # cuántos datasets se intentan por vez
PRESUPUESTO_SEG = 600       # 10 min de tope duro

# Los runners de GitHub tienen IPv6 y lo prueban primero; si el destino publica
# AAAA pero no atiende, cada conexión se cuelga hasta el timeout.
try:
    import urllib3.util.connection as _u3
    _u3.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass
RE_XLSX = re.compile(r'https?://[^"\'\s>]+?\.xlsx', re.I)
RE_POST = re.compile(
    r'href="(https://www\.estadisticaciudad\.gob\.ar/eyc/banco-datos/([^"/]+)/)"', re.I)


ARRANQUE = time.time()


def queda_tiempo():
    return time.time() - ARRANQUE < PRESUPUESTO_SEG


def _get(url, **kw):
    ultimo = None
    for intento in range(REINTENTOS):
        if not queda_tiempo():
            raise RuntimeError("se agotó el presupuesto de tiempo")
        try:
            r = SESION.get(url, timeout=TIMEOUT, **kw)
            if r.status_code == 200:
                return r
            ultimo = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            ultimo = type(e).__name__
        time.sleep(ESPERA[min(intento, len(ESPERA) - 1)])
    raise RuntimeError(ultimo or "sin respuesta")


class SinCoincidencia(RuntimeError):
    """El patrón no encontró post. Lleva los slugs que sí había en la categoría,
    para poder corregir fuentes.py sin adivinar."""

    def __init__(self, msg, categoria, disponibles):
        super().__init__(msg)
        self.categoria = categoria
        self.disponibles = disponibles


def buscar_post(categoria, patron):
    """URL del post vigente de un dataset dentro de su categoría.

    La categoría lista los posts del más nuevo al más viejo, así que el primero
    que coincide con el patrón es el que está publicado ahora.
    """
    html = _get(CAT_BASE + categoria + "/").text
    pat = re.compile(patron, re.I)
    for m in RE_POST.finditer(html):
        if pat.search(m.group(2)):
            return m.group(1)
    disponibles = [m.group(2) for m in RE_POST.finditer(html)]
    raise SinCoincidencia(f"ningún post coincide con /{patron}/", categoria, disponibles)


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


ESTADO = os.path.join(BASE, "estado_descargas.json")


def cola_por_antiguedad():
    """Ordena los datasets por hace cuánto que no se bajan.

    Como IDECBA corta las conexiones cuando se le piden muchos archivos
    seguidos, cada corrida intenta sólo unos pocos: los que hace más tiempo que
    no se actualizan, y siempre primero los que nunca se pudieron bajar. Con
    una corrida diaria el ciclo completo se cierra en pocos días, de sobra para
    series que se publican una vez por mes o por trimestre.
    """
    import json
    try:
        est = json.load(open(ESTADO, encoding="utf-8"))
    except Exception:
        est = {}
    todos = [(n, cat, pat) for n, (cat, pat, _d) in DATASETS.items()]
    # nunca bajado = prioridad máxima (timestamp 0)
    todos.sort(key=lambda t: est.get(t[0], 0))
    return todos, est


def guardar_estado(est):
    import json
    try:
        json.dump(est, open(ESTADO, "w", encoding="utf-8"), indent=1)
    except Exception:
        pass


def main():
    ok, conservados, fallas = [], [], []

    todos, est = cola_por_antiguedad()
    pendientes = todos[:POR_CORRIDA]
    en_espera = [t[0] for t in todos[POR_CORRIDA:]]
    print(f"Se intentan {len(pendientes)} de {len(todos)} datasets en esta corrida.")
    print(f"Quedan para las próximas: {', '.join(en_espera)}\n")

    for nombre, categoria, patron in pendientes:
        destino = os.path.join(DIR_XLSX, nombre)
        existia = os.path.exists(destino)
        print(f"  … {nombre:26} consultando", flush=True)
        if not queda_tiempo():
            conservados.append(nombre)
            print(f"  ~ {nombre:26} sin tiempo, se conserva la copia anterior")
            continue
        try:
            post = buscar_post(categoria, patron)
            url_archivo = link_xlsx(post)
            n = bajar_archivo(url_archivo, destino)
            ok.append(nombre)
            est[nombre] = int(time.time())
            print(f"  ✔ {nombre:26} {n//1024:5} KB  {url_archivo.split('/')[-1]}")
        except Exception as e:
            if existia:
                conservados.append(nombre)
                print(f"  ~ {nombre:26} se conserva la copia anterior ({e})")
            else:
                fallas.append(nombre)
                print(f"  ✘ {nombre:26} SIN COPIA LOCAL ({e})")
        time.sleep(ENTRE_ARCHIVOS)

    guardar_estado(est)

    # El calendario se intenta siempre: es una sola página y es lo que más
    # rápido queda desactualizado.
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

# El calendario lista una publicación por bloque, con el título en un heading y
# la fecha en un atributo de la tarjeta. Partir el texto por fechas no sirve
# (casi ninguna aparece en el texto plano), así que se leen los títulos y la
# fecha se deduce del período que el propio título declara: "Julio de 2026",
# "2do. trimestre de 2026", etc. Las cadencias de IDECBA son regulares, así que
# esa deducción es exacta salvo por el día, que se estima con el patrón de la
# serie. Todo lo proyectado se marca para no presentarlo como fecha oficial.
RE_TAG = re.compile(r"<[^>]+>")
RE_TITULO = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.S | re.I)
RE_FECHA_ATTR = re.compile(r"(\d{2})/(\d{2})/(\d{4})")

MESES_N = {"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,
           "agosto":8,"septiembre":9,"setiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
TRI_N = {"1er":1,"1ro":1,"2do":2,"3er":3,"3ro":3,"4to":4}

# Día típico de publicación y desfasaje respecto del período que informa.
# (regex del título, día del mes, meses de rezago desde el fin del período)
PATRONES = [
    (r"^ipcba", 8, 1),
    (r"l[ií]neas de pobreza", 8, 1),
    (r"^sipcba", 16, 1),
    (r"canasta de crianza", 18, 1),
    (r"situaci[óo]n del mercado laboral", 23, 3),
    (r"ingresos en la ciudad", 24, 3),
    (r"condiciones de vida", 25, 3),
    (r"actividad econ[óo]mica", 26, 3),
    (r"comercio minorista", 29, 3),
    (r"ejes comerciales", 20, 2),
    (r"mercado de alquiler", 12, 1),
    (r"mercado de venta", 14, 1),
]


def _periodo_a_fecha(titulo):
    """Devuelve (fecha_iso, etiqueta_periodo) deducidas del título."""
    t = titulo.lower()
    anio = mes_fin = None
    etiqueta = ""

    m = re.search(r"(\d)(?:er|do|to|ro)\.?\s*(?:trimestre|cuatrimestre)\s*(?:de\s*)?((?:19|20)\d{2})", t)
    if m:
        n, anio = int(m.group(1)), int(m.group(2))
        largo = 4 if "cuatrimestre" in t else 3
        mes_fin = n * largo
        etiqueta = m.group(0).strip()
    if mes_fin is None:
        m = re.search(r"(" + "|".join(MESES_N) + r")\s+(?:de\s+)?((?:19|20)\d{2})", t)
        if m:
            mes_fin, anio = MESES_N[m.group(1)], int(m.group(2))
            etiqueta = m.group(0).strip()
    if mes_fin is None:
        m = re.search(r"a[ñn]o\s+((?:19|20)\d{2})", t)
        if m:
            mes_fin, anio, etiqueta = 12, int(m.group(1)), m.group(0).strip()
    if mes_fin is None or anio is None:
        return None, ""

    dia, rezago = 15, 2
    for patron, d, r in PATRONES:
        if re.search(patron, t):
            dia, rezago = d, r
            break

    mes = mes_fin + rezago
    anio_pub = anio + (mes - 1) // 12
    mes = (mes - 1) % 12 + 1
    try:
        return f"{anio_pub:04d}-{mes:02d}-{dia:02d}", etiqueta
    except ValueError:
        return None, ""


def bajar_calendario():
    """Arma calendario.json a partir del listado de publicaciones de IDECBA."""
    import json
    html = _get(CALENDARIO_URL).text

    items, vistos = [], set()
    for bruto in RE_TITULO.findall(html):
        titulo = RE_TAG.sub(" ", bruto)
        titulo = re.sub(r"&[a-z]+;|&#\d+;", " ", titulo)
        titulo = re.sub(r"\s+", " ", titulo).strip()
        if len(titulo) < 15 or titulo.lower() in vistos:
            continue
        # se descartan encabezados de navegación
        if re.search(r"men[úu]|buscar|calendario de publicaciones|instituto de estad", titulo, re.I):
            continue
        f, periodo = _periodo_a_fecha(titulo)
        if not f:
            continue
        vistos.add(titulo.lower())
        items.append({"f": f, "t": titulo[:180], "p": periodo, "est": True})

    if len(items) < 10:
        raise RuntimeError(f"sólo {len(items)} publicaciones, el layout debe haber cambiado")

    items.sort(key=lambda x: x["f"])
    json.dump({"items": items}, open(os.path.join(BASE, "calendario.json"), "w",
              encoding="utf-8"), ensure_ascii=False)
    return len(items)


if __name__ == "__main__":
    print("Descargando fuentes oficiales de IDECBA\n")
    sys.exit(main())
