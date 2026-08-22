from __future__ import annotations

import json
import requests

BASE = 'https://datos.mapadeladeuda.ar/'
PATHS = [
    'manifest.json',
    'periods/2026-06/slices/barrio_caba/02/default.json',
    'geo/lookup.json',
]


def main() -> None:
    s=requests.Session(); s.headers.update({'User-Agent':'CEPOES/1.0 (+https://cepoes.org)','Origin':'https://cepoes.org'})
    for path in PATHS:
        r=s.get(BASE+path,timeout=60)
        print('GET',path,r.status_code,len(r.content),r.headers.get('content-type'))
        for h in ['access-control-allow-origin','access-control-allow-methods','cache-control','etag','last-modified','content-security-policy']:
            print(' HEADER',h,':',r.headers.get(h))
        r.raise_for_status()
        if path.endswith('default.json'):
            d=r.json(); print('ROWS',len(d.get('rows',[])),'PERIOD',d.get('period'),'LEVEL',d.get('level'),'SCOPE',d.get('scope'))


if __name__=='__main__': main()
