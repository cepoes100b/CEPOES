#!/usr/bin/env python3
import csv, shutil, zipfile
from pathlib import Path
from tableauhyperapi import HyperProcess, Connection, Telemetry

ROOT=Path('ladefe_tableau_inventory')
rows=[]

def table_by_cols(con, schemas, req):
    req=set(req)
    for s in schemas:
        for t in con.catalog.get_table_names(s):
            td=con.catalog.get_table_definition(t)
            cols={str(c.name).strip('"') for c in td.columns}
            if req.issubset(cols): return t

for pkg in sorted(ROOT.glob('download_*_workbook_twb.twb')):
    wb=pkg.name[len('download_'):-len('_workbook_twb.twb')]
    temp=ROOT/f'snapshot_{wb}'
    if temp.exists(): shutil.rmtree(temp)
    temp.mkdir(parents=True)
    with zipfile.ZipFile(pkg) as z:
        hn=next(n for n in z.namelist() if n.lower().endswith('.hyper'))
        z.extract(hn,temp)
    hf=next(temp.rglob('*.hyper'))
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        with Connection(endpoint=hp.endpoint,database=hf) as con:
            schemas=list(con.catalog.get_schema_names())
            dt=table_by_cols(con,schemas,['TABLERO_ID','INDICADOR_ID','VALOR'])
            it=table_by_cols(con,schemas,['INDICADOR_ID','INDICADOR_CODIGO','INDICADOR_FORMULA'])
            gt=table_by_cols(con,schemas,['GRUPO_INDICADOR_ID','GRUPO_INDICADOR_FUENTES'])
            bt=table_by_cols(con,schemas,['TABLERO_ID','TABLERO_NOMBRE','TABLERO_FECHA_ULT_CARGA_DATOS'])
            total=int(con.execute_scalar_query(f'SELECT COUNT(*) FROM {dt}'))
            boards=int(con.execute_scalar_query(f'SELECT COUNT(DISTINCT "TABLERO_ID") FROM {dt} WHERE "TABLERO_ID" <> \'0\''))
            inds=int(con.execute_scalar_query(f'SELECT COUNT(*) FROM {it}'))
            groups=int(con.execute_scalar_query(f'SELECT COUNT(*) FROM {gt}'))
            active=con.execute_list_query(f'SELECT "TABLERO_ID","TABLERO_NOMBRE","TABLERO_FECHA_ULT_CARGA_DATOS" FROM {bt} WHERE "TABLERO_ID" <> \'0\' LIMIT 1')
            aid,aname,adate=(active[0] if active else (None,None,None))
            rows.append({'workbook':wb,'active_tablero_id':str(aid) if aid is not None else '', 'active_tablero_nombre':str(aname) if aname is not None else '', 'active_last_load':str(adate) if adate is not None else '', 'total_fact_rows':total,'distinct_board_ids':boards,'indicator_catalog_rows':inds,'group_catalog_rows':groups})

with (ROOT/'snapshot_counts.csv').open('w',newline='',encoding='utf-8-sig') as f:
    fields=['workbook','active_tablero_id','active_tablero_nombre','active_last_load','total_fact_rows','distinct_board_ids','indicator_catalog_rows','group_catalog_rows']
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('SNAPSHOT COUNTS')
for r in rows: print(r)
