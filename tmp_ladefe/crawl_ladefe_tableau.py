#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,re,time
from collections import deque
from dataclasses import asdict,dataclass
from pathlib import Path
from urllib.parse import unquote,urljoin,urlparse,urlunparse
import requests
from bs4 import BeautifulSoup
TABLEAU_URL_RE=re.compile(r"https?://[^\"'<>\s]*tableau[^\"'<>\s]*",re.I)
PUBLIC_VIEWS_RE=re.compile(r"https?://public\.tableau\.com/views/[^\"'<>\s]+",re.I)
def canonical_page_url(url):
 p=urlparse(url); path=re.sub(r"/{2,}","/",p.path or "/")
 if not path.endswith("/") and "." not in path.rsplit("/",1)[-1]: path+="/"
 return urlunparse((p.scheme or "https",p.netloc.lower(),path,"","",""))
def clean_tableau_url(url):
 url=unquote(url).replace("\\u002F","/").replace("\\/","/").strip("'\" ")
 p=urlparse(url); return urlunparse((p.scheme,p.netloc,p.path,"",p.query,""))
def parse_workbook_view(url):
 parts=[x for x in urlparse(unquote(url)).path.split("/") if x]
 try:i=parts.index("views")
 except ValueError:return "",""
 return (parts[i+1] if len(parts)>i+1 else "",parts[i+2] if len(parts)>i+2 else "")
@dataclass
class Embed:
 page_url:str; embed_type:str; tableau_url:str; workbook:str; view:str; host_url:str=""; name_param:str=""
@dataclass
class PageRow:
 url:str; status_code:int; title:str; has_viz_v1:bool; tableau_embed_count:int; unresolved_viz_v1:bool; error:str=""
def extract_embeds(page_url,html):
 soup=BeautifulSoup(html,"html.parser"); embeds=[]; seen=set(); has_viz_v1=any("viz_v1.js" in (s.get("src") or "") for s in soup.find_all("script"))
 def add(t,u,host_url="",name_param=""):
  if not u:return
  u=clean_tableau_url(urljoin(page_url,u)); wb,view=parse_workbook_view(u); key=(t,u,wb,view)
  if key in seen:return
  seen.add(key); embeds.append(Embed(page_url,t,u,wb,view,host_url,name_param))
 for obj in soup.find_all("object"):
  classes=" ".join(obj.get("class") or [])
  if "tableau" not in classes.lower() and "tableau" not in str(obj).lower():continue
  params={}
  for p in obj.find_all("param"):
   n=(p.get("name") or "").strip(); v=(p.get("value") or "").strip()
   if n:params[n]=v
  host=unquote(params.get("host_url","")); name=unquote(params.get("name",""))
  if name:
   host=host or "https://public.tableau.com/"; base=host.rstrip("/")
   u=urljoin(base+"/",name.lstrip("/")) if "/views/" in name else f"{base}/views/{name.lstrip('/')}"
   add("v1_object",u,host,name)
 for frame in soup.find_all("iframe"):
  src=frame.get("src") or ""
  if "tableau" in src.lower():add("iframe",src)
 for viz in soup.find_all(["tableau-viz","tableau-authoring-viz"]):
  src=viz.get("src") or ""
  if src:add("v3_element",src)
 raw=html.replace("&amp;","&")
 for m in PUBLIC_VIEWS_RE.findall(raw):add("raw_public_views_url",m)
 for m in TABLEAU_URL_RE.findall(raw):
  if "/views/" in m:add("raw_tableau_url",m)
 return embeds,has_viz_v1
def discover_links(page_url,html,host,prefix):
 soup=BeautifulSoup(html,"html.parser"); out=set()
 for a in soup.find_all("a",href=True):
  href=a.get("href")
  if not href or href.startswith(("mailto:","tel:","javascript:")):continue
  u=canonical_page_url(urljoin(page_url,href)); p=urlparse(u)
  if p.netloc.lower()!=host.lower() or not p.path.startswith(prefix):continue
  if any(p.path.lower().endswith(x) for x in (".pdf",".jpg",".jpeg",".png",".zip",".xlsx",".xls",".csv")):continue
  out.add(u)
 return out
def crawl(start,max_pages,delay,timeout):
 start=canonical_page_url(start); parsed=urlparse(start); host=parsed.netloc; prefix="/monitoreo/"
 s=requests.Session(); s.verify=False; requests.packages.urllib3.disable_warnings(); s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; LADEFE-Tableau-Inventory/1.0)","Accept-Language":"es-AR,es;q=0.9,en;q=0.5"})
 q=deque([start]); queued={start}; visited=set(); pages=[]; embeds=[]
 while q and len(visited)<max_pages:
  u=q.popleft()
  if u in visited:continue
  visited.add(u)
  try:
   r=s.get(u,timeout=timeout,allow_redirects=True); status=r.status_code; final=canonical_page_url(r.url); ctype=r.headers.get("content-type","")
   if status>=400 or "html" not in ctype.lower():pages.append(PageRow(final,status,"",False,0,False,f"HTTP {status}; content-type={ctype}"));continue
   html=r.text; soup=BeautifulSoup(html,"html.parser"); title=soup.title.get_text(" ",strip=True) if soup.title else ""; found,has=extract_embeds(final,html); embeds.extend(found); pages.append(PageRow(final,status,title,has,len(found),has and not found,""))
   for nxt in sorted(discover_links(final,html,host,prefix)):
    if nxt not in visited and nxt not in queued:queued.add(nxt);q.append(nxt)
  except Exception as e:pages.append(PageRow(u,0,"",False,0,False,repr(e)))
  if delay:time.sleep(delay)
 uniq={}
 for e in embeds:uniq[(e.page_url,e.embed_type,e.tableau_url,e.workbook,e.view)]=e
 return pages,list(uniq.values())
def write_outputs(outdir,pages,embeds):
 outdir.mkdir(parents=True,exist_ok=True)
 for filename,items,ann in [("pages.csv",pages,PageRow.__annotations__),("embeds.csv",embeds,Embed.__annotations__)]:
  fields=list(asdict(items[0]).keys()) if items else list(ann.keys())
  with (outdir/filename).open("w",newline="",encoding="utf-8-sig") as f:
   w=csv.DictWriter(f,fieldnames=fields);w.writeheader();[w.writerow(asdict(x)) for x in items]
 wv={}
 for e in embeds:
  key=f"{e.workbook}/{e.view}" if (e.workbook or e.view) else e.tableau_url;wv.setdefault(key,set()).add(e.page_url)
 payload={"summary":{"pages_crawled":len(pages),"pages_with_viz_v1":sum(p.has_viz_v1 for p in pages),"pages_with_embeds":sum(p.tableau_embed_count>0 for p in pages),"unresolved_viz_v1_pages":sum(p.unresolved_viz_v1 for p in pages),"embed_rows":len(embeds),"unique_workbook_views":len(wv)},"unique_workbook_views":[{"workbook_view":k,"pages":sorted(v)} for k,v in sorted(wv.items())],"pages":[asdict(p) for p in pages],"embeds":[asdict(e) for e in embeds]}
 (outdir/"inventory.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(payload["summary"],ensure_ascii=False))
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--start",default="https://ladefe.gob.ar/monitoreo/");ap.add_argument("--max-pages",type=int,default=500);ap.add_argument("--delay",type=float,default=.15);ap.add_argument("--timeout",type=float,default=30);ap.add_argument("--out",default="ladefe_tableau_inventory");a=ap.parse_args();p,e=crawl(a.start,a.max_pages,a.delay,a.timeout);write_outputs(Path(a.out),p,e)
