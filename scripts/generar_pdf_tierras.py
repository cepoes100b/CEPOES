"""Genera el informe usando la plantilla CEPOES canónica y su portada como miniatura."""
import argparse,importlib.util,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--contenido',default='docs/tierras-contenido.json');p.add_argument('--plantilla',default='scripts/generar_informes_pdf_cepoes.py');p.add_argument('--sitio',default='deploy/site-overlay');args=p.parse_args()
spec=importlib.util.spec_from_file_location('plantilla',args.plantilla);t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
data=json.loads(Path(args.contenido).read_text());t.SITE_ROOT=Path(args.sitio)
# La miniatura procede de la misma portada PDF, sin un diseño paralelo.
original=t.thumbnail_svg;data['report']['thumb']='tierras-y-soberania-preview.svg'
pdf=t.build(data['report'],data['sections']);(t.SITE_ROOT/'assets/publicaciones/tierras-y-soberania-preview.svg').unlink()
thumb=t.SITE_ROOT/'assets/publicaciones/tierras-y-soberania'
subprocess.run(['pdftoppm','-f','1','-singlefile','-scale-to','1120','-png',str(pdf),str(thumb)],check=True)
print(pdf)
