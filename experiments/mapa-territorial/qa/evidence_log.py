#!/usr/bin/env python3
"""Bounded lossless transport of QA files in Actions logs; never publishes a site.

Only safe basenames with JPG/JSON are accepted. No traces, HTML, env, cookies or
network payloads. Logs do not consume artifact storage. SHA256 protects retrieval.
"""
import argparse,base64,hashlib,json,re
from pathlib import Path
MAX_FILE=600_000
MAX_TOTAL=5_000_000
PREFIX='CEPOES_QA_FILE '
def emit(directory):
    if not directory.is_dir():
        print('QA evidence directory was not produced.');return
    files=[]
    for p in sorted(directory.iterdir()):
        if p.is_file() and re.fullmatch(r'[a-zA-Z0-9_-]+\.(?:jpg|json)',p.name):
            data=p.read_bytes()
            if len(data)>MAX_FILE: print('QA evidence omitted above file limit: '+p.name);continue
            files.append((p,data))
    if sum(len(b) for _,b in files)>MAX_TOTAL:raise SystemExit('QA evidence exceeds total transport limit')
    for p,data in files:
        digest=hashlib.sha256(data).hexdigest();encoded=base64.b64encode(data).decode()
        print(PREFIX+json.dumps({'name':p.name,'bytes':len(data),'sha256':digest,'chunks':(len(encoded)+11999)//12000}))
        for i in range(0,len(encoded),12000): print('CEPOES_QA_DATA '+p.name+' '+str(i//12000)+' '+encoded[i:i+12000])
        print('CEPOES_QA_END '+p.name)
def extract(log,destination):
    destination.mkdir(parents=True,exist_ok=True);entries={};chunks={}
    for line in log.read_text(encoding='utf8',errors='replace').splitlines():
        if PREFIX in line:
            meta=json.loads(line.split(PREFIX,1)[1]);name=meta['name']
            if not re.fullmatch(r'[a-zA-Z0-9_-]+\.(?:jpg|json)',name):raise ValueError('Unsafe evidence name')
            if not isinstance(meta['bytes'],int) or not 0<=meta['bytes']<=MAX_FILE or not isinstance(meta['chunks'],int) or not 0<=meta['chunks']<=68:raise ValueError('Invalid evidence bounds')
            entries[name]=meta;chunks[name]={}
        elif 'CEPOES_QA_DATA ' in line:
            name,index,data=line.split('CEPOES_QA_DATA ',1)[1].split(' ',2)
            if name in chunks:chunks[name][int(index)]=data
    total=0
    for name,meta in entries.items():
        if len(chunks[name])!=meta['chunks']:raise ValueError('Missing chunks: '+name)
        data=base64.b64decode(''.join(chunks[name][i] for i in range(meta['chunks'])),validate=True)
        total+=len(data)
        if len(data)!=meta['bytes'] or len(data)>MAX_FILE or total>MAX_TOTAL:raise ValueError('Size mismatch or limit')
        if hashlib.sha256(data).hexdigest()!=meta['sha256']:raise ValueError('Hash mismatch: '+name)
        (destination/name).write_bytes(data);print(name,meta['bytes'],meta['sha256'])
if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('emit');a.add_argument('--directory',type=Path,required=True)
    a=sub.add_parser('extract');a.add_argument('--log',type=Path,required=True);a.add_argument('--destination',type=Path,required=True)
    x=p.parse_args();emit(x.directory) if x.mode=='emit' else extract(x.log,x.destination)
