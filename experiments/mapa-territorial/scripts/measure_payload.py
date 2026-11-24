#!/usr/bin/env python3
"""Byte-level reproducible estimate, not a browser/network performance measurement."""
import argparse, gzip, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path);args=p.parse_args()
root=Path(__file__).resolve().parents[1]/'public/assets/mapa-territorial'
initial=['app.mjs','engine.mjs','model.mjs','map.css','vendor/maplibre-gl.mjs','vendor/maplibre-gl-worker.mjs','vendor/maplibre-gl.css','data/manifest.json','data/territories.geojson','data/layers/salud.geojson']
rows=[{'path':str(f.relative_to(root)),'bytes':f.stat().st_size,'gzip_bytes':len(gzip.compress(f.read_bytes(),mtime=0))} for f in sorted(root.rglob('*')) if f.is_file()]
byname={x['path']:x for x in rows}
def total(paths):return {key:sum(byname[n][key] for n in paths) for key in ['bytes','gzip_bytes']}
result={'kind':'static_payload_estimate','scope':'Resources owned by experimental map; shared site shell/fonts excluded. Compression assumes gzip, not measured server transfer.','initial_health':total(initial),'deferred_education':total(['data/layers/educacion.geojson']),'deferred_green':total(['data/layers/verdes.geojson']),'runtime':{'map_ready_ms':None,'zoom_fps':None,'filter_latency_ms':None,'browser_memory_bytes':None,'status':'not_measured_by_static_estimator'},'files':rows}
text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
if args.output:args.output.write_text(text)
else:print(text)
