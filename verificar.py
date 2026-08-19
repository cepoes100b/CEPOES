"""Control de calidad de datos.json antes de publicarlo.

Corre después del generador, dentro del workflow. Si algo no cierra, devuelve
código distinto de cero y el commit no se hace: el observatorio se queda con el
archivo anterior, que es correcto aunque esté algo más viejo.

Lo que revisa no es sólo que el archivo exista, sino que los números sean
plausibles: series que no se acortan, porcentajes dentro de rango, y ninguna
serie estancada desde hace demasiado.
"""
import json
import os
import sys
import datetime
import subprocess

# En GitHub Actions stdout no es una terminal: Python la bufferiza y el paso
# queda mudo hasta terminar. Con esto cada línea sale en el momento.
try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(BASE, "datos.json")

# bloque -> (campo de períodos, largo mínimo esperado)
LARGOS = {
    "ipcba":         ("meses", 24),
    "canastas":      ("meses", 24),
    "empleo":        ("trimestres", 20),
    "pobreza":       ("periodos", 8),
    "comex":         ("anios", 10),
    "industria":     ("periodos", 24),
    "masa_salarial": ("periodos", 24),
    "locales_evo":   ("periodos", 4),
}
# serie de porcentajes -> (mínimo, máximo) admisibles
RANGOS = {
    ("empleo", "desocupacion"): (0, 40),
    ("empleo", "actividad"): (30, 80),
    ("empleo", "empleo"): (25, 75),
    ("pobreza", "pob_per_pct"): (0, 80),
    ("pobreza", "ind_per_pct"): (0, 50),
    ("ipcba", "var_m"): (-20, 100),
    ("locales_evo", "tasa"): (50, 100),
}

errores, avisos = [], []


def previo():
    """El datos.json tal como está commiteado, para comparar contra el nuevo."""
    try:
        txt = subprocess.run(["git", "show", "HEAD:datos.json"], cwd=BASE,
                             capture_output=True, text=True, timeout=30)
        return json.loads(txt.stdout) if txt.returncode == 0 else None
    except Exception:
        return None


def main():
    if not os.path.exists(SALIDA):
        print("✘ no existe datos.json")
        return 1
    d = json.load(open(SALIDA, encoding="utf-8"))
    ant = previo()

    # 1. fecha de generación
    try:
        g = datetime.date.fromisoformat(d["generado"])
        if abs((datetime.date.today() - g).days) > 2:
            errores.append(f"'generado' dice {g}, hoy es {datetime.date.today()}")
    except Exception as e:
        errores.append(f"'generado' inválido: {e}")

    # 2. bloques presentes y con largo razonable
    for k, (campo, minimo) in LARGOS.items():
        b = d.get(k)
        if not b:
            errores.append(f"falta el bloque '{k}'")
            continue
        serie = b.get(campo)
        if not isinstance(serie, list) or len(serie) < minimo:
            errores.append(f"{k}.{campo}: {len(serie or [])} elementos, mínimo {minimo}")
            continue
        # ninguna serie del bloque puede tener otro largo
        for c, v in b.items():
            if isinstance(v, list) and len(v) != len(serie):
                errores.append(f"{k}.{c} mide {len(v)} y {k}.{campo} mide {len(serie)}")

    # 3. las 15 comunas
    cl = d.get("comunas_locales") or {}
    if len(cl.get("data") or {}) != 15:
        errores.append(f"comunas_locales: {len(cl.get('data') or {})} comunas, esperaba 15")

    # 3.a las divisiones del IPCBA: 12 o 13, del mismo mes que la serie
    div = ((d.get("ipcba") or {}).get("divisiones") or {})
    filas = div.get("data") or []
    if not 10 <= len(filas) <= 16:
        errores.append(f"ipcba.divisiones: {len(filas)} filas, esperaba entre 12 y 13 "
                       "(¿se colaron los grupos y clases?)")
    meses = (d.get("ipcba") or {}).get("meses") or []
    if meses and div.get("periodo"):
        mm, aa = meses[-1].split("-")
        esperado = f"20{aa}-{['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'].index(mm)+1:02d}"
        if div["periodo"] != esperado:
            avisos.append(f"ipcba.divisiones es de {div['periodo']} y la serie llega a {esperado}")

    # 3.a2 campos que la web da por sentados: si faltan, la página se rompe entera
    REQUERIDOS = {
        "pgb": ("trimestres", "total", "categorias", "ultimo_trim", "ultimo_var",
                "sectores_ultimo", "pesos_ultimo"),
        "industria": ("periodos", "total_const", "pesos", "pesos_periodo"),
        "comex": ("anios", "expo", "pct_pgb"),
        "comunas_locales": ("periodo", "data", "total"),
    }
    for blo, campos in REQUERIDOS.items():
        b = d.get(blo) or {}
        faltan = [c for c in campos if not b.get(c)]
        if faltan:
            errores.append(f"{blo}: faltan campos que la web necesita: {', '.join(faltan)}")

    # 3.a3 orden de magnitud esperado por serie.
    # Antes esto se comparaba contra la versión publicada, pero eso no distingue
    # "se rompió" de "se arregló": cuando corregí el parser de industria, el
    # control frenó justamente el arreglo. Con rangos declarados el criterio no
    # depende de lo que haya publicado antes.
    ESCALAS = {
        ("industria", "total_const"): (20, 2000),        # índice base oct-2001=100
        ("masa_salarial", "total"):   (20, 5_000_000),   # índice, crece con la inflación
        ("canastas", "total"):        (1000, 100_000_000),
        ("comex", "expo"):            (50, 5000),        # millones de dólares
        ("pgb", "total"):             (-60, 60),         # variación porcentual
    }
    for (blo, ser), (lo, hi) in ESCALAS.items():
        vals = [abs(v) for v in ((d.get(blo) or {}).get(ser) or []) if v]
        if not vals:
            continue
        m = max(vals)
        if not lo <= m <= hi:
            errores.append(f"{blo}.{ser}: el máximo es {m:.4g} y debería caer entre "
                           f"{lo:g} y {hi:g} (¿el parser leyó otra columna?)")

    # 3.b los bloques que no se regeneran tienen que seguir estando
    for k in ("presupuesto", "censo", "poblacion"):
        if not d.get(k):
            errores.append(f"falta el bloque conservado '{k}'")

    # 4. rangos plausibles
    for (blo, ser), (lo, hi) in RANGOS.items():
        vals = [v for v in ((d.get(blo) or {}).get(ser) or []) if v is not None]
        fuera = [v for v in vals if not (lo <= v <= hi)]
        if fuera:
            errores.append(f"{blo}.{ser}: {len(fuera)} valores fuera de [{lo},{hi}] "
                           f"(ej. {fuera[:3]})")

    # 5. nada se acortó respecto de lo publicado
    if ant:
        for k, (campo, _) in LARGOS.items():
            n = len((d.get(k) or {}).get(campo) or [])
            v = len((ant.get(k) or {}).get(campo) or [])
            if n < v:
                errores.append(f"{k}.{campo} se acortó: {v} → {n}")
        for k in ("presupuesto", "censo", "poblacion"):
            if k in ant and k not in d:
                errores.append(f"se perdió el bloque conservado '{k}'")

    # 6. series estancadas (aviso, no error: hay datos trimestrales y anuales)
    hoy = datetime.date.today()
    ult = {"ipcba": (d.get("ipcba") or {}).get("meses"),
           "empleo": (d.get("empleo") or {}).get("trimestres"),
           "pobreza": (d.get("pobreza") or {}).get("periodos")}
    for k, v in ult.items():
        if v:
            avisos.append(f"{k}: último período {v[-1]}")

    print(f"datos.json · {os.path.getsize(SALIDA)//1024} KB · generado {d.get('generado')}")
    for a in avisos:
        print("  ·", a)
    if errores:
        print(f"\n✘ {len(errores)} problema(s) — NO se publica:")
        for e in errores:
            print("   ·", e)
        return 1
    print(f"\n✔ verificación superada ({len(LARGOS)} bloques, {len(RANGOS)} rangos, "
          f"{'comparado con la versión publicada' if ant else 'sin versión previa que comparar'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
