"""Compone la página desde plantilla editorial, datos validados y mapa oficial."""
import argparse,html,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--datos',required=True);p.add_argument('--mapa',required=True);p.add_argument('--plantilla',required=True);p.add_argument('--salida',required=True);args=p.parse_args()
rows=json.loads(Path(args.datos).read_text())['registros']
assert len(rows)==513 and len({r['id'] for r in rows})==513
assert sum(r['pct'] is not None and r['pct']>15 for r in rows)==31,'Revisar narrativa y umbrales del nuevo corte'
fmt=lambda n:'Sin informar' if n is None else f'{n:,.2f}'.replace(',','x').replace('.',',').replace('x','.')
trs=''.join(f'<tr data-id="{r["id"]}" data-search="{html.escape(r["provincia"]+" "+r["departamento"])}" data-pct="{r["pct"] if r["pct"] is not None else ""}"><td>{html.escape(r["provincia"])}</td><th scope="row"><button type="button" data-select="{r["id"]}">{html.escape(r["departamento"])+(' (fila duplicada en fuente)' if r['estado']=='duplicado_en_fuente' else '')}</button></th><td>{fmt(r["extranjera_ha"])}</td><td>{fmt(r["pct"])}{ "%" if r["pct"] is not None else ""}</td></tr>' for r in rows)
options='<option value="">Seleccionar</option>'+''.join(f'<option value="{r["id"]}">{html.escape(r["provincia"])} · {html.escape(r["departamento"])+(' (fila duplicada en fuente)' if r['estado']=='duplicado_en_fuente' else '')}</option>' for r in sorted(rows,key=lambda x:(x['provincia'],x['departamento'])))
svg=Path(args.mapa).read_text();ids=set(re.findall(r'data-id="([^"]+)"',svg));assert all(r['id_georef'] in ids for r in rows),'Cobertura del mapa incompleta'
s=Path(args.plantilla).read_text()
for slot,value in [('TABLE',trs),('OPTIONS',options),('MAP',svg)]:
 assert s.count('{{'+slot+'}}')==1
 s=s.replace('{{'+slot+'}}',value)
Path(args.salida).write_text(s)
