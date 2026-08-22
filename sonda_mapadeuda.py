from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import requests

SITE = "https://mapadeladeuda.ar/"
BASE = "https://datos.mapadeladeuda.ar/"


def get_json(s: requests.Session, path: str):
    r = s.get(BASE + path.lstrip('/'), timeout=60)
    print("GETJSON", path, r.status_code, len(r.content), r.headers.get('content-type'))
    r.raise_for_status()
    return r.json(), r


def main() -> None:
    s = requests.Session()
    s.headers.update({'User-Agent':'CEPOES/1.0 (+https://cepoes.org)'})

    home = s.get(SITE, timeout=30)
    home.raise_for_status()
    js = [urljoin(home.url, x) for x in re.findall(r'src=[\"\']([^\"\']+\.js)[\"\']', home.text, re.I)]
    print('JS', js)
    for url in js:
        r=s.get(url, timeout=60); r.raise_for_status(); text=r.text
        for needle in ['licencia','license','copyright','derechos','Creative Commons','creativecommons','contacto','Centro de Estudios para la Ciudad','Friedrich Ebert','FES','©']:
            poss=[m.start() for m in re.finditer(re.escape(needle), text, re.I)]
            print('LEGAL', needle, len(poss))
            for pos in poss[:8]:
                print(text[max(0,pos-800):pos+1200])

    manifest,_=get_json(s,'manifest.json')
    filters,_=get_json(s,manifest['dimensions']['filters'])
    metrics,_=get_json(s,manifest['dimensions']['metrics'])
    print('FILTERS')
    print(json.dumps(filters,ensure_ascii=False,indent=2)[:30000])
    print('METRICS')
    print(json.dumps(metrics,ensure_ascii=False,indent=2)[:30000])

    for p in manifest['periods']:
        summary,_=get_json(s,p['summary'])
        print('SUMMARY',p['id'])
        print(json.dumps(summary,ensure_ascii=False,indent=2)[:12000])

    for path in ['robots.txt','LICENSE','license','terms','terminos','aviso-legal','privacy','privacidad']:
        url = (BASE if path in {'robots.txt','LICENSE','license'} else SITE) + path
        try:
            r=s.get(url,timeout=30,allow_redirects=True)
            print('LEGALURL',url,r.status_code,r.url,r.headers.get('content-type'),len(r.content))
            if r.status_code==200 and len(r.content)<100000:
                print(r.text[:8000])
        except Exception as e:
            print('LEGALERR',url,repr(e))


if __name__=='__main__':
    main()
