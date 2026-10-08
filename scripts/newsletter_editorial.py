"""Extract email excerpts from the approved bulletin HTML, never synthesize data."""
from html.parser import HTMLParser
import re

class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
    def text(self):
        return re.sub(r'\s+', ' ', ''.join(c if isinstance(c,str) else c.text()+' ' for c in self.children)).strip()
    def find(self, tag=None, cls=None, ident=None):
        result=[]
        for c in self.children:
            if isinstance(c,str): continue
            if (tag is None or c.tag==tag) and (cls is None or cls in c.attrs.get('class','').split()) and (ident is None or c.attrs.get('id')==ident): result.append(c)
            result.extend(c.find(tag,cls,ident))
        return result

class Tree(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True); self.root=Node(); self.stack=[self.root]; self.feed(source)
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs); self.stack[-1].children.append(n)
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'): self.stack.append(n)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag: self.stack=self.stack[:i]; break
    def handle_data(self,data): self.stack[-1].children.append(data)

def editorial(source):
    root=Tree(source).root
    def first(nodes): return nodes[0].text() if nodes else ''
    blocks=[]
    for section in root.find('section',cls='bol-sec'):
        sid=section.attrs.get('id','')
        if sid in ('resumen','informes','propuestas'): continue
        title=first(section.find('h2'))
        paragraphs=[p.text() for p in section.find('p') if len(p.text())>100 and not {'bol-fuentes','bol-sec__dek'}.intersection(p.attrs.get('class','').split()) and not p.find(cls='bol-kpi__src')]
        if title and paragraphs:
            body=paragraphs[0]
            if len(body)>900: raise ValueError('Párrafo editorial demasiado extenso para correo')
            if len(paragraphs)>1 and len(body)+len(paragraphs[1])+1<=900: body+=' '+paragraphs[1]
            blocks.append({'title':title,'body':body, 'source':first(section.find(cls='bol-fuentes'))})
        if len(blocks)==4: break
    kpis=[]
    summaries=root.find('section',ident='resumen')
    for kpi in (summaries[0].find(cls='bol-kpi') if summaries else []):
        desc=kpi.find(cls='bol-kpi__desc'); src=kpi.find(cls='bol-kpi__src')
        label=first(desc); source_text=first(src)
        if source_text: label=label.removesuffix(source_text).strip()
        kpis.append({'value':first(kpi.find(cls='bol-kpi__val')),'label':label,'source':source_text})
    if len(kpis)>3: kpis=[kpis[0],kpis[2],kpis[3]]
    proposals=root.find('section',ident='propuestas')
    agenda=[first(li.find('b')) or first(li.find('h3')) for li in proposals[0].find('li')] if proposals else []
    return {'date':first(root.find(cls='bol-hero__meta')).split(' 8 páginas')[0].split(' páginas')[0][:80],
            'intro':first(root.find(cls='bol-hero__dek')), 'metrics':kpis[:3], 'sections':blocks,'agenda':[x for x in agenda if x][:5]}
