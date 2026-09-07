#!/usr/bin/env python3
import csv, io, json, re, shutil, zipfile
from pathlib import Path
from tableauhyperapi import HyperProcess, Connection, Telemetry

ROOT=Path('ladefe_tableau_inventory')
OUT=[]

for pkg in sorted(ROOT.glob('download_*_workbook_twb.twb')):
    wb_key=pkg.name[len('download_'):-len('_workbook_twb.twb')]
    temp=ROOT/f'hyper_{wb_key}'
    if temp.exists(): shutil.rmtree(temp)
    temp.mkdir(parents=True)
    with zipfile.ZipFile(pkg) as z:
        hyper_names=[n for n in z.namelist() if n.lower().endswith('.hyper')]
        twb_names=[n for n in z.namelist() if n.lower().endswith('.twb')]
        for n in hyper_names+twb_names: z.extract(n,temp)
    hyper_file=next(temp.rglob('*.hyper'))
    item={'workbook':wb_key,'hyper_file':hyper_file.name,'schemas':[],'tables':[]}
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        with Connection(endpoint=hp.endpoint,database=hyper_file) as con:
            schemas=list(con.catalog.get_schema_names())
            item['schemas']=[str(s) for s in schemas]
            for schema in schemas:
                for table in con.catalog.get_table_names(schema):
                    td=con.catalog.get_table_definition(table)
                    cols=[{'name':str(c.name),'type':str(c.type)} for c in td.columns]
                    count=con.execute_scalar_query(f'SELECT COUNT(*) FROM {table}')
                    sample=[]
                    try:
                        result=con.execute_list_query(f'SELECT * FROM {table} LIMIT 10')
                        sample=[[None if v is None else str(v) for v in row] for row in result]
                    except Exception as ex:
                        sample=[['ERROR',repr(ex)]]
                    item['tables'].append({'table':str(table),'row_count':int(count),'columns':cols,'sample':sample})
    OUT.append(item)

(ROOT/'hyper_structure.json').write_text(json.dumps(OUT,ensure_ascii=False,indent=2),encoding='utf-8')

# Flatten table/column inventory for easy review.
with (ROOT/'hyper_columns.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['workbook','table','row_count','ordinal','column','type'])
    for item in OUT:
        for t in item['tables']:
            for i,c in enumerate(t['columns'],1):
                w.writerow([item['workbook'],t['table'],t['row_count'],i,c['name'],c['type']])

for item in OUT:
    print('\nWORKBOOK',item['workbook'])
    print('SCHEMAS',item['schemas'])
    for t in item['tables']:
        print('TABLE',t['table'],'ROWS',t['row_count'])
        print('COLUMNS',[(c['name'],c['type']) for c in t['columns']])
        print('SAMPLE')
        for row in t['sample'][:5]: print(row)
