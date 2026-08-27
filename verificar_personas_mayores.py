#!/usr/bin/env python3
import json
from pathlib import Path
from actualizar_personas_mayores import validate
d=json.loads(Path("deploy/site-overlay/assets/data/personas-mayores.json").read_text(encoding="utf-8"));validate(d)
p=Path("deploy/site-overlay/observatorio/personas-mayores/index.html").read_text(encoding="utf-8")
for token in ["Una Ciudad envejecida no es, por eso, una Ciudad cuidada","17,7%","$2.835.928","Dato, elaboración e interpretación","/assets/data/personas-mayores.json","pm-dem-map","pm-care-map","La vejez también tiene geografía"]:assert token in p,token
assert "cargando" not in p.lower() and ">—<" not in p
territory=d["territorio"]
assert len(territory["comunas"])==15 and len(territory["equipamientos"])>=100
assert {x["tipo"] for x in territory["equipamientos"]}=={"centro-dia","centro-jubilados","hogar-permanente","geriatrico"}
print("Personas mayores VALIDADO ·",d["indicadores"]["poblacion_65_mas"]["periodo"],"·",d["indicadores"]["canasta_inquilinos"]["periodo"])
