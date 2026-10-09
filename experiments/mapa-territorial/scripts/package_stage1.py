#!/usr/bin/env python3
"""Bundle only the territorial experiment; no fetches or production assets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--evidence', type=Path, required=True)
a = parser.parse_args()
repo = Path(__file__).resolve().parents[3]
source = repo / 'experiments/mapa-territorial/public'
a.output.mkdir(parents=True, exist_ok=True)
site = a.output / 'site'
shutil.copytree(source, site, dirs_exist_ok=True)
shutil.copy2(site / 'laboratorio/mapa-territorial/index.html', site / 'index.html')
# Existing catalogue links belong to CEPOES production, not to this small preview.
for page in [site / 'index.html', site / 'laboratorio/mapa-territorial/index.html']:
    text = page.read_text().replace('href="/territorio/', 'href="https://cepoes.org/territorio/')
    page.write_text(text)
app = site / 'assets/mapa-territorial/app.mjs'
app.write_text(app.read_text().replace('`/territorio/barrios/', '`https://cepoes.org/territorio/barrios/').replace("'/territorio/equipamientos/'", "'https://cepoes.org/territorio/equipamientos/'"))
shutil.copytree(a.evidence, a.output / 'evidence', dirs_exist_ok=True)
manifest = {
    'schema': 'cepoes-stage1-handoff-v1',
    'base_main': '73d0cf3f10c972a6f404060fb574754a4789b8ad',
    'reused_pr195': 'b1eb068331831e6533f7188033f62fa0bca20a43',
    'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
    'entrypoint': 'site/index.html',
    'target_project': 'appgprj_6ac8da2772ac81918f139b851872e602',
    'target_preview': 'https://cepoes-mapa-territorial-pr195.crivelli725370.chatgpt.site',
    'audience': 'preserve existing private audience',
    'approval': 'Pending owner visual approval. No merge or production deployment authorized.',
    'reference_status': 'Library materialization failed twice; reference pixels not inspected. No benchmark superiority claim.',
    'network': 'Initial render uses local vendored resources only. Optional street map and source/catalogue links retain external origins.',
    'files': [{'path': str(p.relative_to(a.output)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size} for p in sorted(site.rglob('*')) if p.is_file()]
}
(a.output / 'handoff-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
(a.output / 'LEEME.txt').write_text('CEPOES — candidato visual ETAPA1, pendiente de aprobación\n\nServir la carpeta site con un servidor estático. Ejemplo:\n  python3 -m http.server 8000 --directory site\nAbrir http://localhost:8000/\n\nEntrada: 3D, Comuna 8, INDEC Censo 2022.\nMóvil: Comparar comunas abre el panel inferior.\nAlternativas: Plana, ranking, tabla y Explorar servicios.\nGiro voluntario; respeta movimiento reducido.\n\nHandoff exclusivamente al MISMO Site privado indicado en el manifest.\nNo se operó Sites, no se fusionó ni desplegó producción.\nLa referencia Library no pudo descargarse: comparación visual pendiente.\nLas capturas evidence son renders reales de Chromium.\n')
archive=a.output.with_suffix('.zip')
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(a.output.rglob('*')):
        if p.is_file(): z.write(p, p.relative_to(a.output))
print(json.dumps({'zip':str(archive),'bytes':archive.stat().st_size,'files':len(manifest['files'])}))
