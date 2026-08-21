"""Ejecuta el generador territorial con normalizaciones robustas.

BA Data publica algunos identificadores territoriales con convenciones distintas
a las usadas por el Censo 2022 que alimenta las fichas de CEPOES. Este runner
centraliza esas compatibilizaciones sin duplicar el generador principal.
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

# BA Data usa "Boca" en algunas capas mientras la base censal de CEPOES usa
# "La Boca". Sin este alias el registro queda agregado a Comuna 4 pero no al
# barrio, produciendo ceros falsos en la ficha barrial.
G.BARRIO_ALIASES["boca"] = "La Boca"

if __name__ == "__main__":
    raise SystemExit(G.main())
