document.addEventListener('DOMContentLoaded',async()=>{try{
  const C=CEPOES,S=await C.territorySummary();
  const dim=document.getElementById('gap-dimension'),measure=document.getElementById('gap-measure'),comuna=document.getElementById('gap-comuna'),tbody=document.querySelector('#gap-table tbody');
  const pageDate=document.getElementById('data-date');if(pageDate)pageDate.textContent=S?.generado?C.dateLabel(String(S.generado).slice(0,10)):'Fecha no informada';
  if(!S||!S.barrios){document.getElementById('gap-description').textContent='El resumen territorial todavía no está disponible. Probá nuevamente más tarde.';return}
  const params=new URLSearchParams(location.search),highlight=params.get('barrio')||'';
  const order=['educacion','salud','mayores','infancias','cultura','deporte','seguridad','movilidad','servicios','ambiente'];
  const sample=Object.values(S.barrios)[0]?.destacados||{};
  const esc=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  dim.innerHTML=order.filter(id=>sample[id]).map(id=>`<option value="${id}">${esc(sample[id].label||id)}</option>`).join('');
  comuna.innerHTML+=[...Array(15)].map((_,i)=>`<option value="${i+1}">Comuna ${i+1}</option>`).join('');
  const requested=params.get('dimension');if(requested&&[...dim.options].some(o=>o.value===requested))dim.value=requested;
  if(params.get('medida')==='count')measure.value='count';
  if(params.get('comuna')&&Number(params.get('comuna'))>=1&&Number(params.get('comuna'))<=15)comuna.value=params.get('comuna');

  const totalPop=Object.values(S.comunas||{}).reduce((a,x)=>a+(Number(x.poblacion)||0),0);
  function cabaRef(id){const xs=Object.values(S.comunas||{});if(id==='ambiente'){const m2=xs.reduce((a,x)=>a+(Number(x.destacados?.ambiente?.m2)||0),0);return totalPop?m2/totalPop:null}const n=xs.reduce((a,x)=>a+(Number(x.destacados?.[id]?.valor)||0),0);return totalPop?n/totalPop*10000:null}
  function valueFor(b,id){const x=b.destacados?.[id];if(!x)return null;if(measure.value==='count')return Number(x.valor)||0;return id==='ambiente'?Number(x.m2_hab):Number(x.tasa_10k)}
  function format(id,v){if(v==null||!Number.isFinite(v))return 's/d';if(measure.value==='count')return C.n.format(Math.round(v));return id==='ambiente'?C.n1.format(v)+' m²/hab.':C.n1.format(v)+' / 10.000'}
  function median(vals){const x=[...vals].sort((a,b)=>a-b);if(!x.length)return null;const m=Math.floor(x.length/2);return x.length%2?x[m]:(x[m-1]+x[m])/2}
  function quintile(rank,n){const p=n<=1?1:(n-rank)/(n-1);if(p>=.8)return 5;if(p>=.6)return 4;if(p>=.4)return 3;if(p>=.2)return 2;return 1}
  function qlabel(q){return {5:'Alto',4:'Medio-alto',3:'Intermedio',2:'Medio-bajo',1:'Bajo'}[q]}
  function render(){
    const id=dim.value,ref=cabaRef(id),filterC=comuna.value;
    let rows=Object.entries(S.barrios).map(([key,b])=>({key,b,value:valueFor(b,id)})).filter(x=>Number.isFinite(x.value));
    const all=[...rows].sort((a,b)=>b.value-a.value||String(a.b.nombre).localeCompare(String(b.b.nombre),'es'));
    all.forEach((x,i)=>{x.rank=i+1;x.percentile=Math.round((all.length-i)/all.length*100);x.q=quintile(i,all.length)});
    if(filterC)rows=all.filter(x=>String(x.b.comuna)===String(filterC));else rows=all;
    const vals=rows.map(x=>x.value),med=median(vals),hi=rows[0],lo=rows[rows.length-1];
    const stats=document.querySelectorAll('#gap-summary .gap-stat');
    if(stats[0]){stats[0].querySelector('strong').textContent=C.n.format(rows.length);stats[0].querySelector('small').textContent=filterC?`Comuna ${filterC}`:'48 barrios oficiales'}
    if(stats[1])stats[1].querySelector('strong').textContent=format(id,med);
    if(stats[2]){stats[2].querySelector('strong').textContent=hi?format(id,hi.value):'—';stats[2].querySelector('small').textContent=hi?.b.nombre||'—'}
    if(stats[3]){stats[3].querySelector('strong').textContent=lo?format(id,lo.value):'—';stats[3].querySelector('small').textContent=lo?.b.nombre||'—'}
    const meta=sample[id]||{};document.getElementById('gap-title').textContent=meta.label||id;
    document.getElementById('gap-description').textContent=measure.value==='count'?'Cantidad de registros territorializados por barrio. Para comparar disponibilidad relativa entre barrios de distinto tamaño, conviene usar “Por población”.':`${id==='ambiente'?'Superficie verde por habitante':'Registros seleccionados cada 10.000 habitantes'} · referencia CABA: ${format(id,ref)}.`;
    const map=document.getElementById('gap-map-link');map.href=`/territorio/mapa-tematico/?dimension=${encodeURIComponent(id)}&medida=${encodeURIComponent(measure.value)}`;
    tbody.innerHTML=rows.map(x=>{
      const idx=measure.value==='rate'&&ref?x.value/ref*100:null,delta=idx!=null?idx-100:null,selected=highlight&&norm(highlight)===norm(x.b.nombre);
      return `<tr class="gap-q${x.q}${selected?' gap-highlight':''}"${selected?' id="gap-highlight"':''}><td class="num"><b>${x.rank}</b></td><td><a href="/territorio/barrios/${x.key}/"><b>${esc(x.b.nombre)}</b></a></td><td>Comuna ${x.b.comuna}</td><td class="num"><b>${format(id,x.value)}</b></td><td class="num">${idx==null?'—':C.n.format(Math.round(idx))}${idx==null?'':' <small class="gap-delta '+(delta>5?'positive':delta<-5?'negative':'neutral')+'">'+(delta>0?'+':'')+C.n.format(Math.round(delta))+'%</small>'}</td><td class="num">P${x.percentile}</td><td><span class="gap-position q${x.q}">${qlabel(x.q)}</span></td></tr>`
    }).join('');
    const groups=[5,4,3,2,1].map(q=>({q,items:all.filter(x=>x.q===q)}));
    document.getElementById('gap-quintiles').innerHTML=groups.map(g=>`<div class="gap-quintile q${g.q}"><span>${qlabel(g.q)}</span><strong>${g.items.length} barrios</strong><small>${g.items.slice(0,4).map(x=>esc(x.b.nombre)).join(' · ')}${g.items.length>4?'…':''}</small></div>`).join('');
    const p=new URLSearchParams();p.set('dimension',id);p.set('medida',measure.value);if(filterC)p.set('comuna',filterC);if(highlight)p.set('barrio',highlight);history.replaceState(null,'',location.pathname+'?'+p.toString());
    if(highlight){setTimeout(()=>document.getElementById('gap-highlight')?.scrollIntoView({block:'center'}),50)}
  }
  dim.addEventListener('change',render);measure.addEventListener('change',render);comuna.addEventListener('change',render);render();
}catch(e){console.warn('Brechas territoriales:',e);const desc=document.getElementById('gap-description'),dt=document.getElementById('data-date');if(desc)desc.textContent='No se pudieron cargar las brechas territoriales. Probá nuevamente más tarde.';if(dt)dt.textContent='Fecha no informada'}});
