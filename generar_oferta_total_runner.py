"""Genera el catálogo total: 29 capas validadas + segunda ampliación exhaustiva."""
from __future__ import annotations

import generar_oferta_ampliada_runner as R
import oferta_extra_2_fix  # muta la configuración extra antes de importarla
from oferta_extra_2 import EXTRA_CATEGORIES, EXTRA_DATASETS, EXTRA_LAYERS


def main() -> int:
    # El módulo base importa el diccionario por referencia; actualizarlo permite
    # reutilizar el mismo normalizador, trazabilidad de fuentes y control espacial.
    R.E.DATASETS_TERRITORIO.update(EXTRA_DATASETS)
    known = {x["id"] for x in R.E.LAYERS}
    R.E.LAYERS.extend(x for x in EXTRA_LAYERS if x["id"] not in known)
    known_cat = {x[0] for x in R.E.CATEGORIES}
    R.E.CATEGORIES.extend(x for x in EXTRA_CATEGORIES if x[0] not in known_cat)
    print(f"Oferta total configurada: {len(R.E.CORE_LAYERS) + len(R.E.LAYERS)} capas")
    return R.main()


if __name__ == "__main__":
    raise SystemExit(main())
