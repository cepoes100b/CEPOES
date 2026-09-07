#!/usr/bin/env python3
import json, shutil, zipfile, hashlib
from pathlib import Path
from tableauhyperapi import HyperProcess, Connection, Telemetry

ROOT=Path('ladefe_tableau_inventory')
OUT=[]

def qident(s):
    return '"'+str(s).replace('"','""')+'"'

for pkg in sorted(ROOT.glob('download_*_workbook_twb.twb')):
    wb=pkg.name[len('download_'):-len('_workbook_twb.twb')]
    temp=ROOT/f'master_{wb}'
    if temp.exists(): shutil.rmtree(temp)
    temp.mkdir(parents=True)
    with zipfile.ZipFile(pkg) as z:
        hn=next(n for n in z.namelist() if n.lower().endswith('.hyper'))
        z.extract(hn,temp)
    hf=next(temp.rglob('*.hyper'))
    item={'workbook':wb}
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
      with Connection(endpoint=hp.endpoint,database=hf) as con:
        schemas=list(con.catalog.get_schema_names())
        tables=[]
        for sch in schemas:
          for tn in con.catalog.get_table_names(sch):
            td=con.catalog.get_table_definition(tn)
            cols=[(str(c.name).strip('"'),str(c.type)) for c in td.columns]
            sig=hashlib.sha256(json.dumps(cols,ensure_ascii=False).encode()).hexdigest()[:16]
            tables.append({'table':str(tn),'row_count':int(con.execute_scalar_query(f'SELECT COUNT(*) FROM {tn}')),'schema_signature':sig,'columns':cols})
            names=[c[0] for c in cols]
            if 'TEMA_ID' in names and 'TABLERO_ID' in names and 'INDICADOR_ID' in names and 'VALOR' in names:
              # Core fact table
              item['fact_table']=str(tn)
              item['fact_rows']=tables[-1]['row_count']
              for field,key in [('TEMA_ID','distinct_temas'),('TABLERO_ID','distinct_tableros'),('SECCION_ID','distinct_secciones'),('GRUPO_INDICADOR_ID','distinct_grupos'),('INDICADOR_ID','distinct_indicadores'),('TIPO_DE_DATO','distinct_tipos'),('UNIDAD_GEOGRAFICA_CODIGO','distinct_geos')]:
                if field in names:
                  item[key]=int(con.execute_scalar_query(f'SELECT COUNT(DISTINCT {qident(field)}) FROM {tn}'))
              item['min_anio']=con.execute_scalar_query(f'SELECT MIN("ANIO") FROM {tn} WHERE "ANIO" IS NOT NULL')
              item['max_anio']=con.execute_scalar_query(f'SELECT MAX("ANIO") FROM {tn} WHERE "ANIO" IS NOT NULL')
              item['temas']=con.execute_list_query(f'SELECT DISTINCT "TEMA_ID","TEMA_NOMBRE" FROM {tn} WHERE "TEMA_ID" <> \'0\' ORDER BY 1')
              item['tipos']=con.execute_list_query(f'SELECT "TIPO_DE_DATO", COUNT(*) FROM {tn} GROUP BY 1 ORDER BY 2 DESC')
              item['tablero_counts']=con.execute_list_query(f'SELECT "TABLERO_ID", COUNT(*), COUNT(DISTINCT "INDICADOR_ID") FROM {tn} WHERE "TABLERO_ID" <> \'0\' GROUP BY 1 ORDER BY 1')
            if 'INDICADOR_ID' in names and 'INDICADOR_NOMBRE' in names and 'INDICADOR_FORMULA' in names:
              item['indicator_table']=str(tn)
              item['indicator_rows']=tables[-1]['row_count']
              item['indicator_nonempty_formula']=int(con.execute_scalar_query(f'SELECT COUNT(*) FROM {tn} WHERE "INDICADOR_FORMULA" IS NOT NULL AND TRIM("INDICADOR_FORMULA") <> \'\''))
              item['indicator_examples']=con.execute_list_query(f'SELECT "INDICADOR_ID","INDICADOR_CODIGO","INDICADOR_NOMBRE","INDICADOR_UNIDAD_MEDIDA_NOMBRE","INDICADOR_FORMULA" FROM {tn} WHERE "INDICADOR_ID" <> \'0\' ORDER BY "INDICADOR_ID" LIMIT 20')
            if 'TABLERO_ID' in names and 'TABLERO_NOMBRE' in names and 'TABLERO_FECHA_ULT_CARGA_DATOS' in names:
              item['dashboard_metadata']=con.execute_list_query(f'SELECT * FROM {tn} ORDER BY "TABLERO_ID"')
        item['tables']=tables
    # json-safe string conversion
    def safe(v):
      if isinstance(v,(list,tuple)): return [safe(x) for x in v]
      if isinstance(v,dict): return {k:safe(x) for k,x in v.items()}
      if v is None or isinstance(v,(str,int,float,bool)): return v
      return str(v)
    OUT.append(safe(item))

# Compare exact table schemas across representative workbooks
common={}
if OUT:
  table_sigs=[]
  for item in OUT:
    table_sigs.append({t['table'].split('.')[-1].split('_')[0].strip('"'):t['schema_signature'] for t in item['tables']})
  keys=set.intersection(*(set(x) for x in table_sigs))
  for k in sorted(keys): common[k]={'signatures':[x[k] for x in table_sigs],'all_same':len({x[k] for x in table_sigs})==1}

payload={'representative_workbooks':OUT,'schema_comparison':common}
(ROOT/'master_hyper_analysis.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'workbooks':[{
  'workbook':x['workbook'],'fact_rows':x.get('fact_rows'),'temas':x.get('distinct_temas'),'tableros':x.get('distinct_tableros'),'indicadores_en_fact':x.get('distinct_indicadores'),'indicator_metadata_rows':x.get('indicator_rows'),'formulas':x.get('indicator_nonempty_formula'),'anio':[x.get('min_anio'),x.get('max_anio')]
} for x in OUT], 'schema_comparison':common},ensure_ascii=False,indent=2))
