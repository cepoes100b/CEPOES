#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from dataclasses import asdict,dataclass
from pathlib import Path
from urllib.parse import unquote,urljoin,urlparse,urlunparse
import requests
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings()
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36'
PUBLIC_VIEWS_RE=re.compile(r'https?://public\.tableau\.com/views/[^\"\'<>\s]+',re.I)
TABLEAU_URL_RE=re.compile(r'https?://[^\"\'<>\s]*tableau[^\"\'<>\s]*',re.I)

def canon(url):
 p=urlparse(url); path=re.sub(r'/{2,}','/',p.path or '/')
 if not path.endswith('/') and '.' not in path.rsplit('/',1)[-1]: path+='/'
 return urlunparse((p.scheme or 'https',p.netloc.lower(),path,'','',''))

def clean_tableau(url):
 url=unquote(url).replace('\\u002F','/').replace('\\/','/').strip("'\" ")
 p=urlparse(url); return urlunparse((p.scheme,p.netloc,p.path,'',p.query,''))

def wb_view(url):
 parts=[x for x in urlparse(unquote(url)).path.split('/') if x]
 try:i=parts.index('views')
 except ValueError:return '',''
 return (parts[i+1] if len(parts)>i+1 else '',parts[i+2] if len(parts)>i+2 else '')

@dataclass
class Embed:
 page_url:str; embed_type:str; tableau_url:str; workbook:str; view:str; host_url:str=''; name_param:str=''
@dataclass
class Page:
 url:str; status_code:int; title:str; has_viz_v1:bool; tableau_embed_count:int; error:str=''

def extract(page_url,html):
 soup=BeautifulSoup(html,'html.parser'); out=[]; seen=set()
 has_v1=any('viz_v1.js' in (s.get('src') or '') for s in soup.find_all('script'))
 def add(kind,u,host='',name=''):
  if not u:return
  u=clean_tableau(urljoin(page_url,u)); wb,v=wb_view(u); k=(kind,u,wb,v)
  if k in seen:return
  seen.add(k); out.append(Embed(page_url,kind,u,wb,v,host,name))
 for obj in soup.find_all('object'):
  if 'tableau' not in str(obj).lower():continue
  params={(p.get('name') or '').strip():(p.get('value') or '').strip() for p in obj.find_all('param') if (p.get('name') or '').strip()}
  host=unquote(params.get('host_url','')); name=unquote(params.get('name',''))
  if name:
   base=(host or 'https://public.tableau.com/').rstrip('/')
   u=urljoin(base+'/',name.lstrip('/')) if '/views/' in name else f'{base}/views/{name.lstrip("/")}'
   add('v1_object',u,host,name)
 for tag in soup.find_all('iframe'):
  src=tag.get('src') or ''
  if 'tableau' in src.lower():add('iframe',src)
 for tag in soup.find_all(['tableau-viz','tableau-authoring-viz']):
  if tag.get('src'):add('v3_element',tag.get('src'))
 raw=html.replace('&amp;','&')
 for m in PUBLIC_VIEWS_RE.findall(raw):add('raw_public_views_url',m)
 for m in TABLEAU_URL_RE.findall(raw):
  if '/views/' in m:add('raw_tableau_url',m)
 return out,has_v1,soup

def fetch_one(url,host,prefix,timeout):
 try:
  r=requests.get(url,headers={'User-Agent':UA,'Accept-Language':'es-AR,es;q=0.9'},timeout=timeout,allow_redirects=True,verify=False)
  final=canon(r.url); ctype=r.headers.get('content-type','')
  if r.status_code>=400 or 'html' not in ctype.lower():
   return Page(final,r.status_code,'',False,0,f'HTTP {r.status_code}; {ctype}'),[],set()
  embeds,has_v1,soup=extract(final,r.text)
  title=soup.title.get_text(' ',strip=True) if soup.title else ''
  links=set()
  for a in soup.find_all('a',href=True):
   href=a.get('href')
   if not href or href.startswith(('mailto:','tel:','javascript:')):continue
   u=canon(urljoin(final,href)); p=urlparse(u)
   if p.netloc.lower()==host.lower() and p.path.startswith(prefix):links.add(u)
  return Page(final,r.status_code,title,has_v1,len(embeds),''),embeds,links
 except Exception as e:
  return Page(url,0,'',False,0,repr(e)),[],set()

def crawl(start,max_pages,timeout,workers):
 start=canon(start); host=urlparse(start).netloc; prefix='/monitoreo/'
 pending={start}; visited=set(); pages=[]; embeds=[]
 while pending and len(visited)<max_pages:
  batch=list(pending)[:max(1,min(workers*3,max_pages-len(visited)))]; pending.difference_update(batch); visited.update(batch)
  with ThreadPoolExecutor(max_workers=workers) as ex:
   futs={ex.submit(fetch_one,u,host,prefix,timeout):u for u in batch}
   for fut in as_completed(futs):
    p,ee,ll=fut.result(); pages.append(p); embeds.extend(ee)
    for u in ll:
     if u not in visited:pending.add(u)
  print(f'progress pages={len(visited)} pending={len(pending)} embeds={len(embeds)}',flush=True)
 uniq={}
 for e in embeds:uniq[(e.page_url,e.embed_type,e.tableau_url,e.workbook,e.view)]=e
 return pages,list(uniq.values())

def write(outdir,pages,embeds):
 outdir.mkdir(parents=True,exist_ok=True)
 for fn,items,fields in [('pages.csv',pages,list(Page.__annotations__)),('embeds.csv',embeds,list(Embed.__annotations__))]:
  with (outdir/fn).open('w',newline='',encoding='utf-8-sig') as f:
   w=csv.DictWriter(f,fieldnames=fields);w.writeheader();[w.writerow(asdict(x)) for x in items]
 by_wv={}
 for e in embeds:
  k=f'{e.workbook}/{e.view}' if (e.workbook or e.view) else e.tableau_url;by_wv.setdefault(k,set()).add(e.page_url)
 payload={'summary':{'pages_crawled':len(pages),'http_ok':sum(p.status_code==200 for p in pages),'pages_with_viz_v1':sum(p.has_viz_v1 for p in pages),'pages_with_embeds':sum(p.tableau_embed_count>0 for p in pages),'embed_rows':len(embeds),'unique_workbook_views':len(by_wv),'pages_with_errors':sum(bool(p.error) for p in pages)},'unique_workbook_views':[{'workbook_view':k,'pages':sorted(v)} for k,v in sorted(by_wv.items())],'pages':[asdict(p) for p in pages],'embeds':[asdict(e) for e in embeds]}
 (outdir/'inventory.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY',json.dumps(payload['summary'],ensure_ascii=False),flush=True)
 for x in payload['unique_workbook_views']:print('VIEW',x['workbook_view'],'PAGES',len(x['pages']),flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--start',default='https://ladefe.gob.ar/monitoreo/');ap.add_argument('--max-pages',type=int,default=250);ap.add_argument('--timeout',type=float,default=8);ap.add_argument('--workers',type=int,default=16);ap.add_argument('--out',default='ladefe_tableau_inventory');a=ap.parse_args();p,e=crawl(a.start,a.max_pages,a.timeout,a.workers);write(Path(a.out),p,e)
