#!/usr/bin/env python3
import csv,json,re
from pathlib import Path
from urllib.parse import urlparse,urlunparse
import requests

ROOT=Path('ladefe_tableau_inventory')
inv=json.loads((ROOT/'inventory.json').read_text(encoding='utf-8'))
embeds=inv.get('embeds',[])
preferred=['1_1Aspectosdemogrficos_Informacincensal','2_1aTasasdepobreza','3_3dMatrculaECNivelSecundario','4_2aNatalidad','5_4aJusticiajuvenilAdolescentesyjvenes']
by_wb={e.get('workbook'):e for e in embeds}
targets=[by_wb[x] for x in preferred if x in by_wb]
rows=[]
headers={'User-Agent':'Mozilla/5.0','Accept':'text/csv,text/plain,*/*'}
for e in targets:
    base=e['tableau_url'].split('?',1)[0]
    csv_url=base+'.csv?:showVizHome=no'
    try:
        r=requests.get(csv_url,headers=headers,timeout=40,allow_redirects=True)
        ctype=r.headers.get('content-type','')
        body=r.content
        safe=re.sub(r'[^A-Za-z0-9._-]+','_',e['workbook'])
        (ROOT/f'probe_{safe}.bin').write_bytes(body[:500000])
        text=''
        try:text=body[:2000].decode('utf-8-sig','replace')
        except Exception:pass
        rows.append({'workbook':e['workbook'],'view':e['view'],'url':csv_url,'status':r.status_code,'content_type':ctype,'bytes':len(body),'looks_csv':(',' in text or ';' in text) and '\n' in text,'sample':text[:500].replace('\r',' ').replace('\n',' | ')})
    except Exception as ex:
        rows.append({'workbook':e['workbook'],'view':e['view'],'url':csv_url,'status':0,'content_type':'','bytes':0,'looks_csv':False,'sample':repr(ex)})
with (ROOT/'tableau_export_probe.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=['workbook','view','url','status','content_type','bytes','looks_csv','sample']);w.writeheader();w.writerows(rows)
print(json.dumps(rows,ensure_ascii=False,indent=2))
