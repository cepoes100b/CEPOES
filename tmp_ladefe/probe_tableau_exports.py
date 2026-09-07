#!/usr/bin/env python3
import csv,json,re,zipfile,io
from pathlib import Path
import requests

ROOT=Path('ladefe_tableau_inventory')
inv=json.loads((ROOT/'inventory.json').read_text(encoding='utf-8'))
embeds=inv.get('embeds',[])
# One representative workbook per current monitoring axis.
preferred=[
    '1_1Aspectosdemogrficos_Informacincensal',
    '2_1aTasasdepobreza',
    '3_3dMatrculaECNivelSecundario',
    '4_2aNatalidad',
    '5_4aJusticiajuvenilAdolescentesyjvenes',
    '6_1Inversinpblicapresupuestonacional',
    '7_1SaludsexualyreproductivaFecundidadadolescente',
    '8_3aNNyAmigrantes_Losmigrantesenloscensosnacionales',
]
by_wb={e.get('workbook'):e for e in embeds}
targets=[by_wb[x] for x in preferred if x in by_wb]
headers={'User-Agent':'Mozilla/5.0','Accept':'*/*'}
rows=[]

def inspect_body(body,ctype):
    kind='binary'; detail=''
    if body.startswith(b'PK\x03\x04'):
        kind='zip/twbx'
        try:
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                names=z.namelist()
                detail=' | '.join(names[:25])
        except Exception as e: detail=repr(e)
    elif body.lstrip().startswith(b'<?xml') or b'<workbook' in body[:2000]:
        kind='xml/twb'; detail=body[:1000].decode('utf-8','replace').replace('\r',' ').replace('\n',' | ')
    else:
        detail=body[:500].decode('utf-8','replace').replace('\r',' ').replace('\n',' | ')
    return kind,detail

for e in targets:
    wb=e['workbook']
    # The .twb endpoint on Tableau Public returns the downloadable packaged workbook
    # for these public views, including the .hyper extract.
    urls=[
        ('workbook_twb',f'https://public.tableau.com/workbooks/{wb}.twb?showVizHome=no'),
    ]
    for probe,url in urls:
        try:
            r=requests.get(url,headers=headers,timeout=60,allow_redirects=True)
            body=r.content; ctype=r.headers.get('content-type',''); kind,detail=inspect_body(body,ctype)
            safe=re.sub(r'[^A-Za-z0-9._-]+','_',wb)
            ext='.twb'
            if r.status_code==200 and len(body)>0:
                (ROOT/f'download_{safe}_{probe}{ext}').write_bytes(body[:100_000_000])
            rows.append({'workbook':wb,'probe':probe,'url':url,'status':r.status_code,'content_type':ctype,'bytes':len(body),'kind':kind,'final_url':r.url,'detail':detail})
        except Exception as ex:
            rows.append({'workbook':wb,'probe':probe,'url':url,'status':0,'content_type':'','bytes':0,'kind':'error','final_url':'','detail':repr(ex)})

with (ROOT/'tableau_download_probe.csv').open('w',newline='',encoding='utf-8-sig') as f:
    fields=['workbook','probe','url','status','content_type','bytes','kind','final_url','detail']
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print(json.dumps(rows,ensure_ascii=False,indent=2))
