#!/usr/bin/env python3
import requests
import actualizar_migraciones as a

s=requests.Session()
u=a.find_xlsx(s,a.M01_PAGE)
content=a.get(s,u,binary=True)
rows=a.rows_from_workbook(content)
print('XLSX:',u,'filas:',len(rows))
for i,row in enumerate(rows):
    text=' | '.join('' if v is None else str(v) for v in row)
    if 'Ciudad de Buenos Aires' in text and 'País' in text:
        print('HEADER',i,repr(row))
        for j,r in enumerate(rows[i:min(len(rows),i+100)],start=i):
            print('ROW',j,repr(r))
        break
