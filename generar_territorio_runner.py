"""Ejecuta el generador territorial con normalización robusta de comunas.

BA Data publica la comuna del padrón educativo con cero a la izquierda en
algunos registros (01..09). La expresión original interpretaba bien 10..15 pero
podía no reconocer 01..09. Este runner centraliza la corrección sin alterar el
resto del generador.
"""
import re

import generar_territorio as G


def parse_comuna(v):
    s = G.clean_text(v)
    # Acepta 1, 01, "Comuna 01", 10, etc. e ignora otros números que puedan
    # aparecer en el texto. Siempre devuelve un entero 1..15.
    for token in re.findall(r"\d+", s):
        try:
            n = int(token)
        except ValueError:
            continue
        if 1 <= n <= 15:
            return n
    return None


G.parse_comuna = parse_comuna

if __name__ == "__main__":
    raise SystemExit(G.main())
