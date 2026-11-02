#!/usr/bin/env python3
"""CEPOES · Salud reproductiva / PAEV · monitor de fuentes oficiales.

No convierte menciones o denuncias en evidencia. Revisa disponibilidad y huellas
de las fuentes; la matriz de transparencia sólo cambia mediante revisión validada.
"""
from __future__ import annotations
import hashlib,json,re,urllib.request
import argparse, http.client, socket, time, urllib.error
from datetime import datetime,timezone
from pathlib import Path
DATA=Path('deploy/site-overlay/assets/data/salud-reproductiva.json');ROOT=Path('salud_reproductiva.json');UA='CEPOES-data-monitor/1.0 (+https://cepoes.org)'
def get(url,timeout=90):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
def fingerprint(raw,url):
    low=url.lower().split('?',1)[0]
    if low.endswith(('.pdf','.xlsx','.xls','.csv')):payload=raw
    else:
        text=raw.decode('utf-8','ignore')
        text=re.sub(r'<!--.*?-->',' ',text,flags=re.S)
        text=re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',text,flags=re.I|re.S)
        text=re.sub(r'\s+',' ',text).strip()
        payload=text.encode('utf-8')
    return hashlib.sha256(payload).hexdigest()
def transient(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in (408, 429, 500, 502, 503, 504)
    if isinstance(exc, urllib.error.URLError):
        return transient(exc.reason)
    return isinstance(exc, (TimeoutError, ConnectionError, socket.gaierror,
                            http.client.IncompleteRead, http.client.RemoteDisconnected))


def check_source(source_id, url):
    errors = []
    for attempt in range(1, 4):
        print(f"Fuente {source_id}: intento {attempt}/3 · {url}", flush=True)
        try:
            digest = fingerprint(get(url), url)
        except (OSError, http.client.HTTPException) as exc:
            error = f"{type(exc).__name__}: {exc}"
            errors.append(error)
            print(f"Fuente {source_id}: {error}", flush=True)
            if attempt < 3 and transient(exc):
                time.sleep(2 ** (attempt - 1))
                continue
            return {'id': source_id, 'url': url, 'status': 'failed',
                    'attempts': attempt, 'errors': errors}
        print(f"Fuente {source_id}: OK", flush=True)
        return {'id': source_id, 'url': url, 'status': 'ok',
                'attempts': attempt, 'errors': errors, 'sha256': digest}


def main(report_path=None):
    d = json.loads(DATA.read_text(encoding='utf-8'))
    monitoring = d.get('monitoring', {})
    prior = monitoring.get('source_hashes', {})
    review = bool(monitoring.get('review_required', False))
    hashes = dict(prior)
    sources = [(s['id'], s['url']) for s in d['sources']
               if s['id'] != 'proyecto_control']
    xlsx = d.get('ive_ile', {}).get('xlsx')
    if xlsx:
        sources.append(('idecba_ive_xlsx', xlsx))
    results = [check_source(source_id, url) for source_id, url in sources]
    for result in results:
        if result['status'] == 'ok':
            source_id, digest = result['id'], result['sha256']
            hashes[source_id] = digest
            if prior.get(source_id) and prior[source_id] != digest:
                review = True
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    failed = [r['id'] for r in results if r['status'] == 'failed']
    report = {'attempted_at': now, 'status': 'partial' if failed else 'complete',
              'last_complete_checked_at': monitoring.get('last_checked_at') if failed else now,
              'source_hashes': hashes, 'review_required': review, 'sources': results}
    if report_path:
        Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if failed:
        print(f"Revisión parcial: fallaron {', '.join(failed)}. Se conservan ambos JSON y su última revisión completa.", flush=True)
        return 1
    d['monitoring'] = {**monitoring, 'last_checked_at': now,
                       'source_hashes': hashes, 'review_required': review}
    d['generated_at'] = now
    text = json.dumps(d, ensure_ascii=False, indent=2) + '\n'
    DATA.write_text(text, encoding='utf-8')
    ROOT.write_text(text, encoding='utf-8')
    print(f"salud reproductiva: revisión completa de {len(results)} fuentes; revisión={review}")
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', help='Informe de diagnóstico, también para revisiones parciales')
    raise SystemExit(main(parser.parse_args().report))
