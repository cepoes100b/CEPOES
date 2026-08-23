#!/usr/bin/env python3
"""
Descarga las bases de la Central de Deudores del BCRA
 desde https://www5.bcra.gob.ar/ChequesyDeudores/Deudores

Mecanismo real del sitio:
  - Cada link llama Confirmacion(url, nombre), que:
      1. POSTea {Name: nombre} a /ChequesyDeudores/Deudores/Log_Archivo
      2. Envía el form (con hidden sessionid) a
         https://mft.bcra.gob.ar/apilink.aspx?&username=api_user
           &arg01=<ID>&arg05=0/<ARCHIVO>&arg12=downloaddirect&quiet=true
  - Los <ID> cambian con cada publicación mensual: este script los
    extrae dinámicamente de la página, así sirve todos los meses.

NOTA: el sitio pide aceptar términos y condiciones (Ley 25.326 de
Protección de Datos Personales) antes de descargar. Ejecutar este
script equivale a aceptarlos.

Uso:
    pip install requests
    python descargar_bcra_deudores.py            # todo
    python descargar_bcra_deudores.py PADRON     # solo los que matcheen

Fallback con navegador real (ejecuta el JS del sitio y hace click):
    pip install playwright && playwright install chromium
    python descargar_bcra_deudores.py --navegador
"""

import re
import sys
import time
from pathlib import Path

BASE = "https://www5.bcra.gob.ar"
PAGINA = f"{BASE}/ChequesyDeudores/Deudores"
LOG_URL = f"{BASE}/ChequesyDeudores/Deudores/Log_Archivo"
DESTINO = Path("bcra_deudores")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
FIRMA_7Z = b"7z\xbc\xaf\x27\x1c"


def log(msg):
    print(msg, flush=True)


def parsear_pagina(html):
    """Extrae [(nombre, url_mft)] y el sessionid del form."""
    patron = re.compile(
        r"Confirmacion\('([^']*?)'\s*\+\s*'(\d+)'\s*\+\s*'([^']*?)'\s*\+\s*"
        r"'([^']+?)'\s*\+\s*'([^']*?)'\s*,\s*'([^']+)'\)")
    archivos = []
    for m in patron.finditer(html.replace("&amp;", "&")):
        pre, fid, mid, nombre_url, post, nombre = m.groups()
        url = f"{pre}{fid}{mid}{nombre_url}{post}"
        archivos.append((nombre, url))
    sess_m = re.search(
        r"name=['\"]sessionid['\"]\s+value=\"([^\"]+)\"", html)
    sessionid = sess_m.group(1) if sess_m else None
    return archivos, sessionid


def guardar_stream(resp, destino):
    """Guarda una respuesta en streaming. True si el archivo es 7z válido."""
    total = int(resp.headers.get("Content-Length") or 0)
    bajado = 0
    destino_tmp = destino.with_suffix(destino.suffix + ".part")
    destino_tmp.unlink(missing_ok=True)
    try:
        primeros = b""
        with open(destino_tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                if not primeros:
                    primeros = chunk[:6]
                    if len(primeros) >= 2 and not primeros.startswith(FIRMA_7Z[:2]):
                        return False
                f.write(chunk)
                bajado += len(chunk)
                pct = f" ({bajado*100//total}%)" if total else ""
                print(f"\r      {destino.name}: {bajado/1e6:8.1f} MB{pct}",
                      end="", flush=True)
        print()
        with open(destino_tmp, "rb") as f:
            ok = f.read(6) == FIRMA_7Z
        if not ok:
            return False
        destino_tmp.replace(destino)
        return True
    finally:
        destino_tmp.unlink(missing_ok=True)


def descargar(sess, nombre, url, sessionid):
    destino = DESTINO / nombre
    if destino.exists():
        try:
            with destino.open("rb") as f:
                if f.read(6) == FIRMA_7Z:
                    log(f"   YA EXISTE -> {destino}")
                    return True
        except OSError:
            pass
        destino.unlink(missing_ok=True)

    intentos = [
        ("POST", url, {"sessionid": sessionid} if sessionid else {}),
        ("GET", url + "&language=es", None),
        ("GET", url, None),
    ]
    for metodo, u, data in intentos:
        try:
            r = sess.request(metodo, u, data=data, stream=True,
                             timeout=(30, 600), allow_redirects=True)
        except Exception as e:
            log(f"      {metodo} falló: {e}")
            continue
        try:
            if r.status_code == 200 and guardar_stream(r, destino):
                log(f"   OK -> {destino}")
                return True
        finally:
            r.close()
    return False


def via_requests(filtro):
    import requests
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": PAGINA})

    log(f"[1/3] Obteniendo página: {PAGINA}")
    r = sess.get(PAGINA, timeout=60)
    r.raise_for_status()
    archivos, sessionid = parsear_pagina(r.text)
    if not archivos:
        log("   No pude extraer los links (¿cambió el sitio?).")
        return [], ["(todos)"]
    log(f"   {len(archivos)} archivos: "
        + ", ".join(n for n, _ in archivos))
    if filtro:
        archivos = [(n, u) for n, u in archivos
                    if any(f.lower() in n.lower() for f in filtro)]
        log(f"   Filtrados: {', '.join(n for n, _ in archivos)}")

    log("[2/3] Iniciando sesión con el servidor MFT...")
    try:
        sess.get("https://mft.bcra.gob.ar/", timeout=30)
    except Exception:
        pass

    log("[3/3] Descargando...")
    DESTINO.mkdir(exist_ok=True)
    bajados, faltan = [], []
    for nombre, url in archivos:
        log(f"   > {nombre}")
        try:
            sess.post(LOG_URL, data={"Name": nombre}, timeout=30)
        except Exception:
            pass
        (bajados if descargar(sess, nombre, url, sessionid)
         else faltan).append(nombre)
    return bajados, faltan


def via_navegador(filtro):
    """Playwright: clickea cada link, acepta el diálogo de términos
    y captura la descarga. Ejecuta el JS real del sitio."""
    from playwright.sync_api import sync_playwright
    DESTINO.mkdir(exist_ok=True)
    bajados = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(accept_downloads=True, user_agent=UA)
        page = ctx.new_page()
        log(f"[navegador] Abriendo {PAGINA}")
        page.goto(PAGINA, wait_until="networkidle", timeout=90000)
        nombres = [t.strip() for t in
                   page.locator("table a").all_inner_texts() if ".7Z" in t.upper()]
        if filtro:
            nombres = [n for n in nombres
                       if any(f.lower() in n.lower() for f in filtro)]
        log(f"[navegador] Archivos: {', '.join(nombres)}")
        for nombre in nombres:
            log(f"   > {nombre}")
            try:
                page.get_by_text(nombre, exact=False).first.click()
                page.wait_for_selector(".swal2-confirm", timeout=15000)
                with page.expect_download(timeout=900000) as dl_info:
                    page.click(".swal2-confirm")
                dl = dl_info.value
                destino = DESTINO / (dl.suggested_filename or nombre)
                dl.save_as(destino)
                log(f"   OK -> {destino} "
                    f"({destino.stat().st_size/1e6:.1f} MB)")
                bajados.append(nombre)
                page.goto(PAGINA, wait_until="networkidle", timeout=90000)
            except Exception as e:
                log(f"   Falló {nombre}: {e}")
        browser.close()
    return bajados


def main():
    t0 = time.time()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--navegador" in sys.argv:
        bajados, faltan = via_navegador(args), []
    else:
        try:
            bajados, faltan = via_requests(args)
        except Exception as e:
            log(f"Error: {e}")
            bajados, faltan = [], ["(todos)"]
        if faltan:
            log("\nQuedaron pendientes: " + ", ".join(faltan))
            log("Probá el fallback con navegador real:")
            log("   pip install playwright && playwright install chromium")
            log(f"   python {Path(sys.argv[0]).name} --navegador")
    log(f"\nListo en {(time.time()-t0)/60:.1f} min. "
        f"Bajados: {len(bajados)}" + (f" | Pendientes: {len(faltan)}" if faltan else ""))
    if bajados:
        log(f"Archivos en: {DESTINO.resolve()}")


if __name__ == "__main__":
    main()
