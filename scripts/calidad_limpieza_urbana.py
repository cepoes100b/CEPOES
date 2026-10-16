"""Controles de continuidad y cambios de etiqueta, sin imputar valores faltantes."""
import calendar,collections,datetime

def quality(monthly,last_dates,months,last_partial,config):
 totals=collections.Counter();kinds=collections.defaultdict(set);years=collections.defaultdict(collections.Counter)
 for (month,name,kind),n in monthly.items():
  totals[(month,name)]+=n;kinds[name].add(kind);years[(name,month[:4])][kind]+=n
 complete=months[:-1] if last_partial else months
 gaps=[]
 for name in sorted(last_dates):
  # Una prestación con actividad sostenida interrumpida por dos meses completos.
  for i in range(3,len(complete)-1):
   before=[totals[(m,name)] for m in complete[i-3:i]]
   if min(before)>0 and sum(before)/3>=50 and totals[(complete[i],name)]==0 and totals[(complete[i+1],name)]==0:
    missing=[]
    for month in months[i:]:
     if totals[(month,name)]:break
     missing.append(month)
    raw=next(k for k,v in config['canonicalPrestations'].items() if v==name)
    gaps.append({'prestacion':name,'topic':config['groups'][raw],'nature':config['natures'][raw],'kinds':sorted(kinds[name]),'lastRecord':last_dates[name],'missingMonths':missing,'firstMissingMonth':missing[0],'reviewed':name in config.get('acknowledgedDiscontinuities',[]),'explanation':'La causa de la interrupción no está documentada en las fuentes consultadas.'})
 changes=[]
 names=sorted(last_dates);all_years=sorted({m[:4] for m in months})
 for name in names:
  for y1,y2 in zip(all_years,all_years[1:]):
   a=years.get((name,y1),{});b=years.get((name,y2),{})
   if not a or not b:continue
   ka=max(a,key=a.get);kb=max(b,key=b.get);na=sum(a.values());nb=sum(b.values())
   if ka!=kb and min(na,nb)>=100 and a[ka]/na>=.7 and b[kb]/nb>=.7:
    raw=next(k for k,v in config['canonicalPrestations'].items() if v==name)
    changes.append({'prestacion':name,'topic':config['groups'][raw],'nature':config['natures'][raw],'fromYear':y1,'fromKind':ka,'fromCount':a[ka],'fromTotal':na,'toYear':y2,'toKind':kb,'toCount':b[kb],'toTotal':nb})
 return {'discontinuities':gaps,'originalTypeChanges':changes,'comparisonPolicy':'Conservar la naturaleza del motivo entre años. Señalar cobertura incompleta y separar meses parciales. La etiqueta original del GCBA se consulta como atributo administrativo.'}
