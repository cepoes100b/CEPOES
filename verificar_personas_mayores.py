#!/usr/bin/env python3
import json
from pathlib import Path
from actualizar_personas_mayores import validate
d=json.loads(Path("deploy/site-overlay/assets/data/personas-mayores.json").read_text(encoding="utf-8"));validate(d)
p=Path("deploy/site-overlay/observatorio/personas-mayores/index.html").read_text(encoding="utf-8")
for token in ["Una Ciudad envejecida no es, por eso, una Ciudad cuidada","17,7%","$2.835.928","Dato, elaboración e interpretación","/assets/data/personas-mayores.json"]:assert token in p,token
assert "cargando" not in p.lower() and ">—<" not in p
print("Personas mayores VALIDADO ·",d["indicadores"]["poblacion_65_mas"]["periodo"],"·",d["indicadores"]["canasta_inquilinos"]["periodo"])
