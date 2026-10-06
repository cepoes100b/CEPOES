#!/usr/bin/env python3
import json
from pathlib import Path

from bs4 import BeautifulSoup

from actualizar_personas_mayores import page_values, validate


def validate_page(d, source):
    validate(d)
    for token in ["Una Ciudad envejecida no es, por eso, una Ciudad cuidada",
                  "Dato, elaboración e interpretación", "/assets/data/personas-mayores.json",
                  "pm-dem-map", "pm-care-map", "La vejez también tiene geografía"]:
        assert token in source, token
    assert "cargando" not in source.lower() and ">—<" not in source
    soup = BeautifulSoup(source, "html.parser")
    for element_id, expected in page_values(d).items():
        elements = soup.find_all(id=element_id)
        assert len(elements) == 1, f"marcador ausente o duplicado: {element_id}"
        actual = elements[0].get_text(" ", strip=True)
        assert actual == expected, f"{element_id}: {actual!r} != {expected!r}"
    territory = d["territorio"]
    assert len(territory["comunas"]) == 15 and len(territory["equipamientos"]) >= 100
    assert {x["tipo"] for x in territory["equipamientos"]} == {
        "centro-dia", "centro-jubilados", "hogar-permanente", "geriatrico"}


def main():
    d = json.loads(Path("deploy/site-overlay/assets/data/personas-mayores.json").read_text(encoding="utf-8"))
    p = Path("deploy/site-overlay/observatorio/personas-mayores/index.html").read_text(encoding="utf-8")
    validate_page(d, p)
    print("Personas mayores VALIDADO ·", d["indicadores"]["poblacion_65_mas"]["periodo"],
          "·", d["indicadores"]["canasta_inquilinos"]["periodo"])


if __name__ == "__main__":
    main()
