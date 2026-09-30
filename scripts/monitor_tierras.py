"""Detecta cambios documentales. Sus resultados requieren revisión editorial."""
import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCES = {
    'rntr_departamentos': 'https://www.argentina.gob.ar/sites/default/files/2021/02/extranjerizacion_por_departamento_pdf.pdf',
    'rntr_catalogo': 'https://www.argentina.gob.ar/justicia/tierrasrurales/datos/extranjerizacion-departamento',
    'dnu_70': 'https://www.argentina.gob.ar/normativa/nacional/decreto-70-2023-395521/texto',
}

def run(destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    state_path = root / 'estado.json'
    previous = json.loads(state_path.read_text()) if state_path.exists() else {}
    now = datetime.now(timezone.utc).isoformat()
    output = {}
    failed = False
    for name, url in SOURCES.items():
        old = previous.get(name, {})
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'CEPOES-monitor-tierras/1.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read(20_000_001)
                mime = response.headers.get('Content-Type', '')
            if len(body) > 20_000_000 or len(body) < 100:
                raise ValueError('Tamaño inesperado')
            if name == 'rntr_departamentos' and not body.startswith(b'%PDF-'):
                raise ValueError('La fuente no devolvió un PDF')
            if name != 'rntr_departamentos' and b'<html' not in body.lower()[:2000]:
                raise ValueError('La fuente no devolvió HTML')
            digest = hashlib.sha256(body).hexdigest()
            changed = old.get('sha256') != digest
            extension = '.pdf' if name == 'rntr_departamentos' else '.html'
            snapshot = f'{name}-{digest}{extension}'
            (root / snapshot).write_bytes(body)
            output[name] = dict(url=url, sha256=digest, documento=snapshot,
                consultado=now, modificado=now if changed else old.get('modificado', now),
                estado='primera_captura' if not old.get('sha256') else ('cambio_documental' if changed else 'sin_cambios'),
                revision='pendiente' if changed else old.get('revision', 'pendiente'), mime=mime)
        except Exception as error:
            failed = True
            output[name] = dict(old, url=url, consultado=now, estado='error', error=type(error).__name__)
    temp = state_path.with_suffix('.tmp')
    temp.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    temp.replace(state_path)
    print(json.dumps({k: {'estado': v['estado'], 'revision': v.get('revision')} for k, v in output.items()}))
    return 1 if failed else 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='monitor-tierras')
    sys.exit(run(parser.parse_args().output))
