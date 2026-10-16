/* Modelo compartido por el explorador y sus pruebas de comparabilidad. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.LimpiezaUrbanaModel=factory();})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const sum=rows=>rows.reduce((n,r)=>n+r[5],0);
 function months(d,range){const complete=d.lastMonthPartial?d.months.slice(0,-1):d.months;return range==='all'?d.months:range==='current'?d.months.slice(-1):range==='last3'?complete.slice(-3):complete.slice(-12);}
 function applicable(g,f){return (!f.topic||g.topic===f.topic)&&(!f.nature||g.nature===f.nature)&&(!f.kind||!g.kinds||g.kinds.includes(f.kind));}
 function view(d,f){
  const ms=months(d,f.range),msSet=new Set(ms),base=d.counts.filter(r=>msSet.has(r[2])&&(!f.topic||r[3]===f.topic)&&(!f.kind||r[4]===f.kind)&&(!f.nature||r[6]===f.nature));
  const local=r=>(!f.comuna||r[1]===f.comuna)&&(!f.barrio||r[0]===f.barrio),rows=base.filter(local);
  const context=d.counts.filter(r=>msSet.has(r[2])&&(!f.topic||r[3]===f.topic)&&(!f.kind||r[4]===f.kind)&&local(r));
  const gaps=d.quality.discontinuities.filter(g=>applicable(g,f)&&ms.some(m=>g.missingMonths.includes(m)||m===g.lastRecord.slice(0,7)));
  const changes=f.kind?d.quality.originalTypeChanges.filter(g=>applicable(g,f)&&ms.some(m=>m.startsWith(g.fromYear))&&ms.some(m=>m.startsWith(g.toYear))):[];
  const mapTotals=new Map(d.features.map(x=>[x.name,0])),topicTotals=new Map(),natureTotals=new Map(),seriesTotals=new Map(),rankings=new Map();
  for(const r of base)if(mapTotals.has(r[0]))mapTotals.set(r[0],mapTotals.get(r[0])+r[5]);
  for(const r of rows){topicTotals.set(r[3],(topicTotals.get(r[3])||0)+r[5]);seriesTotals.set(r[2],(seriesTotals.get(r[2])||0)+r[5]);const k=r[0]+'|'+r[1];rankings.set(k,(rankings.get(k)||0)+r[5]);}
  for(const r of context)natureTotals.set(r[6],(natureTotals.get(r[6])||0)+r[5]);
  const series=ms.map(m=>({month:m,count:seriesTotals.get(m)||0,gap:gaps.some(g=>g.missingMonths.includes(m)||m===g.lastRecord.slice(0,7)),partial:!!(d.lastMonthPartial&&m===d.months.at(-1))}));
  const total=sum(rows);return {months:ms,rows,total,contextTotal:sum(context),mapTotals,topicTotals,natureTotals,rankings,series,gaps,changes,comparable:!gaps.length&&!changes.length,noCoverage:total===0&&gaps.length>0};
 }
 return {view,months};
});
