#!/usr/bin/env python3
"""Comprobación semanal del SUACI dentro del workflow territorial canónico."""
import argparse,datetime,json,subprocess,sys
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--weekly',action='store_true');p.add_argument('--local',action='store_true');p.add_argument('--directory',type=Path,default=ROOT/'_cache/suaci');a=p.parse_args();now=datetime.datetime.now(ZoneInfo('America/Argentina/Buenos_Aires'))
 if a.weekly and now.weekday()!=0:print('SUACI: la comprobación programada corresponde a los lunes');return
 def run(script,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],cwd=ROOT,check=True)
 if not a.local:run('descargar_suaci.py','--directory',a.directory)
 output=ROOT/'deploy/site-overlay/assets/data/limpieza-urbana.json';status=ROOT/'deploy/site-overlay/assets/data/limpieza-urbana-estado.json';page=ROOT/'deploy/site-overlay/territorio/limpieza-urbana/index.html'
 run('test_limpieza_urbana.py');run('generar_limpieza_urbana.py','--directory',a.directory,'--geometry',ROOT/'badata/barrios.geojson','--output',output)
 d=json.loads(output.read_text());state={'checkedAt':now.date().isoformat(),'periodEnd':d['periodEnd'],'source':d['source'],'status':'ok'}
 # Sólo después de descargar, normalizar y validar todo se actualiza la comprobación.
 from render_limpieza_urbana import render
 render(page,d,state);status.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
 print('SUACI: comprobación y controles satisfactorios; corte '+d['periodEnd'])
if __name__=='__main__':main()
