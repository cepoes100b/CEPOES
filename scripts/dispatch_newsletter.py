#!/usr/bin/env python3
"""Invoke the private dispatcher without logging credentials or subscriber data."""
import json,os,urllib.request

def main():
    secret=os.environ.get('NEWSLETTER_DISPATCH_SECRET','')
    if not secret:
        raise SystemExit('Newsletter no activada: falta NEWSLETTER_DISPATCH_SECRET')
    request=urllib.request.Request('https://nriexnijkjamrmfivfmd.supabase.co/functions/v1/newsletter-dispatch',data=b'{}',headers={'Authorization':'Bearer '+secret,'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=300) as response:result=json.load(response)
    except Exception:
        raise SystemExit('No se completó la distribución; revisar el registro privado del servicio')
    print(json.dumps({k:result.get(k) for k in ('ok','accepted','retry','cancelled','review')}))
    if not result.get('ok') or result.get('retry',0) or result.get('review',0):raise SystemExit(1)
if __name__=='__main__':main()
