#!/usr/bin/env python3
import csv, json, shutil, zipfile
from collections import defaultdict
from pathlib import Path
from tableauhyperapi import HyperProcess, Connection, Telemetry

ROOT=Path('ladefe_tableau_inventory')
OUT=[]
SEM=[]
GLOBAL=None

def sval(v):
    return None if v is None else str(v)

def table_by_columns(con, schemas, required):
    required=set(required)
    for schema in schemas:
        for table in con.catalog.get_table_names(schema):
            td=con.catalog.get_table_definition(table)
            cols={str(c.name).strip('"') for c in td.columns}
            if required.issubset(cols):
                return table
    return None

def all_rows(con, table):
    return con.execute_list_query(f'SELECT * FROM {table}')

def col_names(con, table):
    td=con.catalog.get_table_definition(table)
    return [str(c.name).strip('"') for c in td.columns]

def dict_rows(con, table):
    names=col_names(con,table)
    return [dict(zip(names,[sval(v) for v in row])) for row in all_rows(con,table)]

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
    semantic={'workbook':wb_key}
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        with Connection(endpoint=hp.endpoint,database=hyper_file) as con:
            schemas=list(con.catalog.get_schema_names())
            item['schemas']=[str(s) for s in schemas]
            for schema in schemas:
                for table in con.catalog.get_table_names(schema):
                    td=con.catalog.get_table_definition(table)
                    cols=[{'name':str(c.name).strip('"'),'type':str(c.type)} for c in td.columns]
                    count=con.execute_scalar_query(f'SELECT COUNT(*) FROM {table}')
                    item['tables'].append({'table':str(table),'row_count':int(count),'columns':cols})

            data_t=table_by_columns(con,schemas,['TABLERO_ID','INDICADOR_ID','ANIO','UNIDAD_GEOGRAFICA_NOMBRE','VALOR'])
            boards_t=table_by_columns(con,schemas,['TABLERO_ID','TABLERO_NOMBRE','TABLERO_FECHA_ULT_CARGA_DATOS'])
            indicators_t=table_by_columns(con,schemas,['INDICADOR_ID','INDICADOR_CODIGO','INDICADOR_NOMBRE','INDICADOR_FORMULA'])
            groups_t=table_by_columns(con,schemas,['GRUPO_INDICADOR_ID','GRUPO_INDICADOR_NOMBRE','GRUPO_INDICADOR_FUENTES'])
            semantic['tables']={'data':str(data_t),'boards':str(boards_t),'indicators':str(indicators_t),'groups':str(groups_t)}

            boards=dict_rows(con,boards_t)
            active=[b for b in boards if b.get('TABLERO_ID') not in (None,'0')]
            board=active[0] if active else boards[0]
            bid=board.get('TABLERO_ID')
            semantic['board']=board

            bid_sql=(bid or '').replace("'","''")
            names=col_names(con,data_t)
            raw=con.execute_list_query(f"SELECT * FROM {data_t} WHERE \"TABLERO_ID\" = '{bid_sql}'")
            data=[dict(zip(names,[sval(v) for v in row])) for row in raw]
            semantic['data_row_count']=len(data)

            ind_ids=sorted({r.get('INDICADOR_ID') for r in data if r.get('INDICADOR_ID') not in (None,'0')})
            grp_ids=sorted({r.get('GRUPO_INDICADOR_ID') for r in data if r.get('GRUPO_INDICADOR_ID') not in (None,'0')})
            years=sorted({r.get('ANIO') for r in data if r.get('ANIO') not in (None,'0')})
            types=sorted({r.get('TIPO_DE_DATO') for r in data if r.get('TIPO_DE_DATO')})
            geos=sorted({r.get('UNIDAD_GEOGRAFICA_NOMBRE') for r in data if r.get('UNIDAD_GEOGRAFICA_NOMBRE')})
            aperturas=sorted({r.get('APERTURA_DESCRIPCION') for r in data if r.get('APERTURA_DESCRIPCION')})
            mod1=sorted({r.get('MODALIDAD_APERTURA_NIVEL_1') for r in data if r.get('MODALIDAD_APERTURA_NIVEL_1')})
            mod2=sorted({r.get('MODALIDAD_APERTURA_NIVEL_2') for r in data if r.get('MODALIDAD_APERTURA_NIVEL_2')})
            semantic['dimensions']={'indicator_count':len(ind_ids),'group_count':len(grp_ids),'years':years,'data_types':types,'geography_count':len(geos),'geographies':geos,'aperture_descriptions':aperturas,'level1_modalities':mod1,'level2_modalities':mod2}

            indicator_rows=dict_rows(con,indicators_t)
            imap={r.get('INDICADOR_ID'):r for r in indicator_rows}
            semantic['indicators']=[imap[i] for i in ind_ids if i in imap]
            group_rows=dict_rows(con,groups_t)
            gmap={r.get('GRUPO_INDICADOR_ID'):r for r in group_rows}
            semantic['groups']=[gmap[i] for i in grp_ids if i in gmap]
            semantic['fact_sample']=data[:20]

            # The first public workbook is also inspected as a possible snapshot of the global SM database.
            if GLOBAL is None:
                all_data=dict_rows(con,data_t)
                buckets=defaultdict(list)
                for r in all_data:
                    tid=r.get('TABLERO_ID')
                    if tid not in (None,'0'):
                        buckets[tid].append(r)
                boards_global=[]
                for tid,rows in sorted(buckets.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 999999):
                    boards_global.append({
                        'TABLERO_ID':tid,
                        'fact_rows':len(rows),
                        'TEMA_IDs':sorted({r.get('TEMA_ID') for r in rows if r.get('TEMA_ID')}),
                        'TEMA_NOMBREs':sorted({r.get('TEMA_NOMBRE') for r in rows if r.get('TEMA_NOMBRE')}),
                        'SECCION_IDs':sorted({r.get('SECCION_ID') for r in rows if r.get('SECCION_ID')}),
                        'SECCION_NOMBREs':sorted({r.get('SECCION_NOMBRE') for r in rows if r.get('SECCION_NOMBRE')}),
                        'group_count':len({r.get('GRUPO_INDICADOR_ID') for r in rows if r.get('GRUPO_INDICADOR_ID') not in (None,'0')}),
                        'indicator_count':len({r.get('INDICADOR_ID') for r in rows if r.get('INDICADOR_ID') not in (None,'0')}),
                        'years':sorted({r.get('ANIO') for r in rows if r.get('ANIO')}),
                        'data_types':sorted({r.get('TIPO_DE_DATO') for r in rows if r.get('TIPO_DE_DATO')}),
                        'geography_count':len({r.get('UNIDAD_GEOGRAFICA_NOMBRE') for r in rows if r.get('UNIDAD_GEOGRAFICA_NOMBRE')})
                    })
                GLOBAL={'source_workbook':wb_key,'total_fact_rows':len(all_data),'distinct_nonzero_tablero_ids':len(boards_global),'boards':boards_global,'global_indicator_catalog_rows':len(indicator_rows),'global_group_catalog_rows':len(group_rows)}
    OUT.append(item)
    SEM.append(semantic)

(ROOT/'hyper_structure.json').write_text(json.dumps(OUT,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'dashboard_semantics.json').write_text(json.dumps(SEM,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'global_model_scan.json').write_text(json.dumps(GLOBAL,ensure_ascii=False,indent=2),encoding='utf-8')

with (ROOT/'hyper_columns.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['workbook','table','row_count','ordinal','column','type'])
    for item in OUT:
        for t in item['tables']:
            for i,c in enumerate(t['columns'],1): w.writerow([item['workbook'],t['table'],t['row_count'],i,c['name'],c['type']])

with (ROOT/'dashboard_indicators.csv').open('w',newline='',encoding='utf-8-sig') as f:
    fields=['workbook','tablero_id','tablero_nombre','ultima_carga','indicator_id','codigo','nombre','unidad','formula','definicion','metodologia']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for s in SEM:
        b=s['board']
        for i in s['indicators']:
            w.writerow({'workbook':s['workbook'],'tablero_id':b.get('TABLERO_ID'),'tablero_nombre':b.get('TABLERO_NOMBRE'),'ultima_carga':b.get('TABLERO_FECHA_ULT_CARGA_DATOS'),'indicator_id':i.get('INDICADOR_ID'),'codigo':i.get('INDICADOR_CODIGO'),'nombre':i.get('INDICADOR_NOMBRE'),'unidad':i.get('INDICADOR_UNIDAD_MEDIDA_NOMBRE'),'formula':i.get('INDICADOR_FORMULA'),'definicion':i.get('INDICADOR_DEFINICION'),'metodologia':i.get('INDICADOR_DESC_METODOLOGICA')})

with (ROOT/'dashboard_groups.csv').open('w',newline='',encoding='utf-8-sig') as f:
    fields=['workbook','tablero_id','grupo_id','codigo','nombre','fuentes','definicion','metodologia']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for s in SEM:
        b=s['board']
        for g in s['groups']:
            w.writerow({'workbook':s['workbook'],'tablero_id':b.get('TABLERO_ID'),'grupo_id':g.get('GRUPO_INDICADOR_ID'),'codigo':g.get('GRUPO_INDICADOR_CODIGO'),'nombre':g.get('GRUPO_INDICADOR_NOMBRE'),'fuentes':g.get('GRUPO_INDICADOR_FUENTES'),'definicion':g.get('GRUPO_INDICADOR_DEFINICION'),'metodologia':g.get('GRUPO_INDICADOR_DESC_METODOLOGICA')})

with (ROOT/'global_board_inventory.csv').open('w',newline='',encoding='utf-8-sig') as f:
    fields=['TABLERO_ID','fact_rows','TEMA_IDs','TEMA_NOMBREs','SECCION_IDs','SECCION_NOMBREs','group_count','indicator_count','years','data_types','geography_count']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for b in GLOBAL['boards']:
        row={k:(' | '.join(v) if isinstance(v,list) else v) for k,v in b.items()}
        w.writerow(row)

print('GLOBAL MODEL',json.dumps({k:v for k,v in GLOBAL.items() if k!='boards'},ensure_ascii=False))
print('DASHBOARD SEMANTICS SUMMARY')
for s in SEM:
    d=s['dimensions']; b=s['board']
    print(json.dumps({'workbook':s['workbook'],'tablero_id':b.get('TABLERO_ID'),'nombre':b.get('TABLERO_NOMBRE'),'ultima_carga':b.get('TABLERO_FECHA_ULT_CARGA_DATOS'),'fact_rows':s['data_row_count'],'indicators':d['indicator_count'],'groups':d['group_count'],'years':d['years'],'data_types':d['data_types'],'geographies':d['geography_count']},ensure_ascii=False))
